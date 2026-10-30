# 본문 조각 마크업 (note-template 양식)

`scripts/build.py --sections`에 넘기는 파일은 `<main>` 안에 들어갈 **섹션들만** 담는다. `<html>`, `<head>`, hero, 목차, 패널은 템플릿이 만든다.

## 뼈대

```html
<section id="s1">
  <h2>한눈에 보기</h2>

  <article class="topic" id="t-why">
    <h3>왜 필요할까?</h3>

    <div class="layer eli5">
      <span class="layer-title">쉽게 말하면</span>
      <p class="lead">비유 한 문장.</p>
      <figure class="figure">
        <svg id="fig-why" viewBox="0 0 560 220" role="img" aria-label="그림을 한국어로 설명">…</svg>
        <figcaption>그림 설명 한 줄.</figcaption>
      </figure>
    </div>

    <!-- 선택: 비유가 실제와 어긋날 때만, 2~3문장 -->
    <div class="layer formal">
      <span class="layer-title">정확히 말하면</span>
      <p><b>핵심 용어</b>는 …예요.</p>
    </div>

    <!-- 선택: 흔히 헷갈리는 짝이 있을 때만 -->
    <div class="layer warn">
      <span class="layer-title">꼭 기억해요</span>
      <p>A와 B는 달라요. …</p>
    </div>

    <!-- 필수, 토픽의 맨 끝: 오른쪽 "페이지 요약" 패널로 옮겨진다 -->
    <div class="sum" hidden>
      <p class="sum-lead">토픽 핵심 한 문장(~해요).</p>
      <p class="panel-label">용어</p>
      <dl class="terms"><dt>용어(English)</dt><dd>쉬운 뜻 한 줄.</dd></dl>
    </div>
  </article>
</section>
```

- 섹션(`<section id><h2>`)은 왼쪽 목차의 그룹이다. 토픽(`article.topic`)은 한 화면이다. 토픽 화면은 모두 4~6개로 만든다.
- id는 영소문자·숫자·하이픈을 쓰고, 파일 안에서 유일해야 한다. 템플릿 id(`panel-left`, `pager-next` 등)와 겹치면 빌드가 실패한다.
- `<h3>`는 목차 항목 이름이 된다. 짧게 쓴다.
- 이모지와 원문자(①~⑳)는 쓰지 않는다. 템플릿의 담백한 톤을 유지하기 위해서다.

## 쓸 수 있는 요소

| 용도 | 마크업 |
|---|---|
| 단계 | `<ol class="steps"><li><b>이름</b> — 한 줄</li></ol>` |
| 비교(있을 때 vs 없을 때) | `<div class="table-wrap"><table><thead><tr><th></th><th>없으면</th><th>있으면</th></tr></thead><tbody>…</tbody></table></div>` |
| 짧은 인용·예시 | `<blockquote>…</blockquote>` |
| 강조 배지 | `<span class="badge">…</span>` |
| 수식 | `$…$`, `$$…$$` (KaTeX) |
| 핵심 식(요약 패널) | `.sum` 안에 `<p class="panel-label">핵심 식</p><ul class="eq-list"><li><span class="eq-name">이름</span>$$…$$</li></ul>` |

## SVG 그림

- 색은 클래스로만 지정한다. 그래야 다크 모드에서 색이 따라 바뀐다. 직접 쓴 `fill="#…"`는 다크 모드에서 깨진다.
  - `.fig-ink`: 기본 윤곽선(currentColor)
  - `.fig-accent`: 파란 강조 윤곽선
  - `.fig-danger`: 빨간 경고 윤곽선
  - `.fig-dot`: 파란 채움 점
  - `.fig-text`: 본문 글자(13px)
  - `.fig-muted`: 회색 보조 글자(12px)
- 화살표는 `<defs><marker>` 안의 path에 `fill="currentColor"`를 쓴다.
- figcaption의 설명은 실제 모양과 맞아야 한다. 예를 들어 `fig-accent`로 그린 것은 "파란 윤곽"이다.
- viewBox 폭은 560 안팎으로 잡는다. 375px 화면에서도 가로 스크롤이 생기지 않는다.

## 위젯 (선택, 0~1개)

움직여 봐야 이해되는 개념에만 넣는다.

```html
<div class="widget">
  <h4>직접 바꿔 보기</h4>
  <p class="widget-help">슬라이더를 움직이면 …가 보여요.</p>
  <div class="controls"><label>값 <input type="range" id="w-x" min="0" max="10"></label></div>
  <svg id="w-plot" viewBox="0 0 560 200" role="img" aria-label="…">…</svg>
  <p class="readout" id="w-out"></p>
</div>
<script>/* 조각 안의 script는 빌드 시 </body> 앞으로 옮겨진다 */</script>
```
