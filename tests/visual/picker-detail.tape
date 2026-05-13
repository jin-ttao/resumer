# resumer picker — detail pane (2-column meta | prompts).
# Lets the preview render fully so the GIF captures the new ASCII layout.

Output "docs/visual/picker-detail.gif"

Set Shell "bash"
Set FontSize 14
Set Width 1400
Set Height 900
Set TypingSpeed 50ms
Set Theme "Dracula"

Type "export PATH=tests/mock-bin:$PATH"
Enter
Sleep 200ms

Type "resumer --days 30"
Enter
Sleep 3000ms

# Move around so the preview pane updates.
Down
Sleep 600ms
Down
Sleep 600ms
Up
Sleep 1500ms

Escape
Sleep 400ms
