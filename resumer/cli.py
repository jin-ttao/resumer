#!/usr/bin/env python3
"""resumer — unified AI CLI session resumer (Claude Code + Codex).

Usage:
  resumer                       interactive picker across all active providers
  resumer list                  render merged session list (no interaction)
  resumer --source=codex        filter to a single provider
  resumer --days 7              window (default 3; 'list' and picker both honor)
  resumer --project foo         substring match against project name
  resumer --limit 20
  resumer --json                list-mode machine output
  resumer --full [N]            list-mode detailed boxes for top N
  resumer --preview-for <dir> <source> <sid>   internal fzf hook
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

from resumer import __version__
from resumer.session import Filters
from resumer.render import render_full_box, render_index, render_json
from resumer.picker import pick, preview_for
from resumer.registry import available_source_names, merged_list


_STAR_URL = "https://github.com/jin-ttao/resumer"


def _state_dir() -> str:
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, "resumer")


def _maybe_show_first_run_star(resume_bin: str) -> None:
    """Print a one-time star nudge on the user's first successful resume.

    Guard: if the resume binary itself is not on PATH, skip both the message
    and the sentinel. That way the message fires only when the user is
    actually about to experience the tool — not on a failed first attempt
    that would otherwise burn the sentinel.
    """
    if not shutil.which(resume_bin):
        return
    sentinel = os.path.join(_state_dir(), "first-run-done")
    if os.path.exists(sentinel):
        return
    try:
        os.makedirs(os.path.dirname(sentinel), exist_ok=True)
        with open(sentinel, "w"):
            pass
    except OSError:
        return  # state dir not writable — message can wait
    print(f"\n  Enjoyed resumer? ⭐ {_STAR_URL}\n", file=sys.stderr)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="resumer",
        description="Unified AI CLI session resumer.",
    )
    p.add_argument("--version", action="version", version=f"resumer {__version__}")
    p.add_argument("command", nargs="?", choices=["list"], default=None,
                   help="subcommand (omit for interactive picker)")
    p.add_argument("--source", choices=["claude-code", "codex"],
                   help="limit to a single provider")
    p.add_argument("--days", type=int, default=7,
                   help="only show sessions active in the last N days (default: 7)")
    p.add_argument("--date", help="YYYY-MM-DD — only sessions active on this date")
    p.add_argument("--all", action="store_true", help="no time filter")
    p.add_argument("--project", help="substring match against project name")
    p.add_argument("--limit", type=int, help="top N after sort")
    p.add_argument("--json", action="store_true",
                   help="list mode only: emit JSON array of sessions")
    p.add_argument("--full", nargs="?", type=int, const=5, default=None,
                   metavar="N",
                   help="list mode only: render detailed boxes for top N (default 5)")
    return p


def _run_picker(filters: Filters) -> int:
    sessions = merged_list(filters)
    if not sessions:
        print("No sessions found. Try --days 7 or --all.", file=sys.stderr)
        return 0
    chosen = pick(sessions)
    if chosen is None:
        return 0
    return _exec_resume(chosen)


def _exec_resume(s) -> int:
    # For claude-code, prefer a cwd derived from the session file's encoded
    # parent dir. Stored cwd in the JSONL can be stale/mismatched (seen with
    # iCloud/Obsidian paths), causing `claude --resume` to fail because it
    # derives the project dir from the current cwd.
    target_cwd = None
    if s.source == "claude-code":
        from resumer.providers.claude_code import resolve_exec_cwd
        target_cwd = resolve_exec_cwd(s.path, stored_cwd=s.cwd)
    if not target_cwd:
        target_cwd = s.cwd

    if target_cwd and os.path.isdir(target_cwd):
        os.chdir(target_cwd)
    elif target_cwd:
        print(
            f"warning: session cwd not accessible, running from {os.getcwd()}: {target_cwd}",
            file=sys.stderr,
        )
    _maybe_show_first_run_star(s.resume_argv[0])
    print(
        f"resuming [{s.source}] {s.session_id} from {os.getcwd()}",
        file=sys.stderr,
    )
    try:
        os.execvp(s.resume_argv[0], s.resume_argv)
    except FileNotFoundError:
        bin_name = s.resume_argv[0]
        install_hint = {
            "claude": "https://docs.anthropic.com/en/docs/claude-code/quickstart",
            "codex": "https://github.com/openai/codex",
        }.get(bin_name)
        print(f"error: '{bin_name}' not found in PATH", file=sys.stderr)
        if install_hint:
            print(f"       install: {install_hint}", file=sys.stderr)
        return 127


def _run_list(args, filters: Filters) -> int:
    sessions = merged_list(filters)
    if args.json:
        print(render_json(sessions))
    elif args.full is not None:
        for s in sessions[: args.full]:
            print(render_full_box(s))
            print()
    else:
        print(render_index(sessions))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Internal preview hook (invoked by fzf). Must come before argparse so
    # the custom 3-arg form doesn't clash with the main parser.
    if argv and argv[0] == "--preview-for":
        if len(argv) < 4:
            print("usage: resumer --preview-for <dir> <source> <sid>", file=sys.stderr)
            return 2
        return preview_for(preview_dir=argv[1], source=argv[2], session_id=argv[3])

    parser = _build_parser()
    args = parser.parse_args(argv)

    filters = Filters(
        days=None if args.all else args.days,
        date=args.date,
        all_time=args.all,
        project=args.project,
        limit=args.limit,
        source=args.source,
    )

    # Global availability check only runs when no specific source requested;
    # otherwise merged_list raises a source-specific RuntimeError with better
    # diagnostics ("codex provider not available" vs generic message).
    if not args.source and not available_source_names():
        print(
            "error: no session providers available. "
            "Install claude-code or codex and ensure their session directories exist.",
            file=sys.stderr,
        )
        return 2

    if args.command != "list" and (args.json or args.full is not None):
        print(
            "error: --json and --full are only valid with the 'list' subcommand",
            file=sys.stderr,
        )
        return 2

    try:
        if args.command == "list":
            return _run_list(args, filters)
        return _run_picker(filters)
    except LookupError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
