# ajou-bb Standalone Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ajou-bb own and distribute its Blackboard OpenCLI adapter while preserving the existing opencli ajou-bb command interface.

**Architecture:** The twelve files currently in $HOME/.opencli/clis/ajou-bb move to ajou-bb/adapter, the only source of truth. A setup script creates an ESM dependency shim and connects the OpenCLI command location by symbolic link. The plugin copy is regenerated from the canonical root skill.

**Tech Stack:** Node.js 24+, globally installed @jackwener/opencli, Bash, macOS symbolic links, Node built-in test runner.

**Spec:** Confirmed in this thread: update root and plugin copies; keep timestamped backups; retain ./downloads/<course> as the command default.

## Global Constraints

- Preserve the ten commands: analytics, announcements, assignments, calendar, contents, courses, download, grades, status, and stream.
- Node.js and global OpenCLI stay required. Setup must never install either automatically.
- Setup and automated tests must not navigate to Blackboard, use Chrome, retrieve course data, or download files.
- ajou-bb/adapter is canonical; plugins/ai-skills/skills/ajou-bb is a synchronized portable copy.
- A physical existing OpenCLI adapter becomes ajou-bb.bak.<timestamp> before a symlink replaces it.
- Do not change the adapter default ./downloads/<course_name>. The skill-level 강의노트 path remains an explicit --out choice.
- Never commit generated adapter/node_modules, backups, credentials, browser state, or course data.

---

## File structure

