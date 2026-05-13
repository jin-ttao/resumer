# Verification-only tape — larger font for visual inspection. Not the
# final demo asset (that lives at tests/resumer-demo.tape).

Output "docs/visual/picker-list-big.gif"

Set Shell "bash"
Set FontSize 22
Set Width 1800
Set Height 1200
Set TypingSpeed 50ms
Set Theme "Dracula"

Type "export PATH=tests/mock-bin:$PATH"
Enter
Sleep 200ms

Type "resumer --days 30"
Enter
Sleep 3500ms

Down
Sleep 500ms
Down
Sleep 500ms
Down
Sleep 1500ms

Escape
Sleep 400ms
