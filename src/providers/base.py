from __future__ import annotations

from typing import Iterator, Protocol

from session import Filters, Session


class Provider(Protocol):
    name: str
    badge: str
    badge_ansi: str

    def is_available(self) -> bool: ...

    def list_sessions(self, filters: Filters) -> Iterator[Session]: ...

    def load_detail(self, session_id: str) -> Session | None: ...
