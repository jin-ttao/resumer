"""Layout tests for render.py — column widths, NO_COLOR, 2-pane geometry.

Guards the contract between `header_line()`, `_row_cells()`, and the fzf
picker. If column widths drift, the header and data rows misalign — these
tests catch it.
"""
from __future__ import annotations

import os
import re

import pytest

from resumer.render import (
    ANSI_RESET,
    COL_PROJECT,
    COL_SOURCE,
    COL_SUMMARY,
    COL_TIME,
    COL_TITLE,
    COL_TOKENS,
    DETAIL_LEFT_W,
    DETAIL_RIGHT_W,
    DETAIL_SEP,
    _detail_meta_lines,
    _row_cells,
    header_line,
    render_full_box,
    render_index,
)
from resumer.session import Session, TokenUsage
from resumer.utils import display_width


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def _sample(source: str = "claude-code", **kwargs) -> Session:
    defaults = dict(
        session_id="abc-123",
        path="/tmp/x",
        project_label="resumer",
        cwd="/dev/resumer",
        first_ts="2025-05-13T09:47:26",
        last_ts="2025-05-13T09:47:26",
        title="feat: x",
        first_prompt="hello world",
        prompts=[("t", "first prompt")],
        asst_count=10,
    )
    defaults.update(kwargs)
    return Session(source=source, **defaults)


# ─── Column header / row alignment ──────────────────────────────────────────


def test_header_line_widths_match_row_cells():
    """Each column in header_line() must equal COL_* width (after ANSI strip)."""
    head = header_line()
    parts = head.split(" ")
    # Header is space-joined; right-pad makes each piece exactly COL_* wide,
    # but consecutive spaces from padding + separator merge under split(" ").
    # Use display_width on the whole line vs sum of widths + 5 separators.
    expected = (
        COL_TIME + COL_SOURCE + COL_PROJECT + COL_TOKENS + COL_SUMMARY + 5
    )
    # TITLE is unpadded — its actual width is len("TITLE")=5.
    assert display_width(head) == expected + len("TITLE")


def test_row_cells_widths_match_columns():
    s = _sample()
    time_c, src_c, proj_c, tok_c, summary_c, title_c = _row_cells(s)
    assert display_width(_strip_ansi(time_c)) == COL_TIME
    assert display_width(_strip_ansi(src_c)) == COL_SOURCE
    assert display_width(_strip_ansi(proj_c)) == COL_PROJECT
    assert display_width(_strip_ansi(tok_c)) == COL_TOKENS
    assert display_width(_strip_ansi(summary_c)) == COL_SUMMARY
    # title is final, unpadded — only upper bound enforced
    assert display_width(_strip_ansi(title_c)) <= COL_TITLE


def test_row_cells_cjk_summary_truncation():
    """Wide chars must not break column width."""
    s = _sample(first_prompt="한글" * 40)  # 80 display cols
    _, _, _, _, summary_c, _ = _row_cells(s)
    assert display_width(_strip_ansi(summary_c)) == COL_SUMMARY


# ─── Badge colors ────────────────────────────────────────────────────────────


