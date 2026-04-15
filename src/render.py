"""Provider-agnostic renderers — index (table), full (preview box), JSON.

Takes a list of Session objects. Provider identity shown via [cc]/[codex]
badge column with ANSI color (suppressed when NO_COLOR env set).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict

from session import Session
from utils import (
    display_width,
    fmt_duration,
    fmt_tokens,
    fmt_ts,
    pad_display,
    parse_iso,
    trim,
    trim_display,
    volume_marker,
)


ANSI_RESET = "\x1b[0m"
ANSI_DIM = "\x1b[2m"


def _no_color() -> bool:
    return os.environ.get("NO_COLOR") not in (None, "")


def _badge(source: str, ansi: str) -> str:
    """Fixed-width badge like '[cc]   ' or '[codex]'. Padded to 7 visible cols."""
    text = f"[{'cc' if source == 'claude-code' else source}]"
    padded = pad_display(text, 7)
    if _no_color():
        return padded
    return f"{ansi}{padded}{ANSI_RESET}"


# Map source → badge ansi. Kept here so renderer doesn't import Provider classes.
BADGE_ANSI = {
    "claude-code": "\x1b[32m",  # green
    "codex": "\x1b[36m",        # cyan
}


FIRST_PROMPT_WIDTH = 78
AUX_WIDTH = 46


def _project_label(s: Session) -> str:
    """Short project identifier for the table column.

    claude-code sessions encode project in the parent dir; codex sessions have cwd.
    """
    if s.source == "claude-code":
        # encoded dir like -Users-jintaesong-Desktop-Home-foo → foo
        encoded = os.path.basename(os.path.dirname(s.path))
        from utils import _is_wide_char  # noqa
        d = encoded.lstrip("-")
        for prefix in (
            "Users-jintaesong-Desktop-Home-",
            "Users-jintaesong-Desktop-",
            "Users-jintaesong-Library-Mobile-Documents-iCloud-md-obsidian-Documents-",
            "Users-jintaesong-",
        ):
            if d.startswith(prefix):
                d = d[len(prefix):]
                break
        return d or "(unknown)"
    # codex: take last path component of cwd
    if s.cwd:
        return os.path.basename(s.cwd.rstrip("/")) or "(root)"
    return "(unknown)"


def _fmt_last_short(ts: str | None) -> str:
    """'MM-DD HH:MM:SS' form used in the index table."""
    formatted = fmt_ts(ts, include_year=False)
    return formatted if formatted != "?" else "?"


def render_index(sessions: list[Session]) -> str:
    """Compact one-line-per-session table with [cc]/[codex] badge."""
    if not sessions:
        return "(no sessions)"
    out: list[str] = []
    out.append(
        f"{'last_activity':<17} {'src':<7} {'project':<25} "
        f"{'mk':<3} {'tokens':>9}  {'first prompt'}"
    )
    out.append("─" * 140)
    for s in sessions:
        last = pad_display(_fmt_last_short(s.last_ts), 17)
        badge = _badge(s.source, BADGE_ANSI.get(s.source, ""))
        proj = pad_display(trim_display(_project_label(s), 25), 25)
        msgs = s.asst_count + (len(s.prompts) if s.prompts else 0)
        markers = f"{volume_marker(msgs)}  "
        tok_total = s.tokens.input if s.tokens else 0
        tok_col = f"{fmt_tokens(tok_total):>9}"
        first = trim_display(s.first_prompt or "", FIRST_PROMPT_WIDTH)
        first_padded = pad_display(first, FIRST_PROMPT_WIDTH)
        aux = trim_display(s.title or s.subtitle or "", AUX_WIDTH) if (s.title or s.subtitle) else ""
        label = f"{first_padded}  {aux}" if aux else first_padded
        out.append(f"{last} {badge} {proj} {markers} {tok_col}  {label}")
    return "\n".join(out)


def render_full_box(s: Session) -> str:
    """Single-session detail box (used as fzf preview)."""
    width = 72
    bar = "─" * width
    lines = [f"┌{bar}"]
    lines.append(f"│ source:         [{s.source}]")
    lines.append(f"│ 📁 project:     {_project_label(s)}")
    lines.append(f"│ session id:     {s.session_id}")
    lines.append(f"│ started:        {fmt_ts(s.first_ts)}")
    lines.append(f"│ last activity:  {fmt_ts(s.last_ts)}")
    lines.append(f"│ duration:       {fmt_duration(s.first_ts, s.last_ts)}")
    lines.append(f"│ cwd:            {s.cwd or '(none)'}")
    lines.append(f"│ prompts:        {len(s.prompts)} user / {s.asst_count} assistant")
    if s.title:
        lines.append(f"│ title:          {s.title}")
    if s.subtitle:
        lines.append(f"│ context:        {s.subtitle}")
    if s.tokens and s.tokens.turns > 0:
        total_in = s.tokens.input
        cache_hit = round(s.tokens.cache_read / total_in * 100) if total_in > 0 else 0
        avg_in = total_in // s.tokens.turns if s.tokens.turns else 0
        lines.append(f"│ ── tokens ──")
        lines.append(f"│ input:          {total_in:>10,}    (cache hit {cache_hit}%)")
        lines.append(f"│ output:         {s.tokens.output:>10,}")
        lines.append(
            f"│ cache:          {fmt_tokens(s.tokens.cache_read)} read / "
            f"{fmt_tokens(s.tokens.cache_create)} created"
        )
        lines.append(f"│ avg input/turn: {avg_in:>10,}")
    lines.append(f"├{bar}")
    lines.append("│ opening prompts")
    opening_slice = s.prompts[:3]
    for i, (_ts, text) in enumerate(opening_slice, 1):
        lines.append(f"│  [{i}] {trim(text, 350)}")
    opening_ids = {id(p) for p in opening_slice}
    last_two = [p for p in s.prompts[-2:] if id(p) not in opening_ids]
    if last_two:
        lines.append("│")
        lines.append("│ last prompts")
        for i, (_ts, text) in enumerate(last_two, 1):
            lines.append(f"│  [{i}] {trim(text, 350)}")
    lines.append(f"└{bar}")
    return "\n".join(lines)


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
