#!/bin/bash
# 09-unified-select: in the unified picker, selecting a [cc] row execs claude,
# selecting a [codex] row execs codex. Verifies source-specific dispatch.
TEST_NAME="09-unified-select"
source "$(dirname "$0")/_lib.sh"

run_select_case() {
  local session="$1"
  local want_source="$2"      # "cc" | "codex"
  local filter="$3"           # fzf typed query to isolate a specific row

  tmux_start "$session"
  tmux_enable_codex_mock "$session"
  tmux_use_fixtures "$session"

  : > "$OUTPUT_DIR/${session}-claude.log"

  tmux_run "$session" "resumer --all"
  tmux_wait_for "$session" "session>" 4 || {
    FAIL_REASONS+=("[$want_source] picker did not open")
    tmux_kill "$session"
    return
  }

  # Type the filter so only one row remains, then Enter.
  tmux send-keys -t "$session" "$filter"
  sleep 0.4
  tmux_keys "$session" Enter

  local claude_log="$OUTPUT_DIR/${session}-claude.log"
  local codex_log="$OUTPUT_DIR/${session}-codex.log"
  # Wait for whichever log the dispatch writes to (whichever first reaches
  # non-empty). Avoids fixed sleep.
  local waited=0
  while (( waited < 100 )); do
    [[ -s "$claude_log" ]] && break
    [[ -s "$codex_log" ]] && break
    sleep 0.05
    waited=$((waited + 1))
  done

  if [[ "$want_source" == "cc" ]]; then
    if [[ -s "$claude_log" ]] && [[ ! -s "$codex_log" ]]; then
      echo "  ✓ [$want_source] only claude mock invoked"
    else
      FAIL_REASONS+=("[$want_source] dispatch mismatch (claude_log=$(wc -c <"$claude_log" 2>/dev/null || echo 0), codex_log=$(wc -c <"$codex_log" 2>/dev/null || echo 0))")
    fi
    assert_file_contains "$claude_log" "args=--resume [a-f0-9]{8}-[a-f0-9-]+"  "[$want_source] claude --resume uuid recorded"
  else
    if [[ -s "$codex_log" ]] && [[ ! -s "$claude_log" ]]; then
      echo "  ✓ [$want_source] only codex mock invoked"
    else
      FAIL_REASONS+=("[$want_source] dispatch mismatch (claude_log=$(wc -c <"$claude_log" 2>/dev/null || echo 0), codex_log=$(wc -c <"$codex_log" 2>/dev/null || echo 0))")
    fi
    assert_file_contains "$codex_log" "args=resume 019cccc[1-9]-[a-f0-9-]+"      "[$want_source] codex resume uuid recorded"
  fi

  tmux_kill "$session"
}

# Fixtures sorted desc by last_ts: codex-three(07:00), codex-two(06:00),
# codex-one(05:00), cc fixture-beta forked(04:00), ...
# Top row (0 downs) = codex-three.
run_select_case "resumer-qa-09a" "codex" "codex-three"
run_select_case "resumer-qa-09b" "cc"    "fixture-beta"

if (( ${#FAIL_REASONS[@]} == 0 )); then
  echo "[$TEST_NAME] PASS"
  exit 0
else
  echo "[$TEST_NAME] FAIL (${#FAIL_REASONS[@]} assertion(s))"
  for r in "${FAIL_REASONS[@]}"; do echo "    - $r"; done
  exit 1
fi
