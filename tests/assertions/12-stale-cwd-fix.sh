#!/bin/bash
# 12-stale-cwd-fix: regression guard for the "stale JSONL cwd" bug.
#
# Fixture session at tests/fixtures/claude-code/-tmp-resumer-fixtures-obsidian-
# path-with-space-vault/<uuid>.jsonl records cwd="/bogus/wrong/path" (simulating
# the iCloud/Obsidian path drift observed in real data). The encoded parent
# dir name corresponds to a real FS path `/tmp/resumer-fixtures/obsidian path
# with space/vault` that tmux_use_fixtures materializes.
#
# Expected: resolve_exec_cwd walks the filesystem and recovers the real path,
# so os.chdir lands there (not at /bogus/wrong/path). Verified by the mock
# claude's recorded pwd.
TEST_NAME="12-stale-cwd-fix"
SESSION="resumer-qa-12"
source "$(dirname "$0")/_lib.sh"

tmux_start "$SESSION"
tmux_use_fixtures "$SESSION"

CLAUDE_LOG="$OUTPUT_DIR/${SESSION}-claude.log"
: > "$CLAUDE_LOG"

tmux_run "$SESSION" "resumer --source=claude-code --all"
tmux_wait_for "$SESSION" "session>" 4 || { FAIL_REASONS+=("picker did not open"); finish "$SESSION"; }

tmux send-keys -t "$SESSION" "stale cwd regression"
sleep 0.4
tmux_keys "$SESSION" Enter

wait_for_file "$CLAUDE_LOG" 5 || { FAIL_REASONS+=("claude mock log never appeared"); finish "$SESSION"; }

echo "  — mock claude log —"
cat "$CLAUDE_LOG"

assert_file_contains "$CLAUDE_LOG" \
  "pwd=(/private)?/tmp/resumer-fixtures/obsidian path with space/vault" \
  "walked to real vault path (not stored bogus cwd)"
assert_file_contains "$CLAUDE_LOG" \
  "args=--resume dddddddd-0006-4000-8000-000000000006" \
  "claude --resume with correct uuid"
if grep -q "pwd=/bogus/wrong/path" "$CLAUDE_LOG"; then
  FAIL_REASONS+=("pwd ended at stored bogus cwd — fix not applied")
else
  echo "  ✓ did not chdir to stored bogus cwd"
fi

finish "$SESSION"
