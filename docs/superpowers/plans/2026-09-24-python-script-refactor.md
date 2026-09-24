# Python-based Cross-Platform Script Migration & Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate 8 legacy root shell/PowerShell scripts into a cross-platform (Windows & macOS), zero-dependency Python 3 package under `script/`, delete obsolete root scripts, and migrate tests to `unittest`.

**Architecture:** A modular Python standard library toolchain under `script/` featuring declarative upstream configs (`config.py`), isolated Git/GitHub helpers (`common.py`), status checker (`check.py`), atomic clone & sync engine (`sync.py`), cross-platform NTFS Junction / POSIX symlink manager (`link.py`), and unified CLI router (`manage.py`).

**Tech Stack:** Python 3.8+ (Standard Library only: `urllib.request`, `json`, `argparse`, `pathlib`, `shutil`, `subprocess`, `unittest`, `tempfile`, `sys`, `os`).

**Spec:** Chat design spec approved in the previous `/grill-yourself` session.

## Global Constraints

- Zero pip / third-party dependencies: strictly Python standard library.
- Cross-platform support: Windows (NTFS directory junctions via `mklink /J` or `_winapi`) and macOS/Linux (POSIX symlinks via `os.symlink`).
- Git commit message compatibility: `chore: sync <name> [tag] (<sha7>)` format must be preserved exactly for version log parsing.
- Safe transactional sync: Always clone to `tempfile.TemporaryDirectory` first; never mutate local directories if clone fails.
- Root cleanup: Remove all 8 legacy scripts (`check-*.sh`, `sync-*.sh`, `link-global-skills.ps1`) from the repository root.
- All tasks must follow TDD (failing test -> pass -> verify -> commit).

---

### Task 1: Scaffolding, Configuration, and Common Utilities (`script/config.py`, `script/common.py`)

**Files:**
- Create: `script/__init__.py`
- Create: `script/config.py`
- Create: `script/common.py`
- Create: `tests/__init__.py`
- Test: `tests/test_common.py`

**Interfaces:**
- Consumes: Standard library (`pathlib`, `subprocess`, `urllib.request`, `json`, `dataclasses`, `os`, `sys`).
- Produces:
  - `UpstreamConfig` dataclass and `UPSTREAMS: dict[str, UpstreamConfig]` in `script/config.py`.
  - `GLOBAL_HOST_ROOTS: list[tuple[str, Path]]` in `script/config.py`.
  - `run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]` in `script/common.py`.
  - `fetch_github_json(url: str, timeout: int = 5) -> dict | list | None` in `script/common.py`.
  - `get_repo_root() -> Path` in `script/common.py`.
  - `Color` class in `script/common.py`.

- [ ] **Step 1: Write the failing test for common utilities and configuration**

Create `tests/test_common.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_common.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'script'`

- [ ] **Step 3: Write minimal implementation**

Create `script/__init__.py`:
```python
"""AI Skills management package."""
```

Create `tests/__init__.py`:
```python
"""AI Skills test package."""
```

