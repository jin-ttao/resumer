#!/bin/bash
# 04-select-exec: Enter fires os.chdir + execvp("claude", ["--resume", <sid>]).
TEST_NAME="04-select-exec"
SESSION="ccr-qa-04"
source "$(dirname "$0")/_lib.sh"

MOCK_LOG="$OUTPUT_DIR/${SESSION}-claude.log"

tmux_start "$SESSION"
tmux_run "$SESSION" "cc-resume --days 30 --limit 5"
tmux_wait_for "$SESSION" "session>" 4 || { FAIL_REASONS+=("picker did not open"); finish "$SESSION"; }

# Select the top item
tmux_keys "$SESSION" Enter
sleep 1.5

assert_file_exists "$MOCK_LOG"                                         "mock claude was invoked"
assert_file_contains "$MOCK_LOG" "args=--resume [0-9a-f]{8}-[0-9a-f-]+" "args contain --resume <uuid>"
assert_file_contains "$MOCK_LOG" "pwd=/"                                "pwd is an absolute path"

finish "$SESSION"
