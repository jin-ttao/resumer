"""Claude Code provider.

Ports the parsing logic from bin/cc-recent. Respects RESUMER_CLAUDE_PROJECT_ROOT
env for fixture-based testing.

Session fields mapped to the common schema:
  - title    = custom_title or ai_title (from /rename and auto-generated titles)
  - subtitle = plan_title (H1 of most recent ~/.claude/plans/*.md referenced)
               or fork marker "forked from <short-uuid>"
  - tokens   = aggregated usage across assistant turns
  - resume_argv = ["claude", "--resume", session_id]
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Iterator

from resumer.session import Filters, Session, TokenUsage
from resumer.utils import parse_iso


DEFAULT_PROJECT_ROOT = os.path.expanduser("~/.claude/projects")


BRANCH_RE = re.compile(
    r"Branched conversation.*?claude -r "
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.DOTALL,
)

PLAN_PATH_RE = re.compile(r"/\.claude/plans/[a-z0-9-]+\.md$")

_PLAN_TITLE_PREFIXES = (
    "Plan:", "plan:", "Research Plan:", "[OLD]", "[WIP]", "[DRAFT]",
)

FAKE_PROMPT_PREFIXES = (
    "<local-command",
    "<command-",
    "<system-reminder",
    "<ide_opened_file",
    "Caveat:",
    "[Request interrupted",
    "Base directory for this skill",
)


def _project_root() -> str:
    return os.environ.get("RESUMER_CLAUDE_PROJECT_ROOT") or DEFAULT_PROJECT_ROOT


_plan_title_cache: dict[str, str | None] = {}


def _read_plan_title(path: str) -> str | None:
    if path in _plan_title_cache:
        return _plan_title_cache[path]
    title: str | None = None
    try:
        with open(path, "r", errors="replace") as fp:
            for _ in range(20):
                line = fp.readline()
                if not line:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    text = stripped.lstrip("#").strip()
                    for prefix in _PLAN_TITLE_PREFIXES:
                        if text.startswith(prefix):
                            text = text[len(prefix):].strip()
                    if len(text) > 60:
                        text = text[:59] + "…"
                    title = text or None
                    break
    except OSError:
        title = None
    _plan_title_cache[path] = title
    return title


def _is_real_prompt(txt: object) -> bool:
    if not isinstance(txt, str):
        return False
    s = txt.strip()
    if not s:
        return False
    return not any(s.startswith(p) for p in FAKE_PROMPT_PREFIXES)


def _extract_user_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        return "\n".join(parts)
    return ""


def _parse_jsonl(path: str) -> Session | None:
    session_id = os.path.basename(path).replace(".jsonl", "")
    encoded_dir = os.path.basename(os.path.dirname(path))

    first_ts: str | None = None
    last_ts: str | None = None
    cwd: str | None = None
    asst_count = 0
    prompts: list[tuple[str | None, str]] = []
    forked_from: str | None = None
    plan_path: str | None = None
    custom_title: str | None = None
    ai_title: str | None = None
    tokens = TokenUsage()

    try:
        with open(path, "r", errors="replace") as fp:
            for line in fp:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = r.get("type")
                ts = r.get("timestamp") or (r.get("snapshot") or {}).get("timestamp")
                if ts:
                    if not first_ts:
                        first_ts = ts
                    last_ts = ts
                if t == "system":
                    if not cwd:
                        cwd = r.get("cwd")
                    if forked_from is None and r.get("subtype") == "local_command":
                        content = r.get("content") or ""
                        if "Branched conversation" in content:
                            m = BRANCH_RE.search(content)
                            if m:
                                forked_from = m.group(1)
                elif t in ("message", "assistant"):
                    msg = r.get("message", {}) or {}
                    role = msg.get("role") or ("assistant" if t == "assistant" else None)
                    if role == "assistant":
                        asst_count += 1
                        usage = msg.get("usage")
                        if usage:
                            tokens.input += usage.get("input_tokens", 0)
                            tokens.output += usage.get("output_tokens", 0)
                            tokens.cache_read += usage.get("cache_read_input_tokens", 0)
                            tokens.cache_create += usage.get("cache_creation_input_tokens", 0)
                            tokens.turns += 1
                    content = msg.get("content")
                    if isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            if block.get("type") != "tool_use":
                                continue
                            if block.get("name") not in ("Write", "Edit", "MultiEdit"):
                                continue
                            fp_ = (block.get("input") or {}).get("file_path")
                            if isinstance(fp_, str) and PLAN_PATH_RE.search(fp_):
                                plan_path = fp_
                elif t == "user":
                    text = _extract_user_text((r.get("message") or {}).get("content"))
                    if _is_real_prompt(text):
                        prompts.append((r.get("timestamp"), text.strip()))
                elif t == "custom-title":
                    ct = r.get("customTitle")
                    if isinstance(ct, str) and ct.strip():
                        custom_title = ct.strip()
                elif t == "ai-title":
                    at = r.get("aiTitle")
                    if isinstance(at, str) and at.strip():
                        ai_title = at.strip()
    except OSError:
        return None

    # Project label from the session's real cwd field (basename), matching the
    # Codex provider pattern. Falls back to the encoded dir's last hyphen
    # segment for legacy session files that lack a cwd record.
    if cwd:
        project_label = os.path.basename(cwd.rstrip("/")) or "(unknown)"
    else:
        project_label = encoded_dir.lstrip("-").rsplit("-", 1)[-1] or "(unknown)"

    plan_title = _read_plan_title(plan_path) if plan_path else None

    title = custom_title or ai_title
    subtitle_parts: list[str] = []
    if plan_title:
        subtitle_parts.append(plan_title)
    if forked_from:
        subtitle_parts.append(f"forked from {forked_from[:8]}")
    subtitle = " · ".join(subtitle_parts) if subtitle_parts else None

    return Session(
        source="claude-code",
        session_id=session_id,
        path=path,
        project_label=project_label,
        cwd=cwd,
        first_ts=first_ts,
        last_ts=last_ts,
        title=title,
        subtitle=subtitle,
        first_prompt=prompts[0][1] if prompts else None,
        last_prompt=prompts[-1][1] if prompts else None,
        prompts=[(ts or "", txt) for (ts, txt) in prompts],
        asst_count=asst_count,
        tokens=tokens if tokens.turns else None,
        resume_argv=["claude", "--resume", session_id],
    )


def _find_session_files(root: str) -> Iterator[str]:
    if not os.path.isdir(root):
        return
    for dirpath, _dirs, files in os.walk(root):
        if "subagents" in dirpath.split(os.sep):
            continue
        for fn in files:
            if fn.endswith(".jsonl"):
                yield os.path.join(dirpath, fn)


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


def _cutoff_for_filters(filters: Filters) -> datetime | None:
    if filters.all_time or filters.date:
        return None
    days = filters.days if filters.days is not None else 3
    return datetime.now(timezone.utc).astimezone().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - _days_delta(days)


def _days_delta(days: int):
    from datetime import timedelta
    return timedelta(days=days)


class ClaudeCodeProvider:
    name = "claude-code"
    badge = "cc"
    badge_ansi = "\x1b[32m"  # green

    def is_available(self) -> bool:
        return os.path.isdir(_project_root())

    def list_sessions(self, filters: Filters) -> Iterator[Session]:
        root = _project_root()
        cutoff = _cutoff_for_filters(filters)
        day: datetime | None = None
        if filters.date:
            try:
                day = datetime.fromisoformat(filters.date).replace(tzinfo=timezone.utc)
            except ValueError:
                day = None

        for path in _find_session_files(root):
            s = _parse_jsonl(path)
            if s is None:
                continue
            if filters.project:
                if filters.project.lower() not in s.project_label.lower():
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
        root = _project_root()
        for path in _find_session_files(root):
            if os.path.basename(path).replace(".jsonl", "") == session_id:
                return _parse_jsonl(path)
        return None


# ---------- resume cwd resolution ----------
#
# claude --resume <uuid> derives the project dir from the CURRENT cwd by encoding
# it (replace / space ~ with -) and looking under ~/.claude/projects/<encoded>/.
# If resumer chdirs to the JSONL's stored cwd but that stored value is stale or
# mismatched against the actual file location (observed with iCloud/Obsidian
# vault paths where all 15 system records had cwd=/Users/foo/Desktop while the
# file lived under -Users-foo-Library-Mobile-Documents-...), claude can't find
# the session. Defense: derive cwd from the session file's encoded parent dir,
# which is always correct because it's where claude stored the file.

_MAX_WALK_DEPTH = 15  # guard against symlink loops; typical iCloud paths ~8 deep


def _encode_cwd(path: str) -> str:
    """Mimic Claude Code's cwd → project-dir encoding: / space ~ all become -."""
    return "-" + path.lstrip("/").replace("/", "-").replace(" ", "-").replace("~", "-")


