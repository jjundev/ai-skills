#!/usr/bin/env python3
"""
Unit test for audio-stt video wrapper duration synchronization.
Verifies that wrapping audio in 1-fps black MP4 using -t "$dur"
matches audio stream duration without trailing video silence.
"""

import os
import shutil
import subprocess
import tempfile
import unittest


class TestDurationSync(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_audio_and_video_duration_match(self):
        audio_path = os.path.join(self.test_dir, "test_audio.mp3")
        video_path = os.path.join(self.test_dir, "test_wrapped.mp4")

        # 1. Generate 5-second synthetic tone audio
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=5", audio_path],
            check=True,
            capture_output=True,
        )

        # 2. Extract exact audio duration
        dur = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
        ).decode().strip()

        # 3. Wrap with exact -t "$dur"
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:r=1",
                "-i", audio_path, "-t", dur, "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k", video_path
            ],
            check=True,
            capture_output=True,
        )

        # 4. Measure video container duration vs audio stream duration
        v_dur = float(
            subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            ).decode().strip()
        )
        a_dur = float(
            subprocess.check_output(
                ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            ).decode().strip()
        )

        # Discrepancy must be less than 0.05s (50ms)
        self.assertAlmostEqual(v_dur, a_dur, delta=0.05)
        self.assertAlmostEqual(v_dur, 5.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
