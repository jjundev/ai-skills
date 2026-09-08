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
# Both upstreams are cloned before anything in the local tree is touched,
# so a clone failure exits non-zero without deleting or overwriting any
# local files. Each upstream that actually changes something gets its own
# commit (only that upstream's synced directories are staged), with the
# upstream's exact tag (when its HEAD is exactly tagged) and short SHA in
# the subject, so a later `git log --grep=<label>` can recover the synced
# version:
#   chore: sync <label> <tag> (<sha7>)   when the clone's HEAD is exactly tagged
#   chore: sync <label> (<sha7>)         otherwise
# Missing-upstream WARNs are summarized in a final "⚠ N ..." line.
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

WARN_COUNT=0

print_warn_summary() {
  if [ "$WARN_COUNT" -gt 0 ]; then
    echo "⚠ $WARN_COUNT allowlisted skill(s) missing upstream - see WARN lines above" >&2
  fi
}

# --- Clone both upstreams first. Nothing in the tree is touched until both
# clones have succeeded, so a clone failure leaves the local checkout alone.
echo "=== Cloning superpowers ==="
git clone --quiet --depth 1 "$SUPERPOWERS_REPO" "$TMP_DIR/superpowers"
echo "=== Cloning caveman ==="
git clone --quiet --depth 1 "$CAVEMAN_REPO" "$TMP_DIR/caveman"

SP_CLONE="$TMP_DIR/superpowers"
CM_CLONE="$TMP_DIR/caveman"

# Capture provenance (tag/sha) right after cloning, before the temp dir
# that holds these clones could be cleaned up.
SP_TAG="$(git -C "$SP_CLONE" describe --tags --exact-match 2>/dev/null || true)"
SP_SHA7="$(git -C "$SP_CLONE" rev-parse --short=7 HEAD)"
CM_TAG="$(git -C "$CM_CLONE" describe --tags --exact-match 2>/dev/null || true)"
CM_SHA7="$(git -C "$CM_CLONE" rev-parse --short=7 HEAD)"

SP_SYNCED=()
CM_SYNCED=()

# Copies allowlisted names from $2/skills/<name> into $SKILLS_DIR. Appends
# each synced name into SP_SYNCED or CM_SYNCED depending on $3 ("SP"/"CM") —
# bash 3.2 has no namerefs, so the target array is picked by that tag
# instead of being passed by reference.
copy_skills() {
  local label="$1" clone="$2" which="$3"
  shift 3
  echo "=== Syncing $label ==="
  local name
  for name in "$@"; do
    if [ ! -d "$clone/skills/$name" ]; then
      echo "WARN: $label upstream has no skills/$name (renamed or removed?) - skipping" >&2
      WARN_COUNT=$((WARN_COUNT + 1))
      continue
    fi
    rm -rf "${SKILLS_DIR:?}/$name"
    cp -R "$clone/skills/$name" "$SKILLS_DIR/$name"
    if [ "$which" = "SP" ]; then
      SP_SYNCED+=("$name")
    else
      CM_SYNCED+=("$name")
    fi
  done
}

copy_skills superpowers "$SP_CLONE" SP "${SUPERPOWERS_SKILLS[@]}"
copy_skills caveman "$CM_CLONE" CM "${CAVEMAN_SKILLS[@]}"

# Guard against expanding an empty array below (bash 3.2 + set -u). This
# must run before any "${SP_SYNCED[@]}"/"${CM_SYNCED[@]}" expansion.
if [ "${#SP_SYNCED[@]}" -eq 0 ] && [ "${#CM_SYNCED[@]}" -eq 0 ]; then
  echo "Nothing synced (every allowlisted skill was missing upstream)." >&2
  print_warn_summary
  exit 1
fi

if [ "$NO_COMMIT" = "1" ]; then
  echo "NO_COMMIT=1: files updated, skipping git commit."
  print_warn_summary
  exit 0
fi

cd "$SKILLS_DIR"

COMMITTED=0

# Stages and commits only the given upstream's synced directories. Skips
# committing (but not staging-check) when nothing actually changed.
commit_upstream() {
  local label="$1" tag="$2" sha7="$3" which="$4"
  local count
  if [ "$which" = "SP" ]; then
    count=${#SP_SYNCED[@]}
  else
    count=${#CM_SYNCED[@]}
  fi
  if [ "$count" -eq 0 ]; then
    return 0
  fi
  if [ "$which" = "SP" ]; then
    git add -A -- "${SP_SYNCED[@]}"
  else
    git add -A -- "${CM_SYNCED[@]}"
  fi
  if git diff --cached --quiet; then
    return 0
  fi
  local subject
  if [ -n "$tag" ]; then
    subject="chore: sync $label $tag ($sha7)"
  else
    subject="chore: sync $label ($sha7)"
  fi
  git commit -q -m "$subject"
  echo "✅ Committed $label: $subject"
  COMMITTED=1
}

echo "=== Committing changes ==="
commit_upstream superpowers "$SP_TAG" "$SP_SHA7" SP
commit_upstream caveman "$CM_TAG" "$CM_SHA7" CM

if [ "$COMMITTED" -eq 0 ]; then
  echo "✨ All skills are already up-to-date."
fi

print_warn_summary
