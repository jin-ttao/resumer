"""fzf-based interactive session picker.

Given a list of Session objects, render as a fzf-driven table with preview
and let the user select one. Returns the selected Session or None (cancel).
Separate from the dispatch layer so exec decisions live in bin/resumer.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

# Safe session id shape: alphanumerics, dashes, underscores. Providers emit
# UUIDs (hex + dashes), so this is strict enough to reject any attempt to
# sneak `/` or `..` into preview file paths.
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_SAFE_SOURCE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _safe_preview_path(preview_dir: str, source: str, session_id: str) -> str | None:
    """Return the preview file path only if both source and session_id are
    safe identifiers. Returns None otherwise so callers can skip the write/read
    instead of constructing a path that could escape preview_dir."""
    if not _SAFE_ID_RE.match(session_id or ""):
        return None
    if not _SAFE_SOURCE_RE.match(source or ""):
        return None
    return os.path.join(preview_dir, f"{source}-{session_id}.txt")

from resumer.render import _no_color, _row_cells, header_line, render_full_box
from resumer.session import Session


def _sanitize_cell(s: str) -> str:
    """Strip characters that would break tab-delimited row parsing."""
    return s.replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _resolve_script_path() -> str:
    """Best-effort absolute path to the running resumer entry point.

    fzf --preview invokes this script in a child shell with re-parsed sys.argv[0].
    If launched via PATH as "resumer", argv[0] may just be the basename; use
    shutil.which as a fallback and fall through to a best-effort absolute path.
    """
    argv0 = sys.argv[0]
    if os.path.sep in argv0:
        return os.path.realpath(argv0)
    found = shutil.which(argv0)
    if found:
        return os.path.realpath(found)
    return os.path.realpath(argv0)


def _require_fzf() -> bool:
    if shutil.which("fzf") is None:
        print("error: fzf not found. install with: brew install fzf", file=sys.stderr)
        return False
    return True


def _build_fzf_line(s: Session) -> str:
    """Tab-separated columns: time | badge | project | tokens | summary | title || source | sid | cwd

    First 6 are visible (shared with `render.render_index` via `_row_cells`),
    last 3 are hidden via `--with-nth` and used by `--preview-for` + resume exec.
    """
    cells = _row_cells(s)
    hidden = (s.source, s.session_id, s.cwd or "")
    return "\t".join(_sanitize_cell(c) for c in (*cells, *hidden))


def pick(sessions: list[Session]) -> Session | None:
    """Show fzf picker. Returns selected Session or None on cancel/no-match."""
    if not sessions:
        print("No sessions found. Try --days 7 or --all.", file=sys.stderr)
        return None
    if not _require_fzf():
        return None

    preview_dir = tempfile.mkdtemp(prefix="resumer-")
    try:
        # Pre-render preview boxes, keyed by source+session_id to avoid collisions.
        index: dict[tuple[str, str], Session] = {}
        for s in sessions:
            key = (s.source, s.session_id)
            index[key] = s
            out_path = _safe_preview_path(preview_dir, s.source, s.session_id)
            if out_path is None:
                # Session id/source failed safe-identifier check — skip preview
                # generation rather than risk path traversal. Picker still lists
                # the row (preview will show "not found" if user focuses it).
                print(
                    f"resumer: skipping preview for unsafe session id "
                    f"({s.source}:{s.session_id!r})",
                    file=sys.stderr,
                )
                continue
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(render_full_box(s))

        fzf_input = "\n".join(_build_fzf_line(s) for s in sessions)

        script_path = _resolve_script_path()
        preview_cmd = (
            f"{shlex.quote(script_path)} --preview-for "
            f"{shlex.quote(preview_dir)} {{7}} {{8}}"
        )
        # Header is 2 lines: column titles + lowercase keybind footer.
        # Selected-row colors approximate a wine/pink bar (xterm 88 bg, white fg).
        header_text = f"{header_line()}\n↑/↓ navigate · enter select · esc cancel"
        fzf_args = [
            "fzf",
            "--ansi",
            "--delimiter=\t",
            "--with-nth=1,2,3,4,5,6",  # hide source(7), sid(8), cwd(9)
            "--preview", preview_cmd,
            "--preview-window=down:60%:wrap:border-top",
            "--header", header_text,
            "--header-first",
            "--layout=reverse",
            "--bind", "ctrl-s:toggle-sort",
            "--prompt", "  ",
            "--pointer", "▌",
            "--height=95%",
            "--border", "rounded",
            "--info=inline-right",
        ]
        # Honor NO_COLOR for fzf chrome too — picker palette is what makes
        # the picker look "themed", so it has to drop with the rest of the
        # accents when the user opts out.
        if not _no_color():
            fzf_args += [
                "--color",
                "bg+:#5e1530,fg+:#ffffff,hl+:#ffffff,"
                "hl:#d36b8b,pointer:#d36b8b,"
                "header:#d36b8b,prompt:#d36b8b,"
                "info:#888888,border:#444444",
            ]

        try:
            proc = subprocess.run(fzf_args, input=fzf_input, text=True, capture_output=True)
        except KeyboardInterrupt:
            return None

        if proc.returncode == 130 or not proc.stdout.strip():
            return None
        if proc.returncode not in (0, 1):
            print(f"fzf error: {proc.stderr}", file=sys.stderr)
            return None

        selected = proc.stdout.strip().split("\n")[0]
        fields = selected.split("\t")
        if len(fields) < 9:
            print(f"error: unexpected fzf row shape: {selected!r}", file=sys.stderr)
            return None
        source = fields[6]
        sid = fields[7]
        return index.get((source, sid))
    finally:
        shutil.rmtree(preview_dir, ignore_errors=True)


def preview_for(preview_dir: str, source: str, session_id: str) -> int:
    """Internal: print pre-rendered preview file."""
    path = _safe_preview_path(preview_dir, source, session_id)
    if path is None:
        print(f"(preview rejected: unsafe id {source}:{session_id!r})", file=sys.stderr)
        return 1
    try:
        with open(path, "r", encoding="utf-8") as f:
            sys.stdout.write(f.read())
        return 0
    except FileNotFoundError:
        print(f"(preview not found: {source}-{session_id})", file=sys.stderr)
        return 1
