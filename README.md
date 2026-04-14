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

## QA

Automated regression suite for `cc-resume` — driven by `tmux send-keys` / `capture-pane`. Verifies picker render, navigation, search filtering, select→exec, Esc cancel, and argument pass-through. `claude` is mocked so no real session is started.

```bash
./tests/run-qa.sh              # all scenarios + demo GIF
./tests/run-qa.sh --no-vhs     # skip VHS GIF (faster, no deps)
./tests/run-qa.sh --only 04    # single scenario
```

Pass ⇒ exit 0. Output artifacts (mock logs, `demo.gif`) go to `tests/output/` (gitignored).

### QA dependencies

- `tmux`, `fzf`, `python3` (required)
- `vhs` (optional, for demo GIF): `brew install vhs`

## Roadmap

- [ ] `codex-recent` / `codex-resume`
- [ ] `gemini-recent` / `gemini-resume`
- [ ] Unified `resumer` dispatcher (`resumer cc`, `resumer codex`, …)
