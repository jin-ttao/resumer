#!/bin/bash
# 07-codex-picker: resumer --source=codex selects a codex fixture session,
# Enter fires os.chdir + execvp("codex", ["resume", <uuid>]).
TEST_NAME="07-codex-picker"
SESSION="resumer-qa-07"
source "$(dirname "$0")/_lib.sh"

tmux_start "$SESSION"
tmux_enable_codex_mock "$SESSION"
tmux_use_fixtures "$SESSION"

tmux_run "$SESSION" "resumer --source=codex --all"
tmux_wait_for "$SESSION" "session>" 4 || { FAIL_REASONS+=("picker did not open"); finish "$SESSION"; }

# Verify picker shows codex badge rows but no claude-code rows.
# (The fzf header text "[cc]/[codex] source" contains [cc] for documentation,
# so assert against fixture-specific project tokens instead of the badge text.)
OUT="$(tmux_capture "$SESSION")"
assert_contains "$OUT" "\[codex\]"              "[codex] badge visible in picker"
assert_not_contains "$OUT" "fixture-alpha"      "no claude-code fixture-alpha rows when --source=codex"
assert_not_contains "$OUT" "fixture-beta"       "no claude-code fixture-beta rows when --source=codex"

# Select top and confirm — poll for the mock's log rather than fixed sleep.
tmux_keys "$SESSION" Enter
wait_for_file "$CODEX_LOG" 5 || FAIL_REASONS+=("codex mock log never appeared")

assert_file_exists "$CODEX_LOG"                                              "mock codex was invoked"
assert_file_contains "$CODEX_LOG" "args=resume 019cccc[1-9]-[0-9a-f-]+"      "codex resume <uuid> recorded"
assert_file_contains "$CODEX_LOG" "pwd=(/private)?/tmp/resumer-fixtures/codex-"   "cwd restored to fixture codex dir"

finish "$SESSION"
