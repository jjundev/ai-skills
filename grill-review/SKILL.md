---
name: grill-review
description: >-
  Objectively review a plan produced by grill-yourself (or any plan with a
  decision table) from a FRESH context. Spawns a separate read-only subagent that
  never saw the authoring reasoning, evaluates every decision along 5 axes
  (contradiction, hidden assumption, omission, reality mismatch, vagueness)
  against the real codebase, and returns a two-layer verdict — fact
  (confirmed/false/unverifiable, file:line evidence) × severity
  (Blocker/Advisory) — plus a diff-style revision for Blockers, a disposition,
  and a re-grill list. Flags: --deep (parallel reviewers), auto (hands-free fix
  loop that also folds Advisory into the revision). Optionally pass --viz to render
  the report as a self-contained local HTML dashboard. Invoke explicitly with
  /grill-review.
disable-model-invocation: true
---

The objective-review companion to `grill-yourself`. The agent that wrote a plan is
the worst judge of it — it carries every rationalization in context. So the actual
review is NEVER done by you (the current agent). You hand the plan to a fresh subagent
and relay its verdict.

This skill complements the grill family:
- `grill-me` / `grill-yourself` → produce a plan
- **`grill-review`** → critique that plan from a fresh context (this skill, pre-implementation)
- `grill-verify` → verify implementation against plan (post-implementation)

## Input
Take the plan + decision table from a `.md` path if given as an argument, otherwise
from the most recent plan in the conversation. If neither exists — no path and no plan
inferable from the conversation — ask the user for a plan to review; do not invent one.

Note which repo / working directory the plan targets and pass that to the reviewer, so
it verifies against the right codebase as ground truth (the plan `.md` may live in a
fixture or describe a different repo than the current cwd).

**Never overwrite the input `.md`.** Return the review — and any revised plan from
`auto` — in chat. Write to a file only if the user explicitly asks.

**Hard rule — purity of what you pass.** When you spawn the reviewer, pass ONLY the
plan and its decision table, VERBATIM. Never include your own reasoning, the codebase
exploration that produced the plan, or any defense of it. The reviewer must read it
cold, as a stranger's work. This is the one thing that makes the review objective —
the fresh subagent context is wasted if you leak authoring context into the prompt.

Parse args leniently: `deep`/`--deep` and `auto`/`--auto` set the flags; a `viz`/`--viz`
token enables the local HTML visualization (see *Visualization*); a `.md` token is the
plan path (see *Input*). Order doesn't matter, dashes are optional.

## How to run (default: fast single reviewer)
Use `collaboration.spawn_agent` to run the review in a fresh context. Give the
reviewer the plan, decision table, target working directory, and no authoring rationale.
For `--deep`, spawn two independent reviewers with non-overlapping focuses and reconcile
their reports. Do not dispatch further reviewers from a reviewer.

Instruct that subagent to:

- Treat the plan as a stranger's work — do NOT defend it.
- Work **read-only**: inspect files and run only non-mutating shell commands. Do not
  edit files and do not spawn further subagents.
- **Reality check first (mandatory if the plan touches code).** Identify every concrete
  code/file/API/library/config reference the plan makes and verify each with
  Glob/Grep/Read against the current codebase. Record what was checked and found — this
  is the evidence base for the "reality mismatch" axis. You may NOT raise a reality
  mismatch without first attempting verification; speculation is not a finding. If the
  plan has zero code references, note "Reality check: code-independent plan — skipped".
- **Evaluate each decision along 5 axes** against the REAL codebase (ground truth), not
  against the plan's own claims:
  1. **Contradiction** — does this decision conflict with another in the same plan?
  2. **Hidden assumption** — what unstated premise must hold? Is it actually true?
  3. **Omission** — is a critical sub-decision missing? Is an Unresolved area on a
     critical path that cannot be deferred?
  4. **Reality mismatch** — does the codebase / domain / library actually support this?
     (Must be backed by the reality-check evidence above.)
  5. **Vagueness** — is the decision actionable as-stated, or will the implementer have
     to re-decide it?
  A decision may have findings on several axes (record each), or zero (the expected
  default — do not invent findings to fill a quota).
- **Classify every finding on two orthogonal layers:**
  - **Fact verdict** — `confirmed` / `false` / `unverifiable`, each with **`file:line`
    evidence**. A "false" with no citation is just another unverified opinion —
    forbidden. For **unverifiable**, state the locations inspected or the search scope
    and why the evidence was insufficient — "unverifiable" is not a free pass for not
    looking.
  - **Severity** — `Blocker` (implemented as-is, the plan will fail or behave broken)
    vs `Advisory` (implementable, but worth knowing). The two layers are independent: a
    `false` can be Blocker or Advisory; so can an `unverifiable`.

