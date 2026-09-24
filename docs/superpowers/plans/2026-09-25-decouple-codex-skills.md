# Decouple Codex Skills Linking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple Codex skills management from `.ai-skills` repo linking so Codex uses `~/.agents/skills` natively as the single source of truth for global skills while keeping `~/.codex/skills` dedicated exclusively to its built-in `.system` tools, eliminating duplicated skill prompt injections.

**Architecture:** Remove `codex` (`~/.codex/skills`) from `GLOBAL_HOST_ROOTS` in `script/config.py`. Update tests to verify that `~/.agents/skills` remains the cross-agent host root and that `codex` is no longer managed in `GLOBAL_HOST_ROOTS`. Decouple the local host filesystem symlink `~/.codex/skills -> ~/.ai-skills` into an isolated directory containing only `.system/`, and verify via `codex debug prompt-input` that Codex natively loads all 97 managed skills from `~/.agents/skills` without any duplicate entries.

**Tech Stack:** Python 3.14 (`unittest`, `pathlib`, `shutil`, `subprocess`), OpenAI Codex CLI (`codex debug prompt-input`), Git.

**Spec:** User consultation confirming Codex natively discovers `~/.agents/skills` without requiring symlinks to `~/.codex/skills`, and that linking `~/.codex/skills` to `.ai-skills` creates redundant duplicate skill prompts.

## Global Constraints

- Never break existing global host roots for `agents`, `antigravity-config`, `antigravity-cli`, `claude`, and `antigravity-legacy`.
- Preserve Codex built-in system skills (`imagegen`, `openai-docs`, `plugin-creator`, `review-agent`, `skill-creator`, `skill-installer`) in `~/.codex/skills/.system`.
- Ensure all 68+ tests in `python3 script/manage.py test` pass cleanly.
- Verify zero duplicated skills in `codex debug prompt-input`.

## Review Focus

1. `tests/test_common.py` fails if `codex` assertion is not updated when removed from `GLOBAL_HOST_ROOTS`.
2. Existing backup or marker files in `~/.codex/skills` must be preserved or safely restored during unlinking.
3. `~/.agents/skills` must remain fully populated by `manage.py link` with all managed skills.
4. `manage.py link` output must not attempt to scan or link `~/.codex/skills`.
5. `codex debug prompt-input` must resolve `~/.agents/skills` as `r0` and `.system` as `r1` with 0 duplicate skills.

---

### Task 1: Update `script/config.py` and `tests/test_common.py`

**Files:**
- Modify: `script/config.py:20-27`
- Modify: `tests/test_common.py:18-24`

**Interfaces:**
- Consumes: `script.config.GLOBAL_HOST_ROOTS`
- Produces: `GLOBAL_HOST_ROOTS` without `("codex", USER_HOME / ".codex" / "skills")`

- [ ] **Step 1: Write the failing test**

In `tests/test_common.py`, update `test_global_host_roots_non_empty`:

```python
    def test_global_host_roots_non_empty(self):
        self.assertTrue(len(GLOBAL_HOST_ROOTS) >= 5)
        names = [name for name, _ in GLOBAL_HOST_ROOTS]
        self.assertIn("agents", names)
        self.assertIn("claude", names)
        self.assertIn("antigravity-config", names)
        self.assertNotIn("codex", names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_common.py -k test_global_host_roots_non_empty`
Expected: FAIL with `AssertionError: 'codex' unexpectedly found in [...]`

- [ ] **Step 3: Update `script/config.py`**

In `script/config.py`, remove the codex entry from `GLOBAL_HOST_ROOTS`:

```python
GLOBAL_HOST_ROOTS: list[tuple[str, Path]] = [
    ("agents", USER_HOME / ".agents" / "skills"),
    ("antigravity-config", USER_HOME / ".gemini" / "config" / "skills"),
    ("antigravity-cli", USER_HOME / ".gemini" / "antigravity-cli" / "skills"),
    ("claude", USER_HOME / ".claude" / "skills"),
    ("antigravity-legacy", USER_HOME / ".gemini" / "antigravity" / ".agents" / "skills"),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_common.py -k test_global_host_roots_non_empty`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add script/config.py tests/test_common.py
