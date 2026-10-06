import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from script import check_plugins
from script.check_plugins import (
    parse_github_owner_repo,
    check_plugin_bundle,
    check_internal_plugin_bundles,
    check_all_internal,
    format_terminal_output,
    main,
)


class TestCheckPluginsInternal(unittest.TestCase):
    def test_parse_github_owner_repo(self):
        self.assertEqual(
            parse_github_owner_repo("https://github.com/heygen-com/hyperframes.git"),
            ("heygen-com", "hyperframes"),
        )
        self.assertEqual(
            parse_github_owner_repo("https://github.com/jjundev/ai-skills"),
            ("jjundev", "ai-skills"),
        )
        self.assertIsNone(parse_github_owner_repo(""))
        self.assertIsNone(parse_github_owner_repo("https://gitlab.com/user/repo"))

    @patch("script.check_plugins.fetch_github_json")
    def test_check_plugin_bundle_hyperframes_outdated(self, mock_fetch):
        # mock plugin.json in upstream returning version 0.8.137 and head commit
        mock_fetch.side_effect = [
            {"version": "0.8.137"},
            [{"sha": "f6e419e123", "commit": {"committer": {"date": "2026-10-06T12:00:00Z"}, "message": "feat: new"}}],
        ]

        plugin_dir = Path("/fake/repo/plugins/hyperframes")
        with patch("pathlib.Path.is_file", return_value=True), \
             patch("pathlib.Path.read_text", return_value=json.dumps({"name": "hyperframes", "version": "0.8.72", "repository": "https://github.com/heygen-com/hyperframes"})):
            res = check_plugin_bundle(plugin_dir, Path("/fake/repo"))
            self.assertEqual(res["name"], "hyperframes")
            self.assertEqual(res["local_version"], "0.8.72")
            self.assertEqual(res["upstream_version"], "0.8.137")
            self.assertEqual(res["upstream_head_sha"], "f6e419e")
            self.assertFalse(res["up_to_date"])

    @patch("script.check_plugins.fetch_github_json")
    def test_check_plugin_bundle_up_to_date(self, mock_fetch):
        mock_fetch.side_effect = [
            {"version": "1.0.0"},
            [{"sha": "1234567", "commit": {"committer": {"date": "2026-10-06T12:00:00Z"}, "message": "feat: release"}}],
        ]

        plugin_dir = Path("/fake/repo/plugins/test-plugin")
        with patch("pathlib.Path.is_file", return_value=True), \
             patch("pathlib.Path.read_text", return_value=json.dumps({"name": "test-plugin", "version": "1.0.0", "repository": "https://github.com/test/test-plugin"})):
            res = check_plugin_bundle(plugin_dir, Path("/fake/repo"))
            self.assertEqual(res["local_version"], "1.0.0")
            self.assertEqual(res["upstream_version"], "1.0.0")
            self.assertTrue(res["up_to_date"])

    @patch("script.check_plugins.check_all")
    @patch("script.check_plugins.check_internal_plugin_bundles")
    def test_check_all_internal_aggregation(self, mock_bundles, mock_skills):
        mock_bundles.return_value = {
            "hyperframes": {"name": "hyperframes", "up_to_date": False},
            "ai-skills": {"name": "ai-skills", "up_to_date": True},
        }
        mock_skills.return_value = {
            "superpowers": {"name": "superpowers", "up_to_date": False},
            "caveman": {"name": "caveman", "up_to_date": True},
        }

        res = check_all_internal(Path("/fake/repo"))
        summary = res["summary"]
        self.assertEqual(summary["total_checked"], 4)
        self.assertEqual(summary["updates_available"], 2)
        self.assertEqual(summary["up_to_date"], 2)

    def test_format_terminal_output(self):
        sample_data = {
            "plugin_bundles": {
                "hyperframes": {
                    "path": "plugins/hyperframes",
                    "local_version": "0.8.72",
                    "upstream_version": "0.8.137",
                    "upstream_head_sha": "f6e419e",
                    "up_to_date": False,
                }
            },
            "upstream_skills": {
                "superpowers": {
                    "local_version": "v6.4.1",
                    "upstream_release": "v6.4.2",
                    "up_to_date": False,
                }
            },
            "summary": {
                "total_checked": 2,
                "updates_available": 2,
                "up_to_date": 0,
            },
        }
        text = format_terminal_output(sample_data)
        self.assertIn("AI-Skills 폴더 내부 플러그인 & 스킬 업데이트 점검", text)
        self.assertIn("hyperframes", text)
        self.assertIn("SUPERPOWERS", text)
        self.assertIn("업데이트 가능한 항목이 2개 있습니다", text)

    @patch("script.check_plugins.check_all_internal")
    @patch("script.check_plugins.get_repo_root")
    def test_main_terminal_and_json(self, mock_root, mock_check_internal):
        mock_root.return_value = Path("/fake/repo")
        mock_check_internal.return_value = {
            "plugin_bundles": {},
            "upstream_skills": {},
            "summary": {"total_checked": 0, "updates_available": 0, "up_to_date": 0, "unknown": 0},
        }

        # Terminal run
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main([])
        self.assertEqual(code, 0)
        self.assertIn("AI-Skills 폴더 내부 플러그인 & 스킬 업데이트 점검", buf.getvalue())

        # JSON run
        buf_json = io.StringIO()
        with patch("sys.stdout", buf_json):
            code = main(["--json"])
        self.assertEqual(code, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertIn("summary", parsed)


if __name__ == "__main__":
    unittest.main()
