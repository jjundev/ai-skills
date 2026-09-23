#!/usr/bin/env python3
"""
Automated unit tests for merge_transcripts.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path so merge_transcripts can be imported
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from merge_transcripts import merge_transcripts


class TestMergeTranscripts(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_merge_transcripts_default_cleans_parts(self):
        """
        Verify that default keep_parts=False merges transcripts and deletes
        intermediate part files (*_part*.md, *_part*.mp3, *_temp.mp4),
        while leaving unrelated files intact.
        """
        part1_path = os.path.join(self.test_dir, "recording_part01.md")
        part2_path = os.path.join(self.test_dir, "recording_part02.md")
        mp3_part1 = os.path.join(self.test_dir, "recording_part01.mp3")
        mp3_part2 = os.path.join(self.test_dir, "recording_part02.mp3")
        temp_mp4 = os.path.join(self.test_dir, "recording_part01_temp.mp4")
        unrelated = os.path.join(self.test_dir, "unrelated_document.txt")

        with open(part1_path, "w", encoding="utf-8") as f:
            f.write("00:15\nThis is part one speaking.\n")
        with open(part2_path, "w", encoding="utf-8") as f:
            f.write("00:30\nThis is part two speaking.\n")
        with open(mp3_part1, "wb") as f:
            f.write(b"dummy mp3 1")
        with open(mp3_part2, "wb") as f:
            f.write(b"dummy mp3 2")
        with open(temp_mp4, "wb") as f:
            f.write(b"dummy mp4")
        with open(unrelated, "w", encoding="utf-8") as f:
            f.write("Keep this file safe.")

        result = merge_transcripts(self.test_dir, prefix="recording", keep_parts=False)
        expected_output = os.path.join(self.test_dir, "recording.md")

        # Check return value and output file existence
        self.assertEqual(result, expected_output)
        self.assertTrue(os.path.isfile(expected_output))

        with open(expected_output, "r", encoding="utf-8") as f:
            content = f.read()

        # Check content includes both parts
        self.assertIn("전체 오디오 전사본", content)
        self.assertIn("This is part one speaking.", content)
        self.assertIn("This is part two speaking.", content)

        # Check that intermediate parts were cleaned up
        self.assertFalse(os.path.exists(part1_path), "part01.md should be deleted")
        self.assertFalse(os.path.exists(part2_path), "part02.md should be deleted")
        self.assertFalse(os.path.exists(mp3_part1), "part01.mp3 should be deleted")
        self.assertFalse(os.path.exists(mp3_part2), "part02.mp3 should be deleted")
        self.assertFalse(os.path.exists(temp_mp4), "temp.mp4 should be deleted")

        # Unrelated file should NOT be deleted
        self.assertTrue(os.path.exists(unrelated), "Unrelated file should be preserved")

    def test_merge_transcripts_keep_parts(self):
        """
        Verify that keep_parts=True keeps all intermediate part files intact.
        """
        part1_path = os.path.join(self.test_dir, "recording_part01.md")
        part2_path = os.path.join(self.test_dir, "recording_part02.md")
        mp3_part1 = os.path.join(self.test_dir, "recording_part01.mp3")

        with open(part1_path, "w", encoding="utf-8") as f:
            f.write("01:00\nContent from part 1\n")
        with open(part2_path, "w", encoding="utf-8") as f:
            f.write("01:00\nContent from part 2\n")
        with open(mp3_part1, "wb") as f:
            f.write(b"dummy mp3")

        result = merge_transcripts(self.test_dir, prefix="recording", keep_parts=True)
        expected_output = os.path.join(self.test_dir, "recording.md")

        self.assertEqual(result, expected_output)
        self.assertTrue(os.path.isfile(expected_output))

        # Assert all intermediate part files still exist
        self.assertTrue(os.path.exists(part1_path), "part01.md should still exist")
        self.assertTrue(os.path.exists(part2_path), "part02.md should still exist")
        self.assertTrue(os.path.exists(mp3_part1), "mp3_part1 should still exist")

    def test_merge_transcripts_custom_output(self):
        """
        Verify custom output file handling, both relative and absolute paths.
        """
        part1_path = os.path.join(self.test_dir, "recording_part01.md")
        with open(part1_path, "w", encoding="utf-8") as f:
            f.write("00:10\nSample text\n")

        # Test relative custom output
        custom_relative = "custom_transcript.md"
        result_rel = merge_transcripts(
            self.test_dir,
            prefix="recording",
            keep_parts=True,
            output_file=custom_relative,
        )
        expected_rel = os.path.join(self.test_dir, custom_relative)
        self.assertEqual(result_rel, expected_rel)
        self.assertTrue(os.path.isfile(expected_rel))

        # Test absolute custom output in a subfolder
        nested_dir = os.path.join(self.test_dir, "nested_out")
        custom_abs = os.path.join(nested_dir, "final_output.md")
        result_abs = merge_transcripts(
            self.test_dir,
            prefix="recording",
            keep_parts=True,
            output_file=custom_abs,
        )
        self.assertEqual(result_abs, os.path.abspath(custom_abs))
        self.assertTrue(os.path.isfile(custom_abs))

    def test_merge_transcripts_timestamp_offset(self):
        """
        Verify that relative timestamps in each part are accurately recalculated
        based on part number and segment_seconds offset.
        With segment_seconds=600:
          - Part 1 offset is 0s: 01:30 -> 01:30
          - Part 2 offset is 600s: 01:30 -> 11:30
          - Part 3 offset is 1200s: 02:15 -> 22:15
        """
        part1_path = os.path.join(self.test_dir, "lecture_part01.md")
        part2_path = os.path.join(self.test_dir, "lecture_part02.md")
        part3_path = os.path.join(self.test_dir, "lecture_part03.md")

        with open(part1_path, "w", encoding="utf-8") as f:
            f.write("01:30\nPoint A in part 1\n09:45\nPoint B in part 1\n")

        with open(part2_path, "w", encoding="utf-8") as f:
            f.write("01:30\nPoint C in part 2\n05:10\nPoint D in part 2\n")

        with open(part3_path, "w", encoding="utf-8") as f:
            f.write("02:15\nPoint E in part 3\n")

        result = merge_transcripts(
            self.test_dir,
            prefix="lecture",
            segment_seconds=600,
            keep_parts=True,
            timestamps=True,
        )
        self.assertTrue(os.path.isfile(result))

        with open(result, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]

        # Check Part headers
        self.assertIn("## Part 01 (00:00 ~ )", lines)
        self.assertIn("## Part 02 (10:00 ~ )", lines)
        self.assertIn("## Part 03 (20:00 ~ )", lines)

        # In Part 1:
        self.assertIn("01:30", lines)
        self.assertIn("09:45", lines)

        # In Part 2 (offset +10:00):
        # 01:30 + 10:00 = 11:30
        # 05:10 + 10:00 = 15:10
        self.assertIn("11:30", lines)
        self.assertIn("15:10", lines)

        # In Part 3 (offset +20:00):
        # 02:15 + 20:00 = 22:15
        self.assertIn("22:15", lines)

    def test_merge_transcripts_default_strips_timestamps(self):
        """
        Verify that default timestamps=False strips MM:SS timestamp lines
        and outputs clean headers without time intervals.
        """
        part1_path = os.path.join(self.test_dir, "meeting_part01.md")
        part2_path = os.path.join(self.test_dir, "meeting_part02.md")

        with open(part1_path, "w", encoding="utf-8") as f:
            f.write("00:05\n안녕하세요 반갑습니다.\n\n00:20\n오늘 회의를 시작하겠습니다.\n")
        with open(part2_path, "w", encoding="utf-8") as f:
            f.write("01:10\n이어서 두 번째 안건입니다.\n")

        result = merge_transcripts(self.test_dir, prefix="meeting", keep_parts=True)
        self.assertTrue(os.path.isfile(result))

        with open(result, "r", encoding="utf-8") as f:
            content = f.read()

        # Headers should not contain (XX:00 ~ )
        self.assertIn("## Part 01\n", content)
        self.assertNotIn("## Part 01 (00:00 ~ )", content)
        self.assertIn("## Part 02\n", content)
        self.assertNotIn("## Part 02 (10:00 ~ )", content)

        # Timestamps should be stripped
        self.assertNotIn("00:05", content)
        self.assertNotIn("00:20", content)
        self.assertNotIn("11:10", content)

        # Content must be preserved
        self.assertIn("안녕하세요 반갑습니다.", content)
        self.assertIn("오늘 회의를 시작하겠습니다.", content)
        self.assertIn("이어서 두 번째 안건입니다.", content)

    def test_merge_transcripts_cli_timestamps_flag(self):
        """
        Verify CLI accepts --timestamps and -t flags, and outputs continuous
        timestamps and interval headers when specified.
        """
        script_path = str(SCRIPTS_DIR / "merge_transcripts.py")
        part1_path = os.path.join(self.test_dir, "cli_part01.md")
        with open(part1_path, "w", encoding="utf-8") as f:
            f.write("00:10\nCLI test text.\n")

        # Test with --timestamps
        out1 = os.path.join(self.test_dir, "cli_out1.md")
        cmd1 = [
            sys.executable,
            script_path,
            "--dir", self.test_dir,
            "--prefix", "cli",
            "--keep-parts",
            "--output", out1,
            "--timestamps",
        ]
        proc1 = subprocess.run(cmd1, capture_output=True, text=True)
        self.assertEqual(proc1.returncode, 0, f"CLI stderr: {proc1.stderr}")
        self.assertTrue(os.path.isfile(out1))
        with open(out1, "r", encoding="utf-8") as f:
            c1 = f.read()
        self.assertIn("## Part 01 (00:00 ~ )", c1)
        self.assertIn("00:10", c1)

        # Test with -t
        out2 = os.path.join(self.test_dir, "cli_out2.md")
        cmd2 = [
            sys.executable,
            script_path,
            "--dir", self.test_dir,
            "--prefix", "cli",
            "--keep-parts",
            "--output", out2,
            "-t",
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True)
        self.assertEqual(proc2.returncode, 0, f"CLI stderr: {proc2.stderr}")
        self.assertTrue(os.path.isfile(out2))
        with open(out2, "r", encoding="utf-8") as f:
            c2 = f.read()
        self.assertIn("## Part 01 (00:00 ~ )", c2)
        self.assertIn("00:10", c2)

        # Test default CLI (no timestamps flag)
        out3 = os.path.join(self.test_dir, "cli_out3.md")
        cmd3 = [
            sys.executable,
            script_path,
            "--dir", self.test_dir,
            "--prefix", "cli",
            "--keep-parts",
            "--output", out3,
        ]
        proc3 = subprocess.run(cmd3, capture_output=True, text=True)
        self.assertEqual(proc3.returncode, 0, f"CLI stderr: {proc3.stderr}")
        self.assertTrue(os.path.isfile(out3))
        with open(out3, "r", encoding="utf-8") as f:
            c3 = f.read()
        self.assertIn("## Part 01\n", c3)
        self.assertNotIn("## Part 01 (00:00 ~ )", c3)
        self.assertNotIn("00:10", c3)
        self.assertIn("CLI test text.", c3)

    def test_merge_transcripts_safety_on_error(self):
        """
        Verify safety on error: returns empty string "" and does not delete
        any unrelated files when no parts exist or invalid target directory is given.
        """
        # Scenario 1: Target directory has files, but none matching part pattern
        unrelated_txt = os.path.join(self.test_dir, "unrelated.txt")
        other_audio = os.path.join(self.test_dir, "recording_full.mp3")
        with open(unrelated_txt, "w", encoding="utf-8") as f:
            f.write("Do not delete me")
        with open(other_audio, "wb") as f:
            f.write(b"Audio data")

        result_empty = merge_transcripts(self.test_dir, prefix="recording")
        self.assertEqual(result_empty, "")
        self.assertTrue(os.path.exists(unrelated_txt), "unrelated.txt must be preserved on error")
        self.assertTrue(os.path.exists(other_audio), "other_audio must be preserved on error")

        # Scenario 2: Target directory does not exist
        non_existent_dir = os.path.join(self.test_dir, "does_not_exist")
        result_non_existent = merge_transcripts(non_existent_dir, prefix="recording")
        self.assertEqual(result_non_existent, "")


if __name__ == "__main__":
    unittest.main()
