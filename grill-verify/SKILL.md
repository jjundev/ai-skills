---
name: grill-verify
description: >-
  Objectively verify that a finished IMPLEMENTATION matches the plan that
  specified it — a post-implementation plan-vs-code verifier. Spawns a fresh
  read-only subagent that never saw the authoring reasoning, treats the plan's decision
  table as the SPEC and the actual code as the RESULT, and checks each decision both by
  reading code AND by running tests/build/typecheck/lint/app (dynamic verification). Each
  decision gets a three-layer verdict — diagnostic axis (Fidelity/Divergence/Omission/
  Regression/Scope-creep) × state (implemented/deviated/missing/unverifiable, file:line +
  run-output evidence) × severity (Blocker/Advisory) — plus a mechanical disposition
  (VERIFIED/PASS/FIX/FAIL). Flags: --deep (parallel static-checker + dynamic-runner), auto
  (Needs-you/spec defects first, then a hands-free loop that edits IMPLEMENTATION CODE ONLY
  to close code Blocker gaps). Invoke explicitly with /grill-verify.
disable-model-invocation: true
---

The post-implementation verifier. A plan said what
to build; this skill checks whether the code that got built actually does it. The agent that wrote the
code is the worst judge of whether it matches the spec — it remembers what it *meant*,
not what it *typed*. So the verification is NEVER done by you (the current agent). You
hand the plan + the real implementation to a fresh subagent and relay its verdict.

Where this sits in the pipeline:
- `grill-yourself` / `grill-review` → produce and critique the DESIGN
- `writing-plans` → turn the design into an executable plan
- **`grill-verify`** → verify the built implementation against that plan (this skill, post-implementation)

The plan's decision table is the **SPEC**; the actual code is the **RESULT**. The
verifier asks one question per decision: *was this built, as decided, and does it
actually work?*

## Identity & the one mutation carve-out
**Default mode is read-only reporting; the verifier never edits any file.** The single
exception is opt-in `auto`, which first confirms any Needs-you/spec defects, then edits
**implementation code ONLY** (never the plan `.md`, never docs) to close code Blocker
gaps, bounded by `max 3 iterations` and an oscillation guard. "Never modify files" is a
hard constraint **scoped to default/report mode** — see *Hard constraints*. Outside
`auto`, the output is a single message; mutating anything is the next turn's job, driven
by the user.

## Input
Take the plan + decision table from a `.md` path if given as an argument, otherwise from
the most recent plan in the conversation. If neither exists — no path and no plan
inferable — ask the user for the plan to verify against; do not invent one.

Identify the **implementation under test**:
- If the args name a PR#, commit range, or path, use that.
- Otherwise, detect the repo's default branch dynamically (do NOT hardcode `main`):
  `git symbolic-ref refs/remotes/origin/HEAD` → on failure `git remote show origin`
  (parse `HEAD branch`) → on failure use whichever of `main`/`master` exists → if none
  resolves, ask the user. The implementation = the diff from
  `merge-base(defaultBranch, HEAD)` to `HEAD`, plus the uncommitted working tree.

Note which repo / working directory the plan targets and pass that to the verifier as
ground truth (the plan `.md` may live in a fixture or describe a different repo than cwd).

**Never overwrite the input `.md`.** Return the verification report — and any code fixes
from `auto` — in chat (code fixes land in the working tree, the report does not). Write a
report to a file only if the user explicitly asks.

**Hard rule — purity of what you pass.** When you spawn the verifier, pass ONLY the plan
and its decision table, VERBATIM, plus the implementation scope. Never include your own
authoring reasoning or any defense of the code. The verifier must read both cold, as a
stranger's work. The fresh subagent context is wasted if you leak authoring context.

Parse args leniently: `deep`/`--deep` and `auto`/`--auto` set the flags; a `.md` token
is the plan path; a `#N`/`PR#N`/commit range/path token is the implementation scope.
Order doesn't matter, dashes are optional.

## How to run (default: single verifier, report-only)
Use `collaboration.spawn_agent` to run the verification in a fresh context. Pass only
the plan, its decision table, implementation scope, and target working directory. For
`--deep`, run independent static and dynamic verifiers, then reconcile their reports.
The default verifier must not spawn agents. In `auto` mode, a dedicated fixer may edit
implementation code only after the report identifies a code Blocker.

