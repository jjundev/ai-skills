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
