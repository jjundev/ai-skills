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
