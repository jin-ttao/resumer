#!/bin/bash
# cc-resume QA orchestrator.
# Runs all scenarios + (optionally) produces a VHS demo GIF.
#
# Usage:
#   ./tests/run-qa.sh              # all scenarios + VHS demo
#   ./tests/run-qa.sh --no-vhs     # skip VHS demo
#   ./tests/run-qa.sh --only 04    # run scenario 04 only
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCENARIO_DIR="$REPO_ROOT/tests/assertions"
OUTPUT_DIR="$REPO_ROOT/tests/output"
TAPE="$REPO_ROOT/tests/demo.tape"
mkdir -p "$OUTPUT_DIR"

# --- args ---
RUN_VHS=1
ONLY=""
while (( $# > 0 )); do
  case "$1" in
    --no-vhs) RUN_VHS=0 ;;
    --only) ONLY="$2"; shift ;;
    -h|--help)
      sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
  shift
done

# --- preflight ---
for cmd in tmux fzf cc-recent cc-resume python3; do
  if ! command -v "$cmd" >/dev/null; then
    echo "error: missing dependency: $cmd"
    exit 2
  fi
done
if (( RUN_VHS )) && ! command -v vhs >/dev/null; then
  echo "warn: vhs not installed; skipping GIF (use --no-vhs to silence)"
  RUN_VHS=0
fi

# --- run scenarios ---
scenarios=("$SCENARIO_DIR"/[0-9][0-9]-*.sh)
if [[ -n "$ONLY" ]]; then
  scenarios=("$SCENARIO_DIR"/${ONLY}-*.sh)
fi

pass=0
fail=0
failed_names=()
total=${#scenarios[@]}
i=0

echo "════════════════════════════════════════════════════════"
echo " cc-resume QA — $total scenario(s)"
echo "════════════════════════════════════════════════════════"

for s in "${scenarios[@]}"; do
  i=$((i+1))
  name=$(basename "$s" .sh)
  echo ""
  echo "[$i/$total] $name"
  echo "────────────────────────────────────────────────────────"
  if bash "$s"; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    failed_names+=("$name")
  fi
done

# --- VHS demo ---
if (( RUN_VHS )); then
  echo ""
  echo "[VHS] generating demo.gif"
  echo "────────────────────────────────────────────────────────"
  cd "$REPO_ROOT"
  if vhs "$TAPE" 2>&1 | tail -10; then
    gif="$OUTPUT_DIR/demo.gif"
    if [[ -f "$gif" ]]; then
      size=$(du -h "$gif" | awk '{print $1}')
      echo "  ✓ demo.gif generated ($size) at $gif"
    else
      echo "  ✗ demo.gif not found after vhs run"
    fi
  else
    echo "  ✗ vhs failed"
  fi
fi

# --- summary ---
echo ""
echo "════════════════════════════════════════════════════════"
echo " Summary: $pass passed / $fail failed  (of $total)"
if (( fail > 0 )); then
  for n in "${failed_names[@]}"; do echo "   FAIL: $n"; done
fi
echo "════════════════════════════════════════════════════════"

exit $(( fail > 0 ? 1 : 0 ))
