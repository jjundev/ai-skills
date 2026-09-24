#!/usr/bin/env bash
# sync-taste-skill.sh — pull an explicit allowlist of skills from Leonxlnx/taste-skill.
#
# Only the directory names listed in TASTE_SKILLS are copied out of the
# upstream's skills/ folder. Each listed skill is deleted locally and re-copied,
# so stale/removed files upstream disappear here too.
#
# Provenance is captured upon shallow clone and committed with:
#   chore: sync taste-skill <tag> (<sha7>)   when exactly tagged
#   chore: sync taste-skill (<sha7>)         otherwise
#
# Env overrides:
#   TASTE_REPO  git URL to clone instead of GitHub (default: https://github.com/Leonxlnx/taste-skill.git)
#   NO_COMMIT   set to 1 to copy files but skip the git commit
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASTE_REPO="${TASTE_REPO:-https://github.com/Leonxlnx/taste-skill.git}"
NO_COMMIT="${NO_COMMIT:-0}"

TASTE_SKILLS=(
  taste-skill
  image-to-code-skill
  imagegen-frontend-web
  imagegen-frontend-mobile
  redesign-skill
  stitch-skill
  brandkit
  minimalist-skill
  soft-skill
  brutalist-skill
)

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

WARN_COUNT=0

print_warn_summary() {
  if [ "$WARN_COUNT" -gt 0 ]; then
    echo "⚠ $WARN_COUNT allowlisted skill(s) missing upstream - see WARN lines above" >&2
  fi
}

echo "=== Cloning taste-skill ==="
git clone --quiet --depth 1 "$TASTE_REPO" "$TMP_DIR/taste-skill"

TS_CLONE="$TMP_DIR/taste-skill"
TS_TAG="$(git -C "$TS_CLONE" describe --tags --exact-match 2>/dev/null || true)"
TS_SHA7="$(git -C "$TS_CLONE" rev-parse --short=7 HEAD)"

TS_SYNCED=()

echo "=== Syncing taste-skill ==="
for name in "${TASTE_SKILLS[@]}"; do
  if [ ! -d "$TS_CLONE/skills/$name" ]; then
    echo "WARN: taste-skill upstream has no skills/$name (renamed or removed?) - skipping" >&2
    WARN_COUNT=$((WARN_COUNT + 1))
    continue
  fi
  rm -rf "${SKILLS_DIR:?}/$name"
  cp -R "$TS_CLONE/skills/$name" "$SKILLS_DIR/$name"
  TS_SYNCED+=("$name")
done

if [ "${#TS_SYNCED[@]}" -eq 0 ]; then
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
git add -A -- "${TS_SYNCED[@]}"

if git diff --cached --quiet; then
  echo "✨ taste-skill is already up-to-date."
  print_warn_summary
  exit 0
fi

if [ -n "$TS_TAG" ]; then
  subject="chore: sync taste-skill $TS_TAG ($TS_SHA7)"
else
  subject="chore: sync taste-skill ($TS_SHA7)"
fi

git commit -q -m "$subject"
echo "✅ Committed taste-skill: $subject"
print_warn_summary