Create `script/config.py`:
```python
from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class UpstreamConfig:
    name: str
    repo_url: str
    skills: list[str]
    version_type: str  # "release" or "commit"
    release_api_url: str | None = None
    commits_api_url: str = ""
    extra_targets: list[str] = field(default_factory=list)
    grep_pattern: str = ""


USER_HOME = Path.home()

GLOBAL_HOST_ROOTS: list[tuple[str, Path]] = [
    ("agents", USER_HOME / ".agents" / "skills"),
    ("antigravity-config", USER_HOME / ".gemini" / "config" / "skills"),
    ("antigravity-cli", USER_HOME / ".gemini" / "antigravity-cli" / "skills"),
    ("claude", USER_HOME / ".claude" / "skills"),
    ("codex", USER_HOME / ".codex" / "skills"),
    ("antigravity-legacy", USER_HOME / ".gemini" / "antigravity" / ".agents" / "skills"),
]


def get_backup_root() -> Path:
    return USER_HOME / ".ai-skills-backup"


UPSTREAMS: dict[str, UpstreamConfig] = {
    "superpowers": UpstreamConfig(
        name="superpowers",
        repo_url=os.environ.get("SUPERPOWERS_REPO", "https://github.com/obra/superpowers.git"),
        skills=[
            "brainstorming",
            "dispatching-parallel-agents",
            "executing-plans",
            "finishing-a-development-branch",
            "receiving-code-review",
            "requesting-code-review",
            "subagent-driven-development",
            "systematic-debugging",
            "test-driven-development",
            "using-git-worktrees",
            "using-superpowers",
            "verification-before-completion",
            "writing-plans",
            "writing-skills",
        ],
        version_type="release",
        release_api_url="https://api.github.com/repos/obra/superpowers/releases/latest",
        commits_api_url="https://api.github.com/repos/obra/superpowers/commits?per_page=1",
        grep_pattern="superpowers",
    ),
    "caveman": UpstreamConfig(
        name="caveman",
        repo_url=os.environ.get("CAVEMAN_REPO", "https://github.com/JuliusBrussee/caveman.git"),
        skills=[
            "caveman",
            "caveman-commit",
            "caveman-compress",
            "caveman-explore",
            "caveman-help",
            "caveman-review",
            "migration",
        ],
        version_type="commit",
        commits_api_url="https://api.github.com/repos/JuliusBrussee/caveman/commits?per_page=1",
        grep_pattern="caveman",
    ),
    "taste-skill": UpstreamConfig(
        name="taste-skill",
        repo_url=os.environ.get("TASTE_REPO", "https://github.com/Leonxlnx/taste-skill.git"),
        skills=[
            "taste-skill",
            "image-to-code-skill",
            "imagegen-frontend-web",
            "imagegen-frontend-mobile",
            "redesign-skill",
            "stitch-skill",
            "brandkit",
            "minimalist-skill",
            "soft-skill",
            "brutalist-skill",
        ],
        version_type="commit",
        commits_api_url="https://api.github.com/repos/Leonxlnx/taste-skill/commits?per_page=1",
        grep_pattern="sync taste-skill",
    ),
    "hyperframes": UpstreamConfig(
        name="hyperframes",
        repo_url=os.environ.get("HYPERFRAMES_REPO", "https://github.com/heygen-com/hyperframes.git"),
        skills=[
            "embedded-captions",
            "faceless-explainer",
            "figma",
            "general-video",
            "hyperframes",
            "hyperframes-animation",
            "hyperframes-audio",
            "hyperframes-cli",
            "hyperframes-core",
            "hyperframes-creative",
            "hyperframes-keyframes",
            "hyperframes-registry",
            "hyperframes-studio",
            "media-use",
            "motion-graphics",
            "music-to-video",
            "pr-to-video",
            "product-launch-video",
            "remotion-to-hyperframes",
            "slideshow",
            "talking-head-recut",
        ],
        version_type="commit",
        commits_api_url="https://api.github.com/repos/heygen-com/hyperframes/commits?per_page=1",
        extra_targets=["plugins/hyperframes", "plugins/ai-skills/skills"],
        grep_pattern="sync hyperframes",
    ),
    "ecc": UpstreamConfig(
        name="ecc",
        repo_url=os.environ.get("ECC_REPO", "https://github.com/affaan-m/ECC.git"),
        skills=[
            "architecture-decision-records",
            "hexagonal-architecture",
            "api-design",
            "mcp-server-patterns",
            "backend-patterns",
            "fastapi-patterns",
            "database-migrations",
            "docker-patterns",
            "council",
            "security-review",
        ],
        version_type="commit",
        commits_api_url="https://api.github.com/repos/affaan-m/ECC/commits?per_page=1",
        grep_pattern="sync ecc",
    ),
}
```

Create `script/common.py`:
```python
from pathlib import Path
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error


def get_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current.parent] + list(current.parents):
        if (parent / ".git").is_dir() or (parent / "GLOBAL-SKILLS.md").is_file():
            return parent
    return current.parent.parent


def run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    target_cwd = cwd or get_repo_root()
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    proc = subprocess.run(
        ["git", "-C", str(target_cwd)] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def fetch_github_json(url: str, timeout: int = 5) -> dict | list | None:
    if not url:
        return None
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ai-skills-manager"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


class Color:
    ENABLED = sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1"

    @classmethod
    def wrap(cls, text: str, code: str) -> str:
        if cls.ENABLED:
            return f"\033[{code}m{text}\033[0m"
        return text

    @classmethod
    def bold(cls, text: str) -> str:
        return cls.wrap(text, "1")

    @classmethod
    def green(cls, text: str) -> str:
        return cls.wrap(text, "0;32")

    @classmethod
    def yellow(cls, text: str) -> str:
        return cls.wrap(text, "0;33")

    @classmethod
    def red(cls, text: str) -> str:
        return cls.wrap(text, "0;31")

    @classmethod
    def cyan(cls, text: str) -> str:
        return cls.wrap(text, "0;36")

    @classmethod
    def gray(cls, text: str) -> str:
        return cls.wrap(text, "0;90")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_common.py`
Expected: `Ran 6 tests in ...s OK`

- [ ] **Step 5: Commit**

```bash
git add script/__init__.py script/config.py script/common.py tests/__init__.py tests/test_common.py
git commit -m "feat(script): add core configuration and common utilities"
```

---

### Task 2: Upstream Status Checker (`script/check.py`)

**Files:**
- Create: `script/check.py`
- Test: `tests/test_check.py`

**Interfaces:**
- Consumes: `script/config.py`, `script/common.py`.
- Produces:
  - `check_upstream(config: UpstreamConfig, repo_root: Path) -> dict` in `script/check.py`.
  - `check_all(repo_root: Path, target: str | None = None) -> dict[str, dict]` in `script/check.py`.
  - `format_terminal_output(results: dict[str, dict]) -> str` in `script/check.py`.
  - `main(argv: list[str] | None = None) -> int` in `script/check.py`.

