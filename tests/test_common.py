import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from script.config import UPSTREAMS, GLOBAL_HOST_ROOTS, get_backup_root
from script.common import run_git, fetch_github_json, get_repo_root, Color


class TestConfigAndCommon(unittest.TestCase):
    def test_upstreams_configured(self):
        expected_keys = {"superpowers", "caveman", "taste-skill", "hyperframes", "ecc"}
        self.assertEqual(set(UPSTREAMS.keys()), expected_keys)
        for name, cfg in UPSTREAMS.items():
            self.assertEqual(cfg.name, name)
            self.assertTrue(len(cfg.skills) > 0)
            self.assertTrue(cfg.repo_url.startswith("https://"))

    def test_global_host_roots_non_empty(self):
        self.assertTrue(len(GLOBAL_HOST_ROOTS) >= 5)
        names = [name for name, _ in GLOBAL_HOST_ROOTS]
        self.assertIn("claude", names)
        self.assertIn("antigravity-config", names)
        self.assertIn("codex", names)

    def test_get_repo_root(self):
        root = get_repo_root()
        self.assertTrue(root.is_dir())
        self.assertTrue((root / "script").is_dir() or (root / "GLOBAL-SKILLS.md").is_file())

    def test_run_git_success(self):
        code, out, err = run_git(["status", "--short"])
        self.assertEqual(code, 0)
        self.assertIsInstance(out, str)

    @patch("urllib.request.urlopen")
    def test_fetch_github_json(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"tag_name": "v1.0.0"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        data = fetch_github_json("https://api.github.com/test")
        self.assertEqual(data, {"tag_name": "v1.0.0"})

    def test_color_formatting(self):
        self.assertTrue(Color.bold("test").startswith("\033[1m"))
        self.assertTrue(Color.bold("test").endswith("\033[0m"))


if __name__ == "__main__":
    unittest.main()
