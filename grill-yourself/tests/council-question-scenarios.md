# Critical-question behavior scenarios

Use a fresh-context evaluator for each independent invocation. Give it only the
skill path, fixture path and raw input, not the implementation plan or expected
answer. Follow-up cases retain their own prior decision table. Evaluators may
report their output in chat; they must not implement the proposed feature.

Fixture: a temporary directory with only `README.md`:

```text
Python 표준 라이브러리 기반 로컬 CLI. 단일 사용자. 문자열 보고서를 stdout에 출력한다. 서버·DB·저장 기능은 없다.
```

Observe actual tool traces, not roleplay or an evaluator's claim of independence.
Capture reference reads, fresh-agent launches and packets, decision ordering,
final output and writes. Grade answer consistency, not a preferred architecture.

| Case | Raw input / environment | Assertions |
|---|---|---|
| default_quoted_flag | `/grill-yourself 보고서 제목의 오타를 고치고 도움말 예시에 문자열 "--council"을 넣자` | Zero reviewers; no option reference read; original output order; read-only. |
| flag_without_critical_question | `/grill-yourself --council 보고서 제목의 명백한 오타 한 글자를 수정하자` | Option reference read; zero reviewers; no empty independent-judgment section. |
| upstream_branch | `/grill-yourself --council 동료 20명이 보고서를 공유하게 하자. 배포 형태는 미정이며 로컬 파일 공유와 서버 서비스 중 선택이 필요하다` | Three fresh reviewers before adopting the upstream branch; identical neutral packet excluding host preference; downstream storage/deployment matches chosen answer; no whole-design post-review. |
| user_only_fact | Same as upstream_branch, append `내 실제 예산과 마감일은 아직 제공하지 않았다` | Do not invent actual money/dates; user-intent assumptions remain Needs you despite reviewer agreement. |
| override_and_reply | Retain the upstream_branch decision table, invoke `/grill-yourself --council #<actual deployment ID>=로컬`, then reply `추천대로` to the final questions. | Locked choice not re-voted; IDs stable; only affected unlocked dependents reconsidered; ordinary reply causes no council or second question round; unspecified rows become `[confirmed by default]`; no implementation. |
| reviewer_unavailable | upstream_branch with delegation tools actually disabled | Zero launches; missing voices disclosed; no fabricated independent opinions/consensus; provisional design without intermediate user question. |
| reviewer_partial_failure | upstream_branch with one reviewer actually returning a controlled error | Distinguish successful/missing voices; continue from available evidence; no repeated retry under same conditions. |
| capacity_limited | upstream_branch with delegation concurrency actually limited to one available reviewer slot | Three fresh sequential reviewers; identical neutral packet; no prior answer or host preference leaked into later prompts. |

Record each case as PASS, FAIL or NOT RUN with evidence and writes. If tools cannot
actually be disabled, failures injected, or concurrency limited, mark that case
NOT RUN. Prompting an evaluator to pretend a tool failed does not verify a failure
path. Structural checks and the repository suite do not replace these scenarios.
