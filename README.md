# resumer

AI CLI session resumer. Browse and resume recent sessions across Claude Code (and, eventually, Codex / Gemini / other AI CLIs).

## Tools

- **`cc-recent`** — Lists recent Claude Code sessions from `~/.claude/projects/**/*.jsonl` with opening and last prompts so you can identify which is which.
- **`cc-resume`** — Interactive picker built on `fzf`. Selects a session, `cd`s into its cwd, and execs `claude --resume <session_id>`.

## Install

```bash
git clone https://github.com/jin-ttao/resumer.git ~/Desktop/Home/tao-code/resumer
cd ~/Desktop/Home/tao-code/resumer
./install.sh
```

Creates symlinks in `~/.local/bin/`. Requires `~/.local/bin` in `PATH`.

### Dependencies

- Python 3 (stdlib only)
- `fzf` (for `cc-resume`): `brew install fzf`

## Usage

```bash
cc-recent --help             # show options
cc-recent --days 7           # last 7 days
cc-recent --project tao      # filter by project name

cc-resume                    # interactive picker
cc-resume --days 7           # pass-through args to cc-recent
```

## Roadmap

- [ ] `codex-recent` / `codex-resume`
- [ ] `gemini-recent` / `gemini-resume`
- [ ] Unified `resumer` dispatcher (`resumer cc`, `resumer codex`, …)
