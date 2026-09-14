#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ "$SOURCE_SKILL_DIR" == */plugins/ai-skills/skills/ajou-bb ]]; then
  echo 'Already running from the portable plugin copy; no source-to-plugin sync is needed.'
  exit 0
fi
REPO_ROOT="$(cd "$SOURCE_SKILL_DIR/.." && pwd)"
DESTINATION="$REPO_ROOT/plugins/ai-skills/skills/ajou-bb"

mkdir -p "$DESTINATION"
rm -rf -- "$DESTINATION/adapter/node_modules"
rsync -a --delete --exclude='adapter/node_modules/' --exclude=.DS_Store "$SOURCE_SKILL_DIR/" "$DESTINATION/"
test ! -e "$DESTINATION/adapter/node_modules"
diff -ru --exclude=node_modules --exclude=.DS_Store "$SOURCE_SKILL_DIR" "$DESTINATION"
