---
name: grill-yourself
description: >-
  Autonomously self-interview a plan or design — pose each grilling question AND
  answer it with your own recommended choice, then produce a two-bucket decision
  table (Confident / Assumptions·needs you) plus a plan. No back-and-forth during
  the resolution walk itself; if Assumptions/needs-you rows remain, ask the user
  about them right after emitting the plan, with the recommended answer stated.
  Terminates on convergence or a 20-decision safety cap. Read-only: never edits
  project code. Optionally pass --viz to also render the plan as a self-contained
  local HTML dashboard. Invoke explicitly with /grill-yourself.
disable-model-invocation: true
---

This is the autonomous, no-dialogue counterpart to the `grilling` skill. Instead of
interviewing the user one question at a time, walk the design tree yourself: pose
each question AND answer it with your recommended choice, without stopping for input
during the walk. The one deliberate exception is *after* the plan is on the table: any
Assumptions/needs-you rows are immediately asked directly to the user, with the
recommended answer stated — see *Needs-you grilling* below.

## Hard rule: never modify project code
Plan only. Do NOT use file-editing tools on any source file. Codebase
exploration is strictly read-only (read-only inspection tools, and Bash for inspection only).
The artifact you produce is a plan — output it in chat. Write it to a `.md` file only
if the user explicitly asks. With `--viz`, the one exception is a self-contained HTML
file in the OS temporary directory for the visualization — never the plan `.md`,
project code, or docs. The design is the deliverable, NOT a green light to build:
even if the resolved design is immediately implementable, do not implement it.
Implementation is a separate, user-initiated next turn.

(Note: this rule is enforced by directive, not by the harness. Honor it strictly.)

## How to run (zero stops, end-to-end)
1. **Surface scan.** Explore the codebase (read-only) and enumerate EVERY decision
   the plan hinges on. This list becomes the decision table — don't stop at the
   obvious few. When a decision can be answered by reading existing code rather than
   reasoning abstractly, read the code.
2. **Resolve in dependency order.** Take the next most-important unresolved decision
   (the one whose reversal would change the most other decisions) and resolve it with
   your recommended answer + a one-line rationale, then resolve its dependents. Skip
   purely cosmetic leaf details (give them sensible defaults in the plan instead of a
   table row).
3. **Build the decision table**, numbered, split into two buckets:
   - **Confident** — recommendable from codebase facts and sound defaults. Cite
     `file:line` in the rationale wherever a code fact backs the pick.
   - **Assumptions / needs you** — you filled these with a *guess* the user should
     confirm (deadlines, product direction, priorities, business constraints). The
     plan is complete, but state the assumption you made and flag it.
4. **Write the plan** that follows from those decisions.
5. **Footer:** "To flip a decision, re-invoke with `#<n>=<value>`." (part of the same
   emitted message as step 4 — see the *Output format* template below.)
6. **Needs-you grilling.** Once that message has been sent, if the Assumptions/needs-you
   bucket has rows, immediately follow it with direct, plain-language questions that
   resolve them. See *Needs-you grilling* below.

Run the resolution walk itself with zero stops. The user course-corrects afterward by
overriding numbered rows, or by answering the Needs-you questions asked immediately
after the plan message — that step happens automatically, without waiting for the user
to ask.

## Termination
Stop resolving decisions when **either** condition is met:
- **Convergence** — an implementer could write code from the resolved decisions
  without needing further design clarification.
- **Safety cap** — 20 decisions have been resolved. Stop immediately at the cap
  regardless of convergence.

If the safety cap fires before convergence, include an `## Unresolved areas` section
listing the design questions that remained genuinely *open* (you could not resolve
them at all). This is distinct from the **Assumptions / needs you** bucket, which
holds decisions you DID resolve with a guess. Rule of thumb: filled-with-a-guess →
Assumptions bucket; could-not-fill → Unresolved areas.

"Stop" means stop resolving decisions and emit the design. It never means "begin
implementation."

## Output format

