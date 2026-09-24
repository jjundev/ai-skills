#!/usr/bin/env python3
"""
clean_worktrees.py: Audit, safety-check, and prune git linked worktrees.

Features:
- Audits all linked worktrees (dirty state, untracked files, unmerged commits).
- Safely removes linked worktrees (leaving branches and main tree intact).
- Prunes git worktree metadata.
- Cleans up empty parent container folders (e.g. .claude/worktrees, .gemini/.../worktrees).
"""

import argparse
import json
import os
import subprocess
import sys


def get_git_env():
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    return env


def run_git(args, cwd=None):
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=get_git_env(),
    )


def detect_base_branch(repo_root):
    for candidate in ["origin/main", "main", "origin/master", "master"]:
        res = run_git(["rev-parse", "--verify", candidate], cwd=repo_root)
        if res.returncode == 0:
            return candidate
    return "HEAD"


def audit_worktrees(repo_root):
    res = run_git(["worktree", "list", "--porcelain"], cwd=repo_root)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to list worktrees: {res.stderr.strip()}")

    raw_lines = res.stdout.strip().split("\n")
    worktrees = []
    current = {}

    for line in raw_lines:
        if not line.strip():
            if current:
                worktrees.append(current)
                current = {}
            continue
        parts = line.split(" ", 1)
        k = parts[0]
        v = parts[1] if len(parts) > 1 else ""
        current[k] = v
    if current:
        worktrees.append(current)

    if not worktrees:
        return [], "HEAD"

    main_tree = worktrees[0]["worktree"]
    base_branch = detect_base_branch(repo_root)

    results = []
    for idx, wt in enumerate(worktrees):
        path = wt.get("worktree", "")
        head = wt.get("HEAD", "")
        branch_ref = wt.get("branch", "")
        is_main = (idx == 0) or (path == main_tree)

        branch_name = (
            branch_ref.replace("refs/heads/", "")
            if branch_ref
            else ("(detached)" if "detached" in wt else "")
        )

        exists = os.path.exists(path)
        is_dirty = False
        dirty_files = []
        unmerged_commits = 0

        if exists:
            # Check dirty status
            st_res = run_git(["status", "--porcelain", "-uall"], cwd=path)
            if st_res.returncode == 0 and st_res.stdout.strip():
                is_dirty = True
                dirty_files = [
                    line.strip() for line in st_res.stdout.strip().split("\n") if line.strip()
                ]

            # Check unmerged commits relative to base branch
            if not is_main and head:
                rev_res = run_git(
                    ["rev-list", "--count", f"{base_branch}..{head}"],
                    cwd=repo_root,
                )
                if rev_res.returncode == 0:
                    try:
                        unmerged_commits = int(rev_res.stdout.strip())
                    except ValueError:
                        unmerged_commits = 0

        results.append({
            "path": path,
            "is_main": is_main,
            "branch": branch_name,
            "head": head[:8] if head else "",
            "exists": exists,
            "is_dirty": is_dirty,
            "dirty_count": len(dirty_files),
            "dirty_files": dirty_files[:10],
            "unmerged_commits": unmerged_commits,
        })

    return results, base_branch


def remove_empty_parents(removed_paths):
    cleaned_containers = []
    for path in removed_paths:
        parent = os.path.dirname(os.path.abspath(path))
        while parent and parent != "/" and parent != os.path.expanduser("~"):
            basename = os.path.basename(parent)
            # Only clean up known worktree container directories
            if basename in ["worktrees", ".worktrees"] or "antigravity/worktrees" in parent or "orca/workspaces" in parent:
                try:
                    if os.path.exists(parent) and not os.listdir(parent):
                        os.rmdir(parent)
                        cleaned_containers.append(parent)
                        parent = os.path.dirname(parent)
                        continue
                except OSError:
                    pass
            break
    return cleaned_containers


