#!/usr/bin/env python3
"""Unit tests for resolve_exec_cwd / _encode_cwd in Claude Code provider.

Stdlib only. Run directly: `python3 tests/unit/test_claude_code_cwd.py`.
Also invoked by tests/run-qa.sh.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resumer.providers.claude_code import (  # noqa: E402
    _MAX_WALK_DEPTH,
    _encode_cwd,
    resolve_exec_cwd,
)


class EncodeCwdTests(unittest.TestCase):
    def test_simple_path(self):
        self.assertEqual(_encode_cwd("/Users/me/repo"), "-Users-me-repo")

    def test_space_in_path(self):
        self.assertEqual(
            _encode_cwd("/Users/me/Mobile Documents/foo"),
            "-Users-me-Mobile-Documents-foo",
        )

    def test_tilde_in_path(self):
        self.assertEqual(
            _encode_cwd("/Users/me/iCloud~md~obsidian/foo"),
            "-Users-me-iCloud-md-obsidian-foo",
        )

    def test_combined_space_and_tilde(self):
        self.assertEqual(
            _encode_cwd(
                "/Users/me/Library/Mobile Documents/iCloud~md~obsidian/Documents/tao"
            ),
            "-Users-me-Library-Mobile-Documents-iCloud-md-obsidian-Documents-tao",
        )

    def test_root_path(self):
        self.assertEqual(_encode_cwd("/"), "-")

    def test_empty_path(self):
        self.assertEqual(_encode_cwd(""), "-")


class ResolveExecCwdTests(unittest.TestCase):
    def setUp(self):
        # Build a sandbox that mimics an encoded-dir scenario outside / root.
        # We can't exercise the real / walk without side effects, so we treat
        # a temp dir as our "encoded parent" and verify that:
        #   - fast-path returns stored_cwd when it encodes to the target
        #   - non-matching stored_cwd falls through to slow path
        # The slow path (walk from /) is exercised by tests that use a real
        # existing subtree under /tmp.
        self.tmp_root = tempfile.mkdtemp(prefix="resumer-cwd-test-")
        # Create target dir with spaces + tildes to mimic iCloud-style paths.
        self.target_name = "path with space~and~tilde"
        self.target_dir = os.path.join(self.tmp_root, self.target_name)
        os.makedirs(self.target_dir, exist_ok=True)

        # Compose encoded parent dir name matching target_dir's absolute path.
        self.encoded = _encode_cwd(self.target_dir)
        # Fake session file sits under a projects root; its parent dir name
        # equals the encoded form of self.target_dir.
        projects_root = os.path.join(self.tmp_root, "fake-claude-projects")
        os.makedirs(os.path.join(projects_root, self.encoded), exist_ok=True)
        self.session_path = os.path.join(
            projects_root, self.encoded, "aaaa-bbbb-cccc.jsonl"
        )
        # File doesn't need content for these tests; resolve_exec_cwd only
        # looks at the path string.
        open(self.session_path, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_fast_path_stored_cwd_matches(self):
        # When stored_cwd already encodes to the target, fast-path returns it.
        result = resolve_exec_cwd(self.session_path, stored_cwd=self.target_dir)
        self.assertEqual(result, self.target_dir)

    def test_slow_path_walk_success(self):
        # Bogus stored_cwd forces slow path; walk should find target via FS.
        result = resolve_exec_cwd(
            self.session_path, stored_cwd="/nonexistent/bogus/path"
        )
        self.assertEqual(result, self.target_dir)

    def test_legacy_path_no_dash_prefix(self):
        # Session path whose encoded parent doesn't start with "-" → None.
        legacy_path = os.path.join(self.tmp_root, "not-encoded", "x.jsonl")
        os.makedirs(os.path.dirname(legacy_path), exist_ok=True)
        open(legacy_path, "w").close()
        self.assertIsNone(resolve_exec_cwd(legacy_path))

    def test_walk_miss_returns_none(self):
        # Encoded target names a dir that doesn't exist → None.
        missing_dir = os.path.join(self.tmp_root, "no-such-target")
        missing_encoded = _encode_cwd(missing_dir)
        proj_root = os.path.join(self.tmp_root, "fake-proj-2")
        os.makedirs(os.path.join(proj_root, missing_encoded), exist_ok=True)
        fake_path = os.path.join(proj_root, missing_encoded, "x.jsonl")
        open(fake_path, "w").close()
        self.assertIsNone(resolve_exec_cwd(fake_path))

    def test_depth_limit_defends_against_pathological_input(self):
        # Build an encoded target with more segments than MAX_WALK_DEPTH.
        # Walk should bail out with None rather than hang.
        deep_segments = "-".join(f"seg{i}" for i in range(_MAX_WALK_DEPTH + 5))
        encoded = "-" + deep_segments
        proj_root = os.path.join(self.tmp_root, "fake-proj-3")
        os.makedirs(os.path.join(proj_root, encoded), exist_ok=True)
        fake_path = os.path.join(proj_root, encoded, "x.jsonl")
        open(fake_path, "w").close()
        # Fast path skipped (stored_cwd None), slow path walks, depth exceeds
        # limit well before matching anything → None.
        result = resolve_exec_cwd(fake_path)
        self.assertIsNone(result)

    def test_fast_path_ignored_when_encoding_mismatches(self):
        # stored_cwd exists but encodes to something different → slow path runs.
        other_dir = os.path.join(self.tmp_root, "different-dir")
        os.makedirs(other_dir, exist_ok=True)
        result = resolve_exec_cwd(self.session_path, stored_cwd=other_dir)
        # slow path should still find the real target.
        self.assertEqual(result, self.target_dir)

    def test_permission_denied_subtree_is_skipped(self):
        # Create a subtree the user can't read and ensure walk gracefully
        # skips it instead of crashing. Uses chmod 000 on a decoy sibling
        # that prefix-matches the encoded target.
        if os.geteuid() == 0:
            self.skipTest("root bypasses chmod — can't simulate PermissionError")
        # Build decoy parent that matches the target's first segment prefix
        # so walk tries to enter it. Make it unreadable.
        first_segment = os.path.basename(self.target_dir).split(" ")[0]  # e.g. "path"
        decoy_parent = os.path.join(self.tmp_root, "decoy-perm")
        decoy_inner = os.path.join(decoy_parent, first_segment)
        os.makedirs(decoy_inner, exist_ok=True)
        os.chmod(decoy_parent, 0o000)
        try:
            # The real target still lives at self.target_dir under self.tmp_root,
            # and walk should find it via the correct parent despite the decoy
            # being unreadable. Primary assertion: no exception escapes.
            result = resolve_exec_cwd(
                self.session_path, stored_cwd="/nonexistent/force-slow-path"
            )
            self.assertEqual(result, self.target_dir)
        finally:
            os.chmod(decoy_parent, 0o755)


if __name__ == "__main__":
    unittest.main(verbosity=2)
