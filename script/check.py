import argparse
import json
from pathlib import Path
import re
import sys

# Ensure repo root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from script.config import UPSTREAMS, UpstreamConfig
from script.common import run_git, fetch_github_json, get_repo_root, Color


def parse_local_version_and_sha(msg: str) -> tuple[str, str]:
    ver_match = re.search(r"v\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9.]+)?", msg)
    version = ver_match.group(0) if ver_match else "unknown"

    sha_match = re.search(r"\(([a-f0-9]{7,40})\)", msg)
    sha = sha_match.group(1)[:7] if sha_match else "unknown"
    return version, sha


def check_upstream(config: UpstreamConfig, repo_root: Path) -> dict:
    _, log_output, _ = run_git(
        ["log", f"--grep={config.grep_pattern}", "-n", "10", "--pretty=format:%h|%cr|%s"],
        cwd=repo_root,
    )

    commit_msg = ""
    commit_summary = ""
    local_version = "unknown"
    local_sha = "unknown"

    if log_output:
        lines = [line.strip() for line in log_output.splitlines() if line.strip()]
        for line in lines:
            parts = line.split("|", 2)
            if len(parts) == 3:
                h, cr, s = parts
            else:
                h, cr, s = parts[0], "", parts[-1]
            ver, sha = parse_local_version_and_sha(s)
            if ver != "unknown" or sha != "unknown":
                commit_msg = s
                commit_summary = f"{h} ({cr})" if cr else h
                local_version = ver
                local_sha = sha
                break
        if not commit_msg and lines:
            parts = lines[0].split("|", 2)
            h = parts[0]
            cr = parts[1] if len(parts) > 1 else ""
            commit_msg = parts[-1]
            commit_summary = f"{h} ({cr})" if cr else h
            local_version, local_sha = parse_local_version_and_sha(commit_msg)


    upstream_release = ""
    if config.release_api_url:
        release_data = fetch_github_json(config.release_api_url)
        if isinstance(release_data, dict):
            upstream_release = release_data.get("tag_name", "")

    upstream_head_sha = ""
    upstream_head_date = ""
    upstream_head_msg = ""
    if config.commits_api_url:
        commits_data = fetch_github_json(config.commits_api_url)
        if isinstance(commits_data, list) and len(commits_data) > 0:
            head = commits_data[0]
            if isinstance(head, dict):
                upstream_head_sha = head.get("sha", "")[:7]
                commit_obj = head.get("commit", {})
                if isinstance(commit_obj, dict):
                    committer = commit_obj.get("committer", {})
                    if isinstance(committer, dict):
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
        url = data.get("url", "")
        lines.append(f"{Color.bold(f'[{idx}] {name.upper()}')} {Color.gray(f'({url})')}")

        local_ver = data.get("local_version")
        local_commit = data.get("local_commit", "")
        if local_ver and local_ver != "unknown":
            lines.append(f"  • 로컬 적용 버전 : {Color.bold(local_ver)} {Color.gray(f'[{local_commit}]')}")
        else:
            local_sha = data.get("local_sha", "unknown")
            lines.append(f"  • 로컬 적용 커밋 : {Color.bold(local_sha)} {Color.gray(f'[{local_commit}]')}")

        upstream_rel = data.get("upstream_release")
        upstream_sha = data.get("upstream_head_sha")
        if upstream_rel:
            head_info = upstream_sha or "N/A"
            lines.append(f"  • 업스트림 릴리스: {Color.bold(upstream_rel)} {Color.gray(f'(HEAD: {head_info})')}")
        elif upstream_sha:
            details = [p for p in [data.get("upstream_head_date"), data.get("upstream_head_msg")] if p]
            details_str = f" ({' - '.join(details)})" if details else ""
            lines.append(f"  • 업스트림 HEAD  : {Color.bold(upstream_sha)}{Color.gray(details_str)}")
        else:
            lines.append(f"  • 업스트림 상태  : {Color.yellow('확인 불가 (오프라인 또는 API 제한)')}")

        if data.get("up_to_date"):
            lines.append(f"  • 상태           : {Color.green('✅ 최신 버전 동기화 상태')}\n")
        else:
            all_up_to_date = False
            if not upstream_sha and not upstream_rel:
                lines.append(f"  • 상태           : {Color.yellow('⚠️ 네트워크 상태 확인 필요')}\n")
            elif data.get("local_sha", "unknown") == "unknown" and data.get("local_version", "unknown") == "unknown":
                lines.append(f"  • 상태           : {Color.yellow('⚡ 최초 동기화 필요')}\n")
            else:
                lines.append(f"  • 상태           : {Color.yellow('⚡ 업데이트 가능')}\n")

    lines.append(Color.bold(Color.cyan("=====================================================")))
    if results and all_up_to_date:
        lines.append(Color.green("✨ 모든 대상 스킬셋이 최신 상태입니다."))
    elif not results:
        lines.append(Color.yellow("확인할 대상 스킬셋이 없습니다."))
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
