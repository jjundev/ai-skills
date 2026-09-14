#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_ROOT="$(mktemp -d /tmp/ajou-bb-setup.XXXXXX)"
SHIM="$SKILL_DIR/adapter/node_modules/@jackwener/opencli"
ORIGINAL_SHIM="$(readlink "$SHIM" 2>/dev/null || true)"
restore_test_state() {
  if test -n "$ORIGINAL_SHIM"; then
    ln -sfn "$ORIGINAL_SHIM" "$SHIM"
  fi
  rm -rf "$TEST_ROOT"
}
trap restore_test_state EXIT

for file in common.js parser.js analytics.js announcements.js assignments.js calendar.js contents.js courses.js download.js grades.js status.js stream.js; do
  test -f "$SKILL_DIR/adapter/$file"
  node --check "$SKILL_DIR/adapter/$file"
done

FAKE_OPENCLI_ROOT="$TEST_ROOT/fake-opencli"
FAKE_OPENCLI_BIN="$FAKE_OPENCLI_ROOT/bin"
FAKE_OPENCLI_LOG="$FAKE_OPENCLI_ROOT/calls.log"
mkdir -p "$FAKE_OPENCLI_BIN"
printf '{}' > "$FAKE_OPENCLI_ROOT/package.json"
printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$*" >> "%s"\n' "$FAKE_OPENCLI_LOG" > "$FAKE_OPENCLI_BIN/opencli"
chmod +x "$FAKE_OPENCLI_BIN/opencli"

PATH="$FAKE_OPENCLI_BIN:$PATH" FAKE_OPENCLI_LOG="$FAKE_OPENCLI_LOG" HOME="$TEST_ROOT" bash "$SKILL_DIR/scripts/setup.sh"
TARGET="$TEST_ROOT/.opencli/clis/ajou-bb"
test -L "$TARGET"
test "$(cd -P "$TARGET" && pwd)" = "$SKILL_DIR/adapter"
grep -qx 'ajou-bb --help' "$FAKE_OPENCLI_LOG"
grep -qx 'validate ajou-bb' "$FAKE_OPENCLI_LOG"

FAKE_NODE_BIN="$TEST_ROOT/fake-node-bin"
mkdir -p "$FAKE_NODE_BIN"
printf '#!/usr/bin/env bash\nprintf "v18.20.0\\n"\n' > "$FAKE_NODE_BIN/node"
chmod +x "$FAKE_NODE_BIN/node"
if PATH="$FAKE_NODE_BIN:$FAKE_OPENCLI_BIN:$PATH" HOME="$TEST_ROOT" bash "$SKILL_DIR/scripts/setup.sh" >/dev/null 2>"$TEST_ROOT/node-version.err"; then
  echo 'setup accepted Node.js 18' >&2
  exit 1
fi
grep -q 'Node.js 20+ is required.' "$TEST_ROOT/node-version.err"

ROLLBACK_HOME="$TEST_ROOT/rollback-home"
ROLLBACK_TARGET="$ROLLBACK_HOME/.opencli/clis/ajou-bb"
mkdir -p "$ROLLBACK_TARGET"
touch "$ROLLBACK_TARGET/legacy-marker"
printf '#!/usr/bin/env bash\nexit 1\n' > "$FAKE_OPENCLI_BIN/opencli"
chmod +x "$FAKE_OPENCLI_BIN/opencli"
if PATH="$FAKE_OPENCLI_BIN:$PATH" HOME="$ROLLBACK_HOME" bash "$SKILL_DIR/scripts/setup.sh" >/dev/null 2>&1; then
  echo 'setup unexpectedly passed with a failing OpenCLI command' >&2
  exit 1
fi
test -d "$ROLLBACK_TARGET"
test -f "$ROLLBACK_TARGET/legacy-marker"
test ! -e "$ROLLBACK_HOME/.opencli/clis/ajou-bb.bak."*
