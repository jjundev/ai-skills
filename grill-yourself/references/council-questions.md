# Advice while resolving interview questions

This reference applies only to a current `/grill-yourself --council <idea>`
invocation. It adds advice before adopting individual answers, including the
architectural approach (#0) and unresolved intent interpretation after exploration.
It does not add a review of a completed design. Without the option, use the parent
procedure alone. A normal Needs-you reply does not retain the option.

## Gate each question

After reading relevant evidence, evaluate all three conditions before adopting an
answer. Cosmetic details still get defaults, not decision rows.

| Condition | Observable criterion |
|---|---|
| High impact | Reversing the answer changes scope, architecture, data, external interfaces, or several dependent decisions. |
| Unresolved | Explicit user instructions, locked answers and verified facts do not already determine it; multiple credible options remain. |
| Useful independent judgment | Comparing options and consequences could improve the recommendation. An unknown actual budget, deadline or user preference cannot be discovered by voting. |

If any condition fails, resolve it yourself under the parent rules. A flagged
invocation may need zero reviewers. If all hold, get independent advice before
adopting the answer or designing its dependents. Use the existing decision ID.
If intent is ambiguous, keep the initial interpretation provisional until this gate
after exploration; a chosen interpretation still belongs in Needs you.

## Prepare one neutral packet

First record your provisional answer and brief reason in a short host note, before
reading reviewers. This is a stance on one question, not a whole design draft.
Keep this note separate from the reviewer input.

Send each reviewer the same packet with these fields:

```text
question_id: stable decision ID
question: the single unresolved question
facts: compact verified context, with file:line evidence where applicable
constraints: explicit user requirements and relevant technical limits
locked_decisions: IDs and answers that must be honored
assumptions: unverified premises, explicitly labeled
options: credible alternatives and their consequences, without a favored option
success_criteria: what a useful answer must achieve
```

The packet excludes the full conversation, the host's provisional answer and its
rationale, and every other reviewer's response. Do not present guessed priorities
as requirements or describe an option as the preferred/recommended winner. Reviewers
may propose another option or reject a premise.

## Obtain three fresh perspectives

| Reviewer | Lens |
|---|---|
| Skeptic | Challenge premises and simplify the proposed scope. |
| Pragmatist | Compare user impact, delivery cost and operational reality. |
| Critic | Identify failure modes, losses and reversibility. |

For each role, launch a fresh agent receiving only its role, the neutral packet and
the response contract below. On Codex use `fork_turns: "none"`; never inherit the
conversation. Launch in parallel when capacity permits. If capacity is limited,
run fresh agents sequentially with the identical packet, without earlier answers.
Never reuse a reviewer with another question's history. Select tools/models only
from the current runtime's capabilities; no separate council installation is needed.

Response contract: give a recommended answer, concise reasons and the main risk
(under 300 words). This is read-only advice on this question. Do not ask the user,
write files or delegate recursively. Answer only from the packet; label uncertainty.

If delegation is unavailable or a reviewer fails, record the actual missing role
and reason. Continue with available evidence and a provisional answer, without an
intermediate user question. Do not invent a review, consensus or completed launch;
do not retry the same failed conditions repeatedly. Capacity shortage alone uses
the sequential path when fresh sequential execution is possible.

## Adopt an answer, then continue

Compare advice against explicit constraints, evidence, downstream consequences and
reversibility. Select one answer and state why, including how you treated the
strongest dissent. Count of votes does not determine the answer. Reconsider your
stance if persuasive evidence challenges it; explain accepting or rejecting advice.

Only then resolve dependent questions using that answer. Convene once per question,
not repeatedly until agreement. Revisit a question only if changed upstream premises
alter its basis; reconsider only affected unlocked dependents. Preserve decision
IDs and explicit locks. For `--council #<n>=<value>`, require the prior decision table
as the parent does, and never put the locked answer back to a vote.

Technical judgments and sound defaults can be Confident. Assumptions about the
user's intent, priorities, preferences, deadlines or business rules remain Needs
you, even if all reviewers agree. Recommend an assumption and continue; never invent
the actual amount, date, approval or user preference.

## Finish with the parent's output and one question round

If independent advice was attempted, include a compact summary inside Decisions,
before Confident. For each question show its ID, each reviewer's answer or missing
status, the adopted answer, and the strongest dissent with its treatment. If nobody
could run, show missing statuses and the host's provisional answer, not fictional
positions. When no question needed advice, omit this summary entirely.

Emit the full design before the parent's single batched Needs-you round. Apply its
row-by-row `[confirmed]` and `[confirmed by default]` rules to an ordinary reply;
do not launch another council or ask a second round. A later explicit invocation
with the option is evaluated anew.

The parent's Read-only boundary still governs: no implementation, automatic design
file, issue update or other persistence. Save the design only when explicitly
requested. This reference imports neither the standalone council's clarification
step nor its persistence workflow.
