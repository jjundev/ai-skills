---
name: testing-assumptions
description: >-
  Test plan-shaping assumptions in a design or specification before implementation
  planning. Use when codebase state, runtime behavior, dependencies, external APIs,
  platform rules, versions, or other current facts could change feasibility,
  architecture, file structure, data models, or task decomposition. Do not use to
  design the solution, write the implementation plan, or implement it.
---

# Testing Assumptions

Turn plan-shaping assumptions into evidence before implementation planning. This is
an evidence gate between design work and implementation planning, not another design
or planning pass.

## Hard boundaries

- Do not modify source code, project configuration, dependencies, data, or external
  systems.
- Do not write the implementation plan or silently redesign around a failed
  assumption.
- Safe read-only inspection and diagnostic checks are in scope. A build or test is
  in scope only after its command has been inspected and its effects are limited to
  routine disposable test/build artifacts.
- Do not install packages, run migrations, deploy, commit, call mutating endpoints,
  or execute a command with unclear side effects. Record the blocked probe instead.
- Never report a proposed command, search, or experiment as performed evidence.

## The reversal test

An assumption is **plan-shaping** when reversing it could change feasibility,
architecture, file structure, data models, task decomposition, test strategy,
delivery constraints, or a safety boundary.

Apply this question literally:

> If the opposite were true, would the implementation plan materially change?

Audit assumptions that pass the reversal test. Exclude cosmetic choices and cheap,
localized defaults whose reversal would not change the plan.

## Workflow

### 1. Establish the target and source of truth

Identify the design or specification being tested and the workspace it applies to.
When relevant, establish the actual repository root, checkout/worktree, branch,
runtime, lockfiles, and deployed or supported version. Prefer integrated code and
current configuration over plans, generated artifacts, or a different checkout.

Infer the target from the conversation and working context. Ask only when no target
can be inferred or two plausible targets would produce different audits.

**Complete when:** the audit can name its design/specification scope and the concrete
workspace or external system whose facts are being tested.

### 2. Build the assumption ledger

Read the agreed design, constraints, and relevant implementation surface. Extract
both explicit claims and unstated dependencies. Apply the reversal test to each.

Classify every plan-shaping assumption by the evidence it needs:

- `LOCAL_FACT`: code, configuration, lockfiles, Git state, schemas, or existing tests
- `RUNTIME_PROBE`: a safe version check, dry run, minimal reproduction, build, or test
- `EXTERNAL_FACT`: current official documentation, specifications, release notes, or
  a read-only service response
- `USER_DECISION`: product direction, deadline, budget, priority, risk tolerance, or
  organization-specific policy that evidence cannot choose
- `NOT_CURRENTLY_VERIFIABLE`: credentials, hardware, environment access, authority,
  or another prerequisite is missing

Do not turn a design choice into a factual assumption. Route an unresolved technical
choice back to design; route a product or business choice to the user.

**Complete when:** every claim found by the reversal test has a ledger row and an
evidence class.

### 3. Test the assumptions (Fresh auditor dispatch)

To eliminate confirmation bias and prevent polluting the main conversation context with probe noise, **prefer dispatching a fresh, read-only auditor subagent** to perform the evidence tests whenever the platform supports subagents.

#### Fresh Auditor Subagent Pattern (Recommended)
1. **Dispatch:** Launch an isolated subagent (e.g., `research` or fresh clean-slate agent) with a clean context.
2. **Inputs to subagent:**
   - The design/spec summary or file path.
   - The Assumption Ledger rows requiring testing (`LOCAL_FACT`, `RUNTIME_PROBE`, `EXTERNAL_FACT`).
   - The workspace and repository scope.
3. **Subagent Instructions:**
   - Strictly read-only: inspect files, search docs, run safe non-mutating probes.
   - Collect concrete evidence for each assumption.
   - Return the tested ledger rows populated with exact `file:line`, observed probe output, or authoritative URLs.

#### Inline Testing Fallback
When subagent capabilities are unavailable or when testing a single, trivial local fact, test inline in the current session.

