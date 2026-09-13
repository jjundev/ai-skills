#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_ROOT="$(mktemp -d /tmp/ajou-bb-setup.XXXXXX)"
trap 'rm -rf "$TEST_ROOT"' EXIT

for file in common.js parser.js analytics.js announcements.js assignments.js calendar.js contents.js courses.js download.js grades.js status.js stream.js; do
  test -f "$SKILL_DIR/adapter/$file"
  node --check "$SKILL_DIR/adapter/$file"
done

HOME="$TEST_ROOT" bash "$SKILL_DIR/scripts/setup.sh"
TARGET="$TEST_ROOT/.opencli/clis/ajou-bb"
test -L "$TARGET"
test "$(cd -P "$TARGET" && pwd)" = "$SKILL_DIR/adapter"
HOME="$TEST_ROOT" opencli ajou-bb --help | grep -q assignments
HOME="$TEST_ROOT" opencli validate ajou-bb | grep -q PASS
