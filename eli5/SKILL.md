---
name: eli5
description: Explain a topic like I'm a 5 year old as a dead-simple visual HTML explainer in the 정리노트 (note-template) style — one topic per screen, big SVG pictures, few words, left TOC, right summary panel, dark mode. Use when the user types /eli5 [topic] or asks for a simple visual, picture-book style explanation of how something works.
---

# eli5 — Explain Like I'm 5 (정리노트 양식)

배경지식이 전혀 없는 사람에게 복잡한 주제(개념, 코드베이스, 아키텍처, 기술 용어)를 **큰 그림과 적은 글**로 설명한다. 결과물은 정리노트 양식의 단일 HTML이다. 템플릿은 bio-review-pack `note-template.html`을 그대로 복사한 것이다.

## When to Use

- `/eli5 <topic>` 또는 `/eli5`로 호출됐을 때.
- "5살도 이해할 수 있게 설명해줘", "그림으로 쉽게 설명해줘", "시각적으로 설명해줘", "Explain like I'm 5", "picture book explanation"처럼 쉬운 시각 설명을 요청할 때.
- 낯선 시스템 온보딩, 기술 부채·트레이드오프 설명, 장애 원인 설명에도 쓴다.

## Core Principles

1. **배경지식 0**: 전문용어는 피하거나, 쓰면 바로 일상 비유로 풀어 쓴다.
2. **큰 그림, 적은 글**: `쉽게 말하면` 레이어는 figcaption을 포함해 3문장 이하로 쓴다. 문단 대신 SVG와 단계 목록을 쓴다.
3. **비유 먼저**: 일상 속 비유로 개념을 붙잡는다. 예: DNS는 전화번호부, 로드밸런서는 식당 안내원, Git은 세이브 포인트.
4. **양식 고정**: HTML을 처음부터 새로 쓰지 않는다. 본문 조각만 쓰고 `scripts/build.py`로 템플릿을 채운다. UI 문구(목차·요약·이전/다음)는 한국어로 고정한다.

## Workflow

`SKILL` = 이 파일이 있는 폴더, `OUT` = artifact 디렉터리, `WORK` = `OUT/scratch/`.

### 1. 토픽 설계
`$ARGUMENTS`나 대화에서 주제를 정하고, 아래 순서로 **토픽 화면 4~6개**를 잡는다. 필요하면 합치거나 나눈다.

| # | 토픽 | 담을 것 |
|---|---|---|
| 1 | 왜 필요할까? | 이것이 해결하는 문제 |
| 2 | 무엇과 비슷할까? | 일상 비유와 비유-실제 대응 그림 |
| 3–4 | 어떻게 움직일까? | 3~4단계 흐름(`ol.steps` + 흐름 SVG) |
| 5 | 있을 때 vs 없을 때 | 비교 표 |
| 6 | 한 줄로 기억하기 | 핵심 문장 + 흔한 오해(`꼭 기억해요`) |

- hero(첫 화면)는 빌드 인자 `--title`과 `--subtitle`(비유를 담은 한 줄 요약)로 만든다.
- 섹션은 1~2개면 충분하다(예: `한눈에 보기`, `더 들여다보기`).

### 2. 본문 조각 작성
[references/markup.md](references/markup.md)의 마크업 규칙대로 `WORK/<slug>-body.html`을 쓴다.

- 토픽마다 `layer eli5`(쉽게 말하면 + `p.lead` + 그림)는 필수다.
- `layer formal`(정확히 말하면)은 **비유가 실제와 어긋날 때만** 2~3문장으로 쓴다.
- `layer warn`(꼭 기억해요)은 헷갈리는 짝이 있을 때만 쓴다.
- 토픽 맨 끝에는 `<div class="sum" hidden>`(핵심 한 문장 + 용어)을 반드시 둔다. 이 내용이 오른쪽 "페이지 요약" 패널에 나온다.
- SVG 색은 `.fig-*` 클래스로만 지정한다(다크 모드 대응).
- 위젯은 0~1개만 넣는다.

### 3. 빌드
```powershell
python "$SKILL/scripts/build.py" --title "<주제>" --subtitle "<비유 한 줄>" --slug <kebab-slug> --sections "$WORK/<slug>-body.html" --out "$OUT/ELI5_<slug>.html"
```
- `OK: …`가 나와야 한다. `FAIL: …`이 나오면 메시지대로 조각을 고치고 다시 빌드한다. 실패 원인은 섹션·토픽 누락, id 중복이나 템플릿 id와의 충돌, 자리표시자 잔존 중 하나다.
- `--footer "<출처·참고>"`는 마지막 화면에만 보인다. 필요할 때만 넣는다.

### 4. 확인과 전달
- 생성된 HTML에서 다음을 훑어본다: `$` 짝이 맞는지, 이모지가 없는지, 토픽마다 `.sum`이 있는지.
- 채팅 응답에는 다음만 쓴다.
  1. 2~3문장 요약
  2. 생성된 HTML 링크

## 템플릿 갱신
bio-review-pack 정리노트 템플릿이 바뀌면 `assets/note-template.html`에 파일을 그대로 덮어쓴다. 자리표시자 이름이 바뀌었으면 `scripts/build.py`의 `values`도 맞춘다. `python -m unittest discover -s "$SKILL/tests"`로 확인한다.
