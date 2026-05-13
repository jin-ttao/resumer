# resumer picker — NO_COLOR=1 path. Verifies that the ● badge stays visible
# without ANSI escapes, that 2-pane geometry doesn't depend on color, and
# that section labels degrade cleanly.

Output "docs/visual/picker-nocolor.gif"

Set Shell "bash"
Set FontSize 14
Set Width 1400
Set Height 900
Set TypingSpeed 50ms
Set Theme "Dracula"

Type "export PATH=tests/mock-bin:$PATH"
Enter
Sleep 200ms

Type "NO_COLOR=1 resumer --days 30"
Enter
Sleep 3000ms

Down
Sleep 500ms
Down
Sleep 1000ms

Escape
Sleep 400ms
