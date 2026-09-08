# Relocate DCInside Backend to Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relocate the DCInside OpenCLI backend adapter from the machine-local `~/.opencli/clis/dcinside` into the `ai-skills` Git repository under `ask-dc/adapter/`, set up bidirectional symlinks with ESM resolution, add a self-healing setup/doctor script, and update both `ask-dc` and `write-dc` skills to document and verify this backend architecture.

**Architecture:** The adapter source code (`common.js`, `parser.js`, `list.js`, `read.js`, `write.js`, plus endpoint docs) is committed directly to the `ai-skills` repository under `ask-dc/adapter/`. A self-healing script `ask-dc/scripts/setup.sh` configures the host environment by symlinking `~/.opencli/clis/dcinside` to `ask-dc/adapter` and establishing the required `node_modules/@jackwener/opencli` symlink so Node's ESM loader resolves OpenCLI primitives from the physical directory. A verification script `ask-dc/tests/verify_setup.sh` performs automated linting and execution smoke tests.

**Tech Stack:** Node.js (v20+ ESM), OpenCLI (@jackwener/opencli), Bash, Markdown (Skill format).

**Spec:** Agreed design from user request on 2026-09-09:
1. OpenCLI is assumed installed globally (or prompted to install via npm).
2. The existing DCInside backend on this Mac must be relocated into the skill directory so it is tracked in Git.
3. Both `ask-dc` (Read) and `write-dc` (Write) continue using OpenCLI commands seamlessly via the shared adapter.

## Global Constraints

- Never break existing OpenCLI discovery: `~/.opencli/clis/dcinside` must remain accessible as a symlink pointing to the realpath `ask-dc/adapter`.
- Node.js ESM module resolution constraint: Because Node resolves imports relative to realpaths by default, `ask-dc/adapter` requires `node_modules/@jackwener/opencli` symlinked to the installed OpenCLI root, which `setup.sh` must configure and `.gitignore` must ignore.
- Preserve 100% feature parity of `list.js`, `read.js`, `write.js`, `common.js`, and `parser.js`.
- Both `ask-dc/SKILL.md` and `write-dc/SKILL.md` must clearly document the prerequisite check and point to `ask-dc/scripts/setup.sh`.
- Changes must be tracked in the `ai-skills` workspace (`/Users/hyunjun_macbook_pro/.ai-skills`) and synced to `~/.gemini/config/skills/`.

---

### Task 1: Initialize `ask-dc/adapter/` directory and relocate backend source files

**Files:**
- Create: `ask-dc/adapter/common.js`
- Create: `ask-dc/adapter/parser.js`
- Create: `ask-dc/adapter/list.js`
- Create: `ask-dc/adapter/read.js`
- Create: `ask-dc/adapter/write.js`
- Create: `ask-dc/adapter/docs/endpoints.json`
- Create: `ask-dc/adapter/docs/notes.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Existing files from `~/.opencli/clis/dcinside/` and `~/.opencli/sites/dcinside/`.
- Produces: Version-controlled backend source tree in `ask-dc/adapter/`.

- [ ] **Step 1: Update `.gitignore` to ignore adapter `node_modules`**

Add `ask-dc/adapter/node_modules/` to `/Users/hyunjun_macbook_pro/.ai-skills/.gitignore`.

```text
# OpenCLI adapter local runtime shim
ask-dc/adapter/node_modules/
```

- [ ] **Step 2: Copy adapter and reference files to `ask-dc/adapter`**

Create directory `ask-dc/adapter/docs` and copy:
- `~/.opencli/clis/dcinside/common.js` -> `ask-dc/adapter/common.js`
- `~/.opencli/clis/dcinside/parser.js` -> `ask-dc/adapter/parser.js`
- `~/.opencli/clis/dcinside/list.js` -> `ask-dc/adapter/list.js`
- `~/.opencli/clis/dcinside/read.js` -> `ask-dc/adapter/read.js`
- `~/.opencli/clis/dcinside/write.js` -> `ask-dc/adapter/write.js`
- `~/.opencli/sites/dcinside/endpoints.json` -> `ask-dc/adapter/docs/endpoints.json`
- `~/.opencli/sites/dcinside/notes.md` -> `ask-dc/adapter/docs/notes.md`

- [ ] **Step 3: Verify all 7 files are present and match byte-for-byte**

Run:
```bash
diff -r ~/.opencli/clis/dcinside/ /Users/hyunjun_macbook_pro/.ai-skills/ask-dc/adapter/ --exclude="docs" --exclude="node_modules"
```
Expected: Empty output (exit code 0, perfect match).

---

### Task 2: Create automated setup and doctor script (`ask-dc/scripts/setup.sh`)

**Files:**
- Create: `ask-dc/scripts/setup.sh`

**Interfaces:**
- Consumes: `ask-dc/adapter/` directory, global `opencli` binary or npm package.
- Produces: Working symlinks at `~/.opencli/clis/dcinside` and `ask-dc/adapter/node_modules/@jackwener/opencli`.

- [ ] **Step 1: Write `ask-dc/scripts/setup.sh`**

```bash
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
echo "✅ OpenCLI detected: $(which opencli)"

