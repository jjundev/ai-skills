# Prune Caveman Overlap and Allowlist Upstream Sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Caveman skills that overlap Superpowers or cannot run here, remove the duplicate `tdd/` and `diagnosing-bugs/` alias directories, and make `sync-upstream.sh` copy only an explicit allowlist so the removals stay removed.

**Architecture:** This repo (`~/.ai-skills`) is one flat directory; every subdirectory containing `SKILL.md` is a skill in Claude Code, Gemini CLI and Codex via symlinks. Cleanup is pure `git rm`. The sync script is rewritten around two bash arrays (Superpowers names, Caveman names); each name is deleted locally and re-copied from a shallow clone, and only those paths are staged for the auto-commit. A shell test drives the script against fake local upstream repos via `SUPERPOWERS_REPO` / `CAVEMAN_REPO` overrides.

**Tech Stack:** bash 3.2 (macOS `/bin/bash`; no bash-4 features), git, `mktemp`. No other dependencies.

**Spec:** In-chat design approved 2026-09-08 (no spec file; bounded path). The binding decisions are copied into Global Constraints below.

## Global Constraints

- Work on branch `claude/superpowers-caveman-overlap-3294d9` in worktree `/Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9`. Do not merge to `main`; do not touch the main checkout at `~/.ai-skills`.
- Do not modify any file outside this repo (no `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, settings).
- Keep exactly these Caveman skills: `caveman`, `caveman-commit`, `caveman-compress`, `caveman-explore`, `caveman-help`, `caveman-review`, `migration`.
- Keep all 14 Superpowers skills, all Matt Pocock skills (including `grill-me` and `grilling`), and all user skills.
- Do not edit `caveman-help/SKILL.md` or `setup-matt-pocock-skills/SKILL.md` even though they mention removed skills; they are upstream/third-party files and editing them creates sync drift.
- Scripts must run under `/bin/bash` 3.2: no associative arrays, no `${var,,}`, no `mapfile`, and never expand an empty array with `"${arr[@]}"` under `set -u`.
- Expected end state: 66 directories containing `SKILL.md` (81 now, minus 15), and zero duplicate `name:` values across all `SKILL.md` files.
- The interactive tool shell in this environment is zsh. Run every script through its shebang (`./script.sh`) or `/bin/bash script.sh`, not by pasting bash-only syntax into the tool shell.

---

### Task 1: Remove non-kept Caveman skills and leaked build tooling

**Files:**
- Delete: `investigate-first/`, `lean-build/`, `surgical-patch/`, `safe-refactor/`, `verify-and-stop/`
- Delete: `cavecrew/`, `caveman-stats/`, `caveman-setup/`, `caveman-discover/`, `caveman-evidence-review/`, `caveman-manage/`, `caveman-learn/`, `caveman-optimize/`
- Delete: `compile.mjs`, `verbs-gate.mjs`, `registry.json`, `native-core.md`, `engine-mcp-tools.json`, `generated/`

**Interfaces:**
- Consumes: nothing.
- Produces: a tree where the only Caveman-origin directories are the seven kept ones. Task 3's `CAVEMAN_SKILLS` array lists exactly those seven.

- [ ] **Step 1: Record the baseline count (this is the "failing" state)**

Run:
```bash
/bin/bash -c 'ls -d */SKILL.md | wc -l && ls -d cavecrew compile.mjs generated 2>&1'
```
Expected: `81`, and the three paths print (they exist).

- [ ] **Step 2: Remove the 13 skill directories and 6 build files with git**

Run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && git rm -r -q investigate-first lean-build surgical-patch safe-refactor verify-and-stop cavecrew caveman-stats caveman-setup caveman-discover caveman-evidence-review caveman-manage caveman-learn caveman-optimize compile.mjs verbs-gate.mjs registry.json native-core.md engine-mcp-tools.json generated && git status --short | wc -l'
```
Expected: a positive number of `D` lines (no error output).

- [ ] **Step 3: Verify the count and that every kept Caveman skill survived**

Run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && echo "skills: $(ls -d */SKILL.md | wc -l | tr -d " ")" && for d in caveman caveman-commit caveman-compress caveman-explore caveman-help caveman-review migration; do [ -f "$d/SKILL.md" ] && echo "kept: $d" || echo "MISSING: $d"; done && for f in compile.mjs verbs-gate.mjs registry.json native-core.md engine-mcp-tools.json generated cavecrew lean-build; do [ -e "$f" ] && echo "STILL PRESENT: $f"; done; echo done'
```
Expected: `skills: 68`, seven `kept:` lines, no `MISSING:` and no `STILL PRESENT:` lines.

- [ ] **Step 4: Commit**

```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && git commit -q -m "chore: drop caveman workflow/CLI-dependent skills and leaked build tooling

Superpowers stays the process spine. Removed the 5 caveman workflow
skills that overlap it (investigate-first, lean-build, surgical-patch,
safe-refactor, verify-and-stop), the 8 skills that need the caveman
CLI, hooks or cavecrew agents which are not installed here, and the
build files (compile.mjs, verbs-gate.mjs, registry.json, native-core.md,
engine-mcp-tools.json, generated/) that cp -R leaked into the skills root.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" && git log --oneline -1'
```
Expected: one new commit line beginning with `chore: drop caveman`.

---

### Task 2: Remove the `tdd/` and `diagnosing-bugs/` alias directories

**Files:**
- Delete: `tdd/`, `diagnosing-bugs/`

**Interfaces:**
- Consumes: nothing.
- Produces: unique `name:` values across all `SKILL.md`. Task 3 must not reintroduce the two `if [ -d ... ]` overwrite blocks.

- [ ] **Step 1: Confirm the duplication exists (failing state)**

Run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && sed -n "s/^name: *//p" */SKILL.md | tr -d "\"" | sort | uniq -d'
```
Expected: two lines, `systematic-debugging` and `test-driven-development`.

- [ ] **Step 2: Remove both directories with git**

Run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && git rm -r -q tdd diagnosing-bugs && ls -d tdd diagnosing-bugs 2>&1'
```
Expected: two `No such file or directory` lines.

- [ ] **Step 3: Verify uniqueness and count**

Run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && echo "dups: $(sed -n "s/^name: *//p" */SKILL.md | tr -d "\"" | sort | uniq -d | wc -l | tr -d " ")" && echo "skills: $(ls -d */SKILL.md | wc -l | tr -d " ")" && [ -f test-driven-development/SKILL.md ] && [ -f systematic-debugging/SKILL.md ] && echo canonical-ok'
```
Expected: `dups: 0`, `skills: 66`, `canonical-ok`.

- [ ] **Step 4: Commit**

```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && git commit -q -m "chore: remove tdd/ and diagnosing-bugs/ alias copies of superpowers skills

Both were Matt Pocock skills that sync-upstream.sh overwrote with
byte-identical copies of test-driven-development and
systematic-debugging, so every harness indexed each skill twice under
mismatched directory/name pairs. The canonical superpowers directories
remain.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" && git log --oneline -1'
```
Expected: one new commit line beginning with `chore: remove tdd/`.

---

### Task 3: Rewrite `sync-upstream.sh` around an explicit allowlist (test-first)

**Files:**
- Create: `tests/sync-upstream.test.sh`
- Modify: `sync-upstream.sh` (full rewrite; current file is 31 lines)

**Interfaces:**
- Consumes: the seven kept Caveman directory names from Task 1 and the 14 Superpowers names.
- Produces: `sync-upstream.sh` honoring env overrides `SUPERPOWERS_REPO`, `CAVEMAN_REPO` (git URLs; default GitHub), and `NO_COMMIT=1` (skip the commit step). It copies only allowlisted `skills/<name>` directories, deletes-then-recopies each so upstream file removals propagate, prints `WARN:` and continues when an allowlisted name is missing upstream, stages only the synced paths, and prints `✨ All skills are already up-to-date.` when nothing changed. Task 4 runs it for real.

- [ ] **Step 1: Write the failing test**

Create `tests/sync-upstream.test.sh` with exactly this content and make it executable:

```bash
#!/usr/bin/env bash
# Tests sync-upstream.sh against fake local upstream repos.
# Run: ./tests/sync-upstream.test.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FAILS=0

fail() { echo "FAIL: $*" >&2; FAILS=$((FAILS + 1)); }
pass() { echo "ok: $*"; }

git_q() { git -c user.name=t -c user.email=t@t -c commit.gpgsign=false "$@"; }

# Build a fake upstream repo with the given skill dirs / files under skills/.
make_upstream() {
  local dir="$1"; shift
  mkdir -p "$dir/skills"
  local entry
  for entry in "$@"; do
    case "$entry" in
      */) mkdir -p "$dir/skills/$entry"; printf 'upstream %s\n' "$entry" > "$dir/skills/${entry}SKILL.md" ;;
      *)  printf 'build file\n' > "$dir/skills/$entry" ;;
    esac
  done
  git_q -C "$dir" init -q
  git_q -C "$dir" add -A
  git_q -C "$dir" commit -q -m init
}

make_upstream "$WORK/superpowers" brainstorming/ writing-plans/ lean-build/ compile.mjs
make_upstream "$WORK/caveman" caveman/ cavecrew/ registry.json

# Fake local skills repo containing the script under test.
LOCAL="$WORK/local"
mkdir -p "$LOCAL/brainstorming" "$LOCAL/lean-build"
cp "$HERE/sync-upstream.sh" "$LOCAL/sync-upstream.sh"
printf 'old\n' > "$LOCAL/brainstorming/SKILL.md"
printf 'stale\n' > "$LOCAL/brainstorming/stale.md"        # must disappear
printf 'local only\n' > "$LOCAL/lean-build/SKILL.md"      # not allowlisted: must be left alone
git_q -C "$LOCAL" init -q
git_q -C "$LOCAL" add -A
git_q -C "$LOCAL" commit -q -m init
printf 'mine\n' > "$LOCAL/mine.txt"                        # unrelated, uncommitted: must stay untracked

export SUPERPOWERS_REPO="file://$WORK/superpowers"
export CAVEMAN_REPO="file://$WORK/caveman"

# --- Run 1: real sync with commit ---
OUT1="$( cd "$LOCAL" && ./sync-upstream.sh 2>&1 )" || { echo "$OUT1"; fail "run 1 exited non-zero"; }

[ "$(cat "$LOCAL/brainstorming/SKILL.md")" = "upstream brainstorming/" ] && pass "allowlisted skill copied" || fail "brainstorming not updated"
[ ! -e "$LOCAL/brainstorming/stale.md" ] && pass "stale file removed by delete-then-copy" || fail "stale.md survived"
[ "$(cat "$LOCAL/caveman/SKILL.md")" = "upstream caveman/" ] && pass "caveman copied" || fail "caveman not copied"
[ ! -e "$LOCAL/compile.mjs" ] && [ ! -e "$LOCAL/registry.json" ] && pass "build files not copied" || fail "build file leaked"
[ ! -e "$LOCAL/cavecrew" ] && pass "non-allowlisted upstream skill not copied" || fail "cavecrew leaked"
[ "$(cat "$LOCAL/lean-build/SKILL.md")" = "local only" ] && pass "non-allowlisted local dir untouched" || fail "lean-build was modified"
echo "$OUT1" | grep -q "WARN:.*writing-skills" && pass "missing upstream skill warns" || fail "no WARN for missing writing-skills"
[ "$(git -C "$LOCAL" status --short mine.txt)" = "?? mine.txt" ] && pass "unrelated file left untracked" || fail "mine.txt was staged or committed"
[ "$(git -C "$LOCAL" rev-list --count HEAD)" = "2" ] && pass "one sync commit created" || fail "expected 2 commits, got $(git -C "$LOCAL" rev-list --count HEAD)"
CHANGED="$(git -C "$LOCAL" show --name-only --pretty=format: HEAD | cut -d/ -f1 | sort -u | tr '\n' ' ')"
[ "$CHANGED" = "brainstorming caveman writing-plans " ] && pass "commit touches only synced dirs" || fail "commit touched: $CHANGED"

# --- Run 2: nothing changed upstream ---
OUT2="$( cd "$LOCAL" && ./sync-upstream.sh 2>&1 )" || fail "run 2 exited non-zero"
echo "$OUT2" | grep -q "already up-to-date" && pass "no-op run reports up-to-date" || fail "run 2 output: $OUT2"
[ "$(git -C "$LOCAL" rev-list --count HEAD)" = "2" ] && pass "no-op run makes no commit" || fail "run 2 created a commit"

# --- Run 3: NO_COMMIT=1 leaves changes uncommitted ---
printf 'upstream v2\n' > "$WORK/superpowers/skills/brainstorming/SKILL.md"
git_q -C "$WORK/superpowers" commit -q -am v2
OUT3="$( cd "$LOCAL" && NO_COMMIT=1 ./sync-upstream.sh 2>&1 )" || fail "run 3 exited non-zero"
[ "$(cat "$LOCAL/brainstorming/SKILL.md")" = "upstream v2" ] && pass "NO_COMMIT still copies" || fail "NO_COMMIT did not copy"
[ "$(git -C "$LOCAL" rev-list --count HEAD)" = "2" ] && pass "NO_COMMIT makes no commit" || fail "NO_COMMIT committed"

if [ "$FAILS" -eq 0 ]; then echo "ALL PASSED"; else echo "$FAILS FAILED"; exit 1; fi
```

Then run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && chmod +x tests/sync-upstream.test.sh && bash -n tests/sync-upstream.test.sh && echo syntax-ok'
```
Expected: `syntax-ok`.

- [ ] **Step 2: Run the test against the current script to verify it fails**

Run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && ./tests/sync-upstream.test.sh; echo "exit=$?"'
```
Expected: several `FAIL:` lines (at minimum `build file leaked`, `cavecrew leaked`, `mine.txt was staged or committed`) and `exit=1`. The old script ignores the env overrides and would try to reach GitHub; if the run hangs on network, that is itself the failure — press on to Step 3.

- [ ] **Step 3: Replace `sync-upstream.sh` with the allowlist implementation**

Overwrite `sync-upstream.sh` with exactly this content:

```bash
#!/usr/bin/env bash
# sync-upstream.sh — pull an explicit allowlist of skills from upstream repos.
#
# Only the directory names listed below are copied out of each upstream's
# skills/ folder. Everything else there (build tooling, hook/CLI-dependent
# skills, workflow skills that overlap Superpowers) is ignored on purpose.
# Each listed skill is deleted locally and re-copied, so files removed
# upstream disappear here too. Removing a name from a list makes future
# syncs leave that directory alone; it does not delete it.
#
# Env overrides (mainly for tests):
#   SUPERPOWERS_REPO / CAVEMAN_REPO  git URLs to clone instead of GitHub
#   NO_COMMIT=1                      copy files but skip the git commit
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUPERPOWERS_REPO="${SUPERPOWERS_REPO:-https://github.com/obra/superpowers.git}"
CAVEMAN_REPO="${CAVEMAN_REPO:-https://github.com/JuliusBrussee/caveman.git}"
NO_COMMIT="${NO_COMMIT:-0}"

SUPERPOWERS_SKILLS=(
  brainstorming
  dispatching-parallel-agents
  executing-plans
  finishing-a-development-branch
  receiving-code-review
  requesting-code-review
  subagent-driven-development
  systematic-debugging
  test-driven-development
  using-git-worktrees
  using-superpowers
  verification-before-completion
  writing-plans
  writing-skills
)

# Kept on purpose: pure-prompt utilities with no Superpowers equivalent.
# Dropped on purpose: investigate-first, lean-build, surgical-patch,
# safe-refactor, verify-and-stop (overlap Superpowers) and cavecrew,
# caveman-stats, caveman-setup/discover/evidence-review/manage/learn/optimize
# (need the caveman CLI, hooks or agents, which are not installed).
CAVEMAN_SKILLS=(
  caveman
  caveman-commit
  caveman-compress
  caveman-explore
  caveman-help
  caveman-review
  migration
)

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

SYNCED=()

sync_skills() {
  local label="$1" repo="$2"
  shift 2
  local clone="$TMP_DIR/$label"
  echo "=== Syncing $label ==="
  git clone --quiet --depth 1 "$repo" "$clone"
  local name
  for name in "$@"; do
    if [ ! -d "$clone/skills/$name" ]; then
      echo "WARN: $label upstream has no skills/$name (renamed or removed?) - skipping" >&2
      continue
    fi
    rm -rf "${SKILLS_DIR:?}/$name"
    cp -R "$clone/skills/$name" "$SKILLS_DIR/$name"
    SYNCED+=("$name")
  done
}

sync_skills superpowers "$SUPERPOWERS_REPO" "${SUPERPOWERS_SKILLS[@]}"
sync_skills caveman "$CAVEMAN_REPO" "${CAVEMAN_SKILLS[@]}"

if [ "${#SYNCED[@]}" -eq 0 ]; then
  echo "Nothing synced (every allowlisted skill was missing upstream)." >&2
  exit 1
fi

if [ "$NO_COMMIT" = "1" ]; then
  echo "NO_COMMIT=1: files updated, skipping git commit."
  exit 0
fi

echo "=== Committing changes ==="
cd "$SKILLS_DIR"
git add -A -- "${SYNCED[@]}"
if git diff --cached --quiet; then
  echo "✨ All skills are already up-to-date."
else
  git commit -q -m "chore: auto-sync upstream skills on $(date +'%Y-%m-%d %H:%M:%S')"
  echo "✅ Skills updated and committed to Git."
fi
```

Then run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && chmod +x sync-upstream.sh && bash -n sync-upstream.sh && echo syntax-ok && grep -c "if \[ -d" sync-upstream.sh'
```
Expected: `syntax-ok` and `0` (the tdd/diagnosing-bugs overwrite blocks are gone).

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && ./tests/sync-upstream.test.sh; echo "exit=$?"'
```
Expected: every line starts with `ok:`, then `ALL PASSED`, `exit=0`. If `missing upstream skill warns` fails, check that the WARN line goes to stderr and that the test captures `2>&1` (it does).

- [ ] **Step 5: Commit**

```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && git add sync-upstream.sh tests/sync-upstream.test.sh && git commit -q -m "feat: sync only an explicit allowlist of upstream skills

Replaces cp -R skills/* with per-name delete-then-copy from two arrays,
so dropped caveman skills and build files never come back and upstream
file removals propagate. Stages only synced paths instead of git add -A,
warns on allowlisted names missing upstream, and supports
SUPERPOWERS_REPO/CAVEMAN_REPO/NO_COMMIT overrides used by the new test.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" && git log --oneline -1'
```
Expected: one new commit line beginning with `feat: sync only`.

---

### Task 4: Run the real sync and verify the end state

**Files:**
- No edits intended. The real script run may update allowlisted directories if upstream moved past v6.3.0 / v2.6.0; that lands as its own auto-commit which the user can keep or drop.

**Interfaces:**
- Consumes: `sync-upstream.sh` from Task 3.
- Produces: verified tree; a short report for the user.

- [ ] **Step 1: Snapshot the tree before the run**

Run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && git status --short | wc -l | tr -d " " && git rev-parse --short HEAD && ls -d */SKILL.md | wc -l | tr -d " "'
```
Expected: `0` (clean), a commit hash, `66`.

- [ ] **Step 2: Run the real sync against GitHub**

Run (needs network; allow up to 2 minutes):
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && ./sync-upstream.sh; echo "exit=$?"'
```
Expected: two `=== Syncing ...` blocks, no `WARN:` lines, then either `✨ All skills are already up-to-date.` or `✅ Skills updated and committed to Git.`, and `exit=0`. A `WARN:` line means upstream renamed a skill; report it to the user rather than editing the allowlist silently.

- [ ] **Step 3: Verify nothing outside the allowlist changed**

Run:
```bash
/bin/bash -c 'cd /Users/hyunjun_macbook_pro/.ai-skills/.claude/worktrees/superpowers-caveman-overlap-3294d9 && echo "untracked/dirty: $(git status --short | wc -l | tr -d " ")" && echo "skills: $(ls -d */SKILL.md | wc -l | tr -d " ")" && echo "dups: $(sed -n "s/^name: *//p" */SKILL.md | tr -d "\"" | sort | uniq -d | wc -l | tr -d " ")" && for f in compile.mjs registry.json generated cavecrew lean-build tdd diagnosing-bugs; do [ -e "$f" ] && echo "REAPPEARED: $f"; done; echo "last commit files by top dir:"; git show --name-only --pretty=format: HEAD | cut -d/ -f1 | sort -u'
```
Expected: `untracked/dirty: 0`, `skills: 66`, `dups: 0`, no `REAPPEARED:` lines. If the sync created a commit, the listed top-level dirs must all be names from the two arrays; if it did not, the listed files are `sync-upstream.sh` and `tests/sync-upstream.test.sh` from Task 3.

- [ ] **Step 4: Report**

Tell the user: the branch name, the commit list from `git log --oneline main..HEAD`, whether the real sync produced an upstream-update commit, and that merging into `main` is left to them. Mention that `check-upstream.sh` in the main checkout is still untracked and unaffected by this work.
