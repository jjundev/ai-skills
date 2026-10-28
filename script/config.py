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
        ],
        version_type="commit",
        commits_api_url="https://api.github.com/repos/Leonxlnx/taste-skill/commits?per_page=1",
        grep_pattern="sync taste-skill ",
    ),
    "imagegen-skills": UpstreamConfig(
        name="imagegen-skills",
        repo_url=os.environ.get("IMAGEGEN_REPO", "https://github.com/Leonxlnx/imagegen-skills.git"),
        skills=[
            "image-to-code",
            "imagegen-frontend-web",
            "imagegen-frontend-mobile",
            "brandkit",
        ],
        version_type="commit",
        commits_api_url="https://api.github.com/repos/Leonxlnx/imagegen-skills/commits?per_page=1",
        grep_pattern="sync imagegen-skills",
    ),
    "taste-skill-classics": UpstreamConfig(
        name="taste-skill-classics",
        repo_url=os.environ.get("TASTE_CLASSICS_REPO", "https://github.com/Leonxlnx/taste-skill-classics.git"),
        skills=[
            "minimalist-skill",
            "brutalist-skill",
        ],
        version_type="commit",
        commits_api_url="https://api.github.com/repos/Leonxlnx/taste-skill-classics/commits?per_page=1",
        grep_pattern="sync taste-skill-classics",
    ),
    "hyperframes": UpstreamConfig(
        name="hyperframes",
        repo_url=os.environ.get("HYPERFRAMES_REPO", "https://github.com/heygen-com/hyperframes.git"),
        skills=[
            "figma",
            "hyperframes",
            "hyperframes-cli",
            "hyperframes-registry",
            "media-use",
            "remotion-to-hyperframes",
            "slideshow",
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
    "lateral-thinking": UpstreamConfig(
        name="lateral-thinking",
        repo_url=os.environ.get("LATERAL_THINKING_REPO", "https://github.com/danium/lateral-thinking.git"),
        skills=[
            "lateral",
            "analogy",
            "concept-fan",
            "inversion",
            "post",
            "provocation",
            "random-stimulus",
            "scamper",
            "six-hats",
            "worst-idea",
        ],
        version_type="commit",
        commits_api_url="https://api.github.com/repos/danium/lateral-thinking/commits?per_page=1",
        grep_pattern="sync lateral-thinking",
    ),
}
