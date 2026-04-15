"""Shared formatters (CJK-aware, stdlib only).

Ported from bin/cc-recent's display helpers. Provider-agnostic.
"""
from __future__ import annotations

from datetime import datetime


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def fmt_tokens(n: int) -> str:
    """285120→'285K', 10014000→'10,014K', 0→'—'."""
    if n <= 0:
        return "—"
    if n >= 10_000:
        return f"{n // 1000:,}K"
    if n >= 1_000:
        return f"{n / 1000:.1f}K"
    return str(n)


def fmt_ts(ts: str | None, include_year: bool = True) -> str:
    if not ts:
        return "?"
    s = ts.replace("T", " ")[:19]
    if not include_year and len(s) >= 10 and s[4] == "-":
        return s[5:]
    return s


def fmt_duration(a: str | None, b: str | None) -> str:
    da, db = parse_iso(a), parse_iso(b)
    if not da or not db:
        return "?"
    mins = int((db - da).total_seconds() / 60)
    if mins < 1:
        return "<1min"
    if mins < 60:
        return f"{mins}min"
    return f"{mins // 60}h{mins % 60}m"


def trim(txt: str, limit: int) -> str:
    one = txt.replace("\n", " ").replace("\r", " ")
    if len(one) <= limit:
        return one
    return one[: max(0, limit - 1)] + "…"


def _is_wide_char(ch: str) -> bool:
    o = ord(ch)
    return (
        0x1100 <= o <= 0x115F
        or 0x2E80 <= o <= 0x303E
        or 0x3041 <= o <= 0x33FF
        or 0x3400 <= o <= 0x4DBF
        or 0x4E00 <= o <= 0x9FFF
        or 0xA000 <= o <= 0xA4CF
        or 0xAC00 <= o <= 0xD7A3
        or 0xF900 <= o <= 0xFAFF
        or 0xFE30 <= o <= 0xFE4F
        or 0xFF00 <= o <= 0xFF60
        or 0xFFE0 <= o <= 0xFFE6
    )


def display_width(s: str) -> int:
    return sum(2 if _is_wide_char(c) else 1 for c in s)


def trim_display(txt: str, max_w: int) -> str:
    one = txt.replace("\n", " ").replace("\r", " ")
    if display_width(one) <= max_w:
        return one
    out: list[str] = []
    w = 0
    for ch in one:
        cw = 2 if _is_wide_char(ch) else 1
        if w + cw > max_w - 1:
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"


def pad_display(s: str, target_w: int) -> str:
    w = display_width(s)
    if w >= target_w:
        return s
    return s + (" " * (target_w - w))


def volume_marker(total_msgs: int) -> str:
    """Conversation weight marker (fixed 1-col width).

    <20 blank / 20-49 · / 50-149 ● / 150+ ◉
    """
    if total_msgs < 20:
        return " "
    if total_msgs < 50:
        return "·"
    if total_msgs < 150:
        return "●"
    return "◉"


def decode_project_name(encoded_dir: str) -> str:
    """Decode encoded project dir like '-Users-jintaesong-Desktop-Home-foo' → 'foo'."""
    d = encoded_dir.lstrip("-")
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
