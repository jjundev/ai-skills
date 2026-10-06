import argparse
import json
from pathlib import Path
import re
import sys

# Ensure repo root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from script.common import Color, fetch_github_json, get_repo_root, run_git
from script.check import check_all


def parse_github_owner_repo(repo_url: str) -> tuple[str, str] | None:
    if not repo_url:
        return None
    match = re.search(r"github\.com/([^/]+)/([^/\.]+)", repo_url)
    if match:
        return match.group(1), match.group(2)
    return None


def check_plugin_bundle(plugin_dir: Path, repo_root: Path) -> dict:
    plugin_json = plugin_dir / "plugin.json"
    manifest: dict = {}
    if plugin_json.is_file():
        try:
            manifest = json.loads(plugin_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    name = manifest.get("name", plugin_dir.name)
    local_version = manifest.get("version", "unknown")
    repo_url = manifest.get("repository", "")
    description = manifest.get("description", "")

    upstream_version = ""
    upstream_head_sha = ""
    upstream_head_msg = ""
    upstream_head_date = ""
    up_to_date = False

    gh_info = parse_github_owner_repo(repo_url)

    if gh_info:
        owner, repo_name = gh_info

        # Try fetching upstream plugin.json manifest
        manifest_candidates = [
            f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/plugin.json",
            f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/.claude-plugin/plugin.json",
            f"https://raw.githubusercontent.com/{owner}/{repo_name}/master/plugin.json",
        ]
        for candidate_url in manifest_candidates:
            data = fetch_github_json(candidate_url)
            if isinstance(data, dict) and data.get("version"):
                upstream_version = data.get("version", "")
                break

        # Try fetching upstream HEAD commit
        commits_url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?per_page=1"
        commits_data = fetch_github_json(commits_url)
        if isinstance(commits_data, list) and len(commits_data) > 0 and isinstance(commits_data[0], dict):
            head_commit = commits_data[0]
            upstream_head_sha = head_commit.get("sha", "")[:7]
            commit_obj = head_commit.get("commit", {})
            if isinstance(commit_obj, dict):
                committer = commit_obj.get("committer", {})
                if isinstance(committer, dict):
                    upstream_head_date = committer.get("date", "")[:10]
                upstream_head_msg = commit_obj.get("message", "").split("\n")[0]

    # Special handling for self-repo (ai-skills)
    if name == "ai-skills" or repo_url.endswith("jjundev/ai-skills") or repo_url.endswith("jjundev/ai-skills.git"):
        ret, local_head, _ = run_git(["rev-parse", "--short", "HEAD"], cwd=repo_root)
        local_sha = local_head[:7] if ret == 0 and local_head else "unknown"
        ret_r, remote_out, _ = run_git(["ls-remote", "origin", "refs/heads/main"], cwd=repo_root)
        remote_sha = remote_out.split()[0][:7] if ret_r == 0 and remote_out else "unknown"

        up_to_date = (local_sha == remote_sha) if (local_sha != "unknown" and remote_sha != "unknown") else True
        return {
            "name": name,
            "path": str(plugin_dir.relative_to(repo_root)),
            "local_version": local_version,
            "local_sha": local_sha,
            "upstream_version": local_version,
            "upstream_head_sha": remote_sha,
            "upstream_head_date": "",
            "upstream_head_msg": "remote origin/main",
            "repo_url": repo_url,
            "up_to_date": up_to_date,
        }

    # Version comparison for external plugin bundle (e.g. hyperframes)
    if upstream_version and local_version != "unknown":
        up_to_date = (local_version == upstream_version)
    elif upstream_head_sha:
        up_to_date = False

    return {
        "name": name,
        "path": str(plugin_dir.relative_to(repo_root)),
        "local_version": local_version,
        "local_sha": "",
        "upstream_version": upstream_version,
        "upstream_head_sha": upstream_head_sha,
        "upstream_head_date": upstream_head_date,
        "upstream_head_msg": upstream_head_msg,
        "repo_url": repo_url,
        "up_to_date": up_to_date,
    }


def check_internal_plugin_bundles(repo_root: Path) -> dict[str, dict]:
    plugins_dir = repo_root / "plugins"
    results = {}
    if not plugins_dir.is_dir():
        return results

    for item in sorted(plugins_dir.iterdir()):
        if item.is_dir() and (item / "plugin.json").is_file():
            results[item.name] = check_plugin_bundle(item, repo_root)

    return results


def check_all_internal(repo_root: Path, check_bundles: bool = True, check_skills: bool = True) -> dict:
    results: dict = {
        "plugin_bundles": {},
        "upstream_skills": {},
        "summary": {
            "total_checked": 0,
            "updates_available": 0,
            "up_to_date": 0,
            "unknown": 0,
        },
    }

    if check_bundles:
        bundles = check_internal_plugin_bundles(repo_root)
        results["plugin_bundles"] = bundles
        for _, item in bundles.items():
            results["summary"]["total_checked"] += 1
            if item.get("up_to_date") is True:
                results["summary"]["up_to_date"] += 1
            elif item.get("up_to_date") is False:
                results["summary"]["updates_available"] += 1
            else:
                results["summary"]["unknown"] += 1

    if check_skills:
        skills = check_all(repo_root)
        results["upstream_skills"] = skills
        for _, item in skills.items():
            results["summary"]["total_checked"] += 1
            if item.get("up_to_date") is True:
                results["summary"]["up_to_date"] += 1
            elif item.get("up_to_date") is False:
                results["summary"]["updates_available"] += 1
            else:
                results["summary"]["unknown"] += 1

    return results


def format_terminal_output(data: dict) -> str:
    lines = []
    lines.append(Color.bold(Color.cyan("=================================================================")))
    lines.append(Color.bold(Color.cyan("        AI-Skills 폴더 내부 플러그인 & 스킬 업데이트 점검         ")))
    lines.append(Color.bold(Color.cyan("=================================================================\n")))

    # 1. plugins/ bundles
    bundles = data.get("plugin_bundles", {})
    if bundles:
        lines.append(Color.bold("📦 [1] plugins/ 폴더 내 번들 플러그인 점검"))
        lines.append(Color.gray("    (ai-skills/plugins/*/plugin.json 대상)"))
        for idx, (name, item) in enumerate(bundles.items(), 1):
            path_str = item.get("path", "")
            local_ver = item.get("local_version", "unknown")
            local_sha = item.get("local_sha")
            up_ver = item.get("upstream_version")
            up_sha = item.get("upstream_head_sha")

            local_disp = f"v{local_ver}" if local_ver != "unknown" else (local_sha or "unknown")
            if local_sha and local_ver != "unknown":
                local_disp = f"v{local_ver} ({local_sha})"

            up_disp = f"v{up_ver}" if up_ver else (up_sha or "N/A")
            if up_sha and up_ver:
                up_disp = f"v{up_ver} (HEAD: {up_sha})"

            if item.get("up_to_date"):
                status_str = Color.green("✅ 최신 상태")
            else:
                status_str = Color.yellow("⚡ 업데이트 가능")

            lines.append(f"  • {Color.bold(name)} {Color.gray(f'({path_str})')}:")
            lines.append(f"      로컬 [{local_disp}] → 업스트림 [{up_disp}] {status_str}")
        lines.append("")

    # 2. Curated Upstream Skillsets
    skills = data.get("upstream_skills", {})
    if skills:
        lines.append(Color.bold("🧩 [2] 큐레이션 업스트림 플러그인 스킬셋 점검"))
        lines.append(Color.gray("    (ai-skills 내부로 동기화 관리되는 5개 외부 스킬셋)"))
        for idx, (name, item) in enumerate(skills.items(), 1):
            local_ver = item.get("local_version")
            local_sha = item.get("local_sha")
            if local_ver and local_ver != "unknown":
                local_info = local_ver
            elif local_sha and local_sha != "unknown":
                local_info = local_sha
            else:
                local_info = "unknown"

            up_rel = item.get("upstream_release")
            up_sha = item.get("upstream_head_sha")
            up_str = f"v{up_rel}" if up_rel and not up_rel.startswith("v") else (up_rel or up_sha or "N/A")

            status_str = Color.green("✅ 최신 상태") if item.get("up_to_date") else Color.yellow("⚡ 업데이트 가능")
            lines.append(f"  • {Color.bold(name.upper())}: 로컬 [{local_info}] → 업스트림 [{up_str}] {status_str}")
        lines.append("")

    # Summary
    summary = data.get("summary", {})
    total = summary.get("total_checked", 0)
    updates = summary.get("updates_available", 0)

    lines.append(Color.bold(Color.cyan("=================================================================")))
    if updates > 0:
        lines.append(Color.bold(Color.yellow(f"⚡ 업데이트 가능한 항목이 {updates}개 있습니다! (총 {total}개 점검)")))
        lines.append("\n💡 업데이트 실행 명령어:")
        lines.append(f"   • 업스트림 스킬 및 플러그인 동기화: {Color.bold('python3 script/manage.py sync')}")
    else:
        lines.append(Color.bold(Color.green(f"✨ 모든 내부 플러그인 및 스킬셋이 최신 상태입니다! (총 {total}개 점검)")))
    lines.append(Color.bold(Color.cyan("=================================================================")))

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check update status for plugins and skills inside ai-skills.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON format.")
    parser.add_argument("--plugins-only", action="store_true", help="Check only plugins/ bundles.")
    parser.add_argument("--skills-only", action="store_true", help="Check only curated upstream skills.")
    args = parser.parse_args(argv)

    root = get_repo_root()
    check_bundles = not args.skills_only
    check_skills = not args.plugins_only

    results = check_all_internal(root, check_bundles=check_bundles, check_skills=check_skills)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_terminal_output(results))

    return 0


if __name__ == "__main__":
    sys.exit(main())
