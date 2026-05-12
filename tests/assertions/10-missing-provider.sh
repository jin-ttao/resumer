#!/bin/bash
# 10-missing-provider: when codex session dir is missing, `resumer list`
# still works (claude-code only) but `--source=codex` exits 2 with a
# clear error.
TEST_NAME="10-missing-provider"
source "$(dirname "$0")/_lib.sh"

export PATH="$MOCK_BIN:$PATH"
export RESUMER_CLAUDE_PROJECT_ROOT="$FIXTURES_DIR/claude-code"
export RESUMER_CODEX_SESSION_ROOT="/nonexistent/resumer-qa-missing"
export RESUMER_CODEX_BIN=codex

OUT="$OUTPUT_DIR/10-list.out"
ERR="$OUTPUT_DIR/10-list.err"
resumer list --all >"$OUT" 2>"$ERR"
rc=$?
assert_contains "rc=$rc" "rc=0"                                      "merged list exits 0 with claude-only providers"
assert_file_contains "$OUT" "\[cc\]"                                 "output has [cc] rows"
assert_not_contains "$(cat "$OUT")" "\[codex\]"                      "output has no [codex] rows"

SRC_OUT="$OUTPUT_DIR/10-source.out"
SRC_ERR="$OUTPUT_DIR/10-source.err"
resumer list --source=codex --all >"$SRC_OUT" 2>"$SRC_ERR"
rc2=$?
assert_contains "rc=$rc2" "rc=2"                                     "source=codex exits 2 when provider unavailable"
assert_file_contains "$SRC_ERR" "codex provider not available"       "stderr has provider-specific message"

FAIL_REASONS_COUNT=${#FAIL_REASONS[@]}
if (( FAIL_REASONS_COUNT == 0 )); then
  echo "[$TEST_NAME] PASS"
  exit 0
else
  echo "[$TEST_NAME] FAIL ($FAIL_REASONS_COUNT assertion(s))"
  for r in "${FAIL_REASONS[@]}"; do echo "    - $r"; done
  exit 1
fi
