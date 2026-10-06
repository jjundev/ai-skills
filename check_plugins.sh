#!/usr/bin/env bash
# Quick runner for checking updates of AI skills & CLI plugins
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/script/check_plugins.py" "$@"