- [ ] **Step 1: Write the failing test for check logic**

Create `tests/test_check.py`:
```python
import unittest
from pathlib import Path
from unittest.mock import patch
from script.config import UPSTREAMS
from script.check import check_upstream, check_all, format_terminal_output


class TestCheck(unittest.TestCase):
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
        self.assertEqual(res["local_sha"], "bf70150")
        self.assertEqual(res["upstream_head_sha"], "bf70150")
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

    def test_format_terminal_output(self):
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
        text = format_terminal_output(sample_results)
        self.assertIn("ECC", text)
        self.assertIn("최신", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_check.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'script.check'`

- [ ] **Step 3: Write minimal implementation**

Create `script/check.py`:
```python
from pathlib import Path
import argparse
import json
import re
import sys
from script.config import UPSTREAMS, UpstreamConfig
from script.common import run_git, fetch_github_json, get_repo_root, Color


def parse_local_version_and_sha(msg: str) -> tuple[str, str]:
    ver_match = re.search(r"v\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9.]+)?", msg)
    version = ver_match.group(0) if ver_match else "unknown"

    sha_match = re.search(r"\(([a-f0-9]{7})\)", msg)
    sha = sha_match.group(1) if sha_match else "unknown"
    return version, sha


def check_upstream(config: UpstreamConfig, repo_root: Path) -> dict:
    _, commit_msg, _ = run_git(
        ["log", f"--grep={config.grep_pattern}", "-n", "1", "--pretty=format:%s"],
        cwd=repo_root,
    )
    _, commit_summary, _ = run_git(
        ["log", f"--grep={config.grep_pattern}", "-n", "1", "--pretty=format:%h (%cr)"],
        cwd=repo_root,
    )

    local_version, local_sha = parse_local_version_and_sha(commit_msg)

    upstream_release = ""
    if config.release_api_url:
        release_data = fetch_github_json(config.release_api_url)
        if isinstance(release_data, dict):
            upstream_release = release_data.get("tag_name", "")

    upstream_head_sha = ""
    upstream_head_date = ""
    upstream_head_msg = ""
    commits_data = fetch_github_json(config.commits_api_url)
    if isinstance(commits_data, list) and len(commits_data) > 0:
        head = commits_data[0]
        upstream_head_sha = head.get("sha", "")[:7]
        commit_obj = head.get("commit", {})
        committer = commit_obj.get("committer", {})
        upstream_head_date = committer.get("date", "")[:10]
        upstream_head_msg = commit_obj.get("message", "").split("\n")[0]

    up_to_date = False
    if config.version_type == "release" and upstream_release:
        up_to_date = (local_version == upstream_release)
    elif upstream_head_sha and (local_sha == upstream_head_sha or upstream_head_sha in commit_msg):
        up_to_date = True

    return {
        "name": config.name,
        "url": config.repo_url[:-4] if config.repo_url.endswith(".git") else config.repo_url,
        "local_version": local_version,
        "local_sha": local_sha,
        "local_commit": commit_summary or "최초 동기화 필요",
        "upstream_release": upstream_release,
        "upstream_head_sha": upstream_head_sha,
        "upstream_head_date": upstream_head_date,
        "upstream_head_msg": upstream_head_msg,
        "up_to_date": up_to_date,
    }


def check_all(repo_root: Path, target: str | None = None) -> dict[str, dict]:
    targets = [target] if target else list(UPSTREAMS.keys())
    results = {}
    for name in targets:
        if name in UPSTREAMS:
            results[name] = check_upstream(UPSTREAMS[name], repo_root)
    return results


def format_terminal_output(results: dict[str, dict]) -> str:
    lines = []
    lines.append(Color.bold(Color.cyan("=====================================================")))
    lines.append(Color.bold(Color.cyan("          AI Skills Upstream Status Check            ")))
    lines.append(Color.bold(Color.cyan("=====================================================\n")))

    all_up_to_date = True
    for idx, (name, data) in enumerate(results.items(), 1):
        lines.append(f"{Color.bold(f'[{idx}] {name.upper()}')} {Color.gray(f'({data[\"url\"]})')}")
        if data.get("local_version") != "unknown":
            lines.append(f"  • 로컬 적용 버전 : {Color.bold(data['local_version'])} {Color.gray(f'[{data[\"local_commit\"]}]')}")
        else:
            lines.append(f"  • 로컬 적용 커밋 : {Color.bold(data['local_sha'])} {Color.gray(f'[{data[\"local_commit\"]}]')}")

        if data.get("upstream_release"):
            lines.append(f"  • 업스트림 릴리스: {Color.bold(data['upstream_release'])} {Color.gray(f'(HEAD: {data[\"upstream_head_sha\"] or \"N/A\"})')}")
        elif data.get("upstream_head_sha"):
            lines.append(f"  • 업스트림 HEAD  : {Color.bold(data['upstream_head_sha'])} {Color.gray(f'({data[\"upstream_head_date\"]} - {data[\"upstream_head_msg\"]})')}")
        else:
            lines.append(f"  • 업스트림 상태  : {Color.yellow('확인 불가 (오프라인 또는 API 제한)')}")

        if data["up_to_date"]:
            lines.append(f"  • 상태           : {Color.green('✅ 최신 버전 동기화 상태')}\n")
        else:
            all_up_to_date = False
            if not data.get("upstream_head_sha") and not data.get("upstream_release"):
                lines.append(f"  • 상태           : {Color.yellow('⚠️ 네트워크 상태 확인 필요')}\n")
            elif data.get("local_sha") == "unknown" and data.get("local_version") == "unknown":
                lines.append(f"  • 상태           : {Color.yellow('⚡ 최초 동기화 필요')}\n")
            else:
                lines.append(f"  • 상태           : {Color.yellow('⚡ 업데이트 가능')}\n")

    lines.append(Color.bold(Color.cyan("=====================================================")))
    if all_up_to_date:
        lines.append(Color.green("✨ 모든 대상 스킬셋이 최신 상태입니다."))
    else:
        lines.append("💡 최신 버전을 동기화하려면 다음을 실행하세요:")
        lines.append(f"   {Color.bold('python3 script/manage.py sync')}")
    lines.append(Color.bold(Color.cyan("=====================================================")))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check status against upstream skill repositories.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON format.")
    parser.add_argument("--target", choices=list(UPSTREAMS.keys()), help="Target specific upstream to check.")
    args = parser.parse_args(argv)

    root = get_repo_root()
    results = check_all(root, target=args.target)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_terminal_output(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_check.py`