# 3. Locate OpenCLI package root for ESM resolution shim
OPENCLI_BIN="$(which opencli)"
REAL_OPENCLI_BIN="$(node -e "import('fs').then(fs => console.log(fs.realpathSync('${OPENCLI_BIN}')))")"
OPENCLI_PKG_ROOT="$(node -e "import('path').then(p => console.log(p.resolve(p.dirname('${REAL_OPENCLI_BIN}'), '..')))")"

if [ ! -d "${OPENCLI_PKG_ROOT}" ]; then
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
```

- [ ] **Step 2: Make `ask-dc/scripts/setup.sh` executable and test it**

Run:
```bash
chmod +x /Users/hyunjun_macbook_pro/.ai-skills/ask-dc/scripts/setup.sh
/Users/hyunjun_macbook_pro/.ai-skills/ask-dc/scripts/setup.sh
```
Expected: Output showing green checkmarks and `Success! 'opencli dcinside' is fully operational.` (exit code 0).

- [ ] **Step 3: Verify the symlinks in filesystem**

Run:
```bash
ls -ld ~/.opencli/clis/dcinside
readlink ~/.opencli/clis/dcinside
```
Expected: Symlink pointing to `/Users/hyunjun_macbook_pro/.ai-skills/ask-dc/adapter`.

---

### Task 3: Create automated verification test (`ask-dc/tests/verify_setup.sh`)

**Files:**
- Create: `ask-dc/tests/verify_setup.sh`

**Interfaces:**
- Consumes: Installed symlink and OpenCLI runtime.
- Produces: Test results verifying module imports and CLI command response.

- [ ] **Step 1: Write `ask-dc/tests/verify_setup.sh`**

```bash
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
```

- [ ] **Step 2: Make `verify_setup.sh` executable and run it**

Run:
```bash
chmod +x /Users/hyunjun_macbook_pro/.ai-skills/ask-dc/tests/verify_setup.sh
/Users/hyunjun_macbook_pro/.ai-skills/ask-dc/tests/verify_setup.sh
```
Expected: All 3 tests output PASS and exit code 0.

---

### Task 4: Update `ask-dc/SKILL.md` and `write-dc/SKILL.md` Documentation & Sync

**Files:**
- Modify: `ask-dc/SKILL.md`
- Modify: `write-dc/SKILL.md`

**Interfaces:**
- Consumes: `setup.sh` and `adapter/` architecture.
- Produces: Updated user-facing instructions and self-healing workflow.

- [ ] **Step 1: Update `ask-dc/SKILL.md`**

Add a dedicated `## 0. 사전 점검 및 환경 설정 (Setup & Self-Healing)` section before Section 1:
- Explains that the backend adapter source is hosted in `ask-dc/adapter/` and symlinked to OpenCLI.
- Specifies that if `opencli dcinside` is not found, the agent/user must run `bash ~/.ai-skills/ask-dc/scripts/setup.sh` (or `npm i -g @jackwener/opencli`).

- [ ] **Step 2: Update `write-dc/SKILL.md`**

Add a note in Section 4 (실행 워크플로우):
- Explains that `write-dc` relies on the shared OpenCLI DCInside adapter hosted in `ask-dc/adapter/`.
- References `ask-dc/scripts/setup.sh` if `opencli dcinside write` fails with command not found.

- [ ] **Step 3: Sync changes to `~/.gemini/config/skills/`**

Run:
```bash
cp -r /Users/hyunjun_macbook_pro/.ai-skills/ask-dc /Users/hyunjun_macbook_pro/.gemini/config/skills/
cp -r /Users/hyunjun_macbook_pro/.ai-skills/write-dc /Users/hyunjun_macbook_pro/.gemini/config/skills/
```

- [ ] **Step 4: Commit changes to Git in `ai-skills`**

Run:
```bash
git status
git add ask-dc/ write-dc/ .gitignore docs/superpowers/plans/
git commit -m "feat(dcinside): relocate OpenCLI adapter into ask-dc/adapter with automated setup"
```

---

## Self-Review

1. **Spec coverage**:
   - Backend moved to skill folder? Yes, `ask-dc/adapter/` in Task 1.
   - Symlinked to OpenCLI? Yes, `ask-dc/scripts/setup.sh` in Task 2.
   - ESM resolution handled? Yes, via `@jackwener/opencli` symlink inside `ask-dc/adapter/node_modules/` in Task 2.
   - Shared between `ask-dc` and `write-dc`? Yes, both reference the single adapter, documented in Task 4.
   - Verified? Yes, automated test in Task 3.
2. **Placeholder scan**: No "TBD", "TODO", or pseudo-code. All commands and scripts are fully written out.
3. **Type consistency**: All directory paths and file names match across Tasks 1, 2, 3, and 4.
