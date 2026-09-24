import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from script.config import UPSTREAMS
from script.common import Color
from script.check import (
    check_upstream,
    check_all,
    format_terminal_output,
    parse_local_version_and_sha,
    main,
)


class TestCheck(unittest.TestCase):
    def test_parse_local_version_and_sha(self):
        # Case 1: Release version format (superpowers)
        ver, sha = parse_local_version_and_sha("feat: upgrade superpowers to v6.3.0")
        self.assertEqual(ver, "v6.3.0")
        self.assertEqual(sha, "unknown")

        # Case 2: Commit sha format (ecc / hyperframes / taste-skill)
        ver, sha = parse_local_version_and_sha("chore: sync ecc (bf70150)")
        self.assertEqual(ver, "unknown")
        self.assertEqual(sha, "bf70150")

        # Case 3: Both version and sha
        ver, sha = parse_local_version_and_sha("chore: sync taste-skill v1.2.0 (c184364)")
        self.assertEqual(ver, "v1.2.0")
        self.assertEqual(sha, "c184364")

        # Case 4: Long sha in parentheses
        ver, sha = parse_local_version_and_sha("chore: sync hyperframes (115332f9876543210)")
        self.assertEqual(ver, "unknown")
        self.assertEqual(sha, "115332f")

        # Case 5: Empty / unparseable message
        ver, sha = parse_local_version_and_sha("")
        self.assertEqual(ver, "unknown")
        self.assertEqual(sha, "unknown")

    @patch("script.check.fetch_github_json")
    @patch("script.check.run_git")
    def test_check_upstream_up_to_date(self, mock_git, mock_fetch):
        # mock local git log
        mock_git.side_effect = [
            (0, "chore: sync ecc (bf70150)", ""),
            (0, "bf70150 (2 hours ago)", ""),
        ]
        # mock github api
        mock_fetch.return_value = [
            {
                "sha": "bf70150123456789",
                "commit": {
                    "committer": {"date": "2026-09-24T12:00:00Z"},
                    "message": "fix: update docs\n\nbody",
                },
            }
        ]

        res = check_upstream(UPSTREAMS["ecc"], Path("/fake/repo"))
        self.assertEqual(res["name"], "ecc")
        self.assertEqual(res["local_sha"], "bf70150")
        self.assertEqual(res["upstream_head_sha"], "bf70150")
        self.assertEqual(res["upstream_head_date"], "2026-09-24")
        self.assertEqual(res["upstream_head_msg"], "fix: update docs")
        self.assertTrue(res["up_to_date"])

    @patch("script.check.fetch_github_json")
    @patch("script.check.run_git")
    def test_check_upstream_needs_update(self, mock_git, mock_fetch):
        mock_git.side_effect = [
            (0, "chore: sync ecc (bf70150)", ""),
            (0, "bf70150 (2 hours ago)", ""),
        ]
        mock_fetch.return_value = [
            {
                "sha": "a1b2c3d123456789",
                "commit": {
                    "committer": {"date": "2026-09-24T15:00:00Z"},
                    "message": "feat: new skill",
                },
            }
        ]

        res = check_upstream(UPSTREAMS["ecc"], Path("/fake/repo"))
        self.assertEqual(res["local_sha"], "bf70150")
        self.assertEqual(res["upstream_head_sha"], "a1b2c3d")
        self.assertFalse(res["up_to_date"])

    @patch("script.check.fetch_github_json")
    @patch("script.check.run_git")
    def test_check_upstream_release_up_to_date(self, mock_git, mock_fetch):
        mock_git.side_effect = [
            (0, "feat: upgrade superpowers to v6.3.0", ""),
            (0, "fb6f761 (2 weeks ago)", ""),
        ]
        # mock release api and commits api
        mock_fetch.side_effect = [
            {"tag_name": "v6.3.0"},
            [
                {
                    "sha": "9999999123456789",
                    "commit": {
                        "committer": {"date": "2026-09-10T12:00:00Z"},
                        "message": "release: v6.3.0",
                    },
                }
            ],
        ]

        res = check_upstream(UPSTREAMS["superpowers"], Path("/fake/repo"))
        self.assertEqual(res["local_version"], "v6.3.0")
        self.assertEqual(res["upstream_release"], "v6.3.0")
        self.assertTrue(res["up_to_date"])

    @patch("script.check.fetch_github_json")
    @patch("script.check.run_git")
    def test_check_upstream_release_needs_update(self, mock_git, mock_fetch):
        mock_git.side_effect = [
            (0, "feat: upgrade superpowers to v6.2.0", ""),
            (0, "fb6f761 (3 weeks ago)", ""),
        ]
        mock_fetch.side_effect = [
            {"tag_name": "v6.3.0"},
            [
                {
                    "sha": "9999999123456789",
                    "commit": {
                        "committer": {"date": "2026-09-10T12:00:00Z"},
                        "message": "release: v6.3.0",
                    },
                }
            ],
        ]

        res = check_upstream(UPSTREAMS["superpowers"], Path("/fake/repo"))
        self.assertEqual(res["local_version"], "v6.2.0")
        self.assertEqual(res["upstream_release"], "v6.3.0")
        self.assertFalse(res["up_to_date"])

    @patch("script.check.fetch_github_json")
    @patch("script.check.run_git")
    def test_check_upstream_offline_or_error(self, mock_git, mock_fetch):
        mock_git.side_effect = [
            (0, "chore: sync ecc (bf70150)", ""),
            (0, "bf70150 (2 hours ago)", ""),
        ]
        mock_fetch.return_value = None

        res = check_upstream(UPSTREAMS["ecc"], Path("/fake/repo"))
        self.assertEqual(res["local_sha"], "bf70150")
        self.assertEqual(res["upstream_head_sha"], "")
        self.assertFalse(res["up_to_date"])

    @patch("script.check.fetch_github_json")
    @patch("script.check.run_git")
    def test_check_upstream_initial_sync_needed(self, mock_git, mock_fetch):
        # When no local commit matching pattern exists
        mock_git.side_effect = [
            (0, "", ""),
            (0, "", ""),
        ]
        mock_fetch.return_value = [
            {
                "sha": "a1b2c3d123456789",
                "commit": {
                    "committer": {"date": "2026-09-24T15:00:00Z"},
                    "message": "initial commit",
                },
            }
        ]

        res = check_upstream(UPSTREAMS["ecc"], Path("/fake/repo"))
        self.assertEqual(res["local_sha"], "unknown")
        self.assertEqual(res["local_commit"], "최초 동기화 필요")
        self.assertFalse(res["up_to_date"])

    @patch("script.check.check_upstream")
    def test_check_all_all_targets(self, mock_check_single):
        mock_check_single.return_value = {"up_to_date": True}
        results = check_all(Path("/fake/repo"))
        self.assertEqual(set(results.keys()), set(UPSTREAMS.keys()))
        self.assertEqual(mock_check_single.call_count, len(UPSTREAMS))

    @patch("script.check.check_upstream")
    def test_check_all_single_target(self, mock_check_single):
        mock_check_single.return_value = {"name": "ecc", "up_to_date": True}
        results = check_all(Path("/fake/repo"), target="ecc")
        self.assertEqual(list(results.keys()), ["ecc"])
        self.assertEqual(mock_check_single.call_count, 1)

    @patch("script.check.check_upstream")
    def test_check_all_invalid_target(self, mock_check_single):
        results = check_all(Path("/fake/repo"), target="nonexistent")
        self.assertEqual(results, {})
        self.assertEqual(mock_check_single.call_count, 0)

    def test_format_terminal_output_up_to_date(self):
        sample_results = {
            "ecc": {
                "name": "ecc",
                "url": "https://github.com/affaan-m/ECC",
                "local_sha": "bf70150",
                "local_commit": "bf70150 (2 hours ago)",
                "upstream_head_sha": "bf70150",
                "upstream_head_date": "2026-09-24",
                "upstream_head_msg": "fix: update docs",
                "up_to_date": True,
            }
        }
        # Test with Color enabled
        with patch.object(Color, "ENABLED", True):
            text_colored = format_terminal_output(sample_results)
            self.assertIn("ECC", text_colored)
            self.assertIn("최신", text_colored)
            self.assertIn("모든 대상 스킬셋이 최신 상태입니다", text_colored)

        # Test with Color disabled (e.g. headless/piped run)
        with patch.object(Color, "ENABLED", False):
            text_plain = format_terminal_output(sample_results)
            self.assertIn("ECC", text_plain)
            self.assertIn("최신", text_plain)
            self.assertIn("모든 대상 스킬셋이 최신 상태입니다", text_plain)
            self.assertNotIn("\033[", text_plain)

    def test_format_terminal_output_needs_update(self):
        sample_results = {
            "superpowers": {
                "name": "superpowers",
                "url": "https://github.com/obra/superpowers",
                "local_version": "v6.2.0",
                "local_commit": "fb6f761 (3 weeks ago)",
                "upstream_release": "v6.3.0",
                "upstream_head_sha": "a1b2c3d",
                "up_to_date": False,
            }
        }
        with patch.object(Color, "ENABLED", False):
            text = format_terminal_output(sample_results)
            self.assertIn("SUPERPOWERS", text)
            self.assertIn("업데이트 가능", text)
            self.assertIn("python3 script/manage.py sync", text)

    def test_format_terminal_output_offline(self):
        sample_results = {
            "caveman": {
                "name": "caveman",
                "url": "https://github.com/JuliusBrussee/caveman",
                "local_sha": "bf70150",
                "local_commit": "bf70150 (2 hours ago)",
                "upstream_head_sha": "",
                "up_to_date": False,
            }
        }
        with patch.object(Color, "ENABLED", False):
            text = format_terminal_output(sample_results)
            self.assertIn("CAVEMAN", text)
            self.assertIn("확인 불가", text)
            self.assertIn("네트워크 상태 확인 필요", text)

    def test_format_terminal_output_initial_sync(self):
        sample_results = {
            "taste-skill": {
                "name": "taste-skill",
                "url": "https://github.com/Leonxlnx/taste-skill",
                "local_sha": "unknown",
                "local_version": "unknown",
                "local_commit": "최초 동기화 필요",
                "upstream_head_sha": "c184364",
                "upstream_head_date": "2026-09-24",
                "upstream_head_msg": "init",
                "up_to_date": False,
            }
        }
        with patch.object(Color, "ENABLED", False):
            text = format_terminal_output(sample_results)
            self.assertIn("TASTE-SKILL", text)
            self.assertIn("최초 동기화 필요", text)

    def test_format_terminal_output_empty(self):
        with patch.object(Color, "ENABLED", False):
            text = format_terminal_output({})
            self.assertIn("확인할 대상 스킬셋이 없습니다", text)

    @patch("script.check.check_all")
    @patch("script.check.get_repo_root")
    def test_main_terminal_output(self, mock_root, mock_check_all):
        mock_root.return_value = Path("/fake/repo")
        mock_check_all.return_value = {
            "ecc": {
                "name": "ecc",
                "url": "https://github.com/affaan-m/ECC",
                "local_sha": "bf70150",
                "local_commit": "bf70150 (2 hours ago)",
                "upstream_head_sha": "bf70150",
                "upstream_head_date": "2026-09-24",
                "upstream_head_msg": "fix: update docs",
                "up_to_date": True,
            }
        }
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main([])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("ECC", output)
        self.assertIn("AI Skills Upstream Status Check", output)

    @patch("script.check.check_all")
    @patch("script.check.get_repo_root")
    def test_main_json_output(self, mock_root, mock_check_all):
        mock_root.return_value = Path("/fake/repo")
        mock_check_all.return_value = {
            "ecc": {
                "name": "ecc",
                "url": "https://github.com/affaan-m/ECC",
                "local_sha": "bf70150",
                "up_to_date": True,
            }
        }
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--json"])
        self.assertEqual(code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["ecc"]["name"], "ecc")
        self.assertTrue(parsed["ecc"]["up_to_date"])

    @patch("script.check.check_all")
    @patch("script.check.get_repo_root")
    def test_main_target_filter(self, mock_root, mock_check_all):
        mock_root.return_value = Path("/fake/repo")
        mock_check_all.return_value = {}
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--target", "ecc"])
        self.assertEqual(code, 0)
        mock_check_all.assert_called_once_with(Path("/fake/repo"), target="ecc")


if __name__ == "__main__":
    unittest.main()