Expected: `Ran 3 tests in ...s OK`

- [ ] **Step 5: Commit**

```bash
git add script/check.py tests/test_check.py
git commit -m "feat(script): implement upstream status check engine"
```

---

### Task 3: Atomic Upstream Sync Engine (`script/sync.py`)

**Files:**
- Create: `script/sync.py`
- Test: `tests/test_sync.py`

**Interfaces:**
- Consumes: `script/config.py`, `script/common.py`.
- Produces:
  - `sync_upstream(config: UpstreamConfig, repo_root: Path, no_commit: bool = False) -> tuple[int, list[str], int]` in `script/sync.py`.
  - `sync_all(repo_root: Path, target: str | None = None, no_commit: bool = False) -> int` in `script/sync.py`.
  - `main(argv: list[str] | None = None) -> int` in `script/sync.py`.

- [ ] **Step 1: Write the failing test for sync logic**

Create `tests/test_sync.py`:
```python
import tempfile
import unittest
from pathlib import Path
from script.config import UpstreamConfig
from script.common import run_git
from script.sync import sync_upstream


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
        # Unlisted skill not copied
        self.assertFalse((self.local / "unlisted").exists())
        # Local-only skill untouched
        self.assertTrue((self.local / "local-only" / "SKILL.md").is_file())

        # Check commit created with tag provenance
        _, log_msg, _ = run_git(["log", "-n", "1", "--pretty=format:%s"], cwd=self.local)
        self.assertTrue(log_msg.startswith("chore: sync test-upstream v1.0.0 ("))

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

        # git status should be dirty, commit count unchanged
        _, count, _ = run_git(["rev-list", "--count", "HEAD"], cwd=self.local)
        self.assertEqual(count, "1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_sync.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'script.sync'`

- [ ] **Step 3: Write minimal implementation**