The subagent works in whatever language it reasons best in (English is fine) — only
the final report YOU relay to the user is translated. Don't constrain the reviewer's
language; constrain only the output.

## Output (relay the subagent's report — translate to Korean)

Translate the subagent's report into **Korean** for the user. Keep code identifiers,
file paths, and `file:line` citations verbatim; render verdicts, reasoning, and
findings in Korean. Do not use emoji.

**Relay faithfully — translation only.** You (the orchestrator) may have authored the
plan and carry its bias, so do NOT soften, upgrade, drop, or add to the reviewer's
verdicts. The reviewer's judgment is authoritative; you only restate it in Korean.

Return, in order:

```
<DISPOSITION> — Blocker N, Advisory M    (append " (auto)" when auto mode produced a revision)

**검토 대상**: <mode> / <plan 제목 또는 첫 결정 요약>
**검토 범위**: 결정 K개, 코드 탐색 X회 (또는 "코드 무관 plan")
**리뷰어**: fresh subagent, 격리 컨텍스트

## 비판
| # | 결정 | 사실판정 | 등급 | 축 | 비판 (현실 충돌이면 file:line 인용) |
|---|---|---|---|---|---|

## 수정안   (Blocker는 항상 / Advisory는 auto일 때만)
- <#>: <원래 결정> → **<수정 결정>** — <해결되는 결함 한 줄>.
  (auto 모드에서는 각 항목에 [Blocker]/[Advisory] 접두, Blocker 먼저 정렬)

## Re-grill list
- **Auto-fixable** — 코드 기반 실패. grill-yourself가 ground truth 재독으로 재유도 가능.
- **Needs you** — user-only (가정) 실패. 재유도해도 또 다른 추측일 뿐, user(또는 /grill-me)만 해결.

## Reality check trace
- <검증 항목>: <결과>
```

1. **Verdict table** — per decision: fact verdict + severity + axis + evidence.
2. **Revision (수정안)** — diff-style. Always include Blocker findings. In `auto` mode,
   also fold Advisory findings (tagged `[Advisory]`, ordered after Blockers); if an
   Advisory has no concrete actionable revision, still emit
   `[Advisory] #: (no concrete revision) — <원본 비판 한 줄>` so it is not silently
   dropped. If a finding needs a brand-new decision the plan lacked, label it
   `#-new-<suffix>`. Omit this section entirely if there is nothing to revise.
3. **Disposition** — one line: **SHIP / REVISE (which rows) / REJECT**.
4. **Re-grill list** — the false / unverifiable items, split Auto-fixable vs Needs-you.

When Needs-you items exist, resolve them first. Then **offer once** (default mode only):
"Re-grill the auto-fixable rows now?"

**Needs-you grilling (both modes, when Needs-you items exist):** After the first review,
before any re-derive loop, ask the user directly in plain language about each Needs-you
item. In `auto`, if a later loop iteration discovers a new Needs-you item, pause the
loop, resolve it immediately, then resume with the confirmed decision in context.

- Convert each unresolved assumption into a concrete, answerable question. Do not ask
  yes/no questions; request a specific choice or concrete value, and state the
  recommended answer.
- If there are many items, group the questions into a concise, readable set.
- After the user answers, output each affected decision inline as **[confirmed]** and
  identify the Needs-you item it resolves. Do not silently absorb the answers.

### Disposition line (computed mechanically)
- `REJECT` / `REVISE (#…)` — Blocker > 0
- `SHIP` with advisories — Blocker = 0, Advisory > 0 (keep the Advisory rows + reality trace)
- `CLEAN — 결함 없음` — both = 0. Omit the 비판 / 수정안 / Re-grill / Reality trace
  sections; output the header + 검토 대상/범위 lines + one sentence:
  `이 plan은 5개 축(모순/숨겨진 가정/누락/현실 충돌/모호함) 모두에서 결함이 발견되지 않았습니다. 진행을 권장합니다.` Then stop.

