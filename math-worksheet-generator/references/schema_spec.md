# 데이터 스키마 명세 (Data Schema Specification)

각 단원 데이터셋은 자바스크립트 파일(`data/problems_partX.js`) 형태로 저장되며, 브라우저 환경에서 `file://` 직접 로딩을 지원하기 위해 전역 변수 `window.WORKSHEET_DATA`에 바인딩됩니다.

---

## 1. 최상위 객체 구조

```javascript
window.WORKSHEET_DATA = {
  "meta": {
    "title": "수학 II - I. 함수의 극한과 연속", // 과목명 - 단원명
    "subtitle": "학교 프린트 핵심 유형 및 필기·쌍둥이 문제",
    "student": "오서영",                       // 학생 이름
    "date": "2026. 09. 12 (토)",             // 제작 일자
    "cheer": "서영이의 완벽한 내신 1등급을 응원합니다 ✨" // 하단 응원 문구
  },
  "problems": [
    /* 문제 객체 배열 (반드시 4의 배수) */
  ]
};
```

---

## 2. 개별 문제 객체 (`Problem`)

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | `number` | 필수 | 1부터 시작하는 연속 문항 번호 |
| `source` | `string` | 필수 | 출처 (예: `"학교 프린트 4p 문제 6"`, `"선생님 필기 추가"`, `"AI 숫자 변형"`) |
| `tag` | `string` | 필수 | 난이도/유형 뱃지 (`"기본"`, `"핵심유형"`, `"심화"`, `"필기"`, `"쌍둥이유제"`) |
| `question` | `string` | 필수 | 문제 본문 텍스트 (수식은 KaTeX `$...$` 인라인 표기) |
| `formula` | `string` | 선택 | 별도 행으로 표시할 중앙 정렬 대표 수식 (없으면 빈 문자열 `""`) |
| `subQuestions` | `array` | 필수 | 소문항 배열. 소문항이 없으면 빈 배열 `[]` |
| `tip` | `string` | 필수 | 하단 힌트 영역에 표시될 교수법 맞춤 팁 문장 |
| `answer` | `string` | 필수 | 최종 정답 텍스트/수식 |
| `solution` | `object` | 필수 | 해설지 모드에서 `.card__solution-box`에 조판될 단계별 풀이 객체 |

---

## 3. 소문항 객체 (`SubQuestion`)

```javascript
{
  "no": 1,                                  // 소문항 번호 (1, 2)
  "formula": "\\lim_{x \\to 0} \\frac{|x|}{x}" // 소문항 수식 (KaTeX)
}
```

> **규칙**: 소문항 수식이 길거나 분수/근호/거듭제곱이 포함된 경우, 템플릿의 `buildCard`가 자동으로 세로 1열 스택(`card__subs--stack`)으로 전환하여 전체 폭(84.5mm)을 사용합니다.

---

## 4. 해설 객체 (`Solution`)

```javascript
{
  "steps": [
    {
      "label": "[1단계: 선 대입]", // 단계 뱃지 텍스트
      "content": "$x=1$을 식에 대입하면 $\\frac{0}{0}$ 꼴(부정형)입니다." // 풀이 내용 (KaTeX 포함)
    },
    {
      "label": "[2단계: 식 변형]",
      "content": "분자를 인수분해하여 약분: $\\frac{(x-1)(x+2)}{x-1} = x+2$"
    },
    {
      "label": "[3단계: 재대입]",
      "content": "$x=1$을 다시 대입하면 $1+2 = 3$ $\\therefore$ **3**"
    }
  ]
}
```

- 소문항이 있는 문항은 `label`을 `"(1)"`, `"(2)"`로 구성할 수 있습니다:
```javascript
{
  "steps": [
    {
      "label": "(1)",
      "content": "[1단계: 대입] $x \\to \\infty$ 대입 시 $\\frac{1}{\\infty} \\to 0$이므로 $0+1=1$ $\\therefore$ **1**"
    },
    {
      "label": "(2)",
      "content": "[1단계: 구간 분리] 절댓값 함수는 $x < -1$ 구간 함수 $-(x+1)$로 변경: $\\frac{1}{-(x+1)}$ \\\\ [2단계: 대입] $x \\to -\\infty$ 대입 시 $\\frac{1}{\\infty} \\to 0$ $\\therefore$ **0**"
    }
  ]
}
```

---

## 5. 검증 불변식 (Invariants)

1. **4의 배수 불변식**: `len(problems) % 4 == 0`
2. **KaTeX 구분자 불변식**: 모든 `question`, `formula`, `tip`, `answer`, `step.content` 내 `$` 기호 개수는 반드시 짝수(`count % 2 == 0`).
3. **고유 ID 불변식**: 모든 `id`는 중복되지 않아야 함.