Create `script/sync.py`:
```python
from pathlib import Path
import argparse
import json
import os
import shutil
import sys
import tempfile
from script.config import UPSTREAMS, UpstreamConfig
from script.common import run_git, get_repo_root, Color


def sync_hyperframes_extras(clone_dir: Path, repo_root: Path) -> list[str]:
    staged_extra = []
    hf_plugin = repo_root / "plugins" / "hyperframes"
    ai_skills_plugin = repo_root / "plugins" / "ai-skills" / "skills"
    hf_plugin.mkdir(parents=True, exist_ok=True)
    ai_skills_plugin.mkdir(parents=True, exist_ok=True)

    # Assets
    upstream_assets = clone_dir / "assets"
    if upstream_assets.is_dir():
        dest_assets = hf_plugin / "assets"
        shutil.rmtree(dest_assets, ignore_errors=True)
        shutil.copytree(upstream_assets, dest_assets)
        staged_extra.append(str(dest_assets.relative_to(repo_root)))

    # Plugin descriptors (.claude-plugin, .codex-plugin)
    for p_name in [".claude-plugin", ".codex-plugin"]:
        upstream_p = clone_dir / p_name
        if upstream_p.is_dir():
            dest_p = hf_plugin / p_name
            shutil.rmtree(dest_p, ignore_errors=True)
            shutil.copytree(upstream_p, dest_p)
            staged_extra.append(str(dest_p.relative_to(repo_root)))

    # Extract version
    version = "0.8.71"
    plugin_json_path = clone_dir / ".claude-plugin" / "plugin.json"
    if plugin_json_path.is_file():
        try:
            v_data = json.loads(plugin_json_path.read_text(encoding="utf-8"))
            version = v_data.get("version", version)
        except Exception:
            pass

    # Generate plugin.json
    plugin_manifest = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "hyperframes",
        "version": version,
        "description": "HyperFrames by HeyGen. Write HTML, render video.",
        "author": {
            "name": "HeyGen",
            "email": "hyperframes@heygen.com",
            "url": "https://hyperframes.heygen.com",
        },
        "repository": "https://github.com/heygen-com/hyperframes",
        "license": "Apache-2.0",
        "keywords": ["hyperframes", "video", "html", "animation", "gsap", "rendering"],
        "skills": "./skills/",
        "extensions": {
            "com.openai": {
                "interface": {
                    "displayName": "HyperFrames by HeyGen",
                    "shortDescription": "Write HTML, render video",
                    "longDescription": "Build videos from HTML with HyperFrames.",
                    "developerName": "HeyGen",
                    "category": "Creativity",
                    "capabilities": ["Read", "Write"],
                    "websiteURL": "https://hyperframes.heygen.com",
                }
            }
        },
    }
    (hf_plugin / "plugin.json").write_text(json.dumps(plugin_manifest, indent=2) + "\n", encoding="utf-8")
    staged_extra.append("plugins/hyperframes/plugin.json")

    # Marketplace registration
    marketplace_path = repo_root / ".agents" / "plugins" / "marketplace.json"
    if marketplace_path.is_file():
        try:
            m_data = json.loads(marketplace_path.read_text(encoding="utf-8"))
            plugins = m_data.setdefault("plugins", [])
            names = [p.get("name") for p in plugins if isinstance(p, dict)]
            if "hyperframes" not in names:
                plugins.append({
                    "name": "hyperframes",
                    "source": {"source": "local", "path": "./plugins/hyperframes"},
                    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                    "category": "Creativity",
                })
                marketplace_path.write_text(json.dumps(m_data, indent=2) + "\n", encoding="utf-8")
                staged_extra.append(".agents/plugins/marketplace.json")
        except Exception:
            pass

    return staged_extra


def sync_upstream(config: UpstreamConfig, repo_root: Path, no_commit: bool = False) -> tuple[int, list[str], int]:
    print(Color.bold(f"=== Cloning {config.name} ({config.repo_url}) ==="))
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        clone_path = tmp_dir / "clone"

        code, _, err = run_git(["clone", "--quiet", "--depth", "1", config.repo_url, str(clone_path)], cwd=repo_root)
        if code != 0:
            print(Color.red(f"Error cloning {config.name}: {err}"), file=sys.stderr)
            return 1, [], 0

        _, tag, _ = run_git(["describe", "--tags", "--exact-match"], cwd=clone_path)
        _, sha7, _ = run_git(["rev-parse", "--short=7", "HEAD"], cwd=clone_path)

        synced_skills = []
        warn_count = 0

        print(Color.bold(f"=== Syncing {config.name} skills ==="))
        staging_paths = []

        for skill_name in config.skills:
            upstream_skill = clone_path / "skills" / skill_name
            if not upstream_skill.is_dir():
                print(Color.yellow(f"WARN: {config.name} upstream has no skills/{skill_name} - skipping"), file=sys.stderr)
                warn_count += 1
                continue

            # 1. Sync to repo root
            local_target = repo_root / skill_name
            shutil.rmtree(local_target, ignore_errors=True)
            shutil.copytree(upstream_skill, local_target)
            synced_skills.append(skill_name)
            staging_paths.append(skill_name)

            # 2. Extra targets (e.g. for hyperframes)
            if config.name == "hyperframes":
                hf_skill = repo_root / "plugins" / "hyperframes" / "skills" / skill_name
                ai_skill = repo_root / "plugins" / "ai-skills" / "skills" / skill_name
                shutil.rmtree(hf_skill, ignore_errors=True)
                shutil.rmtree(ai_skill, ignore_errors=True)
                shutil.copytree(upstream_skill, hf_skill)
                shutil.copytree(upstream_skill, ai_skill)
                staging_paths.append(f"plugins/hyperframes/skills/{skill_name}")
                staging_paths.append(f"plugins/ai-skills/skills/{skill_name}")

            print(f"  • Synced {skill_name}")

        if not synced_skills:
            print(Color.red(f"Nothing synced for {config.name}"), file=sys.stderr)
            return 1, [], warn_count

        if config.name == "hyperframes":
            extra_files = sync_hyperframes_extras(clone_path, repo_root)
            staging_paths.extend(extra_files)

        if no_commit:
            print(Color.yellow("no_commit=True: files updated, skipping git commit."))
            return 0, synced_skills, warn_count

        print(Color.bold(f"=== Committing changes for {config.name} ==="))
        run_git(["add", "-A", "--"] + staging_paths, cwd=repo_root)

        diff_code, _, _ = run_git(["diff", "--cached", "--quiet"], cwd=repo_root)
        if diff_code == 0:
            print(Color.green(f"✨ All {config.name} skills are already up-to-date."))
            return 0, synced_skills, warn_count

        subject = f"chore: sync {config.name} {tag} ({sha7})" if tag else f"chore: sync {config.name} ({sha7})"
        commit_code, _, commit_err = run_git(["commit", "-q", "-m", subject], cwd=repo_root)
        if commit_code == 0:
            print(Color.green(f"✅ Committed {config.name}: {subject}"))
        else:
            print(Color.red(f"Failed to commit {config.name}: {commit_err}"), file=sys.stderr)

        return 0, synced_skills, warn_count


def sync_all(repo_root: Path, target: str | None = None, no_commit: bool = False) -> int:
    targets = [target] if target else list(UPSTREAMS.keys())
    total_warns = 0
    any_failed = False

    for name in targets:
        if name in UPSTREAMS:
            code, _, warns = sync_upstream(UPSTREAMS[name], repo_root, no_commit=no_commit)
            total_warns += warns
            if code != 0:
                any_failed = True

    if total_warns > 0:
        print(Color.yellow(f"\n⚠ {total_warns} allowlisted skill(s) missing upstream across syncs"), file=sys.stderr)

    return 1 if any_failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync curated skills from upstream repositories.")
    parser.add_argument("--target", choices=list(UPSTREAMS.keys()), help="Target specific upstream repository to sync.")
    parser.add_argument("--no-commit", action="store_true", help="Copy updated files but skip creating git commits.")
    args = parser.parse_args(argv)

    root = get_repo_root()
    return sync_all(root, target=args.target, no_commit=args.no_commit)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_sync.py`
