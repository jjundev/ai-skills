# grill-yourself Renewal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `grill-yourself/SKILL.md` so it turns a vague feature idea into a concrete design in one autonomous pass, with a single batched question round at the end, at roughly one third of its current length.

**Architecture:** One markdown skill file is replaced wholesale. A small shell check script asserts the file's structure (frontmatter, required sections, absence of removed features, size budget) and serves as the regression test. A manual dry run in a fresh session verifies the behavioral requirements the script cannot.

**Tech Stack:** Markdown skill file with YAML frontmatter; bash + grep for the structural check.

**Spec:** No spec file exists. The design was agreed in chat on 2026-09-08 (bounded path of /brainstorming, merged with a parallel session's decision table). The full agreed design is reproduced in the **Spec summary** section below so this plan is self-contained.

## Global Constraints

- The skill stays manual-only: frontmatter must keep `disable-model-invocation: true`.
- The skill is read-only: the body must forbid editing project code, docs, and the plan, and must state that implementation starts only in a later turn on the user's word.
- Removed entirely: `--viz`, the 20-decision safety cap, the `## Unresolved areas` section, the `## Self-check` section, and any reference to `_shared/grill-viz.md`.
- Kept by name (the user relies on them): the two buckets **Confident** / **Needs you**, numbered decision rows, `#<n>=<value>` overrides, the Needs-you round.
- Size budget: the new `SKILL.md` must be at most 5000 bytes (current file is 9251).
- Do not touch `grill-yourself-with-docs`, `grill-review`, `grill-verify`, or `_shared/grill-viz.md`. The user has marked them for deletion.
- The skill body is written in English like its siblings; it instructs the model to match the conversation language in output, headings included.

## Spec summary (the agreed design)

| # | Decision | Agreed value |
|---|---|---|
| 0 | Approach comparison | Architectural work only. Table (approach / pro / con / chosen). It is decision row #0, flippable with `#0=`. Bounded work skips it. |
| 1 | User intervention point | Exactly one: the Needs-you round right after the design. The intent paragraph is the first Needs-you row when the idea admits more than one reading. |
| 2 | Deliverable | Chat output structured so `writing-plans` can consume the implementation spec directly. File only on explicit request. |
| 3 | Scope classification | Announced out loud as **bounded** or **architectural**. When in doubt, architectural. |
| 4 | Decomposition | Judged in step 1 while locking intent, not by a decision count. If several independent subsystems are bundled, list them and proceed with only the first. No numeric cap. |
| 5 | Termination | Convergence: an implementer could build without asking anything else. Bounded work typically converges within about 8 rows. |
| 6 | Output order | Intent (with classification) → Behavior when done → Not in this round → Approaches (architectural only) → Implementation spec → Decisions (Confident, Needs you) → footer. |
| 7 | Needs-you round | One message, all questions batched, each a concrete choice (never yes/no), assumed value stated as the recommendation. |
| 8 | Needs-you answered | Mark rows **[confirmed]**, re-derive dependents if an answer differs, re-emit only changed sections, then stop. |
| 9 | Needs-you skipped | If the user moves on without answering, accept assumed values and mark **[confirmed by default]**. |
| 10 | Evidence | Prefer reading code over reasoning; cite `file:line` when a code fact backs a decision. |
| 11 | Implementation spec contents | Components, files to touch, interfaces, data flow, error handling, how to test. |
| 12 | Read-only rule | Stated once, in its own short section. No repeated prohibitions, no self-check section. |
| 13 | Invocation | Manual only. Description rewritten to say "vague idea → concrete design", not "stress-test a plan". |

---

### Task 1: Structural check script and the new SKILL.md

**Files:**
- Create: `grill-yourself/tests/check_skill.sh`
- Modify: `grill-yourself/SKILL.md` (full replacement, currently 9251 bytes)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `grill-yourself/tests/check_skill.sh` — exits 0 when `grill-yourself/SKILL.md` satisfies the Global Constraints, exits 1 and prints one line per violation otherwise. Task 2 re-runs it after any wording fix.

- [ ] **Step 1: Write the failing structural check**

Create `grill-yourself/tests/check_skill.sh` with exactly this content:

```bash
#!/usr/bin/env bash
# Structural check for grill-yourself/SKILL.md.
# Exit 0 = all constraints hold. Exit 1 = at least one violation, printed per line.
set -u
here="$(cd "$(dirname "$0")/.." && pwd)"
f="$here/SKILL.md"
fail=0

say() { echo "FAIL: $1"; fail=1; }

[ -f "$f" ] || { echo "FAIL: $f missing"; exit 1; }

# Frontmatter
head -1 "$f" | grep -q '^---$'                       || say "frontmatter must start with ---"
grep -q '^name: grill-yourself$' "$f"                || say "frontmatter name must be grill-yourself"
grep -q '^disable-model-invocation: true$' "$f"      || say "must stay manual-only (disable-model-invocation: true)"
grep -q '/grill-yourself' "$f"                       || say "description must mention /grill-yourself"

# Required sections (headings)
for h in "## Read-only" "## Procedure" "## Output format" "## Needs-you round" "## Overrides"; do
  grep -qF "$h" "$f" || say "missing section: $h"
done

# Required template headings inside the output format
for h in "## Intent" "## Behavior when done" "## Not in this round" "## Approaches" "## Implementation spec" "## Decisions" "### Confident" "### Needs you"; do
  grep -qF "$h" "$f" || say "missing template heading: $h"
done

# Kept-by-name features
grep -qF '#<n>=<value>' "$f"                          || say "override syntax #<n>=<value> missing"
grep -qF '[confirmed]' "$f"                           || say "[confirmed] marker missing"
grep -qF '[confirmed by default]' "$f"                || say "[confirmed by default] marker missing"
grep -qF 'file:line' "$f"                             || say "file:line evidence rule missing"
grep -qiF 'bounded' "$f"                              || say "bounded classification missing"
grep -qiF 'architectural' "$f"                        || say "architectural classification missing"

# Removed features must be gone
for bad in "--viz" "safety cap" "Unresolved areas" "Self-check" "grill-viz" "20 decisions"; do
  grep -qF -- "$bad" "$f" && say "stale reference still present: $bad"
done

# Size budget
size=$(wc -c < "$f" | tr -d ' ')
[ "$size" -le 5000 ] || say "SKILL.md is $size bytes, budget is 5000"

[ "$fail" -eq 0 ] && echo "OK: grill-yourself/SKILL.md passes structural check ($size bytes)"
exit $fail
```

Then make it executable:

```bash
chmod +x grill-yourself/tests/check_skill.sh
```

- [ ] **Step 2: Run the check to verify it fails against the current file**

Run: `grill-yourself/tests/check_skill.sh`

Expected: exit 1 with at least these lines:
```
FAIL: missing section: ## Read-only
FAIL: missing template heading: ## Intent
FAIL: stale reference still present: --viz
FAIL: stale reference still present: safety cap
FAIL: stale reference still present: Unresolved areas
FAIL: stale reference still present: Self-check
FAIL: SKILL.md is 9251 bytes, budget is 5000
```

- [ ] **Step 3: Replace SKILL.md with the renewed skill**

Overwrite `grill-yourself/SKILL.md` with exactly this content:

````markdown
---
name: grill-yourself
description: >-
  Turn a vague feature idea into a concrete, implementable design without a
  back-and-forth interview. Pose every design question yourself and answer it with
  your recommended choice; ask the user only once, at the end, about the guesses the
  codebase cannot confirm. Read-only. Invoke explicitly with /grill-yourself.
disable-model-invocation: true
---

Input is an idea, usually one or two sentences ("add X to the app"). Output is a
concrete design an implementer can act on. The interview still happens, but you play
both sides: the user's turn is collapsed into one batched question round after the
design is on the table.

## Read-only
Never edit project code, docs, or the design itself. Explore the codebase with
read-only tools (Bash for inspection only). The design goes in chat; write it to a
file only if the user explicitly asks. A finished design is not a green light:
implementation starts only when the user says so, in a later turn.

## Procedure (no stops until the design is emitted)
1. **Lock the intent.** Restate the idea in one paragraph: what gets built, for whom,
   what "done" looks like. If the idea bundles several independent subsystems, say
   so, list them, and proceed with only the first. If the intent admits more than one
   reading, pick one and make it the first row of the Needs-you bucket.
2. **Explore, then classify.** Read the code the change touches. Classify out loud:
   **bounded** (changes a flow that already exists in the repo) or **architectural**
   (new subsystem, new interfaces, or nothing existing to change). When in doubt,
   architectural.
3. **Pick an approach** (architectural only). Lay out 2–3 materially different
   approaches in a table, choose one with a one-line reason. This is decision #0.
   Bounded work skips this section.
4. **Resolve decisions in dependency order.** Take the unresolved decision whose
   reversal would change the most others, answer it with your recommendation and a
   one-line rationale, then its dependents. Prefer reading code over reasoning; cite
   `file:line` whenever a code fact backs the pick. Cosmetic leaf details get
   defaults in the spec, not table rows. Stop when an implementer could build without
   asking anything else; bounded work typically converges within about 8 rows.
5. **Sort each decision into a bucket.**
   - **Confident** — backed by codebase facts or sound defaults.
   - **Needs you** — filled with a guess only the user can confirm: product
     direction, priorities, deadlines, business rules.
6. **Emit the design** in the format below, then run the Needs-you round.

## Output format
Match the language of the conversation, headings included.

```
# <Title>

## Intent
<one paragraph: what, for whom, what done looks like>
Classification: bounded | architectural — <one line why>

## Behavior when done
- <user-facing: what they can do, what they see, how it fails>

## Not in this round
- <deliberately excluded item> — <one line why>

## Approaches   (architectural only)
| # | Approach | Pro | Con | Chosen |
|---|---|---|---|---|
| 0 | ... | ... | ... | ✔ / — |

## Implementation spec
<components, files to touch, interfaces, data flow, error handling, how to test —
written so writing-plans can consume it directly>

## Decisions
### Confident
| # | Decision | Answer | Rationale (file:line where applicable) |
|---|---|---|---|
### Needs you
| # | Decision | Assumed | Why only you can decide |
|---|---|---|---|

---
To flip a decision, re-invoke with `#<n>=<value>`.
```

## Needs-you round (same turn, right after the design)
If the Needs-you bucket has rows, immediately send ONE message that asks about all of
them. Each question names a concrete choice or value (never yes/no) and states the
assumed value as the recommended answer.

When the user answers:
- Mark each resolved row **[confirmed]** and restate its final value.
- If an answer differs from the assumption, re-derive dependent decisions and re-emit
  only the sections that changed.
- If the user moves on without answering ("go ahead", a new topic), accept every open
  row at its assumed value and mark it **[confirmed by default]**.
- Then stop. Implementation is the user's call, in the next turn.

## Overrides
`#<n>=<value>` arguments lock those decisions and re-derive everything else around
them. This needs the prior decision table in context; without it, ask the user to
restate the idea and run the full procedure.

## The only stop before the design
Ask only when there is no idea to work from: none stated and none inferable from the
conversation.
````

- [ ] **Step 4: Run the check to verify it passes**

Run: `grill-yourself/tests/check_skill.sh`

Expected: exit 0 with one line `OK: grill-yourself/SKILL.md passes structural check (<N> bytes)` where N is at most 5000.

- [ ] **Step 5: Confirm no other file in the repo changed**

Run: `git status --porcelain -- grill-yourself grill-yourself-with-docs grill-review grill-verify _shared`

Expected: exactly two lines, ` M grill-yourself/SKILL.md` and `?? grill-yourself/tests/`. Any line naming another directory means the read-only-siblings constraint was violated; revert that file with `git checkout -- <path>`.

- [ ] **Step 6: Commit**

```bash
git add grill-yourself/SKILL.md grill-yourself/tests/check_skill.sh
git commit -m "feat(grill-yourself): renew as idea-to-design skill with single batched question round

Replaces the plan-stress-test framing with idea concretization: intent lock,
bounded/architectural classification, approach table as decision #0,
dependency-order resolution, spec-first output, one batched Needs-you round.
Removes --viz, the 20-decision cap, Unresolved areas, and the self-check section.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: Behavioral dry run in a fresh session

The structural check cannot see whether the skill actually walks to the end without
stopping, orders its output as specified, or batches its questions. This task verifies
those three behaviors by running the skill once on a real idea in this repo and fixing
wording if any behavior fails.

**Files:**
- Modify (only if a behavior fails): `grill-yourself/SKILL.md`
- Test: `grill-yourself/tests/check_skill.sh` (re-run after any edit)
- Create: `grill-yourself/tests/dryrun-2026-09-08.md` (the recorded result)

**Interfaces:**
- Consumes: `grill-yourself/tests/check_skill.sh` from Task 1 (exit 0 = structure OK).
- Produces: `grill-yourself/tests/dryrun-2026-09-08.md`, a short record of the dry run with a PASS/FAIL line per behavior.

- [ ] **Step 1: Start a fresh session and invoke the skill on a bounded idea**

In a new Claude Code session rooted at `/Users/hyunjun_macbook_pro/.ai-skills`, send exactly:

```
/grill-yourself audio-stt 스킬에 전사 결과를 SRT 자막 파일로도 내보내는 옵션을 추가하고 싶어. 이 아이디어를 구체화해줘.
```

Use a fresh session so the model has no memory of this plan; the skill must work from its file alone.

- [ ] **Step 2: Judge the first response against three behaviors**

Record one line per behavior. All three must hold for PASS:

| Behavior | PASS condition |
|---|---|
| No mid-walk stop | The first assistant message contains the full design (all headings through the Decisions tables and footer). No question is asked before the design. |
| Output order | Headings appear in this order: Intent (with a `Classification:` line saying bounded) → Behavior when done → Not in this round → Implementation spec → Decisions with Confident then Needs you. The Approaches section is absent because the work is bounded. |
| Batched questions | If the Needs you table has rows, a single follow-up message asks about all of them. Each question offers concrete values and names the assumed value as the recommendation. No yes/no questions. |

Also record, for information: the number of Confident rows, the number of Needs-you rows, and whether at least one Confident row cites a `file:line` under `audio-stt/`.

- [ ] **Step 3: Exercise the skip path**

Reply to the Needs-you message with exactly:

```
그냥 추천대로 진행해.
```

PASS condition: the response marks every open row **[confirmed by default]** (or its Korean rendering), re-emits nothing that did not change, and stops without starting implementation and without asking anything further.

- [ ] **Step 4: Write the dry-run record**

Create `grill-yourself/tests/dryrun-2026-09-08.md` in this shape, filling in the actual observations:

```markdown
# grill-yourself dry run — 2026-09-08

Idea: audio-stt SRT export option (expected classification: bounded)

| Behavior | Result | Note |
|---|---|---|
| No mid-walk stop | PASS/FAIL | <what happened> |
| Output order | PASS/FAIL | <heading order observed> |
| Batched questions | PASS/FAIL | <N questions in one message / or N separate messages> |
| Skip path | PASS/FAIL | <markers observed, did it stop> |

Confident rows: <n>   Needs-you rows: <n>   file:line citation present: yes/no
```

- [ ] **Step 5: If any behavior failed, tighten the wording and re-check**

Edit only the section of `grill-yourself/SKILL.md` that governs the failed behavior:

- Mid-walk stop → strengthen the heading text of "## Procedure (no stops until the design is emitted)" and the sentence in "## The only stop before the design".
- Output order → the template in "## Output format".
- Batched questions → the first paragraph of "## Needs-you round".
- Skip path → the "[confirmed by default]" bullet in "## Needs-you round".

After editing, run `grill-yourself/tests/check_skill.sh` and confirm exit 0, then repeat Steps 1–4 in another fresh session. Do not loop more than twice; if a behavior still fails after two wording fixes, record FAIL with the observation and stop so the user can decide.

- [ ] **Step 6: Commit the dry-run record (and any wording fix)**

```bash
git add grill-yourself/tests/dryrun-2026-09-08.md grill-yourself/SKILL.md
git commit -m "test(grill-yourself): record behavioral dry run on audio-stt SRT idea

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Self-review

**Spec coverage.** Every row of the Spec summary maps to text in Task 1 Step 3: #0 → Procedure step 3 and the Approaches table; #1 → the Needs-you round and Procedure step 1's "first row" sentence; #2 → the Read-only section and the "written so writing-plans can consume it" line; #3 → Procedure step 2; #4 → Procedure step 1's subsystem sentence; #5 → Procedure step 4's stop condition; #6 → the Output format template; #7, #8, #9 → the Needs-you round bullets; #10 → Procedure step 4's `file:line` sentence; #11 → the Implementation spec placeholder line; #12 → the single Read-only section and the absence of a Self-check section; #13 → the frontmatter. Behaviors that text alone cannot prove (#1, #6, #7, #9) are exercised in Task 2.

**Placeholder scan.** The template in Step 3 uses angle-bracket slots by design; they are instructions to the model at run time, not gaps in this plan. No TBD/TODO in the plan itself.

**Consistency.** The check script's required headings match the headings in the SKILL.md content byte for byte: `## Read-only`, `## Procedure`, `## Output format`, `## Needs-you round`, `## Overrides`, and the template headings `## Intent` through `### Needs you`. The stale-reference list matches the removed features in Global Constraints. The size budget (5000) is the same in both places.