def resolve_exec_cwd(
    session_path: str, stored_cwd: str | None = None
) -> str | None:
    """Find a filesystem dir whose encoding matches the session's encoded
    parent dir. Returns None if no match.

    Fast path: if stored_cwd already encodes to the target, use it directly
    (the common case — 99%+ of sessions).
    Slow path: walk from / matching segments. Guards against permission errors
    and symlink loops via depth limit.
    """
    encoded = os.path.basename(os.path.dirname(session_path))
    if not encoded.startswith("-"):
        return None

    if stored_cwd and os.path.isdir(stored_cwd) and _encode_cwd(stored_cwd) == encoded:
        return stored_cwd

    target = encoded.lstrip("-")

    def walk(current: str, remaining: str, depth: int) -> str | None:
        if depth > _MAX_WALK_DEPTH:
            return None
        if not remaining:
            return current if os.path.isdir(current) else None
        try:
            entries = os.listdir(current)
        except (PermissionError, OSError):
            return None
        for entry in entries:
            enc = entry.replace("/", "-").replace(" ", "-").replace("~", "-")
            if remaining == enc:
                full = os.path.join(current, entry)
                return full if os.path.isdir(full) else None
            if remaining.startswith(enc + "-"):
                full = os.path.join(current, entry)
                if os.path.isdir(full):
                    hit = walk(full, remaining[len(enc) + 1:], depth + 1)
                    if hit:
                        return hit
        return None

    return walk("/", target, 0)
