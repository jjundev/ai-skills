#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ADAPTER_DIR="${SKILL_DIR}/adapter"

echo "Running DCInside adapter verification tests..."

# Test 1: Check adapter files exist
for f in common.js parser.js list.js read.js write.js; do
    if [ ! -f "${ADAPTER_DIR}/${f}" ]; then
        echo "FAIL: Missing file ${ADAPTER_DIR}/${f}" >&2
        exit 1
    fi
done
echo "PASS: All 5 adapter JS files exist."

# Test 2: Check ESM module resolution from inside the adapter directory
node -e "
import('${ADAPTER_DIR}/common.js').then(() => {
    console.log('PASS: common.js ESM resolution succeeded');
}).catch(err => {
    console.error('FAIL: common.js ESM resolution failed:', err);
    process.exit(1);
});
"

# Test 3: Check OpenCLI subcommands
output=$(opencli dcinside --help)
if echo "$output" | grep -q "list" && echo "$output" | grep -q "read" && echo "$output" | grep -q "write"; then
    echo "PASS: opencli dcinside exposes list, read, and write subcommands."
else
    echo "FAIL: Missing subcommands in opencli dcinside --help output" >&2
    exit 1
fi

echo "All tests passed successfully!"
