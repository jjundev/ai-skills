# Grill-yourself Critical Questions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `--council` 호출에서 설계를 좌우하는 인터뷰 질문에만 독립 판단을 받아 답을 채택하고, 그 답에 따라 후속 질문을 진행한다.

**Architecture:** 기존 질문 해결 절차에 조건부 분기를 추가한다. 본문은 옵션 진입점만 제공하고, 질문 판정·독립 판단·후속 진행 계약은 별도 reference에 둔다. 실행 코드를 추가하는 작업이 아니라 에이전트가 따르는 지침을 변경하는 작업이다.

**Tech Stack:** Markdown skill instructions, Bash structural checker, fresh-context subagents for behavioral evaluation, existing Python unittest suite.

**Spec:** [이 문서의 설계 확정본](2026-10-21-grill-yourself-critical-questions.md#design-snapshot). 앞선 채팅 설계를 아래에 동봉했으므로 실행자는 이 문서 전체를 읽는다. #8은 다음 사용자 응답에서 변경 지정이 없었으므로 기존 grill-yourself 규칙에 따라 추천값으로 확정했다.

## Global Constraints

- 옵션 이름: `--council`. 명시적인 현재 호출 인자일 때만 활성화한다.
- 일반 호출의 기존 절차, 출력 순서, 수동 호출 정책 `disable-model-invocation: true`를 유지한다.
- 실행 시점은 질문의 답을 채택하기 직전이다. 완성된 설계의 사후 검토를 추가하지 않는다.
- 호출 조건은 큰 영향·미결정·독립 판단의 효용을 모두 만족하는 것이다.
- 관점은 Skeptic·Pragmatist·Critic 세 명이며, 각 질문에 새 문맥을 사용한다.
- 사용자 의도에 관한 가정은 독립 판단 후에도 `Needs you`에 유지한다.
- 읽기 전용, 마지막 한 번의 사용자 질문, `#<n>=<value>` 고정값 및 기존 응답 처리 규칙을 유지한다.
- 기존 본문 제한은 5,000바이트다. 상세 옵션 지침은 별도 reference로 분리한다.
- `council/SKILL.md`, 저장소 관리 코드, 글로벌 설정, upstream 동기화 설정은 변경하지 않는다.
- 원본과 `plugins/ai-skills/skills/grill-yourself/`의 대응 변경 파일은 바이트 단위로 일치시킨다.
- 이 계획 작성은 구현 승인이 아니다. 실행 방식 선택 및 사용자 검토 이후에만 구현한다. 푸시는 별도 요청 없이 하지 않는다.

## Review Focus

1. 예시·인용문에만 `--council`이 등장하는 입력: 옵션으로 오인하거나 reference를 읽지 않는다. Task 1의 `default_quoted_flag`로 확인한다.
2. 옵션이 있어도 핵심 질문이 없는 작은 변경: 추가 에이전트가 0명이다. Task 1의 `flag_without_critical_question`으로 확인한다.
3. 접근법 선택 또는 초기 의도 해석이 큰 분기인 입력: 종속 설계 전에 판단하고, 단순히 절차 4번만 확장해 놓치지 않는다. Task 1의 `upstream_branch`로 확인한다.
4. `#<n>=<value>` 재호출 및 사용자만 아는 사실: 고정 답을 바꾸거나 추측을 사실·동의로 승격하지 않는다. Task 1의 `override_and_reply`, `user_only_fact`로 확인한다.
5. 에이전트 도구 부재·일부 실패·병렬 용량 부족: 실제 실행 여부를 구분하고 가짜 합의나 중간 사용자 질문 없이 진행한다. Task 1의 `reviewer_unavailable`로 확인한다.

---

<a id="design-snapshot"></a>
## 설계 확정본

### 질문 해결 계약

1. 아이디어를 해석하고 관련 자료를 읽는다. 초기 의도 해석은 필요하면 잠정값으로 두고 탐색 뒤 평가한다.
2. 의존성상 먼저 답해야 할 질문부터 해결한다. architectural 접근법의 결정 #0도 이 흐름에 포함한다.
3. 현재 호출에 옵션이 없으면 기존 방식으로 답한다. 옵션이 있으면 아래 세 조건을 평가한다.
   - **큰 영향:** 답을 바꾸면 범위·구조·데이터·외부 인터페이스 또는 여러 후속 결정이 달라진다.
   - **미결정:** 사용자 지시나 확인한 자료로 이미 답이 고정되지 않았으며 타당한 선택지가 여럿이다.
   - **판단 효용:** 선택지와 결과를 비교하면 추천의 질을 높일 수 있다. 실제 마감일 같은 미확인 사실 자체를 추측시키는 용도가 아니다.
4. 조건을 모두 만족하면 해당 질문을 독립 판단한다. 그렇지 않으면 주 에이전트가 답한다. 핵심 질문이 없으면 옵션 호출이어도 추가 에이전트는 없다.
5. 답을 하나 채택한 뒤 그 답을 전제로 다음 질문으로 넘어간다. 아직 결론이 없는 질문의 종속 설계를 먼저 완성하지 않는다.

### 독립 판단 계약

- 주 에이전트는 질문별 잠정 추천과 간단한 근거를 먼저 정리한다. 전체 설계 초안을 만들 필요는 없다.
- 공통 입력: `question_id`, `question`, `facts`(근거 위치 포함), `constraints`, `locked_decisions`, `assumptions`, `options`, `success_criteria`.
- 공통 입력에는 전체 대화, 주 에이전트의 추천·근거, 다른 검토자의 답을 넣지 않는다. 불확실한 사실은 assumptions로 표시한다.
- 세 역할은 각각 전제/단순화(Skeptic), 효과/비용/운영(Pragmatist), 실패/손실(Critic)을 평가한다. 각자 선택지 추가와 전제 반박이 가능하다.
- 각 응답은 추천 답, 짧은 근거, 주요 위험을 담는다. 추가 사용자 질문, 파일 쓰기, 재귀적 위임을 하지 않는다.
- Codex에서는 `fork_turns: "none"`을 사용한다. 병렬 실행이 가능하면 병렬로, 용량이 부족하면 같은 입력으로 새 에이전트를 순차 실행한다.
- 주 에이전트는 명시된 제약·근거·후속 영향·가역성을 고려해 답을 선택한다. 다수결로 결정하거나 반대 의견을 숨기지 않는다.
- 질문별 한 차례 판단한다. 선행 결정이 바뀌어 근거가 달라졌을 때만 해당 질문과 영향을 받는 후속 결정을 재도출한다. 결정 ID와 고정값은 유지한다.
- 일부 또는 전체 실행 실패 시 실제 누락된 관점을 밝히고 확보된 근거로 잠정 답을 선택한다. 같은 조건에서 반복 재시도하거나 가상의 독립 검토 결과를 만들지 않는다.

### 확인 및 출력 계약

- 기술적 판단과 타당한 기본값은 `Confident`에 둘 수 있다. 사용자 우선순위·선호·사업 규칙에 대한 추정은 채택하고 진행하되 `Needs you`에 남긴다.
- 마지막 질문은 기존 한 차례뿐이다. 일반적인 Needs-you 응답은 기존 행별 확정 규칙을 적용하며 자동으로 council을 재실행하지 않는다.
- `--council #<n>=<value>` 재호출은 기존 결정표를 필요로 하며 고정값 주변의 미결정 질문만 평가한다. 이전 표가 없을 때의 기존 안내도 유지한다.
- 기존 출력의 `Decisions` 안에서, `Confident` 앞에 선택적 독립 판단 요약을 둔다. 해당 질문 ID, 각 관점의 추천 또는 누락 상태, 채택 답, 가장 강한 반론과 처리 이유를 간단히 표시한다.
- 요약은 독립 판단을 시도한 질문이 있을 때만 출력한다. 일반 호출과 핵심 질문이 없는 호출에는 새 빈 섹션을 만들지 않는다.
- 독립 판단 후에도 구현·기록 저장·이슈 수정 권한은 생기지 않는다. council 원본의 중간 질문·자동 영속화 절차는 가져오지 않는다. 명시적으로 요청된 설계 파일 저장은 부모 Read-only 규칙을 따른다.

## File Structure

| 파일 | 변경 | 책임 |
|---|---|---|
| `grill-yourself/SKILL.md` | Modify, 현재 22–44행의 절차와 출력 진입점 | 옵션 활성화 및 답 채택 직전의 조건부 분기 연결 |
| `grill-yourself/references/council-questions.md` | Create | 위 질문 해결·독립 판단·확인/출력 계약 전체 |
| `grill-yourself/tests/council-question-scenarios.md` | Create | 다음 평가자가 그대로 사용할 입력, fixture, 관찰 기준 |
| `grill-yourself/tests/dryrun-2026-10-21-critical-questions.md` | Create at execution | 변경 전후 실제 실행 증거와 미검증 범위 기록 |
| `plugins/ai-skills/skills/grill-yourself/`의 위 네 대응 파일 | Modify/Create | 동일한 동작을 배포하는 휴대 가능한 사본 |

기존 `grill-yourself/tests/check_skill.sh`는 수정하지 않는다. 지침 문구를 정규식으로 검사하는 새 테스트나 별도 실행기를 만들지 않고, 기존 구조 검사와 실제 에이전트 실행 관찰을 구분한다. 현재 글로벌 스킬 경로는 원본 디렉터리의 심볼릭 링크이므로 재설치나 전체 `manage.py link` 실행이 필요하지 않다. 실행 시에는 링크를 읽기 전용으로 다시 확인한다.

### Task 1: 질문별 독립 판단과 후속 진행 구현

**Files:**
- Modify: `grill-yourself/SKILL.md:22-44` 및 옵션 출력 안내
- Create: `grill-yourself/references/council-questions.md`
- Test: `grill-yourself/tests/council-question-scenarios.md`
- Evidence: `grill-yourself/tests/dryrun-2026-10-21-critical-questions.md`

**Interfaces:**
- Consumes: 현재 skill의 의존성 순서, 결정 ID, `Confident`/`Needs you`, `#<n>=<value>` 및 행별 응답 규칙.
- Produces: 명시적 옵션 → 질문의 세 조건 판정 → 필요하면 세 독립 응답 → 채택 답 → 종속 질문 진행이라는 지침 계약. 입력 키와 출력 요약은 설계 확정본의 이름을 그대로 사용한다. Python 함수나 CLI 인자 파서를 추가하지 않는다.

- [ ] **Step 1: 평가 입력과 실패 기준을 고정한다.**

  `council-question-scenarios.md`에 아래 사례와 최소 fixture를 기록한다. Fixture는 임시 디렉터리에 README 한 개만 만들며, 내용은 “Python 표준 라이브러리 기반 로컬 CLI, 단일 사용자, 문자열 보고서를 stdout에 출력, 서버·DB·저장 기능 없음”이다. README와 실제 모순되는 추가 사실을 만들지 않는다. 가짜 서비스 구현은 필요 없다.

  | Case | 입력/실행 조건 | 관찰할 assertion |
  |---|---|---|
  | `default_quoted_flag` | 옵션 없이 “보고서 제목의 오타를 고치고 도움말 예시에 문자열 `\"--council\"`을 넣자” | reviewer launches = 0; 옵션 reference 미로딩; 기존 출력 순서 및 읽기 전용 유지 |
  | `flag_without_critical_question` | `--council 보고서 제목의 명백한 오타 한 글자를 수정하자` | reviewer launches = 0; 빈 독립 판단 요약 없음 |
  | `upstream_branch` | `--council 동료 20명이 보고서를 공유하게 하자. 배포 형태는 미정이며 로컬 파일 공유와 서버 서비스 중 선택이 필요하다` | 핵심 분기 답을 채택하기 전에 세 fresh reviewer 호출; 그 답에 맞게 저장·배포 관련 후속 결정 진행; 전체 설계 사후 검토 없음 |
  | `user_only_fact` | 직전 사례에 “내 실제 예산과 마감일은 아직 제공하지 않았다” 추가 | 실제 금액·날짜를 사실로 생성하지 않음; 범위 추천의 가정은 명시하고 사용자 의도 관련 항목은 Needs you에 유지 |
  | `override_and_reply` | 직전 결정표의 배포 결정에 `--council #<실제 ID>=로컬` 재호출 후, 최종 질문에 “추천대로” 응답 | 고정된 로컬 선택을 재투표하지 않음; ID 유지; 종속 결정만 변경; 일반 응답에서 추가 검토·두 번째 질문·구현 없음; 미지정 행은 `[confirmed by default]` |
  | `reviewer_unavailable` | upstream_branch 입력을, 평가 환경에서 위임 도구가 없도록 제한하여 실행 | 실제 reviewer launches = 0; 누락 상태 표시; 가상 관점/가짜 합의 없음; 중간 사용자 질문 없이 잠정 답과 설계 출력 |
  | `reviewer_partial_failure` | 위임을 제어할 수 있는 평가 환경에서 한 관점만 오류 반환 | 실제 성공/누락 관점 구분; 확보된 근거로 진행; 같은 실패의 반복 재시도 없음 |
  | `capacity_limited` | 위임 동시 실행을 한 슬롯으로 제한한 환경에서 upstream_branch 실행 | 같은 중립 입력의 세 fresh 순차 실행; 앞선 응답이나 추천 답이 뒤의 입력에 섞이지 않음 |

  평가자는 선택지의 정답을 미리 강제하지 않는다. 선택 답과 후속 설계의 일관성을 검사한다. 도구 부재/실패/용량 제한을 실제로 통제할 수 없으면 해당 사례를 미실행으로 기록하고, 통과했다고 쓰지 않는다. 실제 실행 제어 대신 단순 역할극을 사용해 독립성이나 실패 경로를 검증했다고 주장하지 않는다.

- [ ] **Step 2: 현재 skill로 baseline을 실행하고 관찰한다.**

  새 문맥 평가자에게 현재 skill 경로, fixture, 사례 입력만 준다. 기본 사례와 upstream_branch를 실행하고, 출력·실제 위임 도구 호출 순서·입력 packet을 증거로 남긴다. 원하는 답이나 제안 수정문을 평가자에게 제공하지 않는다. 예상되는 실패는 질문별 조건부 판단 계약의 부재다. 실제 실패를 관찰하기 전에는 skill을 편집하지 않는다. 이미 특정 기준을 만족하면 실패를 꾸며내지 말고 다른 미충족 기준을 확인한다.

- [ ] **Step 3: 본문 진입점과 질문 reference를 함께 작성한다.**

  현재 호출의 명시적 옵션만 reference를 로드하게 한다. 절차 3·4에서 답을 채택하기 전에 같은 질문 판정 계약을 사용하도록 연결하고, 의도의 큰 분기도 탐색 이후 첫 평가 대상으로 포함한다. 상세 내용은 설계 확정본 그대로 reference에 둔다. 기본 경로의 나머지 본문은 보존하고 5,000바이트 제한을 맞춘다. `council` 원본이 설치되지 않은 배포 환경에서도 동작하도록 reference를 자체 완결적으로 작성한다.

- [ ] **Step 4: 같은 사례를 새 문맥에서 재실행한다.**

  baseline과 동일한 fixture와 사용자 입력을 사용한다. 독립 판단 사례에서는 세 관점이 실제로 실행되었는지와 주 에이전트의 선호가 packet에 들어가지 않았는지를 도구 trace로 확인한다. 핵심 분기 판단 후 후속 설계로 넘어갔다는 관찰을 기록한다. 사용자 질문은 완성된 설계 이후 한 차례여야 한다. 나머지 사례도 실행하고 관찰에 근거한 결함만 수정한다.

  dryrun 기록에는 각 사례의 `PASS`/`FAIL`/`NOT RUN`, 근거, 실행 전후 차이, 파일 쓰기 여부를 남긴다. 단순 구조 검사나 과거에 되돌린 사후 검토 구현의 결과를 이번 동작 증거로 재사용하지 않는다.

- [ ] **Step 5: 원본 구조와 변경 범위를 확인한다.**

  Run: `bash grill-yourself/tests/check_skill.sh`

  Expected: exit 0, `OK: grill-yourself/SKILL.md passes structural check`, 본문 5,000바이트 이하. 새 reference의 상대 경로가 실제 파일을 가리키는지도 확인한다. 기본 출력 순서, Read-only, Overrides, Needs-you 처리의 기존 내용이 불필요하게 변경되지 않았는지 diff를 검토한다.

- [ ] **Step 6: 실행 시 승인된 통합 방식에 맞춰 원본 변경을 커밋한다.**

  실행 단계에서 커밋이 허용된 경우에만 아래 네 파일을 명시적으로 stage한다. 계획 작성만으로 커밋 권한을 가정하지 않는다.

  ```bash
  git add -- grill-yourself/SKILL.md grill-yourself/references/council-questions.md grill-yourself/tests/council-question-scenarios.md grill-yourself/tests/dryrun-2026-10-21-critical-questions.md
  git diff --cached --check
  git commit -m "feat(grill-yourself): resolve critical questions with independent advice"
  ```

### Task 2: 배포 사본 동기화와 회귀 검증

**Files:**
- Modify: `plugins/ai-skills/skills/grill-yourself/SKILL.md`
- Create: `plugins/ai-skills/skills/grill-yourself/references/council-questions.md`
- Create: `plugins/ai-skills/skills/grill-yourself/tests/council-question-scenarios.md`
- Create: `plugins/ai-skills/skills/grill-yourself/tests/dryrun-2026-10-21-critical-questions.md`

**Interfaces:**
- Consumes: Task 1의 검증된 네 원본 파일과 실제 행동 평가 기록.
- Produces: 같은 상대 경로로 옵션 reference가 로드되는 휴대 가능한 사본. 전역 재링크나 council 스킬의 추가 설치에 의존하지 않는다.

- [ ] **Step 1: 동기화 전 원본과 사본의 차이를 관찰한다.**

  Run: `diff -ru grill-yourself plugins/ai-skills/skills/grill-yourself`

  Expected: Task 1의 본문 및 새 파일에 대한 차이. 그 외 기존 사용자 변경이 발견되면 덮어쓰지 말고 분리한다. 광범위한 삭제·동기화 명령은 사용하지 않는다.

- [ ] **Step 2: 대응하는 네 파일만 복사한다.**

  대상의 `references` 디렉터리를 만들고 Task 1의 네 파일을 동일한 상대 경로로 복사한다. 기존 파일을 제거하거나 다른 스킬을 동기화하지 않는다. 실행 시점의 글로벌 링크가 원본을 가리키는지만 읽기 전용으로 확인한다.

- [ ] **Step 3: 사본 일치와 저장소 검사를 실행한다.**

  Run individually:

  ```bash
  diff -ru grill-yourself plugins/ai-skills/skills/grill-yourself
  bash grill-yourself/tests/check_skill.sh
  bash plugins/ai-skills/skills/grill-yourself/tests/check_skill.sh
  python3 script/manage.py test
  git diff --check
  ```

  Expected: diff 출력 없음, 두 구조 검사 exit 0, unittest의 `OK`, whitespace 오류 없음. 테스트 개수를 통과 조건으로 고정하지 않는다. 저장소 테스트는 질문별 독립 판단의 행동 증거를 대신하지 않는다.

- [ ] **Step 4: 사본 경로를 사용해 옵션 reference 로딩을 확인한다.**

  새 문맥에서 사본의 SKILL.md와 동일 fixture로 `flag_without_critical_question`을 실행한다. 사본의 reference를 정상 로드하고 세 조건 판정 후 reviewer launches = 0인 것을 확인한다. 원본 디렉터리의 reference나 council 원본을 대신 읽는 방식으로 통과시키지 않는다.

- [ ] **Step 5: 실행 시 승인된 통합 방식에 맞춰 사본을 커밋한다.**

  커밋 권한이 있는 경우에만 네 대응 파일을 명시적으로 stage하고 staged 범위·whitespace를 확인한 뒤 `chore(grill-yourself): sync critical-question skill distribution`으로 커밋한다. 푸시는 하지 않는다.

## Self-Review

- Spec coverage: 옵션/핵심 판정/삽입 위치/독립성/답 채택/후속 진행/고정값/사용자 가정/실패 경로/출력은 Task 1, 휴대성과 회귀는 Task 2가 담당한다.
- Step scan: 지침 작성과 행동 검증의 책임을 구분했으며, 존재하지 않는 실행 함수·파서·평가 도구를 전제하지 않는다. 실패 주입을 통제할 수 없는 환경은 미검증으로 남긴다.
- Interface consistency: reference 이름은 `council-questions.md`; 공통 packet 키와 결과 요약은 설계 확정본에 한 번 정의했다. 원본과 사본의 상대 경로가 같다.
- Review Focus: 다섯 항목 모두 Task 1의 명명된 사례로 연결했다. 실제 실패와 용량 부족은 별도 사례로 구분했다.
- Proportion: 하나의 조건부 지침 기능과 하나의 배포 작업으로 나눴다. 새 실행기, 옵션 파서, 설정 또는 텍스트 매칭 테스트를 추가하지 않는다.

## Execution Handoff

권장 방식은 **Native**다. 두 작업이 원본 지침과 그 사본으로 강하게 연결되어 있어 주 구현자가 연속해서 처리하는 편이 간단하다. 행동 검증에는 별도의 새 문맥 에이전트를 사용하고, Native 실행 방식이 승인되면 해당 방식의 최종 독립 리뷰를 적용한다.

사용자에게 이 계획을 검토받고 **Native / Subagent-driven** 중 실행 방식을 받은 후에 구현을 시작한다. 계획 작성 단계에서는 위 작업, 행동 평가, 구현 커밋을 실행하지 않는다.
