#!/bin/bash
# 03-search: typing a query filters the list.
TEST_NAME="03-search"
SESSION="ccr-qa-03"
source "$(dirname "$0")/_lib.sh"

tmux_start "$SESSION"
tmux_run "$SESSION" "cc-resume --days 90 --limit 20"
tmux_wait_for "$SESSION" "session>" 4 || { FAIL_REASONS+=("picker did not open"); finish "$SESSION"; }

# Grab initial match count "N/N"
cap0=$(tmux_capture "$SESSION")
total=$(grep -oE "[0-9]+/[0-9]+" <<<"$cap0" | head -1 | awk -F/ '{print $2}')
echo "  ℹ initial count: $total"

# Type a query that is extremely unlikely to match all sessions
tmux send-keys -t "$SESSION" "xyznoMatchLikely"
sleep 0.8
cap1=$(tmux_capture "$SESSION")

# Expect 0/N
if grep -qE "^[[:space:]]*0/[0-9]+" <<<"$cap1" || grep -qE " 0/[0-9]+" <<<"$cap1"; then
  echo "  ✓ query filtered to 0 matches"
else
  FAIL_REASONS+=("expected 0/N after typing unlikely query")
  echo "  ✗ filter result unexpected"
  echo "$cap1" | grep -E "[0-9]+/[0-9]+" | head -3 | sed 's/^/      /'
fi

tmux_keys "$SESSION" Escape
sleep 0.3
finish "$SESSION"
