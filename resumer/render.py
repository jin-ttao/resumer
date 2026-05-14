"""Provider-agnostic renderers — index (table), full (preview box), JSON.

List rows use a `● source` badge (dot is colored, body is default) and a fixed
column layout shared with the fzf picker via `COL_*` constants and `header_line()`.
The detail box is a 2-column ASCII layout — left pane key:value metadata,
right pane opening/last prompts.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict

from resumer.session import Session
from resumer.utils import (
    display_width,
    fmt_duration,
    fmt_tokens,
    fmt_ts,
    pad_display,
    trim,
    trim_display,
    wrap_display,
)


ANSI_RESET = "\x1b[0m"

# Column widths — single source of truth. `header_line()` and `_row_cells()`
# both consume these so changing one place keeps header/row alignment.
COL_TIME = 19      # `YYYY-MM-DD HH:MM:SS`
COL_SOURCE = 8     # `claude` (6) / `codex` (5) plus trailing pad
COL_PROJECT = 16
COL_TOKENS = 7
COL_SUMMARY = 48
COL_TITLE = 30

# Per-source color applied to the source word itself. Earlier revisions
# prefixed a `●` bullet but its display width is Ambiguous in Unicode East
# Asian Width — fzf's wcwidth measured it narrow while our padding assumed
# wide, throwing every downstream column 1 col out of alignment. With the
# bullet gone, the SOURCE cell is pure ASCII and widths match everywhere.
BADGE_DOT_ANSI = {
    "claude-code": "\x1b[32m",  # green
    "codex": "\x1b[36m",        # cyan
}

# Accent for section labels in the detail box ("opening prompts" / "last prompts").
# 256-color pink (xterm 168) — readable on both dark and light themes.
ACCENT_PINK_ANSI = "\x1b[38;5;168m"

# Kept for backwards compatibility with picker.py imports (now unused there).
BADGE_ANSI = BADGE_DOT_ANSI


def _no_color() -> bool:
    return os.environ.get("NO_COLOR") not in (None, "")


def _source_short(source: str) -> str:
    """`claude-code` → `claude`. Other sources pass through unchanged."""
    return "claude" if source == "claude-code" else source


def _badge(source: str, ansi: str = "") -> str:
    """Colored source label (`claude` / `codex`), padded to COL_SOURCE.

    Color wraps the word — trailing padding stays default-colored so the
    selection bar doesn't pick up a phantom colored tail. `ansi` arg kept
    for backwards-compat; color is looked up from BADGE_DOT_ANSI now.
    """
    name = _source_short(source)
    padded = pad_display(name, COL_SOURCE)
    if _no_color():
        return padded
    color = BADGE_DOT_ANSI.get(source, "")
    if not color:
        return padded
    return padded.replace(name, f"{color}{name}{ANSI_RESET}", 1)


def _accent(s: str) -> str:
    if _no_color():
        return s
    return f"{ACCENT_PINK_ANSI}{s}{ANSI_RESET}"


def _fmt_last_short(ts: str | None) -> str:
    """Full `YYYY-MM-DD HH:MM:SS`. (Name kept for picker.py compatibility.)"""
    return fmt_ts(ts, include_year=True)


def _row_cells(s: Session) -> tuple[str, str, str, str, str, str]:
    """Six visible columns for one session row.

    Cells are already padded/trimmed to column widths so `render_index` and
    `picker._build_fzf_line` can join them with single-space separators.
    """
    time_cell = pad_display(_fmt_last_short(s.last_ts), COL_TIME)
    src_cell = _badge(s.source)
    proj_cell = pad_display(trim_display(s.project_label, COL_PROJECT), COL_PROJECT)
    tok_total = s.tokens.input if s.tokens else 0
    tok_cell = f"{fmt_tokens(tok_total):>{COL_TOKENS}}"
    summary_cell = pad_display(trim_display(s.first_prompt or "", COL_SUMMARY), COL_SUMMARY)
    title_cell = trim_display(s.title or s.subtitle or "", COL_TITLE)
    return time_cell, src_cell, proj_cell, tok_cell, summary_cell, title_cell


def header_line() -> str:
    """Column header line — same widths as `_row_cells`."""
    return (
        pad_display("TIME (LOCAL)", COL_TIME)
        + " " + pad_display("SOURCE", COL_SOURCE)
        + " " + pad_display("PROJECT", COL_PROJECT)
        + " " + f"{'TOKENS':>{COL_TOKENS}}"
        + " " + pad_display("SUMMARY", COL_SUMMARY)
        + " " + "TITLE"
    )


def render_index(sessions: list[Session]) -> str:
    """Compact one-line-per-session table."""
    if not sessions:
        return "(no sessions)"
    head = header_line()
    out: list[str] = [head, "─" * display_width(head)]
    for s in sessions:
        out.append(" ".join(_row_cells(s)))
    return "\n".join(out)


# Detail box geometry. fzf preview window wraps if narrower; at ~114 cols
# total (52 + 2 + 60) we fit on standard 120-col terminals. Wider terminals
# get extra slack from --preview-window=wrap.
DETAIL_LEFT_W = 52
DETAIL_RIGHT_W = 60
DETAIL_SEP = "  "


def _detail_meta_lines(s: Session) -> list[str]:
    """Left-pane lines (key:value metadata), padded to DETAIL_LEFT_W."""
    KEY_W = 14
    VAL_W = DETAIL_LEFT_W - KEY_W - 2  # 2 for ": "

    def kv(key: str, value: str) -> str:
        return pad_display(f"{key:<{KEY_W}}: {trim_display(value, VAL_W)}", DETAIL_LEFT_W)

    out: list[str] = []
    out.append(kv("source", _source_short(s.source)))
    out.append(kv("project", s.project_label))
    out.append(kv("session id", s.session_id))
    out.append(kv("started", fmt_ts(s.first_ts)))
    out.append(kv("last activity", fmt_ts(s.last_ts)))
    out.append(kv("duration", fmt_duration(s.first_ts, s.last_ts)))
    out.append(kv("cwd", s.cwd or "(none)"))
    out.append(kv("prompts", f"{len(s.prompts)} user / {s.asst_count} assistant"))
    if s.title:
        out.append(kv("title", s.title))
    if s.subtitle:
        out.append(kv("context", s.subtitle))
    if s.tokens and s.tokens.turns > 0:
        total_in = s.tokens.input
        cache_hit_pct = (s.tokens.cache_read / total_in * 100) if total_in > 0 else 0
        avg_in = total_in // s.tokens.turns if s.tokens.turns else 0
        # Spacer line between meta block and tokens block — quieter than a
        # dash rule on the left, matches the breathing room in the target.
        out.append(" " * DETAIL_LEFT_W)
        out.append(kv("tokens", ""))
        out.append(kv("  input", f"{total_in:>10,} (hit {cache_hit_pct:.1f}%)"))
        out.append(kv("  output", f"{s.tokens.output:>10,}"))
        out.append(kv("  total", f"{total_in + s.tokens.output:>10,}"))
        out.append(kv("  avg input/turn", f"{avg_in:>10,}"))
    return out


def _section_header(label: str) -> str:
    """`opening prompts ────────` style — label + trailing dash rule.

    Total visible width is DETAIL_RIGHT_W. The label is accent-colored
    (pink) unless NO_COLOR is set. Dash rule is plain so the eye reads
    the label first, then the divider.
    """
    rule_len = DETAIL_RIGHT_W - display_width(label) - 1  # 1 for the space
    if rule_len < 3:
        rule_len = 3
    return f"{_accent(label)} {'─' * rule_len}"


def _detail_prompt_lines(s: Session) -> list[str]:
    """Right-pane lines (opening + last prompts). Wrapped to DETAIL_RIGHT_W.

    May embed ANSI color escapes on the section headers — callers must not
    pad these lines (display_width can't see escapes). Right pane is the
    last column on each row, so no padding needed.
    """
    out: list[str] = []
    out.append(_section_header("opening prompts"))
    out.append("")
    opening_slice = s.prompts[:5]
    for i, (_ts, text) in enumerate(opening_slice, 1):
        body = f"[{i}] {trim(text, 400)}"
        out.extend(wrap_display(body, DETAIL_RIGHT_W))

    opening_ids = {id(p) for p in opening_slice}
    last_two = [p for p in s.prompts[-5:] if id(p) not in opening_ids][-5:]
    if last_two:
        out.append("")
        out.append(_section_header("last prompts"))
        out.append("")
        for i, (_ts, text) in enumerate(last_two, 1):
            body = f"[{i}] {trim(text, 400)}"
            out.extend(wrap_display(body, DETAIL_RIGHT_W))
    return out


def render_full_box(s: Session) -> str:
    """Single-session 2-column detail (used as fzf preview)."""
    left = _detail_meta_lines(s)
    right = _detail_prompt_lines(s)
    n = max(len(left), len(right))
    while len(left) < n:
        left.append(" " * DETAIL_LEFT_W)
    while len(right) < n:
        right.append("")
    return "\n".join(L + DETAIL_SEP + R for L, R in zip(left, right))


def render_json(sessions: list[Session]) -> str:
    """JSON array — common fields only (superset of cc-recent for drift test)."""
    out = []
    for s in sessions:
        d = {
            "source": s.source,
            "session_id": s.session_id,
            "path": s.path,
            "cwd": s.cwd,
            "first_ts": s.first_ts,
            "last_ts": s.last_ts,
            "title": s.title,
            "subtitle": s.subtitle,
            "first_prompt": s.first_prompt,
            "last_prompt": s.last_prompt,
            "asst_count": s.asst_count,
            "prompts": [{"ts": ts, "text": txt} for (ts, txt) in s.prompts],
            "resume_argv": s.resume_argv,
        }
        if s.tokens:
            d["tokens"] = asdict(s.tokens)
        out.append(d)
    return json.dumps(out, ensure_ascii=False, indent=2)
