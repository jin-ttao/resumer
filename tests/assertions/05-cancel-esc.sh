#!/bin/bash
# 05-cancel-esc: Escape closes picker without invoking claude.
TEST_NAME="05-cancel-esc"
SESSION="ccr-qa-05"
source "$(dirname "$0")/_lib.sh"

MOCK_LOG="$OUTPUT_DIR/${SESSION}-claude.log"

tmux_start "$SESSION"
tmux_run "$SESSION" "cc-resume --days 30 --limit 5"
tmux_wait_for "$SESSION" "session>" 4 || { FAIL_REASONS+=("picker did not open"); finish "$SESSION"; }

tmux_keys "$SESSION" Escape
sleep 0.8

# Shell should be back; no mock invocation
if [[ -f "$MOCK_LOG" ]]; then
  FAIL_REASONS+=("claude mock was invoked despite Esc cancel")
  echo "  ✗ mock invoked: $(cat "$MOCK_LOG")"
else
  echo "  ✓ claude mock not invoked"
fi

cap=$(tmux_capture "$SESSION")
assert_not_contains "$cap" "Traceback|fzf error" "no errors after cancel"

finish "$SESSION"
