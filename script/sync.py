from pathlib import Path
import argparse
import json
import os
import shutil
import sys
import tempfile

# Ensure repo root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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
            return 0, synced_skills, warn_count
        else:
            print(Color.red(f"Failed to commit {config.name}: {commit_err}"), file=sys.stderr)
            return 1, synced_skills, warn_count


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
        else:
            print(Color.red(f"Unknown upstream target: {name}"), file=sys.stderr)
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
