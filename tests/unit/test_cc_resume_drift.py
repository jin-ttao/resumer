#!/usr/bin/env python3
"""Drift guard: bin/cc-resume's inlined resolve_exec_cwd must stay byte-compatible
with src/providers/claude_code.py's implementation until D1 dedup transition.

Runs the same suite of test vectors against both implementations by importing
src's version and exec'ing cc-resume's version into a sandboxed namespace.
"""
from __future__ import annotations

import os
import re
import sys
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(REPO, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from providers.claude_code import (  # noqa: E402
    _encode_cwd as src_encode,
    resolve_exec_cwd as src_resolve,
)


def _load_cc_resume_helpers():
    """Exec only the helper function definitions from bin/cc-resume into an
    isolated namespace. Extracts the block from `_MAX_WALK_DEPTH = ` through
    the end of `resolve_exec_cwd` by matching the next top-level `def check`.
    """
    path = os.path.join(REPO, "bin", "cc-resume")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # Capture from _MAX_WALK_DEPTH up to the next top-level def that is NOT
    # one of the helpers we want. The helpers are _encode_cwd and
    # resolve_exec_cwd; after them comes `def check(...)` or similar.
    m = re.search(
        r"(_MAX_WALK_DEPTH = .*?return walk\(\"/\", target, 0\))",
        text,
        re.DOTALL,
    )
    if not m:
        raise RuntimeError("cc-resume helpers block not found — drift guard broken")
    block = m.group(1)
    ns: dict = {"os": os}
    exec(block, ns)
    return ns["_encode_cwd"], ns["resolve_exec_cwd"]


class DriftTests(unittest.TestCase):
    def setUp(self):
        self.cc_encode, self.cc_resolve = _load_cc_resume_helpers()
        self.tmp = tempfile.mkdtemp(prefix="resumer-drift-")
        self.target = os.path.join(self.tmp, "weird path~with tilde", "nested")
        os.makedirs(self.target, exist_ok=True)
        encoded = src_encode(self.target)
        self.session_path = os.path.join(
            self.tmp, "fake-projects", encoded, "id.jsonl"
        )
        os.makedirs(os.path.dirname(self.session_path), exist_ok=True)
        open(self.session_path, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_encode_parity(self):
        vectors = [
            "/Users/me/repo",
            "/Users/me/Mobile Documents/foo",
            "/Users/me/iCloud~md~obsidian",
            "/a b c~d~e/f",
            "/",
            "",
        ]
        for v in vectors:
            with self.subTest(path=v):
                self.assertEqual(src_encode(v), self.cc_encode(v))

    def test_resolve_parity_fast_path(self):
        self.assertEqual(
            src_resolve(self.session_path, stored_cwd=self.target),
            self.cc_resolve(self.session_path, stored_cwd=self.target),
        )

    def test_resolve_parity_slow_path(self):
        self.assertEqual(
            src_resolve(self.session_path, stored_cwd="/bogus/nonexistent"),
            self.cc_resolve(self.session_path, stored_cwd="/bogus/nonexistent"),
        )

    def test_resolve_parity_legacy_no_dash(self):
        legacy_path = os.path.join(self.tmp, "not-encoded", "x.jsonl")
        os.makedirs(os.path.dirname(legacy_path), exist_ok=True)
        open(legacy_path, "w").close()
        self.assertEqual(
            src_resolve(legacy_path), self.cc_resolve(legacy_path)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
