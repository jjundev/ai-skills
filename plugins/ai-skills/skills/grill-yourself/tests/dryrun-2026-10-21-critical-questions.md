# Critical-question advice dry run — 2026-10-21

This evaluates interview-time advice, not the earlier discarded post-design review.
Inputs and assertions are in `council-question-scenarios.md`. The fixture is a
temporary README-only directory describing a stdlib, single-user stdout CLI with
no server, database or persistence. Each independent run starts with fresh context.
Architecture choice itself is not the pass criterion.

## Baseline, before editing SKILL.md

| Case | Result | Observed evidence |
|---|---|---|
| default_quoted_flag | PASS | `/root/default_baseline` read SKILL.md and fixture README only; zero references, reviewers and writes. Original output sections and one final question round retained; quoted flag treated as help text. |
| upstream_branch | FAIL (expected RED) | `/root/critical_baseline` read the same two files, launched zero reviewers, selected internal server B, then specified SQLite/auth/API dependents. It explicitly reported no `--council` handling/reference in the original skill. No writes. |

The baseline failure is absent independent advice before adopting the critical
deployment answer. No claim is made that choosing server B was intrinsically wrong.

## Updated skill

| Case | Result | Observed evidence |
|---|---|---|
| default_quoted_flag | PASS | `/root/default_green` read SKILL.md and fixture only; references = 0, reviewers = 0, writes = 0. Original output order and final Needs-you question retained; no advice summary. Classification/title guesses varied from baseline; these are not the asserted feature. |
| flag_without_critical_question | PASS | `/root/small_green` loaded canonical SKILL.md, canonical `references/council-questions.md` and fixture. Gate rejected the typo as low impact; actual reviewers = 0 and writes = 0; no independent-advice summary. |
| user_only_fact | PASS | `/root/user_fact_green` launched deployment_skeptic, deployment_pragmatist and deployment_critic, all fresh. Host changed B to conditional A on proportionality/reversibility grounds. Actual budget #5 and deadline #6 remained explicitly unknown in Needs you, not zero money or invented dates; sharing direction/resources/access also remained assumptions. No writes. |

The critical run's actual collaboration trace recorded `q0_skeptic`,
`q0_pragmatist`, `q0_critic`, each with `fork_turns: "none"`, at
10:14:05, 10:14:29 and 10:14:51 UTC respectively. `/root/critical_green` then adopted conditional shared-folder A before specifying
per-file JSON storage, CLI publish/list/show, temporary-file publication and folder
operations. No server/DB design was retained after selecting A. One final batched
Needs-you round retained deployment feasibility, sharing intent and access scope.
No writes and no final whole-design review. **upstream_branch: PASS.**

Packet audit: all three roles received only role + response contract + the same
fields: `question_id: 0`; deployment question; README:1 facts; 20-person/design-only
constraints; no locks; publishing/reading and available folder/server explicitly
unverified; options A shared-folder files / B authenticated server / C manual
export; success = proportionate architecture with explicit prerequisites. No host
stance or other reviewer output was included. Host's separate stance and final
choice were both conditional A; strongest caveat (unknown folder availability)
remained Needs you. All three actual reviewer recommendations were conditional A.
Sequential execution was observed with no capacity error, but this is not a
controlled one-slot test.

## Override continuation

After the evaluator could resume, `/root/critical_green` received
`/grill-yourself --council #0=로컬` with its actual prior table. It locked #0 to local
folder A without re-voting; IDs 1–7 retained their meanings, and unknown folder
availability became new row #8 instead of falsely becoming confirmed. Additional
reviewer launches = 0, writes = 0. On the normal reply `추천대로`, it marked #1,
#2 and #8 confirmed by default (localized as `[기본값으로 확정]`), retained the
#0 lock, then stopped: zero additional tools/reviewers/questions/writes and no
implementation. **override_and_reply: PASS.**

## Controlled-environment cases

| Case | Result | Reason |
|---|---|---|
| reviewer_unavailable | NOT RUN | This harness exposes delegation tools; no supported tool-removal control was used. |
| reviewer_partial_failure | NOT RUN | No supported mechanism to inject one reviewer tool error without replacing actual execution with roleplay. |
| capacity_limited | NOT RUN | Fresh sequential reviewers were observed, but concurrency was not forcibly restricted to exactly one reviewer slot for the whole case. |

An initial follow-up dispatch for the override case hit a real harness
`agent thread limit reached` before the evaluator resumed. That dispatch is not
counted as a skill failure-path test or successful override execution.

## Distribution and regression checks

- Portable `flag_without_critical_question`: PASS. `/root/portable_green` read
  `plugins/ai-skills/skills/grill-yourself/SKILL.md` and its own
  `references/council-questions.md`, plus fixture README. It did not read the
  canonical reference or standalone council. Zero reviewer launches and writes.
- Canonical and portable Bash structural checks: PASS, 4,982-byte SKILL.md.
- Full directory comparison: identical. Read-only, Needs-you, Overrides and the
  output template were compared to HEAD and preserved verbatim.
- `python3 script/manage.py test`: 75 tests, OK. Existing test fixtures emit a
  missing-upstream warning; the suite succeeded.
- `git diff --check`: no whitespace errors.
- Final fresh-context review by `/root/critical_final_review`: no Critical,
  Important or Minor findings; nothing declined to judge. Reviewer independently
  checked both Bash checks, directory parity and whitespace. The three controlled
  environments remain unverified; no review claim substitutes for executing them.

## Scope of evidence

Repository unit tests and Bash structure checks are separate from behavior tests.
No failed-tool or constrained-capacity case is a pass unless the environment
actually imposed that condition; pretending failure is not independent evidence.
The feature is an instruction contract, not an executable CLI parser.
