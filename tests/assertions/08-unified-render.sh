#!/bin/bash
# 08-unified-render: `resumer list` shows both [cc] and [codex] rows
# interleaved by last_ts desc.
TEST_NAME="08-unified-render"
SESSION="resumer-qa-08"
source "$(dirname "$0")/_lib.sh"

tmux_start "$SESSION"
tmux_use_fixtures "$SESSION"

OUT_FILE="$OUTPUT_DIR/${SESSION}.out"
rm -f "$OUT_FILE" "$OUT_FILE.done"
tmux_run "$SESSION" "resumer list --all > $OUT_FILE 2>/dev/null; echo DONE_${SESSION} > $OUT_FILE.done"
# Wait up to 5s for the done marker.
for _ in $(seq 1 50); do [[ -f "$OUT_FILE.done" ]] && break; sleep 0.1; done

assert_file_exists "$OUT_FILE"                               "list output file created"

OUT="$(cat "$OUT_FILE")"
assert_contains "$OUT" "\[cc\]"                              "at least one [cc] row"
assert_contains "$OUT" "\[codex\]"                           "at least one [codex] row"
assert_contains "$OUT" "fixture-alpha"                       "cc fixture-alpha appears"
assert_contains "$OUT" "fixture-beta"                        "cc fixture-beta appears"
assert_contains "$OUT" "codex-one|codex-two|codex-three"     "at least one codex fixture project appears"

# Sort: first data row (after header + divider) should be the most recent one,
# which in fixtures is codex-three (07:00) beating all cc rows (<= 04:00).
FIRST_ROW="$(sed -n '3p' "$OUT_FILE")"
assert_contains "$FIRST_ROW" "codex-three"                   "top row is most-recent codex session (desc sort)"
assert_contains "$FIRST_ROW" "\[codex\]"                     "top row has [codex] badge"

# Last row should be the oldest cc fixture (01:05 plain session).
LAST_ROW="$(tail -1 "$OUT_FILE")"
assert_contains "$LAST_ROW" "fixture-alpha"                  "last row is oldest cc session"
assert_contains "$LAST_ROW" "plain fixture"                  "last row shows plain fixture first prompt"

finish "$SESSION"
