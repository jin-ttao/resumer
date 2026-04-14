#!/bin/bash
# Shared helpers for cc-resume QA scenarios.
# Source this at the top of each scenario script.

set -u

# Paths (relative to repo root)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MOCK_BIN="$REPO_ROOT/tests/mock-bin"
OUTPUT_DIR="$REPO_ROOT/tests/output"
mkdir -p "$OUTPUT_DIR"

# --- tmux helpers ---

tmux_start() {
  local session="$1"
  local width="${2:-220}"
  local height="${3:-55}"
  tmux kill-session -t "$session" 2>/dev/null || true
  tmux new-session -d -s "$session" -x "$width" -y "$height"
  # Inject mock PATH + reset claude mock log
  local log="$OUTPUT_DIR/${session}-claude.log"
  rm -f "$log"
  tmux send-keys -t "$session" "export PATH=$MOCK_BIN:\$PATH" Enter
  tmux send-keys -t "$session" "export CLAUDE_MOCK_LOG=$log" Enter
  sleep 0.3
}

tmux_run() {
  # send a shell command + Enter
  tmux send-keys -t "$1" "$2" Enter
}

tmux_keys() {
  # send raw keys (e.g., Down Down Enter)
  local session="$1"; shift
  tmux send-keys -t "$session" "$@"
}

tmux_capture() {
  tmux capture-pane -t "$1" -p
}

tmux_wait_for() {
  # Poll capture-pane for pattern. Usage: tmux_wait_for SESSION "pattern" [timeout_s=3]
  local session="$1"
  local pattern="$2"
  local timeout="${3:-3}"
  local elapsed=0
  while (( elapsed < timeout * 10 )); do
    if tmux_capture "$session" | grep -qE "$pattern"; then
      return 0
    fi
    sleep 0.1
    elapsed=$((elapsed + 1))
  done
  return 1
}

tmux_kill() {
  tmux kill-session -t "$1" 2>/dev/null || true
}

# --- assertions ---

TEST_NAME="${TEST_NAME:-unknown}"
FAIL_REASONS=()

assert_contains() {
  local haystack="$1"
  local needle="$2"
  local label="${3:-contains '$needle'}"
  if grep -qE "$needle" <<<"$haystack"; then
    echo "  ✓ $label"
  else
    FAIL_REASONS+=("$label")
    echo "  ✗ $label"
  fi
}

assert_not_contains() {
  local haystack="$1"
  local needle="$2"
  local label="${3:-does not contain '$needle'}"
  if ! grep -qE "$needle" <<<"$haystack"; then
    echo "  ✓ $label"
  else
    FAIL_REASONS+=("$label")
    echo "  ✗ $label"
  fi
}

assert_file_exists() {
  local path="$1"
  local label="${2:-file exists: $path}"
  if [[ -f "$path" ]]; then
    echo "  ✓ $label"
  else
    FAIL_REASONS+=("$label")
    echo "  ✗ $label"
  fi
}

assert_file_contains() {
  local path="$1"
  local needle="$2"
  local label="${3:-file contains '$needle'}"
  if [[ -f "$path" ]] && grep -qE "$needle" "$path"; then
    echo "  ✓ $label"
  else
    FAIL_REASONS+=("$label")
    echo "  ✗ $label"
  fi
}

finish() {
  local session="${1:-}"
  [[ -n "$session" ]] && tmux_kill "$session"
  if (( ${#FAIL_REASONS[@]} == 0 )); then
    echo "[$TEST_NAME] PASS"
    exit 0
  else
    echo "[$TEST_NAME] FAIL (${#FAIL_REASONS[@]} assertion(s))"
    for r in "${FAIL_REASONS[@]}"; do echo "    - $r"; done
    exit 1
  fi
}

# Safety: kill session on unexpected exit
trap 'tmux_kill "${SESSION:-}"' EXIT
