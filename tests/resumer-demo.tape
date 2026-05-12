# resumer demo — unified list + interactive picker with [cc]/[codex] badges.
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
# launch a real CLI. resumer itself comes from pipx / `pip install -e .`.
Type "export PATH=tests/mock-bin:$PATH"
Enter
Sleep 300ms

# 1. Merged list — shows [cc]/[codex] badges interleaved.
Type "resumer list --days 14 --limit 10"
Enter
Sleep 2500ms

# 2. Unified interactive picker.
Type "resumer --days 14"
Enter
Sleep 2500ms

# Browse
Down
Sleep 400ms
Down
Sleep 400ms
Up
Sleep 500ms

# Filter
Type "codex"
Sleep 1500ms
Backspace
Backspace
Backspace
Backspace
Backspace
Sleep 500ms

# Cancel so mock is not invoked in the recorded GIF.
Escape
Sleep 600ms