Expected: `Ran 2 tests in ...s OK`

- [ ] **Step 5: Commit**

```bash
git add script/sync.py tests/test_sync.py
git commit -m "feat(script): implement atomic upstream sync engine"
```

---

### Task 4: Cross-Platform Global Skill Linker (`script/link.py`)

**Files:**
- Create: `script/link.py`
- Test: `tests/test_link.py`

**Interfaces:**
- Consumes: `script/config.py`, `script/common.py`.
- Produces:
  - `create_link(target: Path, link_path: Path) -> None` in `script/link.py`.
  - `save_existing_directory(dir_path: Path, root_name: str, backup_root: Path) -> Path` in `script/link.py`.
  - `link_skills(repo_root: Path, backup_root: Path, dry_run: bool = False) -> int` in `script/link.py`.
  - `main(argv: list[str] | None = None) -> int` in `script/link.py`.

- [ ] **Step 1: Write the failing test for link logic**

Create `tests/test_link.py`:
```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from script.link import is_skill_directory, save_existing_directory, link_skills, create_link


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

    def test_save_existing_directory(self):
        conflicting = self.host_root / "skill-1"
        conflicting.mkdir()
        (conflicting / "file.txt").write_text("old content")

        backup_dest = save_existing_directory(conflicting, "claude", self.backup_root)
        self.assertTrue(backup_dest.is_dir())
        self.assertFalse(conflicting.exists())
        self.assertTrue((backup_dest / "file.txt").is_file())

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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_link.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'script.link'`

- [ ] **Step 3: Write minimal implementation**