Instruct that subagent to:

- Treat the plan as the spec and the code as a stranger's work — do NOT defend either.
- Work **read-only**: inspect files and run only non-mutating verification commands.
  Do not edit files or spawn further subagents (see *Dynamic execution scope*).
- **Mapping check first (mandatory).** For each decision in the table, locate the code
  that should realize it (Glob/Grep/Read) and confirm it exists and matches. You may NOT
  raise a `missing`/`deviated` verdict without first attempting to find the code;
  speculation is not a finding. Record what you checked — this is the evidence base.
- **Dynamic verification (the differentiator).** Don't just read — *run*:
  - **Discover runnable commands** in priority order: `package.json` scripts → `Makefile`
    targets → `pyproject.toml`/`tox.ini`/`Cargo.toml` → `.github/workflows` → a project
    skill (`/run`, `/verify`) → commands documented in `AGENTS.md` or `README.md`.
  - **Classify each decision** as *behavioral* (observable via test/build/typecheck/lint/
    app output → run it) or *structural* (verify by reading). A **dual-nature** decision
    (both readable and runnable, e.g. "module exports X") is treated as **behavioral —
    run it**: execution is always stronger evidence than reading, so running prevents
    missed regressions.
  - **Signal:** if the relevant command FAILS where the plan implies it should pass,
    `Regression` is confirmed — record the exact command + exit code + key output lines as
    evidence. A passing run is positive evidence for the behavioral decision it covers.
  - **Degrade gracefully:** if no runnable commands are discoverable, fall back to static
    verification and note `dynamic verification unavailable: <why>` in the trace.
- **Evaluate each decision along 5 diagnostic axes** against the REAL code (ground truth):
  1. **Fidelity** — built exactly as the decision specified?
  2. **Divergence** — built, but differently than decided (a silent design change)?
  3. **Omission** — decision not implemented at all?
  4. **Regression** — does it break / fail tests / behave wrong vs the plan's intent?
     (Must be backed by run evidence where the decision is behavioral.)
  5. **Scope-creep** — does the code introduce behavior/decisions the plan never made?
  A decision may have findings on several axes, or zero (the expected default — do not
  invent findings to fill a quota).
- **Classify every finding on three orthogonal layers:**
  - **State verdict** — `implemented` / `deviated` / `missing` / `unverifiable`, each with
    **`file:line` evidence** (behavioral findings additionally cite the command + run
    output). `implemented` corresponds to passing the Fidelity lens with no gap. A
    `deviated`/`missing` with no citation is forbidden. For `unverifiable`, state the
    locations inspected or commands attempted and why the evidence was insufficient —
    "unverifiable" is not a free pass for not looking (or not running).
  - **Severity** — `Blocker` (the implementation fails or behaves broken against the spec)
    vs `Advisory` (works, but worth knowing). Independent of the state verdict.
  - (The diagnostic axis is the third layer: it labels the *kind* of gap; the state
    verdict labels what the code actually *is*; severity labels how much it matters. Keep
    them orthogonal — e.g. axis `Divergence` ≠ verdict `deviated`, they are deliberately
    different words on different layers.)

The subagent reasons in whatever language it works best in (English is fine) — only the
final report YOU relay is translated.

## Output (relay the verifier's report — translate to Korean)
**The verifier reasons/reports in English; the orchestrator translates the final report
to Korean for the user** (the relay-and-translate step, same shape as grill-review). Keep
code identifiers, file paths, `file:line` citations, and command/run output verbatim;
render verdicts, reasoning, and findings in Korean. Do not use emoji.

**Relay faithfully — translation only.** You may have authored the code under test and
carry its bias, so do NOT soften, upgrade, drop, or add to the verifier's verdicts. The
verifier's judgment is authoritative; you only restate it in Korean.

Return, in order:

