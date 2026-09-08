---
name: grill-yourself-with-docs
description: Autonomous, no-dialogue counterpart to grill-with-docs — self-grill a plan (two-bucket decision table + plan, like grill-yourself) and write the domain model it settles to disk (glossary + ADRs) instead of leaving it in chat. Never touches source code. Invoke explicitly with /grill-yourself-with-docs.
disable-model-invocation: true
---

Run a `/grill-yourself` session, using the `/domain-modeling` skill. The decision table
and plan stay the primary artifact; the docs are what that thinking leaves behind.
Everything in `grill-yourself` applies here — the surface scan, dependency-order
resolution, the two-bucket decision table (Confident / Assumptions·needs you), the
termination rule, and the output format — with the doc-writing capture layered on top.

## When the docs get written
grill-yourself resolves decisions in one pass (surface scan → resolve in dependency
order → two-bucket table → plan). Hook the domain-modeling capture onto the **resolve**
step: the moment a decision settles a term, write that glossary entry to `CONTEXT.md`;
when a settled decision clears domain-modeling's ADR bar, write the ADR under
`docs/adr/`. Capture inline as each decision resolves — don't batch to the end.

## Writing docs is allowed here; source code still isn't
grill-yourself bars writing any file unless the user explicitly asks. **Invoking this
skill is that ask** — it authorises exactly two outputs, the glossary (`CONTEXT.md`) and
the ADRs (`docs/adr/`). Nothing else about grill-yourself's read-only stance changes:
**never** file-editing tools a source file. The settled design is still a plan,
not a green light to implement it.

## No user in the loop
domain-modeling's moves assume a live interview — challenge the user, ask which meaning
they intend, offer an ADR. There's no one to ask, so make those calls yourself: pick the
canonical term with a one-line rationale, exactly as grill-yourself picks a decision, and
apply domain-modeling's ADR bar yourself instead of offering it.

## Termination still applies
grill-yourself's termination rule is unchanged: stop resolving decisions on
**convergence** (an implementer could build from the resolved decisions) or at the
**20-decision safety cap**, whichever comes first. If the cap fires before convergence,
include the `## Unresolved areas` section — and do NOT fabricate glossary/ADR entries for
areas you could not actually resolve.

## Self-check before ending the turn
After emitting the design message, confirm you wrote **only** the glossary (`CONTEXT.md`)
and ADRs (`docs/adr/`) — and that you did NOT file-editing tools any source file
or run an implementation-oriented Bash command. Writing those two doc types is the sole
exception this skill grants to grill-yourself's read-only rule; anything beyond them is a
violation.
