import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from script.link import (
    is_skill_directory,
    is_link,
    remove_link_or_dir,
    create_link,
    save_existing_directory,
    link_skills,
    main,
)


class TestLink(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.repo_root = self.base / "repo"
        self.backup_root = self.base / "backup"
        self.host_root = self.base / "fake_home" / ".claude" / "skills"

        self.repo_root.mkdir(parents=True)
        self.backup_root.mkdir(parents=True)
        self.host_root.mkdir(parents=True)

        # Create managed skills in repo
        (self.repo_root / "skill-1").mkdir()
        (self.repo_root / "skill-1" / "SKILL.md").write_text("skill 1\n")
        (self.repo_root / "skill-2").mkdir()
        (self.repo_root / "skill-2" / "SKILL.md").write_text("skill 2\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_is_skill_directory(self):
        self.assertTrue(is_skill_directory(self.repo_root / "skill-1"))
        self.assertFalse(is_skill_directory(self.repo_root))
        non_dir = self.repo_root / "skill-1" / "SKILL.md"
        self.assertFalse(is_skill_directory(non_dir))

    def test_save_existing_directory(self):
        conflicting = self.host_root / "skill-1"
        conflicting.mkdir()
        (conflicting / "file.txt").write_text("old content")

        backup_dest = save_existing_directory(conflicting, "claude", self.backup_root)
        self.assertTrue(backup_dest.is_dir())
        self.assertFalse(conflicting.exists())
        self.assertTrue((backup_dest / "file.txt").is_file())

    def test_save_existing_directory_collision_handling(self):
        conflicting1 = self.host_root / "skill-1"
        conflicting1.mkdir()
        (conflicting1 / "file1.txt").write_text("content 1")
        backup1 = save_existing_directory(conflicting1, "claude", self.backup_root)

        conflicting2 = self.host_root / "skill-1"
        conflicting2.mkdir()
        (conflicting2 / "file2.txt").write_text("content 2")
        # Same timestamp folder / destination name collision
        backup2 = save_existing_directory(conflicting2, "claude", self.backup_root)

        self.assertTrue(backup1.is_dir())
        self.assertTrue(backup2.is_dir())
        self.assertNotEqual(backup1, backup2)

    def test_link_skills_creates_symlinks(self):
        with patch("script.link.GLOBAL_HOST_ROOTS", [("claude", self.host_root)]):
            res = link_skills(self.repo_root, self.backup_root)
            self.assertEqual(res, 0)

            # Check links created
            link1 = self.host_root / "skill-1"
            link2 = self.host_root / "skill-2"
            self.assertTrue(link1.exists())
            self.assertTrue(link2.exists())
            self.assertTrue(link1.is_symlink() or link1.is_dir())
            self.assertEqual((link1 / "SKILL.md").read_text(), "skill 1\n")

    def test_create_and_remove_link(self):
        target = self.repo_root / "skill-1"
        link_path = self.host_root / "link-1"
        create_link(target, link_path)
        self.assertTrue(is_link(link_path))
        self.assertTrue((link_path / "SKILL.md").exists())

        remove_link_or_dir(link_path)
        self.assertFalse(link_path.exists())
        self.assertFalse(is_link(link_path))

    def test_absorb_unmanaged_skill(self):
        # Create an unmanaged skill in host_root
        unmanaged = self.host_root / "external-skill"
        unmanaged.mkdir(parents=True)
        (unmanaged / "SKILL.md").write_text("external skill content\n")

        with patch("script.link.GLOBAL_HOST_ROOTS", [("claude", self.host_root)]):
            res = link_skills(self.repo_root, self.backup_root)
            self.assertEqual(res, 0)

            # Should be absorbed into repo_root
            repo_skill = self.repo_root / "external-skill"
            self.assertTrue(repo_skill.is_dir())
            self.assertEqual((repo_skill / "SKILL.md").read_text(), "external skill content\n")

            # And link created in host_root
            host_link = self.host_root / "external-skill"
            self.assertTrue(host_link.exists())
            self.assertTrue(is_link(host_link) or host_link.is_dir())

    def test_absorb_linked_skill(self):
        # Create an external directory outside repo
        external_dir = self.base / "some_other_place" / "linked-skill"
        external_dir.mkdir(parents=True)
        (external_dir / "SKILL.md").write_text("linked skill content\n")

        # Symlink it into host_root
        host_link = self.host_root / "linked-skill"
        create_link(external_dir, host_link)

        with patch("script.link.GLOBAL_HOST_ROOTS", [("claude", self.host_root)]):
            res = link_skills(self.repo_root, self.backup_root)
            self.assertEqual(res, 0)

            # Should be copied into repo_root
            repo_skill = self.repo_root / "linked-skill"
            self.assertTrue(repo_skill.is_dir())
            self.assertFalse(repo_skill.is_symlink())
            self.assertEqual((repo_skill / "SKILL.md").read_text(), "linked skill content\n")

    def test_skip_codex_runtime_and_non_skill(self):
        codex_root = self.base / "fake_home" / ".codex" / "skills"
        codex_root.mkdir(parents=True)
        (codex_root / ".system").mkdir()
        (codex_root / "codex-primary-runtime").mkdir()
        (codex_root / "not-a-skill").mkdir()
        (codex_root / "not-a-skill" / "random.txt").write_text("hello")

        with patch("script.link.GLOBAL_HOST_ROOTS", [("codex", codex_root)]):
            res = link_skills(self.repo_root, self.backup_root)
            self.assertEqual(res, 0)

            # Runtime and non-skill directories should NOT be absorbed
            self.assertFalse((self.repo_root / ".system").exists())
            self.assertFalse((self.repo_root / "codex-primary-runtime").exists())
            self.assertFalse((self.repo_root / "not-a-skill").exists())

            # They should still exist in codex_root
            self.assertTrue((codex_root / ".system").is_dir())
            self.assertTrue((codex_root / "codex-primary-runtime").is_dir())
            self.assertTrue((codex_root / "not-a-skill").is_dir())

    def test_conflict_with_non_skill_dir_in_host(self):
        # host_root already has skill-1 as a non-skill directory (no SKILL.md)
        conflicting = self.host_root / "skill-1"
        conflicting.mkdir()
        (conflicting / "config.json").write_text("{}")

        with patch("script.link.GLOBAL_HOST_ROOTS", [("claude", self.host_root)]):
            res = link_skills(self.repo_root, self.backup_root)
            self.assertEqual(res, 0)

            # skill-1 should not be overwritten
            self.assertTrue((conflicting / "config.json").is_file())
            self.assertFalse(conflicting.is_symlink())

            # skill-2 should still be linked
            self.assertTrue((self.host_root / "skill-2").exists())

    def test_link_skills_dry_run(self):
        unmanaged = self.host_root / "external-skill"
        unmanaged.mkdir(parents=True)
        (unmanaged / "SKILL.md").write_text("external skill content\n")

        with patch("script.link.GLOBAL_HOST_ROOTS", [("claude", self.host_root)]):
            res = link_skills(self.repo_root, self.backup_root, dry_run=True)
            self.assertEqual(res, 0)

            # Nothing moved into repo
            self.assertFalse((self.repo_root / "external-skill").exists())
            # Nothing linked into host
            self.assertFalse((self.host_root / "skill-1").exists())

    def test_is_link_windows_reparse_point(self):
        mock_path = MagicMock(spec=Path)
        mock_path.is_symlink.return_value = False
        mock_stat = MagicMock()
        mock_stat.st_file_attributes = 0x400  # Reparse point
        mock_path.lstat.return_value = mock_stat

        with patch("sys.platform", "win32"):
            self.assertTrue(is_link(mock_path))

        mock_stat.st_file_attributes = 0x10  # Regular directory
        with patch("sys.platform", "win32"):
            self.assertFalse(is_link(mock_path))

    def test_create_link_windows_winapi(self):
        target = self.repo_root / "skill-1"
        link_path = self.host_root / "winapi-link"
        mock_winapi = MagicMock()

        with patch("sys.platform", "win32"), \
             patch.dict("sys.modules", {"_winapi": mock_winapi}):
            create_link(target, link_path)
            mock_winapi.CreateJunction.assert_called_once_with(str(target), str(link_path))

    def test_create_link_windows_mklink(self):
        target = self.repo_root / "skill-1"
        link_path = self.host_root / "mklink-link"

        with patch("sys.platform", "win32"), \
             patch.dict("sys.modules", {"_winapi": None}), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            create_link(target, link_path)
            mock_run.assert_called_once_with(
                ["cmd", "/c", "mklink", "/J", str(link_path), str(target)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

    def test_create_link_windows_fallback_symlink(self):
        target = self.repo_root / "skill-1"
        link_path = self.host_root / "fallback-link"

        with patch("sys.platform", "win32"), \
             patch.dict("sys.modules", {"_winapi": None}), \
             patch("subprocess.run") as mock_run, \
             patch("os.symlink") as mock_symlink:
            mock_run.return_value = MagicMock(returncode=1)
            create_link(target, link_path)
            mock_symlink.assert_called_once_with(str(target), str(link_path), target_is_directory=True)

    def test_remove_link_or_dir_windows(self):
        mock_path = MagicMock(spec=Path)
        mock_path.is_symlink.return_value = False
        mock_stat = MagicMock()
        mock_stat.st_file_attributes = 0x400
        mock_path.lstat.return_value = mock_stat

        with patch("sys.platform", "win32"), \
             patch("os.rmdir") as mock_rmdir:
            remove_link_or_dir(mock_path)
            mock_rmdir.assert_called_once_with(mock_path)

    def test_main_cli(self):
        with patch("script.link.get_repo_root", return_value=self.repo_root), \
             patch("script.link.get_backup_root", return_value=self.backup_root), \
             patch("script.link.GLOBAL_HOST_ROOTS", [("claude", self.host_root)]):
            res = main(["--dry-run"])
            self.assertEqual(res, 0)


if __name__ == "__main__":
    unittest.main()
