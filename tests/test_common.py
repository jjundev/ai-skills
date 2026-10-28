import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from script.config import UPSTREAMS, GLOBAL_HOST_ROOTS, get_backup_root
from script.common import run_git, fetch_github_json, get_repo_root, Color
import tempfile


class TestConfigAndCommon(unittest.TestCase):
    def test_upstreams_configured(self):
        expected_keys = {"superpowers", "caveman", "taste-skill", "hyperframes", "ecc", "lateral-thinking", "imagegen-skills", "taste-skill-classics"}
        self.assertEqual(set(UPSTREAMS.keys()), expected_keys)
        for name, cfg in UPSTREAMS.items():
            self.assertEqual(cfg.name, name)
            self.assertTrue(len(cfg.skills) > 0)
            self.assertTrue(cfg.repo_url.startswith("https://"))

    def test_global_host_roots_non_empty(self):
        self.assertTrue(len(GLOBAL_HOST_ROOTS) >= 5)
        names = [name for name, _ in GLOBAL_HOST_ROOTS]
        self.assertIn("agents", names)
        self.assertIn("claude", names)
        self.assertIn("antigravity-config", names)
        self.assertNotIn("codex", names)

    def test_get_backup_root(self):
        self.assertEqual(get_backup_root(), Path.home() / ".ai-skills-backup")

    def test_get_repo_root(self):
        root = get_repo_root()
        self.assertTrue(root.is_dir())
        self.assertTrue((root / ".git").exists() or (root / "GLOBAL-SKILLS.md").is_file())

    def test_get_repo_root_worktree(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            git_file = tmp_path / ".git"
            git_file.write_text("gitdir: /some/path/to/.git/worktrees/wt\n", encoding="utf-8")
            sub_dir = tmp_path / "script"
            sub_dir.mkdir()
            common_file = sub_dir / "common.py"
            common_file.touch()

            with patch("script.common.__file__", str(common_file)):
                detected = get_repo_root()
                self.assertEqual(detected, tmp_path.resolve())

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

    @patch("urllib.request.urlopen")
    def test_fetch_github_json_with_token(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"tag_name": "v1.0.0"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_secret123"}):
            data = fetch_github_json("https://api.github.com/test")
            self.assertEqual(data, {"tag_name": "v1.0.0"})
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.headers.get("Authorization"), "Bearer ghp_secret123")

    def test_color_formatting_enabled(self):
        with patch.object(Color, "ENABLED", True):
            self.assertTrue(Color.bold("test").startswith("\033[1m"))
            self.assertTrue(Color.bold("test").endswith("\033[0m"))
            self.assertEqual(Color.green("ok"), "\033[0;32mok\033[0m")
            self.assertEqual(Color.red("fail"), "\033[0;31mfail\033[0m")

    def test_color_formatting_disabled(self):
        with patch.object(Color, "ENABLED", False):
            self.assertEqual(Color.bold("test"), "test")
            self.assertEqual(Color.green("ok"), "ok")
            self.assertEqual(Color.red("fail"), "fail")


if __name__ == "__main__":
    unittest.main()
