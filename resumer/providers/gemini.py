"""Gemini CLI provider.

Reads ~/.gemini/sessions/YYYY/MM/DD/session-<timestamp>-<uuid>.jsonl files.

JSONL structure (based on Gemini CLI session format):
  - metadata line: session info including id, cwd, timestamps
  - event lines: conversation events with user prompts and assistant responses
  - session IDs are UUIDs

Env overrides (for fixture-based QA):
  - RESUMER_GEMINI_SESSION_ROOT
  - RESUMER_GEMINI_INDEX_FILE
  - RESUMER_GEMINI_BIN (bypass shutil.which for mock)

Session fields mapped to the common schema:
  - title    = session metadata title or generated from first prompt
  - subtitle = project label (cwd basename)
  - resume_argv = ["gemini", "resume", session_id]
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from typing import Iterator

from resumer.session import Filters, Session
from resumer.utils import parse_iso


DEFAULT_SESSION_ROOT = os.path.expanduser("~/.gemini/sessions")
DEFAULT_INDEX_FILE = os.path.expanduser("~/.gemini/session_index.jsonl")


def _session_root() -> str:
    return os.environ.get("RESUMER_GEMINI_SESSION_ROOT") or DEFAULT_SESSION_ROOT


def _index_file() -> str:
    return os.environ.get("RESUMER_GEMINI_INDEX_FILE") or DEFAULT_INDEX_FILE


def _gemini_bin_available() -> bool:
    override = os.environ.get("RESUMER_GEMINI_BIN")
    if override:
        return bool(shutil.which(override))
    return shutil.which("gemini") is not None


_index_cache: dict[str, dict[str, str]] = {}
_index_warned_paths: set[str] = set()


def _load_index() -> dict[str, str]:
    """Map session_id → session title. Graceful on missing/corrupt."""
    path = _index_file()
    if path in _index_cache:
        return _index_cache[path]
    out: dict[str, str] = {}
    try:
        with open(path, "r", errors="replace") as fp:
            for line in fp:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid = r.get("id")
                name = r.get("title") or r.get("name")
                if isinstance(sid, str) and isinstance(name, str) and name.strip():
                    out[sid] = name.strip()
    except OSError:
        if path not in _index_warned_paths:
            print(
                f"resumer: gemini session_index missing or unreadable ({path}); "
                "titles will be derived from prompts",
                file=sys.stderr,
            )
            _index_warned_paths.add(path)
    _index_cache[path] = out
    return out


def _parse_jsonl(path: str) -> Session | None:
    """Parse a gemini session file. Returns None on missing session metadata."""
    session_id: str | None = None
    cwd: str | None = None
    first_ts: str | None = None
    last_ts: str | None = None
    title: str | None = None
    prompts: list[tuple[str, str]] = []
    event_count = 0

    try:
        with open(path, "r", errors="replace") as fp:
            for lineno, line in enumerate(fp, start=1):
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = r.get("timestamp")
                if ts:
                    if not first_ts:
                        first_ts = ts
                    last_ts = ts

                # Try to extract session metadata from first line
                if lineno == 1:
                    if r.get("type") == "session" or r.get("session_id"):
                        session_id = r.get("session_id") or r.get("id")
                        cwd = r.get("cwd")
                        title = r.get("title") or r.get("name")
                        p_ts = r.get("timestamp")
                        if p_ts:
                            first_ts = p_ts
                    elif r.get("id") and r.get("created_at"):
                        # Alternative format: direct metadata
                        session_id = r.get("id")
                        cwd = r.get("cwd")
                        title = r.get("title")
                        p_ts = r.get("created_at")
                        if p_ts:
                            first_ts = p_ts
                else:
                    # Conversation events
                    if r.get("role") == "user" or r.get("type") == "user_message":
                        msg = r.get("content") or r.get("message") or r.get("text")
                        if isinstance(msg, str) and msg.strip():
                            prompts.append((ts or "", msg.strip()))
                            event_count += 1
                    elif r.get("type") == "assistant" or r.get("role") == "model":
                        event_count += 1
    except OSError:
        return None

    if not session_id:
        return None

    index = _load_index()
    if not title:
        title = index.get(session_id)

    project_label = os.path.basename((cwd or "").rstrip("/")) or "(unknown)"

    return Session(
        source="gemini",
        session_id=session_id,
        path=path,
        project_label=project_label,
        cwd=cwd,
        first_ts=first_ts,
        last_ts=last_ts,
        title=title,
        subtitle=None,
        first_prompt=prompts[0][1] if prompts else None,
        last_prompt=prompts[-1][1] if prompts else None,
        prompts=prompts,
        asst_count=event_count,
        tokens=None,
        resume_argv=["gemini", "resume", session_id],
    )


_SESSION_DATE_RE = re.compile(r"session-(\d{4}-\d{2}-\d{2})T")


def _session_date_from_name(fn: str) -> datetime | None:
    m = _SESSION_DATE_RE.search(fn)
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _find_session_files(root: str) -> Iterator[str]:
    if not os.path.isdir(root):
        return
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.startswith("session-") and fn.endswith(".jsonl"):
                yield os.path.join(dirpath, fn)


def _cutoff_for_filters(filters: Filters) -> datetime | None:
    if filters.all_time or filters.date:
        return None
    days = filters.days if filters.days is not None else 3
    return datetime.now(timezone.utc).astimezone().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=days)


def _touches_date(s: Session, day: datetime) -> bool:
    start = day.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    end = start.replace(hour=23, minute=59, second=59)
    fs = parse_iso(s.first_ts)
    ls = parse_iso(s.last_ts)
    if not fs and not ls:
        return False
    fs = fs or ls
    ls = ls or fs
    return not (ls < start or fs > end)


class GeminiProvider:
    name = "gemini"
    badge = "gemini"
    badge_ansi = "\x1b[33m"  # yellow

    def is_available(self) -> bool:
        return os.path.isdir(_session_root()) and _gemini_bin_available()

    def list_sessions(self, filters: Filters) -> Iterator[Session]:
        root = _session_root()
        cutoff = _cutoff_for_filters(filters)
        day: datetime | None = None
        if filters.date:
            try:
                day = datetime.fromisoformat(filters.date).replace(tzinfo=timezone.utc)
            except ValueError:
                day = None

        for path in _find_session_files(root):
            # Pre-filter by filename date to avoid parsing historical files
            fname = os.path.basename(path)
            fdate = _session_date_from_name(fname)
            if fdate is not None:
                if day is not None:
                    same_day = fdate.date() == day.astimezone(timezone.utc).date()
                    if not same_day:
                        continue
                elif cutoff is not None and fdate < cutoff - timedelta(days=1):
                    continue

            s = _parse_jsonl(path)
            if s is None:
                continue
            if filters.project:
                cwd_tail = os.path.basename(s.cwd or "")
                if filters.project.lower() not in cwd_tail.lower():
                    continue
            if day is not None:
                if not _touches_date(s, day):
                    continue
            elif cutoff is not None:
                ls = parse_iso(s.last_ts)
                if not ls or ls < cutoff:
                    continue
            yield s

    def load_detail(self, session_id: str) -> Session | None:
        root = _session_root()
        suffix = f"-{session_id}.jsonl"
        for path in _find_session_files(root):
            if os.path.basename(path).endswith(suffix):
                s = _parse_jsonl(path)
                if s and s.session_id == session_id:
                    return s
        return None