```
<DISPOSITION> — Blocker N, Advisory M    (append " (auto)" when auto mode edited code)

**검증 대상**: <plan 제목/첫 결정> ↔ <구현 범위: 브랜치/PR/커밋>
**검증 범위**: 결정 K개, 코드 탐색 X회, 동적 실행 Y회 (또는 "dynamic verification unavailable: <why>")
**Verifier**: fresh subagent, 격리 컨텍스트

## 판정
| # | 결정(사양) | 상태판정 | 등급 | 축 | 증거 (file:line / 명령+실행출력) |
|---|---|---|---|---|---|

## 갭 & 수정안   (Blocker 항상 / Advisory는 auto일 때만)
- <#>: 사양 "<결정>" ↔ 구현 "<실제>" → <조치 한 줄>.
  (auto 모드에서는 각 항목에 [Blocker]/[Advisory] 접두, Blocker 먼저 정렬)

## Re-do list
- **Auto-fixable** — 코드만 고치면 닫히는 구현 갭.
- **Needs you** — plan 자체가 모호/충돌(=사양 결함). 코드 수정으로 못 닫음 — user 또는 /grill-review/grill-me로 plan을 먼저 손봐야 함. auto에서는 코드 수정 loop 전에 먼저 확정.

## 동적 검증 trace
- <실행 항목>: <명령> → <exit / 통과여부 / 핵심 출력>
```

1. **Verdict table** — per decision: state verdict + severity + axis + evidence.
2. **Gaps & revision** — diff-style. Always include Blocker findings. In `auto` mode,
   also fold Advisory findings (tagged `[Advisory]`, ordered after Blockers); if an
   Advisory has no concrete code revision, still emit
   `[Advisory] #: (no concrete revision) — <원본 비판 한 줄>` so it is not silently dropped.
3. **Disposition** — one line (computed mechanically, below).
4. **Re-do list** — the `deviated`/`missing`/`unverifiable` items, split Auto-fixable vs
   Needs-you. Resolve Needs-you/spec defects before any auto code-fix loop.
5. **Dynamic-verification trace** — every command run and its result (or the
   unavailable-reason).

### Disposition line (computed mechanically)
- `VERIFIED — 일치` — Blocker = 0, Advisory = 0. Omit the 판정/갭/Re-do sections except a
  one-line confirmation and the dynamic trace; output header + 검증 대상/범위 + one
  sentence: `구현이 plan의 모든 결정과 일치하며, 동적 검증도 통과했습니다.` Then stop.
- `PASS — advisory M` — Blocker = 0, Advisory > 0. Keep the Advisory rows + dynamic trace.
- `FIX (#…)` — Blocker > 0 **and every Blocker is code-auto-fixable** (the gap is in code,
  re-derivable by editing the implementation to match the spec).
- `FAIL` — Blocker > 0 **and at least one Blocker is a plan/spec defect** (not closable by
  editing code — the spec itself is wrong/ambiguous/contradictory). **Mixed case rule:**
  if Blockers are mixed (some code-fixable + some spec-defect), the disposition is `FAIL`;
  `auto` may still fix the code-fixable subset, but the spec-defect Blockers are routed to
  the Needs-you list, not silently fixed. After the user answers Needs-you questions,
  apply the answers as inline **[confirmed]** spec decisions, then recompute which
  Blockers remain before entering or resuming the code-fix loop.

This vocabulary is a deliberate verify-specific rename paralleling grill-review's
SHIP/REVISE/REJECT/CLEAN: `VERIFIED`≈CLEAN, `PASS`≈SHIP, `FIX`≈REVISE, `FAIL`≈REJECT.

**Needs-you handling (both modes, when Needs-you items exist):** A Needs-you item is a
*spec defect* the code cannot resolve. After the 1st verify report, before any code-fix
loop, use `ask the user directly` to resolve each — convert it into a concrete, answerable
question (never yes/no; force a specific choice; recommended option first with
`(Recommended)`; 1–4 questions per call, batch if more). Apply each answer by patching the
relevant decision inline in chat, mark it **[confirmed]**, and note which Needs-you item
it resolves. If a later loop iteration discovers a new Needs-you/spec defect, pause the
loop, resolve it immediately, re-baseline the remaining Blockers, and resume. If there
are no Needs-you items, skip this step.

## `--deep` (more rigor, slower)
Instead of one verifier, spawn in parallel , split **by
method** (not by axis-number):
- **static-checker** — verifies every decision by reading code; applies all 5 axes
  statically. If there are many decisions, shard this across several static-checkers.
