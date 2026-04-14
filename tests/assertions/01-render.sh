#!/bin/bash
# 01-render: cc-resume launches, picker renders with sessions + preview pane.
TEST_NAME="01-render"
SESSION="ccr-qa-01"
source "$(dirname "$0")/_lib.sh"

tmux_start "$SESSION"
tmux_run "$SESSION" "cc-resume --days 30 --limit 5"

# Wait until fzf prompt AND preview pane appear (preview is the slower one)
if ! tmux_wait_for "$SESSION" "session>" 4; then
  FAIL_REASONS+=("session> prompt did not appear within 4s")
  finish "$SESSION"
fi
if ! tmux_wait_for "$SESSION" "📁 project:" 4; then
  FAIL_REASONS+=("preview pane did not render within 4s")
  finish "$SESSION"
fi

cap=$(tmux_capture "$SESSION")
assert_contains "$cap" "session>"                    "fzf prompt visible"
assert_contains "$cap" "↑↓ browse"                   "header line visible"
assert_contains "$cap" "📁 project:"                  "preview pane rendered"
assert_not_contains "$cap" "Traceback|error:"         "no errors in output"

# Clean exit: Esc
tmux_keys "$SESSION" Escape
sleep 0.3

finish "$SESSION"
