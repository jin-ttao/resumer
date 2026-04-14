# resumer demo — launch cc-resume, navigate, search, cancel.
# Runs against real ~/.claude/projects/ — GIF contains live previews.
# Keep local (see .gitignore: tests/output/).

Output "tests/output/demo.gif"

Set Shell "bash"
Set FontSize 14
Set Width 1400
Set Height 760
Set TypingSpeed 50ms
Set Theme "Dracula"

# Safety: route 'claude' to mock so accidental Enter can't launch real claude.
Type "export PATH=tests/mock-bin:$PATH"
Enter
Sleep 300ms

Type "cc-resume --days 14 --limit 8"
Enter
Sleep 2500ms

# Browse
Up
Sleep 400ms
Up
Sleep 400ms
Up
Sleep 500ms
Down
Sleep 400ms

# Filter
Type "code"
Sleep 1500ms
Backspace
Backspace
Backspace
Backspace
Sleep 500ms

# Cancel
Escape
Sleep 600ms
