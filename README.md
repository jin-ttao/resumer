# resumer

> Browse & resume your Claude Code / Codex sessions with fzf.

![demo](docs/demo.gif)

```bash
brew install jin-ttao/tap/resumer
# or
pipx install resumer
```

## Usage

```bash
resumer              # interactive picker
resumer list         # plain list, last 7 days
resumer --help       # everything else
```

Requires Python 3.10+, [fzf](https://github.com/junegunn/fzf), and macOS or Linux (Windows planned).

<details>
<summary>Development</summary>

```bash
git clone https://github.com/jin-ttao/resumer.git
cd resumer
pip install -e .
./tests/run-qa.sh --no-vhs   # tmux + fzf required
```

Roadmap: Gemini provider. CI/CD release automation. Windows support.

</details>

---

Built by [@jin-ttao](https://github.com/jin-ttao). If this helped, leaving a ⭐ helps others find it.
