#!/usr/bin/env python3
"""Unit tests for Claude Code project_label resolution.

After dropping decode_project_name (which hardcoded a single user's home
prefix), project_label comes from os.path.basename(cwd) read out of the
session JSONL. Falls back to the encoded dir's last hyphen segment when
cwd is missing.

Stdlib only. Run directly: `python3 tests/unit/test_project_label.py`.
Also invoked by tests/run-qa.sh.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resumer.providers.claude_code import _parse_jsonl  # noqa: E402


def _write_session(parent_dir: str, encoded_dir: str, cwd: str | None) -> str:
    """Create a minimal JSONL session file under parent_dir/encoded_dir/ and
    return the path. cwd=None omits the cwd field on the system record."""
    session_dir = os.path.join(parent_dir, encoded_dir)
    os.makedirs(session_dir, exist_ok=True)
    path = os.path.join(session_dir, "aaaaaaaa-0001-4000-8000-000000000001.jsonl")
    records: list[dict] = []
    sys_rec: dict = {
        "type": "system",
        "subtype": "init",
        "timestamp": "2026-04-15T01:00:00.000Z",
    }
    if cwd is not None:
        sys_rec["cwd"] = cwd
    records.append(sys_rec)
    records.append({
        "type": "user",
        "timestamp": "2026-04-15T01:00:05.000Z",
        "message": {"role": "user", "content": "hi"},
    })
    with open(path, "w") as fp:
        for r in records:
            fp.write(json.dumps(r) + "\n")
    return path


class ProjectLabelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="resumer-label-test-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cwd_basename_simple(self):
        path = _write_session(self.tmp, "-Users-alice-Desktop-myrepo",
                              cwd="/Users/alice/Desktop/myrepo")
        s = _parse_jsonl(path)
        self.assertIsNotNone(s)
        self.assertEqual(s.project_label, "myrepo")

    def test_cwd_basename_other_user(self):
        path = _write_session(self.tmp, "-Users-bob-projects-foo",
                              cwd="/Users/bob/projects/foo")
        s = _parse_jsonl(path)
        self.assertEqual(s.project_label, "foo")

    def test_cwd_basename_icloud_obsidian(self):
        cwd = "/Users/alice/Library/Mobile Documents/iCloud~md~obsidian/Documents/tao"
        path = _write_session(
            self.tmp,
            "-Users-alice-Library-Mobile-Documents-iCloud-md-obsidian-Documents-tao",
            cwd=cwd,
        )
        s = _parse_jsonl(path)
        self.assertEqual(s.project_label, "tao")

    def test_cwd_with_trailing_slash(self):
        path = _write_session(self.tmp, "-tmp-resumer-test-x",
                              cwd="/tmp/resumer-test/x/")
        s = _parse_jsonl(path)
        self.assertEqual(s.project_label, "x")

    def test_cwd_missing_fallback_to_encoded_segment(self):
        # No cwd field at all → fall back to the encoded dir's last segment.
        path = _write_session(self.tmp, "-some-encoded-myproject", cwd=None)
        s = _parse_jsonl(path)
        self.assertEqual(s.project_label, "myproject")

    def test_cwd_missing_unknown_when_encoded_empty(self):
        # Encoded dir name is just "-" (no segments) → "(unknown)".
        path = _write_session(self.tmp, "-", cwd=None)
        s = _parse_jsonl(path)
        self.assertEqual(s.project_label, "(unknown)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
