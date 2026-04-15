from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TokenUsage:
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_create: int = 0
    turns: int = 0


@dataclass
class Session:
    source: str
    session_id: str
    path: str
    cwd: str | None = None
    first_ts: str | None = None
    last_ts: str | None = None
    title: str | None = None
    subtitle: str | None = None
    first_prompt: str | None = None
    last_prompt: str | None = None
    prompts: list[tuple[str, str]] = field(default_factory=list)
    asst_count: int = 0
    tokens: TokenUsage | None = None
    resume_argv: list[str] = field(default_factory=list)


@dataclass
class Filters:
    days: int | None = 3
    date: str | None = None
    all_time: bool = False
    project: str | None = None
    limit: int | None = None
    source: str | None = None
