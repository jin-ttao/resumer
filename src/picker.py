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

from render import (
    BADGE_ANSI,
    _badge,
    _fmt_last_short,
    render_full_box,
)
from session import Session
from utils import fmt_tokens, pad_display, trim_display, volume_marker


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


FIRST_PROMPT_WIDTH = 78
AUX_WIDTH = 40


def _require_fzf() -> bool:
    if shutil.which("fzf") is None:
        print("error: fzf not found. install with: brew install fzf", file=sys.stderr)
        return False
    return True


def _build_fzf_line(s: Session) -> str:
    """Tab-separated columns: last | badge | project | markers | tok | label || source | sid | cwd"""
    last = pad_display(_fmt_last_short(s.last_ts), 15)
    badge = _badge(s.source, BADGE_ANSI.get(s.source, ""))
    proj = pad_display(trim_display(s.project_label, 22), 22)
    msgs = s.asst_count + len(s.prompts)
    markers = pad_display(volume_marker(msgs), 2)
    tok_total = s.tokens.input if s.tokens else 0
    tok_col = f"{fmt_tokens(tok_total):>9}"
    first = pad_display(trim_display(s.first_prompt or "", FIRST_PROMPT_WIDTH), FIRST_PROMPT_WIDTH)
    aux = trim_display(s.title or s.subtitle or "", AUX_WIDTH) if (s.title or s.subtitle) else ""
    label = f"{first}  {aux}" if aux else first
    # Hidden trailing fields (source, session_id, cwd) used by --preview-for and exec.
    cells = [last, badge, proj, markers, tok_col, label, s.source, s.session_id, s.cwd or ""]
    return "\t".join(_sanitize_cell(c) for c in cells)


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
        fzf_args = [
            "fzf",
            "--ansi",
            "--delimiter=\t",
            "--with-nth=1,2,3,4,5,6",  # hide source(7), sid(8), cwd(9)
            "--preview", preview_cmd,
            "--preview-window=down:65%:wrap:border-top",
            "--header=↑↓ browse · Ctrl-S=toggle sort · Enter=resume · Esc=cancel",
            "--bind", "ctrl-s:toggle-sort",
            "--prompt=session> ",
            "--height=95%",
            "--border",
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
