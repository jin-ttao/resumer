# resumer picker — list view (column headers + ● badges + selected row)
# Output is committed at docs/visual/picker-list.gif and compared by eye
# against the target OSS-grade design.

Output "docs/visual/picker-list.gif"

Set Shell "bash"
Set FontSize 14
Set Width 1400
Set Height 760
Set TypingSpeed 50ms
Set Theme "Dracula"

# Mock-bin so accidental Enter can't launch a real CLI.
Type "export PATH=tests/mock-bin:$PATH"
Enter
Sleep 200ms

Type "resumer --days 30"
Enter
Sleep 2500ms

# Browse a couple rows so the selected-row highlight is visible.
Down
Sleep 400ms
Down
Sleep 400ms
Down
Sleep 600ms

Escape
Sleep 400ms