Create `script/link.py`:
```python
from datetime import datetime
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
from script.config import GLOBAL_HOST_ROOTS, get_backup_root
from script.common import get_repo_root, Color


def is_skill_directory(p: Path) -> bool:
    return p.is_dir() and (p / "SKILL.md").is_file()


def is_link(p: Path) -> bool:
    if p.is_symlink():
        return True
    if sys.platform == "win32":
        try:
            return bool(p.stat().st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
        except Exception:
            return False
    return False


def remove_link_or_dir(p: Path) -> None:
    if is_link(p):
        if sys.platform == "win32" and p.is_dir():
            try:
                os.rmdir(p)
            except OSError:
                shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                p.unlink()
            except OSError:
                shutil.rmtree(p, ignore_errors=True)
    elif p.is_dir():
        shutil.rmtree(p)


def create_link(target: Path, link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or is_link(link_path):
        remove_link_or_dir(link_path)

    if sys.platform == "win32":
        # Create NTFS Directory Junction without requiring Administrator rights
        cmd = ["cmd", "/c", "mklink", "/J", str(link_path), str(target)]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            # Fallback to os.symlink
            os.symlink(str(target), str(link_path), target_is_directory=True)
    else:
        os.symlink(str(target), str(link_path), target_is_directory=True)


def save_existing_directory(dir_path: Path, root_name: str, backup_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_backup_dir = backup_root / timestamp
    target_backup_dir.mkdir(parents=True, exist_ok=True)
    destination = target_backup_dir / f"{root_name}--{dir_path.name}"
    shutil.move(str(dir_path), str(destination))
    print(Color.gray(f"  backup: {dir_path} -> {destination}"))
    return destination


def link_skills(repo_root: Path, backup_root: Path, dry_run: bool = False) -> int:
    managed_skills: dict[str, Path] = {}
    for entry in repo_root.iterdir():
        if is_skill_directory(entry):
            managed_skills[entry.name] = entry

    print(Color.bold(f"Central skill repository: {repo_root}"))
    print(Color.bold(f"Existing managed skills: {len(managed_skills)}"))

    # 1. Absorb unmanaged skills from global roots into repo
    for root_name, host_path in GLOBAL_HOST_ROOTS:
        if not host_path.is_dir():
            continue

        print(f"\nScanning {root_name}: {host_path}")
        for entry in list(host_path.iterdir()):
            if root_name == "codex" and entry.name in {".system", "codex-primary-runtime"}:
                print(Color.gray(f"  keep runtime directory: {entry.name}"))
                continue

            if not is_skill_directory(entry):
                print(Color.gray(f"  keep unmanaged directory: {entry.name}"))
                continue

            if entry.name in managed_skills:
                continue

            dest = repo_root / entry.name
            if not dry_run:
                if is_link(entry):
                    shutil.copytree(entry, dest)
                    print(Color.green(f"  import linked skill: {entry.name}"))
                else:
                    shutil.move(str(entry), str(dest))
                    print(Color.green(f"  import skill: {entry.name}"))
            managed_skills[entry.name] = dest

    # 2. Expose every managed skill in each global store
    for root_name, host_path in GLOBAL_HOST_ROOTS:
        if not dry_run:
            host_path.mkdir(parents=True, exist_ok=True)
        print(f"\nLinking skills into {root_name} ({host_path})")

        for skill_name, skill_path in sorted(managed_skills.items()):
            link_target = host_path / skill_name
            if link_target.exists() or is_link(link_target):
                if is_link(link_target):
                    if not dry_run:
                        remove_link_or_dir(link_target)
                elif not is_skill_directory(link_target):
                    print(Color.yellow(f"  WARN: Cannot link '{link_target}': non-skill directory exists."))
                    continue
                else:
                    if not dry_run:
                        save_existing_directory(link_target, root_name, backup_root)

            if not dry_run:
                create_link(skill_path, link_target)
            print(f"  • Linked {skill_name}")

    print(Color.green(f"\n✨ Done. Global skill stores now reference: {repo_root}"))
    print(Color.gray(f"Backups (when replacements were needed): {backup_root}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Link central repository skills into global host directories.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate linking operations without altering filesystem.")
    args = parser.parse_args(argv)

    root = get_repo_root()
    backup = get_backup_root()
    return link_skills(root, backup, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_link.py`
Expected: `Ran 3 tests in ...s OK`

- [ ] **Step 5: Commit**

```bash
git add script/link.py tests/test_link.py
git commit -m "feat(script): implement cross-platform global skill linker"
```

---

### Task 5: Unified CLI Entrypoint (`script/manage.py`)

**Files:**
- Create: `script/manage.py`
- Test: `tests/test_manage.py`

**Interfaces:**
- Consumes: `script/check.py`, `script/sync.py`, `script/link.py`.
- Produces:
  - `main(argv: list[str] | None = None) -> int` in `script/manage.py`.

- [ ] **Step 1: Write the failing test for manage CLI router**

Create `tests/test_manage.py`:
```python
import unittest
from unittest.mock import patch
from script.manage import main


class TestManage(unittest.TestCase):
    @patch("script.check.main")
    def test_route_check(self, mock_check):
        mock_check.return_value = 0
        code = main(["check", "--json"])
        self.assertEqual(code, 0)
        mock_check.assert_called_once_with(["--json"])

    @patch("script.sync.main")
    def test_route_sync(self, mock_sync):
        mock_sync.return_value = 0
        code = main(["sync", "--target", "ecc", "--no-commit"])
        self.assertEqual(code, 0)
        mock_sync.assert_called_once_with(["--target", "ecc", "--no-commit"])

    @patch("script.link.main")
    def test_route_link(self, mock_link):
        mock_link.return_value = 0
        code = main(["link", "--dry-run"])
        self.assertEqual(code, 0)
        mock_link.assert_called_once_with(["--dry-run"])

    @patch("unittest.main")
    def test_route_test(self, mock_unittest):
        # mock unittest.main exit
        mock_unittest.side_effect = SystemExit(0)
        code = main(["test"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_manage.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'script.manage'`

- [ ] **Step 3: Write minimal implementation**