## Visualization (optional, `--viz`)
When the args carry a `viz`/`--viz` token, also render the review as a self-contained
local HTML dashboard — but only **after** the normal chat report is emitted and
translated. The translated chat report remains the primary deliverable and comes first;
the dashboard is supplementary. Read the shared local-HTML procedure at
`<this skill's base directory>/../_shared/grill-viz.md` (the `_shared` sibling of this
skill's directory; read it by path, not as a skill) and follow it.

Map the review into its data contract: `title` = plan title / first-decision summary;
`subtitle` = `<mode> / 결정 K개`; `disposition` = the disposition line and
`dispositionKind` = its keyword (`ship`/`revise`/`reject`/`clean`); one `buckets` entry
(for example, `"비판"`) whose rows set `n`, `question` = the full 결정 text (omit
`answer`), `axis`, `verdict`, `severity`, and `rationale`; `revisions` = the 수정안;
`realityTrace` = the reality-check trace lines; `reGrillList` = the Auto-fixable /
Needs-you split. Favicon 🔎.

- **CLEAN disposition** → emit a minimal dashboard: title + the green CLEAN banner, no
  cards, matching the no-findings chat output.
- **`auto` mode** → update the same dashboard once after the fix loop finishes, with the
  final revised state and the iteration count in `subtitle`; do not update per iteration.

If the local-HTML procedure cannot complete, report the failure without delaying the
chat report.

## `--deep` (more rigor, slower)
Instead of one reviewer, spawn in parallel:
- **fact-checker** — axes ②③④ + reality check, verifying rows against code. If there
  are many rows, shard this across several fact-checkers by row.
- **critic** — axes ①⑤ + plan-level coherence / feasibility only.

Merge and dedupe their findings into the single output above. Parallel reviewers share
the session model and may share blind spots; `--deep` improves coverage by assigning
independent lenses, not by selecting a different model. Do not attempt per-subagent
model overrides in Codex.

## `auto` (Needs-you first, then hands-free fix loop, Advisory included)
Skip the confirmation and run the fix loop yourself. `auto` does two things at once:
it **folds Advisory findings into the revision** (not just Blockers), and it **drives a
hands-free re-derive loop**. The loop is hands-free only after user-only assumptions are
confirmed:
- **Step 1 — Needs-you rows first** → Do NOT best-guess fill. After the first review, if
  any Needs-you rows exist, resolve them with the direct questions in *Needs-you grilling*
  and place the confirmed decisions in context before any re-derive loop starts. If there
  are no Needs-you rows, skip this step.
- **Step 2 — Auto-fixable rows** → re-derive them by invoking the `grill-yourself` skill on
  those rows. It relies on the prior decision table being in context; if its instructions
  are not loaded, read `.agents/skills/grill-yourself/SKILL.md` first. Then spawn a
  **fresh** reviewer (new context) on the revised plan and repeat until the disposition is
  SHIP **or** a **max of 3 iterations** is reached. The 3-iteration cap counts re-derive
  loop iterations only; Needs-you resolution steps do not count. Keep every revision in
  chat — never write it back over the input `.md`.
- **Step 3 — New Needs-you during the loop** → if a later iteration discovers a new
  Needs-you row, pause the loop, resolve it immediately with direct user questions, place
  the confirmed decision in context, then resume the loop.
- **Oscillation guard** — if a fix introduces a new auto-fixable failure, stop and report
  rather than looping. A newly discovered Needs-you row is not oscillation; resolve it
  through Step 3 instead.

`--deep` and `auto` are orthogonal and combine (`/grill-review --deep auto`). Accept the
flags with or without leading dashes and in any order (`/grill-review --deep auto`).
**Auto mode is opt-in** — only the explicit `auto` argument activates it; never infer
it from the user's surrounding language, the plan's content, or the finding count.

## Hard constraints
- **Never modify files.** Not the plan, not the codebase, not docs. The output is a
  single message. Editing is the next turn's job, driven by the user. The sole exception
  is a `--viz` run writing one self-contained HTML file to the OS temporary directory for
  the dashboard; never write the plan, codebase, or docs.
- **Never re-enter Q&A (reviewer only).** The reviewer subagent must not ask clarifying
  questions: if the plan is ambiguous, log it as a Vagueness finding and move on. The
  orchestrator's direct Needs-you questions are the deliberate exception: in default mode
  they run after the first report; in `auto` they run before the re-derive loop and may
  pause later iterations for newly discovered Needs-you rows.
- **Never invent Reality mismatches.** If you didn't actually grep/read, you can't claim
  the codebase contradicts the plan.
- **Never fill quota.** No findings on an axis is the correct output when there are none.
- **Default = single reviewer + review-only.** The fix loop waits for your one
  confirmation. The pure objective review lands instantly; mutating the plan is opt-in.
