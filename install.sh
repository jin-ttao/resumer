#!/usr/bin/env bash
# resumer installer — symlinks cc-recent / cc-resume into ~/.local/bin
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing resumer..."

# 1. Ensure ~/.local/bin exists and is in PATH
mkdir -p "$HOME/.local/bin"
if ! echo "$PATH" | tr ':' '\n' | grep -q "$HOME/.local/bin"; then
  echo "Warning: ~/.local/bin is not in your PATH."
  echo "Add this to your shell profile (~/.zshrc or ~/.bashrc):"
  echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

# 2. Symlink executables
# Legacy (Claude Code only) commands — kept for backward compatibility.
# New unified + codex commands — resumer is the canonical entry; codex-*
# are convenience shims that call `resumer --source=codex`.
for f in cc-recent cc-resume resumer codex-recent codex-resume; do
  ln -sf "$SCRIPT_DIR/bin/$f" "$HOME/.local/bin/$f"
  echo "  Linked: ~/.local/bin/$f → bin/$f"
done

# 3. Check optional dependency
if ! command -v fzf >/dev/null 2>&1; then
  echo ""
  echo "Note: resumer / cc-resume require 'fzf'. Install with: brew install fzf"
fi

echo ""
echo "Done. Try:"
echo "  resumer                  # unified picker (Claude Code + Codex)"
echo "  resumer list --days 7    # merged list"
echo "  cc-recent --help         # legacy Claude Code only"