#### Evidence Standards
Use the strongest proportionate evidence available:

1. Actual local behavior and configuration (inspect source of truth, cite `file:line`).
2. Current authoritative external sources (primary sources, record direct URL + access date).
3. A narrow, safe executable probe (record exact command and observed output).
4. Secondary sources only as leads, never as sole proof of a plan-shaping claim.

Run safe, low-cost checks without stopping for confirmation. If one assumption needs
permission or unavailable access, continue testing the others and collect the
blockers for the final report.

Evidence must support the claim itself. A search with no result is not evidence of
absence unless the searched scope is demonstrably exhaustive. When authoritative
evidence conflicts, investigate only until the conflict can be resolved by a more
direct source; otherwise mark it unresolved.

**Complete when:** every ledger row contains either performed evidence (collected via fresh auditor or inline fallback) or the exact reason its test could not be performed.

### 4. Judge each assumption

Assign exactly one status:

- `VERIFIED`: direct, current evidence supports the assumption
- `REFUTED`: direct, current evidence contradicts the assumption
- `UNRESOLVED`: evidence is insufficient, conflicting, inaccessible, or would require
  an unauthorized probe
- `USER_DECISION`: the assumption is a user-owned choice rather than a discoverable
  fact

For each row, state what would change in the implementation plan if the assumption
is false or resolved differently. Do not weaken `UNRESOLVED` into confidence merely
because a conventional default seems likely.

**Complete when:** every row has a status, evidence summary, and plan impact.

### 5. Set the evidence gate

The most restrictive applicable result wins:

- `READY`: every plan-shaping fact is `VERIFIED`, and every user-owned decision is
  already explicit.
- `CONDITIONAL`: there is no plan-shaping `REFUTED` assumption, and every remaining
  `UNRESOLVED` assumption can be isolated behind an explicit reversible boundary or
  a bounded first validation task. No dependent implementation may precede that
  validation.
- `BLOCKED`: a `REFUTED`, `UNRESOLVED`, or `USER_DECISION` row could change
  feasibility, architecture, file structure, data models, or task decomposition and
  cannot satisfy the `CONDITIONAL` rule.

When blocked, identify the affected design decisions. Return refuted technical
premises to design resolution and ask concrete user-owned questions directly. Do not
invent a replacement design inside this skill.

**Complete when:** the gate follows mechanically from the ledger and every
non-`READY` row has a next action.

### 6. Report the audit

Use this structure:

```markdown
# Assumption Test: <target>

**Scope:** <design/specification and workspace or external system>
**Gate:** READY | CONDITIONAL | BLOCKED

## Evidence ledger

| # | Assumption | Why plan-shaping | Test performed | Evidence | Status | Plan impact |
|---|---|---|---|---|---|---|

## Verified premises for implementation planning

- <exact verified fact or constraint with its evidence reference>

## Conditions and prohibited assumptions

- <condition that must remain explicit>
- Do not assume: <unsupported claim>

## Required next actions

- <user decision, permitted probe, access request, or design question>
```

Omit empty detail from ledger cells only when the status makes it inapplicable; do
not omit entire sections. Write `None` when a section has no entries so the audit's
coverage is visible.

If the gate is `READY`, hand the verified premises forward as planning constraints.
If it is `CONDITIONAL`, hand off every condition, prohibited assumption, and
validation task. If it is `BLOCKED`, stop before implementation planning.

If user input or authorization is needed, ask all resulting questions after the
report rather than interrupting safe checks one by one. After an answer arrives,
update the affected rows and recompute the gate before handing off.

**Complete when:** the report contains a traceable ledger, one gate, and an actionable
handoff without claiming unperformed verification.

## Termination

Stop when every plan-shaping assumption has a status and the gate is determined, or
when further progress requires user input, new authority, unavailable access, or a
state-changing action. An unchanged or inaccessible fact remains explicit in the
ledger; it is never silently converted into an assumption for the implementation
plan.
