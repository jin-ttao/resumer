"""fzf-based interactive session picker.

Given a list of Session objects, render as a fzf-driven table with preview
and let the user select one. Returns the selected Session or None (cancel).
Separate from the dispatch layer so exec decisions live in bin/resumer.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

from render import (
    BADGE_ANSI,
    _badge,
    _fmt_last_short,
    _project_label,
    render_full_box,
)
from session import Session
from utils import fmt_tokens, pad_display, trim_display, volume_marker


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
    proj = pad_display(trim_display(_project_label(s), 22), 22)
    msgs = s.asst_count + len(s.prompts)
    markers = pad_display(volume_marker(msgs), 2)
    tok_total = s.tokens.input if s.tokens else 0
    tok_col = f"{fmt_tokens(tok_total):>9}"
    first = pad_display(trim_display(s.first_prompt or "", FIRST_PROMPT_WIDTH), FIRST_PROMPT_WIDTH)
    aux = trim_display(s.title or s.subtitle or "", AUX_WIDTH) if (s.title or s.subtitle) else ""
    label = f"{first}  {aux}" if aux else first
    # Hidden trailing fields (source, session_id, cwd) used by --preview-for and exec.
    return "\t".join([last, badge, proj, markers, tok_col, label, s.source, s.session_id, s.cwd or ""])


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
            with open(os.path.join(preview_dir, f"{s.source}-{s.session_id}.txt"), "w") as f:
                f.write(render_full_box(s))

        fzf_input = "\n".join(_build_fzf_line(s) for s in sessions)

        script_path = os.path.abspath(sys.argv[0])
        preview_cmd = (
            f"{script_path!r} --preview-for {preview_dir!r} {{7}} {{8}}"
        )
        fzf_args = [
            "fzf",
            "--ansi",
            "--delimiter=\t",
            "--with-nth=1,2,3,4,5,6",  # hide source(7), sid(8), cwd(9)
            "--preview", preview_cmd,
            "--preview-window=down:65%:wrap:border-top",
            "--header=↑↓ browse · [cc]/[codex] source · ·/●/◉=volume · Enter=resume · Esc=cancel",
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
    path = os.path.join(preview_dir, f"{source}-{session_id}.txt")
    try:
        with open(path, "r") as f:
            sys.stdout.write(f.read())
        return 0
    except FileNotFoundError:
        print(f"(preview not found: {source}-{session_id})", file=sys.stderr)
        return 1
