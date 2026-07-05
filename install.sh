#!/bin/sh
set -e

echo "Installing resumer..."
go build -o /usr/local/bin/resumer

echo "Creating convenience symlinks..."
ln -sf /usr/local/bin/resumer /usr/local/bin/claude-recent
ln -sf /usr/local/bin/resumer /usr/local/bin/claude-resume
ln -sf /usr/local/bin/resumer /usr/local/bin/codex-recent
ln -sf /usr/local/bin/resumer /usr/local/bin/codex-resume
ln -sf /usr/local/bin/resumer /usr/local/bin/gemini-recent
ln -sf /usr/local/bin/resumer /usr/local/bin/gemini-resume

echo "Done."
