#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ADAPTER_DIR="${SKILL_DIR}/adapter"

echo "Running DCInside adapter verification tests..."

# Test 1: Check adapter and CLI files exist
for f in adapter/http.js adapter/common.js adapter/list.js adapter/read.js adapter/write.js scripts/dc.mjs; do
    if [ ! -f "${SKILL_DIR}/${f}" ]; then
        echo "FAIL: Missing file ${SKILL_DIR}/${f}" >&2
        exit 1
    fi
done
echo "PASS: Adapter and CLI files exist."

# Test 2: The HTTP core and standalone CLI must load without OpenCLI
node -e "
import('${ADAPTER_DIR}/http.js').then(() => {
    console.log('PASS: http.js loads without OpenCLI');
}).catch(err => {
    console.error('FAIL: http.js failed to load:', err);
    process.exit(1);
});
"
set +e
node "${SKILL_DIR}/scripts/dc.mjs" >/dev/null 2>&1
code=$?
set -e
if [ "$code" -ne 2 ]; then
    echo "FAIL: dc.mjs without arguments should exit 2 (usage), got ${code}" >&2
    exit 1
fi
echo "PASS: dc.mjs prints usage and exits 2."

# Test 3: Check OpenCLI subcommands (write-dc still depends on them)
output=$(opencli dcinside --help)
if echo "$output" | grep -q "list" && echo "$output" | grep -q "read" && echo "$output" | grep -q "write"; then
    echo "PASS: opencli dcinside exposes list, read, and write subcommands."
else
    echo "FAIL: Missing subcommands in opencli dcinside --help output" >&2
    exit 1
fi

echo "All tests passed successfully!"
