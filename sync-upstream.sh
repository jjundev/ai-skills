#!/usr/bin/env bash
# sync-upstream.sh — pull an explicit allowlist of skills from upstream repos.
#
# Only the directory names listed below are copied out of each upstream's
# skills/ folder. Everything else there (build tooling, hook/CLI-dependent
# skills, workflow skills that overlap Superpowers) is ignored on purpose.
# Each listed skill is deleted locally and re-copied, so files removed
# upstream disappear here too. Removing a name from a list makes future
# syncs leave that directory alone; it does not delete it.
#
# Env overrides (mainly for tests):
#   SUPERPOWERS_REPO / CAVEMAN_REPO  git URLs to clone instead of GitHub
#   NO_COMMIT=1                      copy files but skip the git commit
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUPERPOWERS_REPO="${SUPERPOWERS_REPO:-https://github.com/obra/superpowers.git}"
CAVEMAN_REPO="${CAVEMAN_REPO:-https://github.com/JuliusBrussee/caveman.git}"
NO_COMMIT="${NO_COMMIT:-0}"

SUPERPOWERS_SKILLS=(
  brainstorming
  dispatching-parallel-agents
  executing-plans
  finishing-a-development-branch
  receiving-code-review
  requesting-code-review
  subagent-driven-development
  systematic-debugging
  test-driven-development
  using-git-worktrees
  using-superpowers
  verification-before-completion
  writing-plans
  writing-skills
)

# Kept on purpose: pure-prompt utilities with no Superpowers equivalent.
# Dropped on purpose: investigate-first, lean-build, surgical-patch,
# safe-refactor, verify-and-stop (overlap Superpowers) and cavecrew,
# caveman-stats, caveman-setup/discover/evidence-review/manage/learn/optimize
# (need the caveman CLI, hooks or agents, which are not installed).
CAVEMAN_SKILLS=(
  caveman
  caveman-commit
  caveman-compress
  caveman-explore
  caveman-help
  caveman-review
  migration
)

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

SYNCED=()

sync_skills() {
  local label="$1" repo="$2"
  shift 2
  local clone="$TMP_DIR/$label"
  echo "=== Syncing $label ==="
  git clone --quiet --depth 1 "$repo" "$clone"
  local name
  for name in "$@"; do
    if [ ! -d "$clone/skills/$name" ]; then
      echo "WARN: $label upstream has no skills/$name (renamed or removed?) - skipping" >&2
      continue
    fi
    rm -rf "${SKILLS_DIR:?}/$name"
    cp -R "$clone/skills/$name" "$SKILLS_DIR/$name"
    SYNCED+=("$name")
  done
}

sync_skills superpowers "$SUPERPOWERS_REPO" "${SUPERPOWERS_SKILLS[@]}"
sync_skills caveman "$CAVEMAN_REPO" "${CAVEMAN_SKILLS[@]}"

if [ "${#SYNCED[@]}" -eq 0 ]; then
  echo "Nothing synced (every allowlisted skill was missing upstream)." >&2
  exit 1
fi

if [ "$NO_COMMIT" = "1" ]; then
  echo "NO_COMMIT=1: files updated, skipping git commit."
  exit 0
fi

echo "=== Committing changes ==="
cd "$SKILLS_DIR"
git add -A -- "${SYNCED[@]}"
if git diff --cached --quiet; then
  echo "✨ All skills are already up-to-date."
else
  git commit -q -m "chore: auto-sync upstream skills on $(date +'%Y-%m-%d %H:%M:%S')"
  echo "✅ Skills updated and committed to Git."
fi
