#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ADAPTER_DIR="${SKILL_DIR}/adapter"
OPENCLI_DIR="${HOME}/.opencli"
OPENCLI_CLIS_DIR="${OPENCLI_DIR}/clis"
TARGET_SYMLINK="${OPENCLI_CLIS_DIR}/dcinside"

echo "=== [ask-dc / write-dc] OpenCLI DCInside Backend Setup & Doctor ==="

# 1. Check Node.js
if ! command -v node >/dev/null 2>&1; then
    echo "❌ Node.js is not installed. Please install Node.js (v20+ recommended)." >&2
    exit 1
fi
echo "✅ Node.js detected: $(node -v)"

# 2. Check OpenCLI
if ! command -v opencli >/dev/null 2>&1; then
    echo "⚠️ OpenCLI binary not found in PATH." >&2
    echo "   Please install it globally via: npm install -g @jackwener/opencli" >&2
    exit 1
fi
echo "✅ OpenCLI detected: $(command -v opencli)"

# 3. Locate OpenCLI package root for ESM resolution shim
OPENCLI_BIN="$(command -v opencli)"
REAL_OPENCLI_BIN="$(node -e "import('fs').then(fs => console.log(fs.realpathSync('${OPENCLI_BIN}')))")"
OPENCLI_PKG_ROOT="$(node -e "import('fs').then(async fs => { const path = await import('path'); let cur = path.dirname('${REAL_OPENCLI_BIN}'); while (cur !== '/' && !fs.existsSync(path.join(cur, 'package.json'))) { cur = path.dirname(cur); } if (cur === '/') process.exit(1); console.log(cur); })")"

if [ ! -d "${OPENCLI_PKG_ROOT}" ] || [ ! -f "${OPENCLI_PKG_ROOT}/package.json" ]; then
    echo "❌ Could not locate OpenCLI package root at ${OPENCLI_PKG_ROOT}" >&2
    exit 1
fi
echo "✅ OpenCLI package root: ${OPENCLI_PKG_ROOT}"

# 4. Create ESM node_modules symlink in adapter dir
# Required because Node.js resolves imports based on realpath
mkdir -p "${ADAPTER_DIR}/node_modules/@jackwener"
ln -sfn "${OPENCLI_PKG_ROOT}" "${ADAPTER_DIR}/node_modules/@jackwener/opencli"
echo "✅ Adapter ESM shim linked: ${ADAPTER_DIR}/node_modules/@jackwener/opencli -> ${OPENCLI_PKG_ROOT}"

# 5. Backup existing directory if not a symlink, then create symlink
mkdir -p "${OPENCLI_CLIS_DIR}"
if [ -d "${TARGET_SYMLINK}" ] && [ ! -L "${TARGET_SYMLINK}" ]; then
    BACKUP_DIR="${OPENCLI_CLIS_DIR}/dcinside.bak.$(date +%s)"
    echo "⚠️ Existing physical directory found at ${TARGET_SYMLINK}. Moving to backup: ${BACKUP_DIR}"
    mv "${TARGET_SYMLINK}" "${BACKUP_DIR}"
fi

ln -sfn "${ADAPTER_DIR}" "${TARGET_SYMLINK}"
echo "✅ OpenCLI adapter symlinked: ${TARGET_SYMLINK} -> ${ADAPTER_DIR}"

# 6. Verify command registration
echo "🔍 Verifying OpenCLI DCInside command registration..."
if opencli dcinside --help >/dev/null 2>&1; then
    echo "🎉 Success! 'opencli dcinside' is fully operational."
    exit 0
else
    echo "❌ Verification failed. 'opencli dcinside --help' exited with an error." >&2
    exit 1
fi