Create `script/manage.py`:
```python
import argparse
import sys
import unittest
from script import check, sync, link
from script.common import Color


def run_tests() -> int:
    print(Color.bold("=== Running AI Skills Test Suite ==="))
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="AI Skills unified management toolchain (check, sync, link, test).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to execute")

    # check
    check_parser = subparsers.add_parser("check", help="Check upstream repositories for updates")
    check_parser.add_argument("--json", action="store_true", help="Output JSON format")
    check_parser.add_argument("--target", help="Specific upstream target to check")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Sync curated skills from upstream repositories")
    sync_parser.add_argument("--target", help="Specific upstream target to sync")
    sync_parser.add_argument("--no-commit", action="store_true", help="Skip git commit after copying")

    # link
    link_parser = subparsers.add_parser("link", help="Link managed skills to global host directories")
    link_parser.add_argument("--dry-run", action="store_true", help="Dry run without filesystem changes")

    # test
    subparsers.add_parser("test", help="Run the test suite")

    if argv is None:
        argv = sys.argv[1:]

    args, unknown = parser.parse_known_args(argv)

    if args.command == "check":
        forward_args = []
        if args.json:
            forward_args.append("--json")
        if args.target:
            forward_args.extend(["--target", args.target])
        forward_args.extend(unknown)
        return check.main(forward_args)

    elif args.command == "sync":
        forward_args = []
        if args.target:
            forward_args.extend(["--target", args.target])
        if args.no_commit:
            forward_args.append("--no-commit")
        forward_args.extend(unknown)
        return sync.main(forward_args)

    elif args.command == "link":
        forward_args = []
        if args.dry_run:
            forward_args.append("--dry-run")
        forward_args.extend(unknown)
        return link.main(forward_args)

    elif args.command == "test":
        return run_tests()

    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_manage.py`
Expected: `Ran 4 tests in ...s OK`

- [ ] **Step 5: Commit**

```bash
git add script/manage.py tests/test_manage.py
git commit -m "feat(script): add unified CLI entrypoint manage.py"
```

---

### Task 6: Legacy Scripts Deletion & Documentation Update

**Files:**
- Delete: `check-ecc.sh`, `check-hyperframes.sh`, `check-upstream.sh`
- Delete: `sync-ecc.sh`, `sync-hyperframes.sh`, `sync-taste-skill.sh`, `sync-upstream.sh`
- Delete: `link-global-skills.ps1`
- Delete: `tests/sync-upstream.test.sh`, `tests/sync-taste-skill.test.sh`, `tests/sync-hyperframes.test.sh`
- Modify: `GLOBAL-SKILLS.md`

**Interfaces:**
- Consumes: Cleaned repository structure.
- Produces: Updated `GLOBAL-SKILLS.md` documenting `python3 script/manage.py` commands.

- [ ] **Step 1: Run complete new test suite before deletion**

Run: `python3 script/manage.py test`
Expected: All tests pass (test_common, test_check, test_sync, test_link, test_manage).

- [ ] **Step 2: Delete legacy root scripts and shell tests**

```bash
git rm check-ecc.sh check-hyperframes.sh check-upstream.sh
git rm sync-ecc.sh sync-hyperframes.sh sync-taste-skill.sh sync-upstream.sh
git rm link-global-skills.ps1
git rm tests/sync-upstream.test.sh tests/sync-taste-skill.test.sh tests/sync-hyperframes.test.sh
```

- [ ] **Step 3: Update `GLOBAL-SKILLS.md`**

Replace PowerShell execution command with cross-platform Python command:
```markdown
# Global skill storage

This repository is the canonical source for user-managed skills across Codex, Claude, and Google Antigravity on Windows, macOS, and Linux.

## Setup & Linking

Run the unified manager from the repository root:

```bash
# Link all skills to global agent directories (macOS / Linux / Windows)
python3 script/manage.py link

# On Windows PowerShell:
python script/manage.py link
```

The script automatically handles filesystem differences:
- **Windows**: Creates NTFS Directory Junctions without requiring Administrator privileges.
- **macOS / Linux**: Creates standard POSIX symbolic links.

Global host locations linked:
- `~/.gemini/config/skills` (Antigravity IDE / Antigravity 2.0)
- `~/.gemini/antigravity-cli/skills` (Antigravity CLI)
- `~/.claude/skills` (Claude Code)
- `~/.codex/skills` (Codex)
- `~/.agents/skills` (Agent Reach / OpenCLI)
- `~/.gemini/antigravity/.agents/skills` (Antigravity Legacy mirror)

## Checking and Syncing Upstreams

```bash
# Check if upstream skills have updates
python3 script/manage.py check

# Sync all allowlisted skills from upstream repos
python3 script/manage.py sync

# Sync specific upstream repo (e.g. ecc, hyperframes, taste-skill, superpowers, caveman)
python3 script/manage.py sync --target ecc
```

## Running Tests

```bash
python3 script/manage.py test
```
```

- [ ] **Step 4: Verify test suite and clean git status**

Run: `python3 script/manage.py test`
Expected: All tests pass cleanly.

Run: `git status`
Expected: Only modified `GLOBAL-SKILLS.md` and deleted files staged.

- [ ] **Step 5: Commit**

```bash
git add GLOBAL-SKILLS.md
git commit -m "chore: remove legacy shell/ps1 scripts and update documentation"
```