def test_badge_dot_colored_by_default(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    _, src_c, *_ = _row_cells(_sample(source="claude-code"))
    assert "\x1b[32m" in src_c  # green
    assert ANSI_RESET in src_c
    assert "claude" in src_c

    _, src_c2, *_ = _row_cells(_sample(source="codex"))
    assert "\x1b[36m" in src_c2  # cyan
    assert "codex" in src_c2


def test_no_color_strips_ansi(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    _, src_c, *_ = _row_cells(_sample(source="claude-code"))
    assert "\x1b[" not in src_c

    box = render_full_box(_sample())
    assert "\x1b[" not in box


# ─── Volume marker / brackets removal ────────────────────────────────────────


def test_no_bracket_badge_in_row():
    """Old `[cc]` / `[codex]` brackets must be gone."""
    _, src_c, *_ = _row_cells(_sample(source="claude-code"))
    plain = _strip_ansi(src_c)
    assert "[cc]" not in plain
    assert "[claude-code]" not in plain
    assert "●" in plain
    assert "claude" in plain


def test_no_volume_marker_column():
    """Row must have exactly 6 visible columns — no volume marker."""
    cells = _row_cells(_sample())
    assert len(cells) == 6


# ─── Full timestamp ──────────────────────────────────────────────────────────


def test_timestamp_includes_year():
    time_c, *_ = _row_cells(_sample(last_ts="2025-05-13T09:47:26"))
    plain = _strip_ansi(time_c).strip()
    assert plain.startswith("2025-")
    assert plain == "2025-05-13 09:47:26"


# ─── Detail box 2-pane geometry ──────────────────────────────────────────────


def test_detail_box_left_pane_width(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    s = _sample(
        session_id="9f3b1d2a-6c78-4e77-9c2d-0b9a7e6f2c11",
        tokens=TokenUsage(input=384721, output=682193, cache_read=240000, turns=28),
    )
    lines = _detail_meta_lines(s)
    for line in lines:
        assert display_width(line) == DETAIL_LEFT_W, f"left line width mismatch: {line!r}"


def test_detail_box_has_two_panes(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    s = _sample(prompts=[("t", f"prompt {i}") for i in range(10)])
    box = render_full_box(s)
    lines = box.split("\n")
    # First line must contain the separator: left | sep | right
    first = lines[0]
    assert DETAIL_SEP in first
    # Left pane on first line should be padded to DETAIL_LEFT_W
    left = first[:DETAIL_LEFT_W]
    assert display_width(left) == DETAIL_LEFT_W


def test_detail_box_opening_and_last_labels(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    s = _sample(prompts=[("t", f"prompt number {i}") for i in range(10)])
    box = render_full_box(s)
    assert "opening prompts" in box
    assert "last prompts" in box


def test_detail_box_session_id_not_truncated(monkeypatch):
    """Full UUID must fit in the left pane (was truncated in prior layout)."""
    monkeypatch.setenv("NO_COLOR", "1")
    full_uuid = "9f3b1d2a-6c78-4e77-9c2d-0b9a7e6f2c11"
    s = _sample(session_id=full_uuid)
    box = render_full_box(s)
    assert full_uuid in box


# ─── render_index integration ────────────────────────────────────────────────


def test_render_index_header_present(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_index([_sample()])
    lines = out.split("\n")
    assert "TIME (LOCAL)" in lines[0]
    assert "SOURCE" in lines[0]
    assert "PROJECT" in lines[0]
    assert "TOKENS" in lines[0]
    assert "SUMMARY" in lines[0]
    assert "TITLE" in lines[0]


def test_render_index_empty():
    assert render_index([]) == "(no sessions)"


# ─── picker.py hidden-fields contract ───────────────────────────────────────
#
# These tests freeze the row-shape contract the fzf picker depends on:
# `_build_fzf_line` must emit exactly 9 tab-separated cells, with hidden
# fields at positions 6 (source), 7 (session_id), 8 (cwd). If anyone
# changes column counts without updating `--with-nth` and the post-select
# field indices, resume dispatch silently breaks. Direct unit test catches
# the drift even when the picker isn't run end-to-end.


def test_build_fzf_line_has_nine_cells():
    from resumer.picker import _build_fzf_line

    s = _sample(source="codex", session_id="sid-xyz", cwd="/work")
    line = _build_fzf_line(s)
    cells = line.split("\t")
    assert len(cells) == 9, f"expected 9 tab-separated cells, got {len(cells)}: {cells!r}"


def test_build_fzf_line_hidden_field_indices():
    from resumer.picker import _build_fzf_line

    s = _sample(source="codex", session_id="sid-xyz", cwd="/work/dir")
    fields = _build_fzf_line(s).split("\t")
    assert fields[6] == "codex"
    assert fields[7] == "sid-xyz"
    assert fields[8] == "/work/dir"


def test_build_fzf_line_handles_none_cwd():
    from resumer.picker import _build_fzf_line

    s = _sample(cwd=None)
    fields = _build_fzf_line(s).split("\t")
    assert len(fields) == 9
    assert fields[8] == ""