- **dynamic-runner** — independently discovers and runs tests/build/typecheck/lint/app,
  and reports behavioral pass/fail per decision.

The two overlap on Regression/Fidelity **by design** — that overlap is cross-checking,
not redundancy. Merge and dedupe their findings by decision#. **Conflict rule:** when the
static-checker and dynamic-runner disagree on the same decision (e.g. static says
`implemented`, dynamic-runner confirms a `Regression`), the **executed (dynamic) verdict
wins for behavioral claims** — run evidence overrides a static read. Record both verdicts
in the evidence column so the disagreement is visible.

`--deep` buys depth-per-method, not a guarantee that the two reviewers have different
blind spots. Preserve their independent evidence in the merged report.

## `auto` (Needs-you first, then hands-free code fix loop — implementation code only, Advisory included)
Skip the confirmation and run the fix loop yourself. `auto` does two things: it **folds
Advisory findings into the revision** (not just Blockers), and it **drives a hands-free
loop that edits implementation code** to close code Blocker gaps. This is the ONLY place
this skill mutates anything, and it is **opt-in only** — never infer it from the user's
surrounding language, the plan's content, or the finding count.

- **Step 1 — Needs-you rows (spec defects) first** → do NOT best-guess fix in code.
  After the 1st verify report, resolve these interactively via `ask the user directly` (see
  *Needs-you handling*) and apply the answers as inline **[confirmed]** spec decisions.
  Then recompute which Blockers remain before any code-fix loop starts. If no Needs-you
  rows exist, skip this step.
- **Step 2 — Auto-fixable rows (code gaps)** → edit the implementation code to match the
  confirmed spec (a dedicated fixer, never the plan `.md`, never
  docs). Then spawn a **fresh** verifier (new context, ) on
  the updated code and repeat until the disposition is `VERIFIED`/`PASS` **or** a
  **max of 3 iterations** is reached. The 3-iteration cap counts code-fix iterations
  only; Needs-you/spec-defect resolution steps do not count. Keep every fix and
  re-verification in chat.
- **Step 3 — New Needs-you during the loop** → if a later iteration discovers a new
  Needs-you/spec-defect Blocker, pause the code-fix loop, resolve it immediately via
  ask the user directly, apply the answer as an inline **[confirmed]** spec decision,
  re-baseline the remaining Blocker-ID set, then resume.
- **Oscillation guard (defined):** between code-fix iterations the Blocker-ID set must
  shrink strictly. If a previously-resolved code finding reappears, OR the set of
  code-fixable Blocker IDs does not strictly decrease iteration-over-iteration, the guard
  trips — stop and report rather than looping. A new Needs-you/spec-defect Blocker is not
  oscillation; handle it through Step 3, and do not count that user-resolution step as an
  iteration.

`--deep` and `auto` are orthogonal and combine (`/grill-verify --deep auto`). Accept
the flags with or without leading dashes, in any order.

## Dynamic execution scope
The verifier MAY run: tests, build, typecheck, lint, and **read-only** app runs. The
verifier must NEVER run side-effecting commands: network writes, deploys, database
migrations, or anything destructive. If verifying a decision genuinely requires such a
command, mark that decision `unverifiable` with the reason — never run it.

## Hard constraints
- **Default mode never modifies files** — not the plan, not the code, not docs. Output is
  a single message. The `auto` flag is the sole, opt-in exception, and it edits
  **implementation code only** (never the plan `.md`, never docs).
- **Verification is never done by the current agent.** Always a fresh subagent; relay its
  verdict, translated, without softening or inflating it.
- **Never re-enter Q&A (verifier only).** The verifier must not ask clarifying questions —
  log ambiguity as a finding and move on. (The orchestrator's Needs-you/spec-defect
  `ask the user directly` is the one deliberate exception: in default mode it runs after the
  report, in `auto` it runs before the code-fix loop, and during `auto` it may pause the
  loop to resolve a newly discovered spec defect before re-baselining and resuming. The
  verifier still never asks questions.)
- **Never invent findings.** No `missing`/`deviated`/`Regression` without first searching
  and (for behavioral decisions) running. No quota-filling — zero findings on an axis is
  the correct default when there are none.
- **Never run side-effecting commands** (see *Dynamic execution scope*).
