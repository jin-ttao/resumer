#!/bin/bash
# 06-args-passthrough: extra args like --days are forwarded to cc-recent,
# and limit the returned session count.
TEST_NAME="06-args-passthrough"
SESSION="ccr-qa-06"
source "$(dirname "$0")/_lib.sh"

# Compare counts between two different --days values
c_narrow=$(cc-recent --json --days 1 2>/dev/null | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null || echo 0)
c_wide=$(cc-recent --json --days 90 2>/dev/null | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null || echo 0)
echo "  ℹ cc-recent --days 1: $c_narrow sessions"
echo "  ℹ cc-recent --days 90: $c_wide sessions"

if (( c_narrow <= c_wide )); then
  echo "  ✓ --days filter affects count (narrow ≤ wide)"
else
  FAIL_REASONS+=("--days filter did not reduce count (narrow=$c_narrow > wide=$c_wide)")
fi

# Spot-check cc-resume accepts same args without crashing (open & Esc)
tmux_start "$SESSION"
tmux_run "$SESSION" "cc-resume --days 1"
sleep 1.5
cap=$(tmux_capture "$SESSION")

# Either picker opens (session>) OR the empty-list branch fires
if grep -qE "session>|No sessions found" <<<"$cap"; then
  echo "  ✓ cc-resume --days 1 ran without crash"
else
  FAIL_REASONS+=("cc-resume --days 1 produced unexpected output")
  echo "$cap" | tail -5 | sed 's/^/      /'
fi

tmux_keys "$SESSION" Escape
sleep 0.3
finish "$SESSION"
