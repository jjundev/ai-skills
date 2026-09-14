#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ADAPTER_DIR="$SKILL_DIR/adapter"
CLI_DIR="$HOME/.opencli/clis"
TARGET="$CLI_DIR/ajou-bb"

command -v node >/dev/null || { echo 'Node.js 20+ is required.' >&2; exit 1; }
NODE_VERSION="$(node --version)"
NODE_MAJOR="${NODE_VERSION#v}"
NODE_MAJOR="${NODE_MAJOR%%.*}"
case "$NODE_MAJOR" in
  ''|*[!0-9]*) echo 'Node.js 20+ is required.' >&2; exit 1 ;;
esac
if (( NODE_MAJOR < 20 )); then
  echo 'Node.js 20+ is required.' >&2
  exit 1
fi
command -v opencli >/dev/null || { echo 'Install OpenCLI first: npm install -g @jackwener/opencli' >&2; exit 1; }
test -f "$ADAPTER_DIR/common.js" || { echo 'Canonical adapter is incomplete.' >&2; exit 1; }

OPENCLI_BIN="$(command -v opencli)"
REAL_OPENCLI_BIN="$(node -e "import('fs').then(fs => console.log(fs.realpathSync(process.argv[1])))" "$OPENCLI_BIN")"
OPENCLI_PKG_ROOT="$(node -e "import('fs').then(async fs => { const path = await import('path'); let cur = path.dirname(process.argv[1]); while (cur !== '/' && !fs.existsSync(path.join(cur, 'package.json'))) cur = path.dirname(cur); if (cur === '/') process.exit(1); console.log(cur); })" "$REAL_OPENCLI_BIN")"

mkdir -p "$ADAPTER_DIR/node_modules/@jackwener" "$CLI_DIR"
ln -sfn "$OPENCLI_PKG_ROOT" "$ADAPTER_DIR/node_modules/@jackwener/opencli"
BACKUP=""
ORIGINAL_TARGET_LINK=""
restore_target() {
  status=$?
  trap - EXIT
  if test "$status" -ne 0; then
    test ! -L "$TARGET" || rm "$TARGET"
    if test -n "$BACKUP"; then
      mv "$BACKUP" "$TARGET"
    elif test -n "$ORIGINAL_TARGET_LINK"; then
      ln -s "$ORIGINAL_TARGET_LINK" "$TARGET"
    fi
  fi
  exit "$status"
}
trap restore_target EXIT
if test -L "$TARGET"; then
  ORIGINAL_TARGET_LINK="$(readlink "$TARGET")"
elif test -e "$TARGET"; then
  BACKUP="$CLI_DIR/ajou-bb.bak.$(date +%Y%m%d%H%M%S)"
  mv "$TARGET" "$BACKUP"
fi
ln -sfn "$ADAPTER_DIR" "$TARGET"
opencli ajou-bb --help >/dev/null
opencli validate ajou-bb
trap - EXIT
