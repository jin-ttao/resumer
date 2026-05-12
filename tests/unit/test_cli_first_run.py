#!/usr/bin/env python3
"""Unit tests for first-run star message + XDG state sentinel.

Stdlib only. Run directly: `python3 tests/unit/test_cli_first_run.py`.
Also invoked by tests/run-qa.sh.
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from resumer import cli  # noqa: E402


class FirstRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="resumer-firstrun-test-")
        self._saved_xdg = os.environ.get("XDG_STATE_HOME")
        os.environ["XDG_STATE_HOME"] = self.tmp

    def tearDown(self):
        if self._saved_xdg is None:
            os.environ.pop("XDG_STATE_HOME", None)
        else:
            os.environ["XDG_STATE_HOME"] = self._saved_xdg
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _sentinel_path(self) -> str:
        return os.path.join(self.tmp, "resumer", "first-run-done")

    def test_state_dir_honors_xdg(self):
        self.assertEqual(cli._state_dir(), os.path.join(self.tmp, "resumer"))

    def test_state_dir_default_without_xdg(self):
        os.environ.pop("XDG_STATE_HOME", None)
        self.assertEqual(
            cli._state_dir(),
            os.path.join(os.path.expanduser("~/.local/state"), "resumer"),
        )

    def test_missing_bin_skips_both_message_and_sentinel(self):
        # Force shutil.which to return None — simulating claude/codex not installed.
        with mock.patch.object(cli, "shutil") as m:
            m.which.return_value = None
            err = io.StringIO()
            with mock.patch.object(sys, "stderr", err):
                cli._maybe_show_first_run_star("claude")
        self.assertFalse(os.path.exists(self._sentinel_path()),
                         "sentinel must not be created when bin missing")
        self.assertEqual(err.getvalue(), "", "no message when bin missing")

    def test_present_bin_prints_and_creates_sentinel(self):
        with mock.patch.object(cli, "shutil") as m:
            m.which.return_value = "/usr/local/bin/claude"
            err = io.StringIO()
            with mock.patch.object(sys, "stderr", err):
                cli._maybe_show_first_run_star("claude")
        self.assertTrue(os.path.exists(self._sentinel_path()),
                        "sentinel must be created on first successful gate")
        self.assertIn("⭐", err.getvalue())
        self.assertIn("github.com/jin-ttao/resumer", err.getvalue())

    def test_sentinel_present_is_silent(self):
        os.makedirs(os.path.dirname(self._sentinel_path()), exist_ok=True)
        with open(self._sentinel_path(), "w"):
            pass
        with mock.patch.object(cli, "shutil") as m:
            m.which.return_value = "/usr/local/bin/claude"
            err = io.StringIO()
            with mock.patch.object(sys, "stderr", err):
                cli._maybe_show_first_run_star("claude")
        self.assertEqual(err.getvalue(), "",
                         "message must not repeat when sentinel exists")


if __name__ == "__main__":
    unittest.main(verbosity=2)
