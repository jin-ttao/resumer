# resumer

AI CLI session resumer. Browse and resume recent sessions across Claude Code and Codex — with Gemini and other providers planned.

## Tools

### Primary — unified resumer

- **`resumer`** — Interactive `fzf` picker showing sessions from every active provider, sorted by most recent activity and tagged with a provider badge (`[cc]` green for Claude Code, `[codex]` cyan for Codex). Enter selects → `cd`s into the session's original cwd → execs the provider's resume command (`claude --resume <id>` or `codex resume <id>`).
- **`resumer list`** — Prints the merged, sorted list without interaction. Supports `--json` for scripting and `--full [N]` for detailed session boxes.
- **`resumer --source=<claude-code|codex>`** — Filter to a single provider (picker or list). `resumer list --source=codex --days 7`, etc.

### Convenience shims
- **`codex-recent`** — `resumer list --source=codex "$@"` (thin bash wrapper).
- **`codex-resume`** — `resumer --source=codex "$@"`.

### Legacy (Claude Code only, unchanged)
- **`cc-recent`** — Original Claude Code-only lister. Reads `~/.claude/projects/**/*.jsonl`.
- **`cc-resume`** — Original Claude Code-only picker + `claude --resume`.

The legacy commands are preserved untouched so existing muscle memory keeps working while `resumer` stabilizes. Internally resumer re-implements Claude Code parsing — parity is guarded by a drift test (scenario 11).

## Install

```bash
git clone https://github.com/jin-ttao/resumer.git ~/Desktop/Home/tao-code/resumer
cd ~/Desktop/Home/tao-code/resumer
./install.sh
```

Creates five symlinks in `~/.local/bin/`: `resumer`, `codex-recent`, `codex-resume`, `cc-recent`, `cc-resume`. Requires `~/.local/bin` in `PATH`.

### Dependencies

- Python 3 (stdlib only — zero external Python packages)
- `fzf` (for interactive pickers): `brew install fzf`

Optional:
- `codex` CLI: enables the Codex provider. Without it, resumer silently shows only Claude Code sessions.
- `claude` CLI: needed for actual resume of Claude Code sessions (listing works without it).

## Usage

### Unified

```bash
resumer                        # interactive picker across all providers
resumer list                   # merged list, default last 3 days
resumer list --days 7          # wider window
resumer list --project foo     # substring match on project name
resumer list --json            # machine-readable
resumer list --full 5          # detailed box view for top 5
resumer --source=codex         # picker, codex only
```

### Legacy

```bash
cc-recent --days 7             # Claude Code only, original output format
cc-resume --days 7             # Claude Code only picker
```

## QA

Automated regression suite — driven by `tmux send-keys` / `capture-pane`. Covers:

- **Legacy cc-resume** (01–06): picker render, navigation, search filtering, select→exec, Esc cancel, arg pass-through
- **Resumer (new)** (07–11): codex picker, unified render with badges, dispatch branching by source, missing-provider fallback, cc-recent ↔ resumer parser drift guard

Both `claude` and `codex` are mocked during QA so no real session is started. Fixtures under `tests/fixtures/` give the scenarios deterministic inputs (user `~/.claude/projects` / `~/.codex/sessions` not touched except for scenario 11).

```bash
./tests/run-qa.sh              # all 11 scenarios + demo GIFs
./tests/run-qa.sh --no-vhs     # skip VHS GIFs (faster, no deps)
./tests/run-qa.sh --only 07    # single scenario
```

Pass ⇒ exit 0. Output artifacts (mock logs, `demo.gif`, `resumer-demo.gif`) land in `tests/output/` (gitignored).

### QA dependencies

- `tmux`, `fzf`, `python3` (required)
- `vhs` (optional, for demo GIFs): `brew install vhs`

## Roadmap

- [x] Codex provider (`codex-recent` / `codex-resume` + unified `resumer`)
- [ ] `gemini-recent` / `gemini-resume`
- [ ] Collapse legacy `cc-recent` / `cc-resume` into resumer shims (follow-up PR after resumer burns in)
