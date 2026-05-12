"""resumer — unified AI CLI session resumer (Claude Code + Codex)."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("resumer")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