git commit -m "refactor(config): remove codex from GLOBAL_HOST_ROOTS"
```

---

### Task 2: Verify and Update `tests/test_link.py` and `script/link.py`

**Files:**
- Modify: `tests/test_link.py:138-160`
- Modify: `script/link.py:118-121` (optional / verify runtime filter retention)

**Interfaces:**
- Consumes: `script.link.link_skills`, `script.config.GLOBAL_HOST_ROOTS`
- Produces: Clean link execution without codex host scanning

- [ ] **Step 1: Check existing link tests**

Verify if `tests/test_link.py` has any tests expecting `codex` in `GLOBAL_HOST_ROOTS`. Note that `test_skip_codex_runtime_and_non_skill` uses `patch("script.link.GLOBAL_HOST_ROOTS", [("codex", codex_root)])`, which tests the defensive check in `link.py`. Ensure it continues to pass as defense-in-depth, or document that codex runtime protection remains active if patched.

- [ ] **Step 2: Run the full test suite**

Run: `python3 script/manage.py test`
Expected: PASS (all 68 tests pass)

- [ ] **Step 3: Commit if any adjustments made**

```bash
git add tests/test_link.py script/link.py
git commit -m "test(link): verify link tests pass with decoupled codex"
```

---

### Task 3: Decouple `~/.codex/skills` Symlink on Host Filesystem

**Files:**
- Target: `~/.codex/skills` (currently symlink pointing to `/Users/hyunjun_macbook_pro/.ai-skills`)
- Source for `.system`: `~/.ai-skills/.system` or `~/.codex/skills.bak_20260908_111117/.system`

**Interfaces:**
- Consumes: Filesystem state of `~/.codex/skills`
- Produces: Real directory `~/.codex/skills/` containing `.system/` only

- [ ] **Step 1: Inspect and backup current `~/.codex/skills` symlink**

Check current link target:
```bash
ls -ld ~/.codex/skills
```

- [ ] **Step 2: Remove symlink and create dedicated directory**

```bash
rm ~/.codex/skills
mkdir -p ~/.codex/skills
cp -R /Users/hyunjun_macbook_pro/.ai-skills/.system ~/.codex/skills/.system
```

- [ ] **Step 3: Verify contents of `~/.codex/skills`**

Run:
```bash
ls -la ~/.codex/skills
ls -la ~/.codex/skills/.system
```
Expected:
`~/.codex/skills` is a directory (not a symlink) containing only `.system`.
`.system` contains `imagegen`, `openai-docs`, `plugin-creator`, `review-agent`, `skill-creator`, `skill-installer`, `.codex-system-skills.marker`.

---

### Task 4: Run `manage.py link` and End-to-End Verification

**Files:**
- Host: `~/.agents/skills`
- Codex CLI runtime: `codex debug prompt-input`

**Interfaces:**
- Consumes: `python3 script/manage.py link`, `codex debug prompt-input`
- Produces: Clean, duplicate-free skill catalog loaded in Codex

- [ ] **Step 1: Execute `manage.py link`**

Run:
```bash
python3 script/manage.py link
```
Expected output:
- Central skill repository: `/Users/hyunjun_macbook_pro/.ai-skills`
- Scans `agents`, `antigravity-config`, `antigravity-cli`, `claude`, `antigravity-legacy`.
- Does NOT scan or link `codex`.
- All skills in `~/.agents/skills` are verified up-to-date symlinks.

- [ ] **Step 2: Verify Codex skill discovery and duplicate elimination**

Run python verification script:
```bash
python3 -c '
import json, subprocess
res = subprocess.run(["codex", "debug", "prompt-input"], capture_output=True, text=True, cwd="/tmp")
data = json.loads(res.stdout)
for msg in data:
    for content in msg.get("content", []):
        text = content.get("text", "")
        if "<skills_instructions>" in text:
            print("=== Skill Roots ===")
            for line in text.split("\n"):
                if line.startswith("- `r"):
                    print(line)
            # Check duplicates
            skills = [line.split(":")[0].strip("- ") for line in text.split("\n") if line.strip().startswith("- ") and "file:" in line]
            from collections import Counter
            counts = Counter(skills)
            dups = {k: v for k, v in counts.items() if v > 1}
            print(f"Total skills: {len(skills)}")
            print(f"Duplicate skills count: {len(dups)}")
            if dups:
                print("Duplicates found:", dups)
            else:
                print("✅ ZERO duplicates found!")
'
```
Expected:
- `r0` = `/Users/hyunjun_macbook_pro/.agents/skills`
- `r1` = `/Users/hyunjun_macbook_pro/.codex/skills/.system`
- Zero duplicate skills found.

- [ ] **Step 3: Run complete project test suite**

Run:
```bash
python3 script/manage.py test
```
Expected:
`OK` (all tests pass)

- [ ] **Step 4: Final commit and git status check**

```bash
git status
```
Ensure working tree is clean.
