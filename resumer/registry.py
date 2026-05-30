"""Provider registry.

Lazy instantiation: providers defined at import but is_available() is only
called on first query so env overrides set by the dispatcher take effect.
"""
from __future__ import annotations

from typing import Iterator

from resumer.providers.base import Provider
from resumer.providers.claude_code import ClaudeCodeProvider
from resumer.providers.codex import CodexProvider
from resumer.providers.gemini import GeminiProvider
from resumer.session import Filters, Session


_all_providers: list[Provider] = [ClaudeCodeProvider(), CodexProvider(), GeminiProvider()]


def all_providers() -> list[Provider]:
    return list(_all_providers)


def active_providers() -> list[Provider]:
    return [p for p in _all_providers if p.is_available()]


def get_provider(name: str) -> Provider | None:
    for p in _all_providers:
        if p.name == name:
            return p
    return None


def merged_list(filters: Filters) -> list[Session]:
    """Collect sessions from active providers (or single provider if filter set),
    sorted by last_ts descending, interleaved across sources."""
    out: list[Session] = []
    if filters.source:
        p = get_provider(filters.source)
        if p is None:
            raise LookupError(f"unknown provider: {filters.source}")
        if not p.is_available():
            raise RuntimeError(
                f"{filters.source} provider not available "
                f"(binary or session directory missing)"
            )
        out.extend(p.list_sessions(filters))
    else:
        for p in active_providers():
            out.extend(p.list_sessions(filters))
    out.sort(key=lambda s: (s.last_ts or "", s.source), reverse=True)
    if filters.limit:
        out = out[: filters.limit]
    return out


def available_source_names() -> list[str]:
    return [p.name for p in active_providers()]