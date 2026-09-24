import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from script.config import UpstreamConfig
from script.common import run_git, Color
from script.sync import sync_upstream, sync_all, sync_hyperframes_extras, main


def make_mock_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-q"], cwd=path)
    run_git(["config", "user.name", "test"], cwd=path)
    run_git(["config", "user.email", "test@test.com"], cwd=path)
    run_git(["config", "commit.gpgsign", "false"], cwd=path)


class TestSync(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.upstream = self.base / "upstream"
        self.local = self.base / "local"

        make_mock_git_repo(self.upstream)
        make_mock_git_repo(self.local)

        # populate upstream with skills
        (self.upstream / "skills" / "skill-a").mkdir(parents=True)
        (self.upstream / "skills" / "skill-a" / "SKILL.md").write_text("upstream skill a\n")
        (self.upstream / "skills" / "skill-b").mkdir(parents=True)
        (self.upstream / "skills" / "skill-b" / "SKILL.md").write_text("upstream skill b\n")
        (self.upstream / "skills" / "unlisted").mkdir(parents=True)
        (self.upstream / "skills" / "unlisted" / "SKILL.md").write_text("unlisted\n")

        run_git(["add", "-A"], cwd=self.upstream)
        run_git(["commit", "-q", "-m", "initial upstream commit"], cwd=self.upstream)
        run_git(["tag", "v1.0.0"], cwd=self.upstream)

        # initial local commit
        (self.local / "local-only").mkdir(parents=True)
        (self.local / "local-only" / "SKILL.md").write_text("local only\n")
        run_git(["add", "-A"], cwd=self.local)
        run_git(["commit", "-q", "-m", "init local"], cwd=self.local)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sync_allowlisted_skills_and_commit(self):
        # Create a stale file inside skill-a locally to verify it gets deleted
        (self.local / "skill-a").mkdir(parents=True, exist_ok=True)
        (self.local / "skill-a" / "stale.txt").write_text("stale\n")

        cfg = UpstreamConfig(
            name="test-upstream",
            repo_url=str(self.upstream),
            skills=["skill-a", "missing-skill"],
            version_type="release",
        )

        code, synced, warns = sync_upstream(cfg, self.local, no_commit=False)
        self.assertEqual(code, 0)
        self.assertEqual(synced, ["skill-a"])
        self.assertEqual(warns, 1)

        # Check skill copied
        self.assertTrue((self.local / "skill-a" / "SKILL.md").is_file())
        self.assertEqual((self.local / "skill-a" / "SKILL.md").read_text(), "upstream skill a\n")
        # Check stale file was removed
        self.assertFalse((self.local / "skill-a" / "stale.txt").exists())
        # Unlisted skill not copied
        self.assertFalse((self.local / "unlisted").exists())
        # Local-only skill untouched
        self.assertTrue((self.local / "local-only" / "SKILL.md").is_file())

        # Check commit created with tag provenance
        _, log_msg, _ = run_git(["log", "-n", "1", "--pretty=format:%s"], cwd=self.local)
        self.assertTrue(log_msg.startswith("chore: sync test-upstream v1.0.0 ("))

    def test_sync_without_tag_commit(self):
        # Create commit on upstream without tag
        (self.upstream / "skills" / "skill-a" / "SKILL.md").write_text("upstream skill a v2\n")
        run_git(["commit", "-q", "-am", "upstream v2 without tag"], cwd=self.upstream)

        cfg = UpstreamConfig(
            name="test-upstream",
            repo_url=str(self.upstream),
            skills=["skill-a"],
            version_type="commit",
        )

        code, synced, warns = sync_upstream(cfg, self.local, no_commit=False)
        self.assertEqual(code, 0)
        self.assertEqual(synced, ["skill-a"])
        self.assertEqual(warns, 0)

        _, log_msg, _ = run_git(["log", "-n", "1", "--pretty=format:%s"], cwd=self.local)
        self.assertTrue(log_msg.startswith("chore: sync test-upstream ("))
        self.assertNotIn("v1.0.0", log_msg)

    def test_sync_no_commit_flag(self):
        cfg = UpstreamConfig(
            name="test-upstream",
            repo_url=str(self.upstream),
            skills=["skill-a"],
            version_type="release",
        )

        code, synced, warns = sync_upstream(cfg, self.local, no_commit=True)
        self.assertEqual(code, 0)
        self.assertTrue((self.local / "skill-a" / "SKILL.md").is_file())

        # git status should show untracked/dirty files, commit count unchanged
        _, count, _ = run_git(["rev-list", "--count", "HEAD"], cwd=self.local)
        self.assertEqual(count, "1")

    def test_sync_no_changes_up_to_date(self):
        cfg = UpstreamConfig(
            name="test-upstream",
            repo_url=str(self.upstream),
            skills=["skill-a"],
            version_type="release",
        )

        # First sync
        code1, _, _ = sync_upstream(cfg, self.local, no_commit=False)
        self.assertEqual(code1, 0)
        _, count1, _ = run_git(["rev-list", "--count", "HEAD"], cwd=self.local)
        self.assertEqual(count1, "2")

        # Second sync with no changes upstream
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code2, _, _ = sync_upstream(cfg, self.local, no_commit=False)
        self.assertEqual(code2, 0)
        _, count2, _ = run_git(["rev-list", "--count", "HEAD"], cwd=self.local)
        self.assertEqual(count2, "2")
        self.assertIn("already up-to-date", buf.getvalue())

    def test_sync_clone_failure_safe_transactional(self):
        cfg = UpstreamConfig(
            name="invalid-upstream",
            repo_url="/non/existent/repo/path",
            skills=["skill-a"],
            version_type="commit",
        )

        err_buf = io.StringIO()
        with patch("sys.stderr", err_buf):
            code, synced, warns = sync_upstream(cfg, self.local, no_commit=False)
        self.assertEqual(code, 1)
        self.assertEqual(synced, [])
        self.assertEqual(warns, 0)
        # Verify local repository was not modified
        self.assertFalse((self.local / "skill-a").exists())
        self.assertTrue((self.local / "local-only" / "SKILL.md").is_file())
        _, count, _ = run_git(["rev-list", "--count", "HEAD"], cwd=self.local)
        self.assertEqual(count, "1")

    def test_sync_all_skills_missing_returns_error(self):
        cfg = UpstreamConfig(
            name="test-upstream",
            repo_url=str(self.upstream),
            skills=["non-existent-skill"],
            version_type="commit",
        )
        err_buf = io.StringIO()
        with patch("sys.stderr", err_buf):
            code, synced, warns = sync_upstream(cfg, self.local, no_commit=False)
        self.assertEqual(code, 1)
        self.assertEqual(synced, [])
        self.assertEqual(warns, 1)

    def test_sync_hyperframes_extras(self):
        # Setup hyperframes upstream structure
        hf_upstream = self.base / "hf_upstream"
        make_mock_git_repo(hf_upstream)
        (hf_upstream / "skills" / "hyperframes").mkdir(parents=True)
        (hf_upstream / "skills" / "hyperframes" / "SKILL.md").write_text("hf router\n")
        (hf_upstream / "assets").mkdir(parents=True)
        (hf_upstream / "assets" / "icon.png").write_text("icon data\n")
        (hf_upstream / ".claude-plugin").mkdir(parents=True)
        (hf_upstream / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "1.2.3"}))
        (hf_upstream / ".codex-plugin").mkdir(parents=True)
        (hf_upstream / ".codex-plugin" / "descriptor.json").write_text("{}")
        run_git(["add", "-A"], cwd=hf_upstream)
        run_git(["commit", "-q", "-m", "init hf upstream"], cwd=hf_upstream)
        run_git(["tag", "v1.2.3"], cwd=hf_upstream)

        # Setup local marketplace.json
        marketplace_dir = self.local / ".agents" / "plugins"
        marketplace_dir.mkdir(parents=True)
        (marketplace_dir / "marketplace.json").write_text(json.dumps({
            "name": "ai-skills",
            "plugins": [{"name": "existing-plugin"}]
        }))
        run_git(["add", "-A"], cwd=self.local)
        run_git(["commit", "-q", "-m", "add marketplace"], cwd=self.local)

        cfg = UpstreamConfig(
            name="hyperframes",
            repo_url=str(hf_upstream),
            skills=["hyperframes"],
            version_type="commit",
            extra_targets=["plugins/hyperframes", "plugins/ai-skills/skills"],
        )

        code, synced, warns = sync_upstream(cfg, self.local, no_commit=False)
        self.assertEqual(code, 0)
        self.assertEqual(synced, ["hyperframes"])
        self.assertEqual(warns, 0)

        # Check root skill
        self.assertTrue((self.local / "hyperframes" / "SKILL.md").is_file())
        # Check portable plugin skill
        self.assertTrue((self.local / "plugins" / "hyperframes" / "skills" / "hyperframes" / "SKILL.md").is_file())
        # Check ai-skills bundle skill
        self.assertTrue((self.local / "plugins" / "ai-skills" / "skills" / "hyperframes" / "SKILL.md").is_file())
        # Check assets copied
        self.assertTrue((self.local / "plugins" / "hyperframes" / "assets" / "icon.png").is_file())
        # Check descriptors copied
        self.assertTrue((self.local / "plugins" / "hyperframes" / ".claude-plugin" / "plugin.json").is_file())
        self.assertTrue((self.local / "plugins" / "hyperframes" / ".codex-plugin" / "descriptor.json").is_file())
        # Check generated plugin.json
        plugin_json = json.loads((self.local / "plugins" / "hyperframes" / "plugin.json").read_text())
        self.assertEqual(plugin_json["name"], "hyperframes")
        self.assertEqual(plugin_json["version"], "1.2.3")
        # Check marketplace registration
        m_data = json.loads((marketplace_dir / "marketplace.json").read_text())
        names = [p["name"] for p in m_data["plugins"]]
        self.assertIn("hyperframes", names)

        # Check commit
        _, log_msg, _ = run_git(["log", "-n", "1", "--pretty=format:%s"], cwd=self.local)
        self.assertTrue(log_msg.startswith("chore: sync hyperframes v1.2.3 ("))

    @patch("script.sync.sync_upstream")
    def test_sync_all_target_filter(self, mock_sync_up):
        mock_sync_up.return_value = (0, ["skill-a"], 0)
        res = sync_all(self.local, target="superpowers", no_commit=False)
        self.assertEqual(res, 0)
        self.assertEqual(mock_sync_up.call_count, 1)
        self.assertEqual(mock_sync_up.call_args[0][0].name, "superpowers")

    @patch("script.sync.sync_upstream")
    def test_sync_all_warning_summary(self, mock_sync_up):
        mock_sync_up.return_value = (0, ["skill-a"], 2)
        err_buf = io.StringIO()
        with patch("sys.stderr", err_buf):
            res = sync_all(self.local, target="superpowers", no_commit=False)
        self.assertEqual(res, 0)
        self.assertIn("2 allowlisted skill(s) missing upstream across syncs", err_buf.getvalue())

    @patch("script.sync.sync_all")
    @patch("script.sync.get_repo_root")
    def test_main_cli(self, mock_root, mock_sync_all):
        mock_root.return_value = self.local
        mock_sync_all.return_value = 0
        code = main(["--target", "superpowers", "--no-commit"])
        self.assertEqual(code, 0)
        mock_sync_all.assert_called_once_with(self.local, target="superpowers", no_commit=True)

    def test_tty_and_headless_determinism(self):
        # Headless with NO_COLOR=1
        with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            Color.ENABLED = False
            raw = Color.green("testing")
            self.assertEqual(raw, "testing")

        # Piped/headless (isatty is False)
        with patch.dict(os.environ, {}, clear=True):
            Color.ENABLED = False
            raw = Color.green("testing")
            self.assertEqual(raw, "testing")

        # TTY forced
        with patch.dict(os.environ, {"FORCE_COLOR": "1"}, clear=False):
            Color.ENABLED = True
            colored = Color.green("testing")
            self.assertEqual(colored, "\033[0;32mtesting\033[0m")


    def test_sync_commit_failure(self):
        from script.common import run_git as real_run_git

        def mock_git(args, cwd=None):
            if len(args) > 0 and args[0] == "commit":
                return 1, "", "fatal: git commit failed"
            return real_run_git(args, cwd=cwd)

        cfg = UpstreamConfig(
            name="test-upstream",
            repo_url=str(self.upstream),
            skills=["skill-a"],
            version_type="release",
        )
        err_buf = io.StringIO()
        with patch("script.sync.run_git", side_effect=mock_git), patch("sys.stderr", err_buf):
            code, synced, warns = sync_upstream(cfg, self.local, no_commit=False)
        self.assertEqual(code, 1)
        self.assertEqual(synced, ["skill-a"])
        self.assertIn("Failed to commit test-upstream", err_buf.getvalue())

    def test_sync_all_unknown_target(self):
        err_buf = io.StringIO()
        with patch("sys.stderr", err_buf):
            res = sync_all(self.local, target="non-existent-target", no_commit=False)
        self.assertEqual(res, 1)
        self.assertIn("Unknown upstream target", err_buf.getvalue())

    def test_cli_subprocess_execution(self):
        import subprocess
        import sys
        import script.sync
        script_path = Path(script.sync.__file__).resolve()
        proc = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Sync curated skills from upstream repositories.", proc.stdout)


if __name__ == "__main__":
    unittest.main()
