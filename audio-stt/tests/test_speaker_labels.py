#!/usr/bin/env python3
"""
Unit tests for speaker-label handling in merge_transcripts.py
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from merge_transcripts import merge_transcripts


class TestSpeakerLabels(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _write(self, name, text):
        with open(os.path.join(self.test_dir, name), "w", encoding="utf-8") as f:
            f.write(text)

    def _merge(self, **kwargs):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            out = merge_transcripts(self.test_dir, prefix="rec", **kwargs)
        return out, err.getvalue()

    def test_speaker_lines_preserved(self):
        self._write("rec_part01.md", "**진행자:** 안녕하세요.\n\n**게스트:** 네.\n")
        out, err = self._merge(speakers=["진행자", "게스트"])
        text = Path(out).read_text(encoding="utf-8")
        self.assertIn("**진행자:** 안녕하세요.", text)
        self.assertIn("**게스트:** 네.", text)
        self.assertEqual(err, "")

    def test_timestamps_with_speakers(self):
        self._write("rec_part01.md", "00:05\n**진행자:** 첫 발화.\n")
        self._write("rec_part02.md", "00:10\n**게스트:** 둘째 발화.\n")
        out, _ = self._merge(speakers=["진행자", "게스트"], timestamps=True)
        text = Path(out).read_text(encoding="utf-8")
        self.assertIn("00:05\n**진행자:** 첫 발화.", text)
        self.assertIn("10:10\n**게스트:** 둘째 발화.", text)

    def test_unknown_label_warns_but_succeeds(self):
        self._write("rec_part01.md", "**진행자:** 하나.\n\n**낯선이:** 둘.\n")
        out, err = self._merge(speakers=["진행자", "게스트"])
        self.assertTrue(out)
        self.assertIn("낯선이", err)
        self.assertNotIn("진행자'", err)

    def test_unconfirmed_label_allowed(self):
        self._write("rec_part01.md", "**화자?:** 누군지 모름.\n")
        out, err = self._merge(speakers=["진행자"])
        self.assertTrue(out)
        self.assertEqual(err, "")

    def test_no_speakers_arg_keeps_legacy_behavior(self):
        self._write("rec_part01.md", "**낯선이:** 그대로.\n")
        out, err = self._merge()
        self.assertTrue(out)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
