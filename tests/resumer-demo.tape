# resumer demo — unified list + native TUI picker with [cc]/[codex] badges.
# Runs against real ~/.claude/projects and ~/.codex/sessions. Output is the
# committed README GIF at docs/demo.gif.

Output "docs/demo.gif"

Set Shell "bash"
Set FontSize 14
Set Width 1400
Set Height 760
Set TypingSpeed 50ms
Set Theme "Dracula"

# Safety: route 'claude' and 'codex' to mocks so accidental Enter can't
# launch a real CLI. resumer itself comes from PATH (brew / go install).
Type "export PATH=tests/mock-bin:$PATH"
Enter
Sleep 300ms

# 1. Merged list — shows [cc]/[codex] badges interleaved.
Type "resumer list --days 14 --limit 10"
Enter
Sleep 2500ms

# 2. Native TUI picker with live preview pane.
Type "resumer --days 14"
Enter
Sleep 2500ms

# Browse — preview pane follows the selection.
Down
Sleep 400ms
Down
Sleep 400ms
Up
Sleep 500ms

# Filter ('/' opens the filter prompt).
Type "/"
Sleep 300ms
Type "codex"
Sleep 1200ms
Enter
Sleep 800ms

# Clear the filter, then cancel so the mock is not invoked in the GIF.
Escape
Sleep 400ms
Escape
Sleep 600ms
