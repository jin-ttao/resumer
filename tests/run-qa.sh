#!/bin/bash
# resumer QA orchestrator.
# Runs all scenarios + (optionally) produces a VHS demo GIF.
#
# Usage:
#   ./tests/run-qa.sh              # all scenarios + VHS demo
#   ./tests/run-qa.sh --no-vhs     # skip VHS demo
#   ./tests/run-qa.sh --only 04    # run scenario 04 (cc-resume) only
#   ./tests/run-qa.sh --only 07    # run scenario 07 (codex picker) only
#
# Scenarios 01-06 cover the legacy cc-resume picker.
# Scenarios 07-11 cover the new resumer unified system (codex provider,
# unified dispatch, missing-provider fallback, parser drift guard).
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCENARIO_DIR="$REPO_ROOT/tests/assertions"
OUTPUT_DIR="$REPO_ROOT/tests/output"
# Tapes run in listed order. Add more tape paths here to grow coverage;
# each one produces its own GIF via the Output directive inside the tape.
TAPES=(
  "$REPO_ROOT/tests/demo.tape"           # legacy cc-resume demo
  "$REPO_ROOT/tests/resumer-demo.tape"   # unified resumer demo
)
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
# resumer + codex mock must be resolvable from the repo checkout (PATH needn't
# include them; scenarios prepend BIN_DIR and MOCK_BIN via _lib.sh).
for path in "$REPO_ROOT/bin/resumer" "$REPO_ROOT/tests/mock-bin/codex"; do
  if [[ ! -x "$path" ]]; then
    echo "error: missing executable: $path"
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
echo " resumer QA — $total scenario(s)"
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

# --- VHS demos ---
if (( RUN_VHS )); then
  cd "$REPO_ROOT"
  for tape in "${TAPES[@]}"; do
    if [[ ! -f "$tape" ]]; then
      echo ""
      echo "[VHS] skip (tape missing): $tape"
      continue
    fi
    tape_name="$(basename "$tape")"
    echo ""
    echo "[VHS] generating GIF from $tape_name"
    echo "────────────────────────────────────────────────────────"
    # Parse the Output directive to know which gif to verify.
    gif_rel="$(grep -m1 '^Output' "$tape" | awk '{print $2}' | tr -d '"')"
    gif_abs="$REPO_ROOT/$gif_rel"
    if vhs "$tape" 2>&1 | tail -10; then
      if [[ -f "$gif_abs" ]]; then
        size=$(du -h "$gif_abs" | awk '{print $1}')
        echo "  ✓ $(basename "$gif_abs") generated ($size) at $gif_abs"
      else
        echo "  ✗ $(basename "$gif_abs") not found after vhs run"
      fi
    else
      echo "  ✗ vhs failed for $tape_name"
    fi
  done
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
