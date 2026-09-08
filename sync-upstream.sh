#!/usr/bin/env bash
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="/tmp/ai-skills-sync-$$"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== Syncing Superpowers ==="
git clone --depth 1 https://github.com/obra/superpowers.git "$TMP_DIR/superpowers"
cp -R "$TMP_DIR/superpowers/skills/"* "$SKILLS_DIR/"
if [ -d "$SKILLS_DIR/tdd" ]; then
  cp -R "$TMP_DIR/superpowers/skills/test-driven-development/"* "$SKILLS_DIR/tdd/"
fi
if [ -d "$SKILLS_DIR/diagnosing-bugs" ]; then
  cp -R "$TMP_DIR/superpowers/skills/systematic-debugging/"* "$SKILLS_DIR/diagnosing-bugs/"
fi

echo "=== Syncing Caveman ==="
git clone --depth 1 https://github.com/JuliusBrussee/caveman.git "$TMP_DIR/caveman"
cp -R "$TMP_DIR/caveman/skills/"* "$SKILLS_DIR/"

echo "=== Committing changes ==="
cd "$SKILLS_DIR"
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "chore: auto-sync upstream skills on $(date +'%Y-%m-%d %H:%M:%S')"
  echo "✅ Skills updated and committed to Git."
else
  echo "✨ All skills are already up-to-date."
fi
