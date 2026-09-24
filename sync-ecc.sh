#!/usr/bin/env bash
# ==============================================================================
# sync-ecc.sh — pull an explicit allowlist of curated skills from affaan-m/ECC.
#
# Only the directory names listed in ECC_SKILLS are copied out of the upstream's
# skills/ folder. Everything else is ignored on purpose.
# Each listed skill is deleted locally and re-copied, so files removed
# upstream disappear here too.
#
# The upstream is cloned into a temporary directory before anything in the
# local tree is touched, so a clone failure exits non-zero without modifying
# any local files.
#
# Env overrides:
#   ECC_REPO   git URL to clone instead of GitHub (default: https://github.com/affaan-m/ECC.git)
#   NO_COMMIT  copy files but skip git commit (default: 0)
# ==============================================================================
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ECC_REPO="${ECC_REPO:-https://github.com/affaan-m/ECC.git}"
NO_COMMIT="${NO_COMMIT:-0}"

# Curated high-value architecture, backend, and pattern skills from ECC
ECC_SKILLS=(
  architecture-decision-records
  hexagonal-architecture
  api-design
  mcp-server-patterns
  backend-patterns
  fastapi-patterns
  database-migrations
  docker-patterns
  council
  security-review
)

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

WARN_COUNT=0

print_warn_summary() {
  if [ "$WARN_COUNT" -gt 0 ]; then
    echo "⚠ $WARN_COUNT allowlisted skill(s) missing upstream - see WARN lines above" >&2
  fi
}

echo "=== Cloning affaan-m/ECC ==="
git clone --quiet --depth 1 "$ECC_REPO" "$TMP_DIR/ecc"

ECC_CLONE="$TMP_DIR/ecc"
ECC_TAG="$(git -C "$ECC_CLONE" describe --tags --exact-match 2>/dev/null || true)"
ECC_SHA7="$(git -C "$ECC_CLONE" rev-parse --short=7 HEAD)"

ECC_SYNCED=()

echo "=== Syncing ECC skills ==="
for name in "${ECC_SKILLS[@]}"; do
  if [ ! -d "$ECC_CLONE/skills/$name" ]; then
    echo "WARN: ECC upstream has no skills/$name - skipping" >&2
    WARN_COUNT=$((WARN_COUNT + 1))
    continue
  fi
  rm -rf "${SKILLS_DIR:?}/$name"
  cp -R "$ECC_CLONE/skills/$name" "$SKILLS_DIR/$name"
  ECC_SYNCED+=("$name")
  echo "  • Synced $name"
done

if [ "${#ECC_SYNCED[@]}" -eq 0 ]; then
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

echo "=== Committing changes ==="
git add -A -- "${ECC_SYNCED[@]}"

if git diff --cached --quiet; then
  echo "✨ All ECC skills are already up-to-date."
  print_warn_summary
  exit 0
fi

if [ -n "$ECC_TAG" ]; then
  SUBJECT="chore: sync ecc $ECC_TAG ($ECC_SHA7)"
else
  SUBJECT="chore: sync ecc ($ECC_SHA7)"
fi

git commit -q -m "$SUBJECT"
echo "✅ Committed ECC: $SUBJECT"

print_warn_summary