```
# Plan: <one-line title>

<2–4 sentence summary of the resolved design — what gets built, how it behaves, what
the user will see.>

## Decision table

### Confident
| # | Decision (question) | Recommended answer | Rationale (one line, file:line where applicable) |
|---|---|---|---|

### Assumptions / needs you
| # | Decision (question) | Assumed value | Why only the user can truly decide |
|---|---|---|---|

## Plan

<Concrete design specification that follows from the decisions: components, data
flow, file layout, interfaces, behaviors. Written so an implementer can act on it
directly.>

## Unresolved areas (only if the cap fired before convergence)
- <open question that could not be resolved at all>

## Termination
<"Converged after N decisions." or "Hit safety cap at 20 decisions — see Unresolved areas.">

---
To flip a decision, re-invoke with `#<n>=<value>`.
```

Match the language of the surrounding conversation (e.g., if the user is writing
Korean, output in Korean). If the **Assumptions / needs you** bucket is non-empty,
immediately follow this output with the direct questions described in *Needs-you
grilling* below — do not wait for the user to prompt it.

## Visualization (optional, `--viz`)
By default the deliverable is the chat plan and nothing else. If the args contain a
`viz` / `--viz` token (dashes optional; strip it before interpreting any `#<n>=<value>`
overrides), also render the plan as a self-contained local HTML dashboard — but only
**after** the plan message and any immediate Needs-you questions. The chat output is
unchanged and always comes first; the dashboard is supplementary.

1. Emit the full plan and run *Needs-you grilling* exactly as normal.
2. Read the shared local-HTML procedure at
   `<this skill's base directory>/../_shared/grill-viz.md` (the `_shared` sibling of this
   skill's directory; read it by path, not as a skill) and follow it. Map this skill's
   output into its data contract: `title` = the plan title; two `buckets` — `"Confident"`
   and `"Assumptions / needs you"` — whose rows carry `n`/`question`/`answer`/`rationale`
   (set `severity:"confident"` on Confident rows); `planBody` = the `## Plan` narrative.
   Leave the review-only fields (`verdict`/`axis`/`revisions`/`realityTrace`/
   `reGrillList`/`disposition`) omitted. Favicon 📋.
3. After Needs-you confirmations — or any `#<n>=<value>` re-derive — rebuild the data
   and update the same local HTML file path so the dashboard stays current.

If the local-HTML procedure cannot complete, report the failure without delaying the
plan or its questions.

## Needs-you grilling (right after the plan)
If the Assumptions/needs-you bucket has rows, do not leave them for a later override.
Immediately after emitting the plan, ask the user a direct, plain-language question for
each row.

- Convert each row into a concrete, answerable question. Do not ask yes/no questions;
  request a specific choice or concrete value.
- State the row's assumed value as the recommended answer.
- If there are many rows, group the questions into a concise, readable set.
- After the user answers, output each affected decision inline as **[confirmed]** and
  identify the row it resolves; do not silently absorb answers.
- If an answer differs from the recommendation, propagate the change to dependent
  decisions using the original dependency-order logic.
- This is the one deliberate exception to zero stops: it fires once after the full plan
  is on the table, never during the resolution walk.

## Overrides
If invoked with one or more `#<n>=<value>` arguments, treat those decisions as locked
to the given values and re-derive everything else around them. This relies on the
prior decision table being present in the conversation context — if it isn't (e.g. a
fresh session), ask the user to restate the plan, then re-run the full scan.

## The one allowed stop
If no plan or target is given, infer it from the conversation and working context.
Only if there is genuinely nothing to grill — no plan stated and none inferable — ask
the user what to grill. That is the sole exception to the zero-stops rule during the
resolution walk; the post-plan Needs-you grilling above is a separate deliberate
exception that always fires when applicable.

## Self-check before ending the turn
After emitting the design message, confirm you did NOT use file-editing tools, or an
implementation-oriented Bash command during this turn. The sole exception is the
scratchpad HTML file permitted by `--viz`; editing the plan `.md`, project code, or docs
still violates this skill.