def main():
    parser = argparse.ArgumentParser(description="Audit and clean up git linked worktrees.")
    parser.add_argument("--cwd", default=".", help="Target git repository path")
    parser.add_argument("--execute", action="store_true", help="Perform actual removal of linked worktrees")
    parser.add_argument("--force", action="store_true", help="Force remove dirty worktrees")
    parser.add_argument("--target", help="Specific worktree path to remove (default: all linked worktrees)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    repo_path = os.path.abspath(args.cwd)

    # Validate git repo
    root_check = run_git(["rev-parse", "--show-toplevel"], cwd=repo_path)
    if root_check.returncode != 0:
        print(f"Error: {repo_path} is not inside a git repository.", file=sys.stderr)
        sys.exit(1)
    repo_root = root_check.stdout.strip()

    worktrees, base_branch = audit_worktrees(repo_root)
    linked = [w for w in worktrees if not w["is_main"]]

    if args.target:
        target_abs = os.path.abspath(args.target)
        linked = [w for w in linked if os.path.abspath(w["path"]) == target_abs]
        if not linked:
            print(f"Target worktree not found among linked worktrees: {args.target}", file=sys.stderr)
            sys.exit(1)

    if not args.execute:
        # Audit mode
        if args.json:
            print(json.dumps({"base_branch": base_branch, "worktrees": worktrees}, indent=2))
            return

        print(f"\n🔍 Git Worktree Audit (Base: {base_branch})")
        print(f"Repository Root: {repo_root}")
        print(f"Total Linked Worktrees: {len(linked)}\n")

        if not linked:
            print("✅ No linked worktrees found. Clean state!")
            return

        header = f"{'Idx':<4} | {'Branch':<32} | {'State':<8} | {'Unmerged':<8} | {'Path'}"
        print(header)
        print("-" * len(header) + "-" * 30)

        for i, wt in enumerate(linked, 1):
            state = "DIRTY" if wt["is_dirty"] else "Clean"
            unm = str(wt["unmerged_commits"]) if wt["unmerged_commits"] > 0 else "0"
            print(f"{i:<4} | {wt['branch']:<32} | {state:<8} | {unm:<8} | {wt['path']}")
            if wt["is_dirty"]:
                print(f"       ⚠️  Uncommitted files ({wt['dirty_count']}): {', '.join(wt['dirty_files'][:3])}...")

        print("\n💡 Run with `--execute` to remove clean worktrees.")
        print("💡 Use `--execute --force` to also remove dirty worktrees.")
        return

    # Execution mode
    removed = []
    skipped = []

    print(f"\n🚀 Cleaning up {len(linked)} linked worktree(s)...")

    for wt in linked:
        path = wt["path"]
        if wt["is_dirty"] and not args.force:
            print(f"⚠️  Skipping DIRTY worktree: {path} (Use --force to override)")
            skipped.append(path)
            continue

        cmd = ["worktree", "remove"]
        if args.force or wt["is_dirty"]:
            cmd.append("--force")
        cmd.append(path)

        res = run_git(cmd, cwd=repo_root)
        if res.returncode == 0:
            print(f"✅ Removed: {path}")
            removed.append(path)
        else:
            print(f"❌ Failed to remove {path}: {res.stderr.strip()}")
            skipped.append(path)

    # Prune
    prune_res = run_git(["worktree", "prune", "-v"], cwd=repo_root)
    prune_msg = prune_res.stdout.strip() or "Metadata already clean"
    print(f"\n🧹 Prune result: {prune_msg}")

    # Clean empty parent directories
    cleaned_containers = remove_empty_parents(removed)
    for c in cleaned_containers:
        print(f"🗑️  Removed empty container: {c}")

    # Final check
    post_check, _ = audit_worktrees(repo_root)
    post_linked = [w for w in post_check if not w["is_main"]]

    print(f"\n📊 Summary: {len(removed)} removed, {len(skipped)} skipped, {len(post_linked)} remaining.")
    if len(post_linked) == 0:
        print("🎉 All linked worktrees successfully cleaned up!")
    else:
        print(f"⚠️  {len(post_linked)} linked worktree(s) still remaining.")


if __name__ == "__main__":
    main()
