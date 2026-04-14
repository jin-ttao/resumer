#!/bin/bash
# 02-navigate: arrow keys change the preview content.
TEST_NAME="02-navigate"
SESSION="ccr-qa-02"
source "$(dirname "$0")/_lib.sh"

tmux_start "$SESSION"
tmux_run "$SESSION" "cc-resume --days 30 --limit 5"
tmux_wait_for "$SESSION" "session>" 4 || { FAIL_REASONS+=("picker did not open"); finish "$SESSION"; }
# Extra settle time so fzf finishes rendering preview pane
sleep 0.8

sid1=$(tmux_capture "$SESSION" | grep -oE "session id:[[:space:]]+[0-9a-f-]{36}" | head -1)

# fzf default layout: cursor starts at BOTTOM (newest item).
# Up moves toward older items (displayed higher on screen).
tmux send-keys -t "$SESSION" Up
sleep 0.4
tmux send-keys -t "$SESSION" Up
sleep 1.0
sid2=$(tmux_capture "$SESSION" | grep -oE "session id:[[:space:]]+[0-9a-f-]{36}" | head -1)

if [[ -n "$sid1" && -n "$sid2" && "$sid1" != "$sid2" ]]; then
  echo "  ✓ preview changed after Down Down ($sid1 → $sid2)"
else
  FAIL_REASONS+=("preview did not change (sid1='$sid1' sid2='$sid2')")
  echo "  ✗ preview did not change"
fi

tmux_keys "$SESSION" Escape
sleep 0.3
finish "$SESSION"
