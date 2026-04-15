#!/bin/bash
# 11-drift-json-diff: cc-recent (legacy) vs resumer list --source=claude-code
# must agree on the common fields for real ~/.claude/projects data. Catches
# parser drift between the two Claude Code implementations early.
#
# Intentionally uses real user data (not fixtures) because cc-recent has no
# RESUMER_CLAUDE_PROJECT_ROOT override and we want parity checked against
# whatever shape real sessions have in practice.
TEST_NAME="11-drift-json-diff"
source "$(dirname "$0")/_lib.sh"

export PATH="$BIN_DIR:$PATH"

CC_OUT="$OUTPUT_DIR/11-cc.json"
RZ_OUT="$OUTPUT_DIR/11-rz.json"

cc-recent --json --days 1 --limit 5 >"$CC_OUT" 2>/dev/null || {
  FAIL_REASONS+=("cc-recent --json failed")
  finish ""
}
resumer list --source=claude-code --json --days 1 --limit 5 >"$RZ_OUT" 2>/dev/null || {
  FAIL_REASONS+=("resumer list --json failed")
  finish ""
}

# Drift test scope: PARSING parity on the intersection of session_ids that
# both tools returned. (Sort order differs — cc-recent sorts by last real
# user prompt, resumer by last_ts — so --limit may pick different sessions.
# That's not a parsing bug.)
export OUTPUT_DIR
python3 - <<'PYEOF'
import json, os, sys
out_dir = os.environ['OUTPUT_DIR']
cc = {s['session_id']: s for s in json.load(open(f"{out_dir}/11-cc.json"))}
rz = {s['session_id']: s for s in json.load(open(f"{out_dir}/11-rz.json"))}
common = set(cc) & set(rz)
if not common:
    print(f"  ✗ no overlapping sessions (cc={len(cc)}, rz={len(rz)}) — parity unverifiable")
    sys.exit(1)

mismatches = []
for sid in sorted(common):
    a, b = cc[sid], rz[sid]
    a_first = (a['prompts'][0]['text'] if a.get('prompts') else None)
    b_first = (b['prompts'][0]['text'] if b.get('prompts') else b.get('first_prompt'))
    for field, va, vb in [
        ('first_ts', a['first_ts'], b['first_ts']),
        ('last_ts', a['last_ts'], b['last_ts']),
        ('cwd', a['cwd'], b['cwd']),
        ('first_prompt', a_first, b_first),
    ]:
        if va != vb:
            mismatches.append(f"{sid[:8]}.{field}: cc={va!r} != rz={vb!r}")

if mismatches:
    print(f"  ✗ parsing drift on {len(mismatches)} field(s) across {len(common)} shared session(s):")
    for m in mismatches[:10]:
        print(f"    - {m}")
    sys.exit(1)
print(f"  ✓ common-field parity on {len(common)} shared session(s)")
PYEOF
rc=$?

if [[ $rc -eq 0 ]]; then
  echo "[$TEST_NAME] PASS"
  exit 0
fi
echo "[$TEST_NAME] FAIL"
exit 1