| Path | Responsibility |
|---|---|
| ajou-bb/adapter/*.js | Canonical Blackboard commands, parser, API/session helpers, and downloader. |
| ajou-bb/scripts/setup.sh | Preflight runtime, ESM shim, backup/link adapter, validate registration. |
| ajou-bb/scripts/sync-plugin-copy.sh | Rebuild plugin distribution from the canonical skill. |
| ajou-bb/tests/adapter.test.mjs | Pure helper regression tests. |
| ajou-bb/tests/verify_setup.sh | Isolated temporary-home installation test. |
| ajou-bb/SKILL.md | Setup, dependency, ownership, and download-default documentation. |
| plugins/ai-skills/skills/ajou-bb/** | Portable root-skill mirror. |
| .gitignore | Ignore generated module-resolution shims. |

### Task 1: Create canonical adapter source and regression tests

**Files:**
- Create: ajou-bb/adapter/common.js, parser.js, analytics.js, announcements.js, assignments.js, calendar.js, contents.js, courses.js, download.js, grades.js, status.js, stream.js
- Create: ajou-bb/tests/adapter.test.mjs
- Modify: .gitignore

**Interfaces:**
- Consumes: the existing validated source in $HOME/.opencli/clis/ajou-bb.
- Produces: the unchanged command registrations and exports requireTerm(value), sanitizeFileName(name), resolveOutDir(outArg, courseName), filterFilesForDownload(files, options).

- [ ] **Step 1: Write the failing test**

Create ajou-bb/tests/adapter.test.mjs:

```js
import assert from 'node:assert/strict';
import test from 'node:test';
import { requireTerm } from '../adapter/common.js';
import { filterFilesForDownload, resolveOutDir, sanitizeFileName } from '../adapter/download.js';

test('normalizes academic terms', () => {
  assert.equal(requireTerm('2026년 2학기'), '2026-2');
  assert.equal(requireTerm('2026-summer'), '2026-summer');
  assert.throws(() => requireTerm('2026-3'), /Invalid term semester/);
});

test('does not widen a requested download', () => {
  const files = [{ content_id: '_a', file_name: '1주차.pdf', title: '1주차' }, { content_id: '_b', file_name: '2주차.pdf', title: '2주차' }];
  assert.deepEqual(filterFilesForDownload(files, { query: '2주차' }), [files[1]]);
  assert.deepEqual(filterFilesForDownload(files, {}), []);
});

test('keeps current download behavior', () => {
  assert.equal(sanitizeFileName('  1주차: 회로?  '), '1주차_ 회로_');
  assert.match(resolveOutDir(undefined, '회로이론'), /downloads\\/회로이론$/);
});
```

- [ ] **Step 2: Verify red**

Run: `node --test ajou-bb/tests/adapter.test.mjs`

Expected: module-not-found, because the canonical modules do not yet exist.

- [ ] **Step 3: Migrate source unchanged**

Use apply_patch to add verbatim copies of all twelve current files from $HOME/.opencli/clis/ajou-bb into matching ajou-bb/adapter paths. Do not change imports, command names, site values, browser/session settings, parsing, masking, or the default path implementation:

```js
if (!outArg || typeof outArg !== 'string' || !outArg.trim()) {
  return path.join(process.cwd(), 'downloads', sanitizeFileName(courseName));
}
```

Append:

```gitignore
ajou-bb/adapter/node_modules/
plugins/ai-skills/skills/ajou-bb/adapter/node_modules/
```

- [ ] **Step 4: Verify syntax**

Run:

```bash
for file in ajou-bb/adapter/*.js; do node --check "$file"; done
```

Expected: twelve passing syntax checks. The import test runs after Task 2 creates the shim.

- [ ] **Step 5: Commit**

```bash
git add .gitignore ajou-bb/adapter ajou-bb/tests/adapter.test.mjs
git commit -m "feat(ajou-bb): own Blackboard adapter source"
```

### Task 2: Implement safe setup and isolated setup verification

**Files:**
- Create: ajou-bb/scripts/setup.sh
- Create: ajou-bb/tests/verify_setup.sh

**Interfaces:**
- Consumes: Task 1 adapter and global opencli.
- Produces: OpenCLI ajou-bb entry as a symlink to the canonical adapter.
- Supports: OPENCLI_HOME override for controlled installations; the automated test exercises the default location inside a temporary HOME.

- [ ] **Step 1: Write the failing installer test**

Create ajou-bb/tests/verify_setup.sh:

```bash
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
```

- [ ] **Step 2: Verify red**

Run: `bash ajou-bb/tests/verify_setup.sh`

Expected: scripts/setup.sh does not exist.

- [ ] **Step 3: Implement setup**

Create ajou-bb/scripts/setup.sh:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ADAPTER_DIR="$SKILL_DIR/adapter"
OPENCLI_HOME="${OPENCLI_HOME:-$HOME/.opencli}"
CLI_DIR="$OPENCLI_HOME/clis"
TARGET="$CLI_DIR/ajou-bb"

command -v node >/dev/null || { echo 'Node.js 20+ is required.' >&2; exit 1; }
command -v opencli >/dev/null || { echo 'Install OpenCLI first: npm install -g @jackwener/opencli' >&2; exit 1; }
test -f "$ADAPTER_DIR/common.js" || { echo 'Canonical adapter is incomplete.' >&2; exit 1; }

OPENCLI_BIN="$(command -v opencli)"
REAL_OPENCLI_BIN="$(node -e "import('fs').then(fs => console.log(fs.realpathSync(process.argv[1])))" "$OPENCLI_BIN")"
OPENCLI_PKG_ROOT="$(node -e "import('fs').then(async fs => { const path = await import('path'); let cur = path.dirname(process.argv[1]); while (cur !== '/' && !fs.existsSync(path.join(cur, 'package.json'))) cur = path.dirname(cur); if (cur === '/') process.exit(1); console.log(cur); })" "$REAL_OPENCLI_BIN")"

mkdir -p "$ADAPTER_DIR/node_modules/@jackwener" "$CLI_DIR"
ln -sfn "$OPENCLI_PKG_ROOT" "$ADAPTER_DIR/node_modules/@jackwener/opencli"
if test -e "$TARGET" && ! test -L "$TARGET"; then
  BACKUP="$CLI_DIR/ajou-bb.bak.$(date +%Y%m%d%H%M%S)"
  mv "$TARGET" "$BACKUP"
fi
ln -sfn "$ADAPTER_DIR" "$TARGET"
opencli ajou-bb --help >/dev/null
opencli validate ajou-bb
```

If Node 24 rejects the package-root resolver, correct only that resolver. Do not add package installation, browser automation, Blackboard calls, or writes outside the ajou-bb destination.

- [ ] **Step 4: Verify green**

Run:

```bash
bash ajou-bb/tests/verify_setup.sh
node --test ajou-bb/tests/adapter.test.mjs
```

Expected: only a temporary home changes, the link target is exact, helper tests pass, and OpenCLI validates.

- [ ] **Step 5: Perform a real non-live migration check**

Run:

```bash
bash ajou-bb/scripts/setup.sh
readlink $HOME/.opencli/clis/ajou-bb
opencli ajou-bb --help
opencli validate ajou-bb
```

Expected: old physical source is a timestamped backup, the active entry links to ajou-bb/adapter, ten commands appear, and validation passes. Do not call status or courses.

- [ ] **Step 6: Commit**

```bash
git add ajou-bb/scripts/setup.sh ajou-bb/tests/verify_setup.sh
git commit -m "feat(ajou-bb): link canonical adapter into OpenCLI"
```

### Task 3: Synchronize and test portable plugin distribution

**Files:**
- Create: ajou-bb/scripts/sync-plugin-copy.sh
- Create: plugins/ai-skills/skills/ajou-bb/adapter/*.js
- Create: plugins/ai-skills/skills/ajou-bb/scripts/setup.sh, sync-plugin-copy.sh
- Create: plugins/ai-skills/skills/ajou-bb/tests/adapter.test.mjs, verify_setup.sh

**Interfaces:**
- Consumes: Tasks 1 and 2 root skill.
- Produces: a byte-identical plugin copy excluding generated node_modules.

- [ ] **Step 1: Add a failing parity assertion**

Append to verify_setup.sh:

```bash
PLUGIN_SKILL_DIR="$SKILL_DIR/../../plugins/ai-skills/skills/ajou-bb"
diff -ru --exclude=node_modules --exclude=.DS_Store "$SKILL_DIR" "$PLUGIN_SKILL_DIR"
```

- [ ] **Step 2: Verify red**

Run: `bash ajou-bb/tests/verify_setup.sh`

Expected: plugin parity fails because it currently contains only SKILL.md.

- [ ] **Step 3: Implement deterministic synchronization**

Create ajou-bb/scripts/sync-plugin-copy.sh:

```bash
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
rsync -a --delete --exclude='adapter/node_modules/' --exclude=.DS_Store "$SOURCE_SKILL_DIR/" "$DESTINATION/"
diff -ru --exclude=node_modules --exclude=.DS_Store "$SOURCE_SKILL_DIR" "$DESTINATION"
```

Run it once. Its delete scope is only the explicitly confirmed generated plugin mirror.

- [ ] **Step 4: Verify green**

Run:

```bash
bash ajou-bb/scripts/sync-plugin-copy.sh
bash ajou-bb/tests/verify_setup.sh
for file in plugins/ai-skills/skills/ajou-bb/adapter/*.js; do node --check "$file"; done
git diff --check
```

Expected: no parity output, both copies pass syntax checks, and no generated shim is copied.

- [ ] **Step 5: Commit**

```bash
git add ajou-bb/scripts/sync-plugin-copy.sh plugins/ai-skills/skills/ajou-bb
git commit -m "feat(ajou-bb): package standalone adapter"
```

### Task 4: Document semantics and complete scoped acceptance

**Files:**
- Modify: ajou-bb/SKILL.md
- Modify: plugins/ai-skills/skills/ajou-bb/SKILL.md

**Interfaces:**
- Consumes: canonical source, setup, and plugin mirror.
- Produces: accurate setup and default-output documentation.

- [ ] **Step 1: Add setup documentation**

Before Ground Rules in the root SKILL.md, add:

```markdown
## Setup

This skill owns the ajou-bb adapter source. Before the first Blackboard request on a machine, run bash ./scripts/setup.sh from this skill directory.

Prerequisites: Node.js 20+ and a globally installed opencli command. Setup links $HOME/.opencli/clis/ajou-bb to this skill's adapter directory; it does not copy the adapter or make a Blackboard request. A physical existing adapter is kept as a timestamped backup.
```

Revise Ground Rule 1 to say opencli ajou-bb invokes this linked, skill-owned adapter. Add troubleshooting to rerun the setup script if command registration fails.

- [ ] **Step 2: Clarify preserved default path**

Add next to the download workflow:

```markdown
The adapter command default remains ./downloads/<course_name>/. The ./강의노트/<course_name>/ location is used only when the workflow explicitly passes --out ./강의노트/<course_name>/.
```

- [ ] **Step 3: Sync and run final non-live checks**

Run:

```bash
bash ajou-bb/scripts/sync-plugin-copy.sh
bash ajou-bb/tests/verify_setup.sh
node --test ajou-bb/tests/adapter.test.mjs
opencli validate ajou-bb
git diff --check
git status --short
```

Expected: local checks pass, no Blackboard request occurs, both distributions match, and generated shims remain unstaged.

- [ ] **Step 4: Commit**

```bash
git add ajou-bb/SKILL.md plugins/ai-skills/skills/ajou-bb/SKILL.md
git commit -m "docs(ajou-bb): document standalone adapter setup"
```

## Self-review

### Spec coverage

- Canonical source ownership: Task 1.
- Symlink runtime, backup, and no automatic install: Task 2.
- Root and plugin packaging: Task 3.
- Chrome-session boundary and unchanged download behavior: Task 4.
- Automated/local verification stays separate from an optional future logged-in Blackboard smoke test.

### Placeholder scan

No implementation placeholders remain. Live Blackboard calls are excluded because this work proves packaging and registration without account-data access.

### Type consistency

The tests use actual adapter exports: requireTerm(value), sanitizeFileName(name), resolveOutDir(outArg, courseName), and filterFilesForDownload(files, options).
