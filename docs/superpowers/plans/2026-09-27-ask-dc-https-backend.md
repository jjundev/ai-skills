# ask-dc HTTPS 백엔드 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ask-dc`의 읽기 기능(목록·검색·개념글·본문·댓글)을 Chrome/OpenCLI 없이 Node 내장 `fetch`만으로 동작하게 바꾸고, `opencli dcinside list/read`도 같은 코어를 쓰게 한다.

**Architecture:** 의존성 없는 HTTP 코어 `ask-dc/adapter/http.js`(요청·리다이렉트 판별·HTML 문자열 파싱·댓글 JSON 정리)를 만들고, 독립 CLI `ask-dc/scripts/dc.mjs`와 OpenCLI 래퍼 `adapter/list.js`·`adapter/read.js`(`Strategy.PUBLIC`, `browser:false`)가 이를 호출한다. `write.js`와 `write-dc`는 브라우저 방식 그대로 둔다.

**Tech Stack:** Node.js 18+ (내장 `fetch`, `node:test`, `node:util.parseArgs`), OpenCLI 1.8.6 (`@jackwener/opencli`, 래퍼 전용), Bash, Python 3 (SKILL.md 패치 스크립트).

**Spec:** 이 세션의 grill-yourself 설계(2026-09-27, 채팅) — 요약은 이 문서 끝 "Appendix A. 설계 요약"에 포함. Needs-you: N1=(a) `search_pos` 확장 제외, N2=(a) 별도 브랜치 → main 병합·커밋, push 안 함.

## Global Constraints

- 작업 위치: `~/.ai-skills/.claude/worktrees/ask-dc-https` (브랜치 `feat/ask-dc-https`, base `main` @ `ba72481`). main 체크아웃은 6개 에이전트 호스트에 실시간 링크되어 있으므로 병합 전에는 건드리지 않는다.
- 런타임 의존성 추가 금지: `ask-dc/adapter/node_modules/`는 gitignore 대상(OpenCLI shim 전용)이다. `http.js`와 `dc.mjs`는 Node 내장 모듈만 쓴다.
- `http.js`는 `@jackwener/opencli`를 import하지 않는다.
- 출력 컬럼 유지: list = `rank, postId, title, author, publishedAt, commentCount, viewCount, recommendCount, isNotice, url`; read = `type, postId, parentId, author, publishedAt, title, content, views, recommendations, url`.
- 인자 범위 유지: `page` 1-1000, `limit` 1-50, `comment-limit` 0-50, `content-limit` 100-10000.
- 독립 CLI 종료 코드: 0 성공, 1 NETWORK, 2 ARG, 3 EMPTY, 4 NOT_FOUND, 5 AUTH/BLOCKED. 오류는 stderr에 `{"error":{"code","message"}}`.
- 요청 간격 300ms, 429/5xx/네트워크 오류 1회 재시도(1초 후).
- `write.js`, `write-dc/`, `agent-reach/`는 수정하지 않는다.
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. push 금지.

## Review Focus

- 일반 경로로 요청한 마이너 갤러리: 200 + `location.replace` 스크립트만 오고 쿼리가 사라진다 → 검색어·페이지를 유지한 채 `/mgallery/`로 재요청해야 한다. (Task 1 테스트 `listGallery follows the minor-gallery JS redirect and keeps the query`)
- 일반 경로로 요청한 미니 갤러리: 리다이렉트 없이 404 → `/mini/`로 1회 재시도, 둘 다 404면 NOT_FOUND. (Task 1 테스트 `listGallery falls back to /mini/ on 404, then reports NOT_FOUND`)
- 댓글 응답의 광고(`COMMENT_BOY`/`no:0`)·삭제(`del_yn:Y`)·HTML(멘션, 디시콘, 엔티티, ` - dc App`) → 보고서 인용문이 HTML/광고로 오염되면 안 된다. (Task 1 테스트 `normalizeComment ...`)
- 댓글 페이지를 늘려도 같은 댓글만 반복될 때 무한 루프·중복 → 새 댓글이 없으면 멈춘다. (Task 1 테스트 `readPost pages comments until the limit and stops on a repeated page`)
- 토큰 누락/차단 시 "정상적인 접근이 아닙니다." 텍스트 → JSON 파싱 실패를 BLOCKED로 보고해야 한다. (Task 1 테스트 `readPost maps missing posts ... BLOCKED`)

---

### Task 1: HTTP 코어 `adapter/http.js` + fixture + 단위 테스트

**Files:**
- Create: `ask-dc/adapter/http.js`
- Create: `ask-dc/tests/fixtures/list-general.html`, `list-minor.html`, `redirect-minor.html`, `view-general.html`, `comments.json`
- Test: `ask-dc/tests/http.test.mjs`

**Interfaces:**
- Consumes: 없음 (Node 내장 `fetch`만 사용)
- Produces (모두 named export):
  - `DCINSIDE_ORIGIN: string`, `timing: { gapMs: number, retryDelayMs: number }`
  - `class DcError extends Error { code: 'ARG'|'EMPTY'|'NOT_FOUND'|'AUTH'|'BLOCKED'|'NETWORK' }`
  - `requireGalleryId(value) → string`, `requireBoundedInteger(value, defaultValue, min, max, label) → number` (둘 다 `DcError('ARG')`를 던짐)
  - `isLoginUrl(url: URL) → boolean`
  - `listGallery(galleryId, { page?, limit?, head?, recommend?, sort?, search?, searchType?, includeNotices?, galleryType?: 'G'|'M'|'MI' }) → Promise<ListRow[]>`
  - `readPost(postUrl, { commentLimit?, contentLimit? }) → Promise<ReadRow[]>`
  - 테스트용: `listUrl`, `viewUrl`, `parsePostUrl`, `galleryTypeFromPath`, `jsRedirectTarget`, `htmlToText`, `decodeEntities`, `attr`, `parseListHtml`, `parseViewHtml`, `normalizeComment`, `request`, `getPage`, `fetchCommentPage`

- [ ] **Step 1: fixture 작성** (2026-09-27 실제 페이지에서 잘라낸 마크업)

`ask-dc/tests/fixtures/list-general.html`:
```html
<table class="gall_list"><tbody>
<tr class="ub-content ">
	<td class="gall_num">설문</td>
	<td class="gall_tit ub-word"><a href="javascript:;" class="font_orangefa6" onclick="survey_layer('x');"><em class="icon_img icon_n_survey"></em><b>설문 제목</b></a></td>
	<td class="gall_writer ub-writer" user_name="운영자"><b>운영자</b></td>
	<td class="gall_date">26/09/21</td>
	<td class="gall_count">-</td>
	<td class="gall_recommend">-</td>
</tr>
<tr class="ub-content" data-no="1" data-type="icon_notice" >
	<td class="gall_num">공지</td>
	<td class="gall_tit ub-word">
		<a href="/board/view/?id=shaving&no=1&page=1" view-msg ="">
		<em class="icon_img icon_notice"></em><b><b>면도 갤러리 이용 안내</b></b></a>
		<a class="reply_numbox" href="https://gall.dcinside.com/board/view/?id=shaving&no=1&t=cv&page=1"><span class="reply_num">[142]</span></a>
	</td>
	<td class="gall_writer ub-writer" data-nick="운영자" data-uid="" data-ip="" data-loc="list"><div class="addbox"><b>운영자</b></div></td>
	<td class="gall_date" title="2007-12-28 14:51:23">07.12.28</td>
	<td class="gall_count">24622</td>
	<td class="gall_recommend">6</td>
</tr>
<tr class="ub-content us-post" data-no="40288" data-type="icon_pic" >
	<td class="gall_num">40288</td>
	<td class="gall_tit ub-word">
		<a  href="/board/view/?id=shaving&amp;no=40288&amp;page=1" view-msg ="">
		<em class="icon_img icon_pic"></em> 이거 이즈미 IKS-6000 &amp; 면도기 쓸만하냐?  </a>
	</td>
	<td class="gall_writer ub-writer" data-nick="ㅇㅡㅇ" data-uid="" data-ip="119.235" data-loc="list"><div class="addbox"><span class='nickname' title='ㅇㅡㅇ'><em>ㅇㅡㅇ</em></span><span class="ip">(119.235)</span></div></td>
	<td class="gall_date" title="2026-09-27 17:38:15">17:38</td>
	<td class="gall_count">23</td>
	<td class="gall_recommend">0</td>
</tr>
<tr class="ub-content us-post" data-no="40285" data-type="icon_txt" >
	<td class="gall_num">40285</td>
	<td class="gall_tit ub-word">
		<a  href="/board/view/?id=shaving&no=40285&page=1" view-msg ="">
		<em class="icon_img icon_txt"></em>s9 pro에 네보 면도날끼워도 됨?</a>
		<a class="reply_numbox" href="https://gall.dcinside.com/board/view/?id=shaving&no=40285&t=cv&page=1"><span class="reply_num">[2/1]</span></a>
	</td>
	<td class="gall_writer ub-writer" data-nick="면갤러" data-uid="" data-ip="133.114" data-loc="list"><div class="addbox"><span class='nickname' title='면갤러'><em>면갤러</em></span></div></td>
	<td class="gall_date" title="2026-09-27 15:53:52">15:53</td>
	<td class="gall_count">1,035</td>
	<td class="gall_recommend">0</td>
</tr>
</tbody></table>
```

`ask-dc/tests/fixtures/list-minor.html`:
```html
<table class="gall_list"><tbody>
<tr class="ub-content us-post" data-no="2708715" data-type="icon_txt" >
	<td class="gall_num">2708715</td>
	<td class="gall_subject">일반</td>
	<td class="gall_tit ub-word">
		<a  href="/mgallery/board/view/?id=laptop&no=2708715&page=1" view-msg ="">
		<em class="icon_img icon_txt"></em>갤북프를 데탑 외장모니터로 쓰는 방법 있을까??</a>
		<a class="reply_numbox" href="https://gall.dcinside.com/mgallery/board/view/?id=laptop&no=2708715&t=cv&page=1"><span class="reply_num">[2]</span></a>
	</td>
	<td class="gall_writer ub-writer" data-nick="ㅇㅇ" data-uid="" data-ip="211.201" data-loc="list"><div class="addbox"></div></td>
	<td class="gall_date" title="2026-09-27 20:21:35">20:21</td>
	<td class="gall_count">34</td>
	<td class="gall_recommend">0</td>
</tr>
</tbody></table>
```

`ask-dc/tests/fixtures/redirect-minor.html` (개행 없이 한 줄):
```html
<script type="text/javascript">location.replace("https://gall.dcinside.com/mgallery/board/lists?id=laptop");</script>
```

`ask-dc/tests/fixtures/view-general.html`:
```html
<html><body>
<input type="hidden" id="e_s_n_o" name="e_s_n_o" value="0f317ce69463bdf3">
<input type="hidden" name="_GALLTYPE_" id="_GALLTYPE_" value="G" />
<header>
	<div class="gallview_head clear ub-content">
		<h3 class="title ub-word"><span class="title_headtext"></span> <span class="title_subject">네보 vs 뉴갤주 &quot;하루&quot; 사용기</span><span class="title_device"></span></h3>
		<div class="gall_writer ub-writer" data-nick="Ceja" data-uid="cejaluna1764" data-ip="" data-loc="view">
			<div class="fl"><span><span class='nickname in' title='Ceja'><em>Ceja</em></span>
				<span class="gall_date" title="2026-08-27 17:24:58">2026.08.27 17:24:58</span></span></div>
			<div class="fr">
				<span class="gall_count">조회 3014</span>
				<span class="gall_reply_num">추천 14</span>
				<span class="gall_comment"><a href="#focus_cmt">댓글 7</a></span>
			</div>
		</div>
	</div>
</header>
<div class="writing_view_box">
	<div class="write_div" style="overflow:hidden;width:900px;" data-tracking="x">
		<p><br></p><p> 갤럼들이 궁금해 할만한 본론만 간다ㅇㅇ</p>
		<div class="nested"><p>1. 모터소음 &amp; 파워</p></div>
		<script>window.bad = "SCRIPT_TEXT";</script>
		<p>끝</p>
	</div>
	<div class="after_body">본문 밖 텍스트</div>
</div>
<p class="up_num font_red" id="recommend_view_up_39837">14</p>
</body></html>
```

`ask-dc/tests/fixtures/comments.json`:
```json
{"total_cnt":6,"comment_cnt":0,"comments":[
{"no":"103919","name":"면갤러1","memo":"4중날이 6중날을 어찌이기노ㅋㅋ","reg_date":"08.27 17:47:07","depth":0,"c_no":0,"nicktype":"00","del_yn":"N","is_delete":"0"},
{"no":"103924","name":"ㅇㅇ","memo":"lv97급을 29만원주고 산다라.. - dc App","reg_date":"08.27 18:42:12","depth":0,"c_no":0,"nicktype":"00","del_yn":"N","is_delete":"0"},
{"no":"103950","name":"어머_","memo":"<a href=\"javascript:focusComment(103924);\" class=\"mention\">@ㅇㅇ(118.235)</a> 97은 좀 내려치기지 &lt;9u&gt;","reg_date":"08.27 22:07:43","depth":1,"c_no":"103924","nicktype":"20","del_yn":"N","is_delete":"0"},
{"no":"103960","name":"콘쟁이","memo":"<img class=\"written_dccon \" src=\"https://dcimg5.dcinside.com/dccon.php?no=abc\" conalt=\"쉿\" alt=\"쉿\" title=\"쉿\" data-dcconoverstatus=\"false\">","reg_date":"08.27 22:10:00","depth":0,"c_no":0,"nicktype":"00","del_yn":"N","is_delete":"0"},
{"no":"103961","name":"ㅇㅇ","memo":"해당 댓글은 삭제되었습니다.","reg_date":"08.27 22:11:00","depth":0,"c_no":0,"nicktype":"00","del_yn":"Y","is_delete":"3"},
{"no":0,"name":"댓글돌이","memo":"<div class=\"comment_dory clean\"><a href=\"https://issuefeed.dcinside.com/content/1\">광고</a></div>","reg_date":"","depth":0,"c_no":0,"nicktype":"COMMENT_BOY"},
{"no":"103970","name":"ㅇㅇ","memo":"   ","reg_date":"08.27 23:00:00","depth":0,"c_no":0,"nicktype":"00","del_yn":"N","is_delete":"0"}
],"pagination":"<em>1</em>","allow_reply":1}
```

- [ ] **Step 2: 실패하는 테스트 작성** — `ask-dc/tests/http.test.mjs`:
```js
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as dc from '../adapter/http.js';

const fixture = (name) => readFileSync(new URL(`./fixtures/${name}`, import.meta.url), 'utf8');
const realFetch = globalThis.fetch;
let calls;

// routes: [matcher(url, init) => boolean, { status, body, headers }]
function stubFetch(routes) {
    globalThis.fetch = async (url, init = {}) => {
        calls.push({ url: String(url), init });
        const route = routes.find(([match]) => match(String(url), init));
        if (!route) throw new Error(`unrouted fetch: ${url}`);
        const { status = 200, body = '', headers = {} } = route[1];
        return new Response(body, { status, headers });
    };
}

beforeEach(() => {
    calls = [];
    dc.timing.gapMs = 0;
    dc.timing.retryDelayMs = 0;
});
afterEach(() => {
    globalThis.fetch = realFetch;
});

// ---------- validation & URLs ----------

test('requireGalleryId accepts ids, maps ibook, rejects junk', () => {
    assert.equal(dc.requireGalleryId(' shaving '), 'shaving');
    assert.equal(dc.requireGalleryId('ibook'), 'macbook');
    assert.throws(() => dc.requireGalleryId('bad id'), { code: 'ARG' });
    assert.throws(() => dc.requireGalleryId(''), { code: 'ARG' });
});

test('requireBoundedInteger parses strings and enforces range', () => {
    assert.equal(dc.requireBoundedInteger('20', 5, 1, 50, 'limit'), 20);
    assert.equal(dc.requireBoundedInteger(undefined, 5, 1, 50, 'limit'), 5);
    assert.throws(() => dc.requireBoundedInteger('51', 5, 1, 50, 'limit'), { code: 'ARG', message: /between 1 and 50/ });
    assert.throws(() => dc.requireBoundedInteger('abc', 5, 1, 50, 'limit'), { code: 'ARG' });
});

test('listUrl builds each gallery type with search params', () => {
    assert.equal(
        dc.listUrl('laptop', 'M', 2, { search: '맥북 에어', recommend: true, head: '70', sort: 'N' }),
        'https://gall.dcinside.com/mgallery/board/lists/?id=laptop&page=2&search_head=70&exception_mode=recommend&sort_type=N&s_type=search_subject_memo&s_keyword=%EB%A7%A5%EB%B6%81+%EC%97%90%EC%96%B4',
    );
    assert.equal(dc.listUrl('x', 'MI', 1), 'https://gall.dcinside.com/mini/board/lists/?id=x&page=1');
    assert.equal(dc.listUrl('x', 'G', 1, { search: 'a', searchType: 'search_name' }), 'https://gall.dcinside.com/board/lists/?id=x&page=1&s_type=search_name&s_keyword=a');
});

test('parsePostUrl accepts all three view paths and rejects others', () => {
    assert.deepEqual(dc.parsePostUrl('https://gall.dcinside.com/board/view/?id=shaving&no=39837&page=1'), { galleryId: 'shaving', postId: '39837', galleryType: 'G' });
    assert.deepEqual(dc.parsePostUrl('https://gall.dcinside.com/mgallery/board/view?id=laptop&no=5'), { galleryId: 'laptop', postId: '5', galleryType: 'M' });
    assert.equal(dc.parsePostUrl('https://gall.dcinside.com/mini/board/view/?id=a&no=1').galleryType, 'MI');
    assert.throws(() => dc.parsePostUrl('not a url'), { code: 'ARG' });
    assert.throws(() => dc.parsePostUrl('https://example.com/board/view/?id=a&no=1'), { code: 'ARG' });
    assert.throws(() => dc.parsePostUrl('https://gall.dcinside.com/board/lists/?id=a'), { code: 'ARG' });
    assert.throws(() => dc.parsePostUrl('https://gall.dcinside.com/board/view/?id=a&no=abc'), { code: 'ARG' });
});

test('jsRedirectTarget only fires on tiny redirect bodies', () => {
    assert.equal(dc.jsRedirectTarget(fixture('redirect-minor.html')).pathname, '/mgallery/board/lists');
    assert.equal(dc.jsRedirectTarget(`<html>${'x'.repeat(2000)}location.replace("/elsewhere")</html>`), null);
});

// ---------- HTML helpers ----------

test('htmlToText decodes entities, drops scripts, separates blocks', () => {
    assert.equal(dc.htmlToText('<p>a&amp;b</p><p>c&#39;d&#x41;</p><script>x()</script><b>e</b>f'), "a&b c'dA ef");
});

// ---------- parsers ----------

test('parseListHtml skips survey + notice rows and parses post rows', () => {
    const rows = dc.parseListHtml(fixture('list-general.html'));
    assert.equal(rows.length, 2);
    assert.deepEqual(rows[0], {
        rank: 1, postId: '40288', title: '이거 이즈미 IKS-6000 & 면도기 쓸만하냐?', author: 'ㅇㅡㅇ',
        publishedAt: '2026-09-27 17:38:15', commentCount: 0, viewCount: 23, recommendCount: 0,
        isNotice: false, url: 'https://gall.dcinside.com/board/view/?id=shaving&no=40288',
    });
    assert.equal(rows[1].commentCount, 21); // "[2/1]" -> digits only, same as the old DOM parser
    assert.equal(rows[1].viewCount, 1035);
});

test('parseListHtml includes notices on request', () => {
    const rows = dc.parseListHtml(fixture('list-general.html'), { includeNotices: true });
    assert.equal(rows[0].isNotice, true);
    assert.equal(rows[0].title, '면도 갤러리 이용 안내');
    assert.equal(rows[0].commentCount, 142);
});

test('parseListHtml keeps the minor-gallery path in row urls', () => {
    const [row] = dc.parseListHtml(fixture('list-minor.html'));
    assert.equal(row.url, 'https://gall.dcinside.com/mgallery/board/view/?id=laptop&no=2708715');
    assert.equal(row.commentCount, 2);
});

test('parseViewHtml reads header, body (balanced div, no script), tokens', () => {
    const view = dc.parseViewHtml(fixture('view-general.html'));
    assert.equal(view.title, '네보 vs 뉴갤주 "하루" 사용기');
    assert.equal(view.author, 'Ceja');
    assert.equal(view.publishedAt, '2026-08-27 17:24:58');
    assert.equal(view.views, 3014);
    assert.equal(view.recommendations, 14);
    assert.equal(view.content, '갤럼들이 궁금해 할만한 본론만 간다ㅇㅇ 1. 모터소음 & 파워 끝');
    assert.equal(view.esno, '0f317ce69463bdf3');
    assert.equal(view.gallType, 'G');
});

test('parseViewHtml returns null for non-post pages', () => {
    assert.equal(dc.parseViewHtml('<html><body>안내</body></html>'), null);
});

test('normalizeComment filters ads, deleted, empty and cleans memo HTML', () => {
    const { comments } = JSON.parse(fixture('comments.json'));
    const out = comments.map(dc.normalizeComment);
    assert.deepEqual(out[0], { commentId: '103919', type: 'COMMENT', parentId: null, author: '면갤러1', publishedAt: '08.27 17:47:07', content: '4중날이 6중날을 어찌이기노ㅋㅋ' });
    assert.equal(out[1].content, 'lv97급을 29만원주고 산다라..');
    assert.deepEqual([out[2].type, out[2].parentId, out[2].content], ['REPLY', '103924', '@ㅇㅇ(118.235) 97은 좀 내려치기지 <9u>']);
    assert.equal(out[3].content, '[디시콘: 쉿]');
    assert.equal(out[4], null); // del_yn Y
    assert.equal(out[5], null); // 댓글돌이 ad
    assert.equal(out[6], null); // blank
});

// ---------- transport + commands (stubbed fetch) ----------

test('listGallery follows the minor-gallery JS redirect and keeps the query', async () => {
    stubFetch([
        [(u) => u.startsWith('https://gall.dcinside.com/board/lists/'), { body: fixture('redirect-minor.html') }],
        [(u) => u.startsWith('https://gall.dcinside.com/mgallery/board/lists'), { body: fixture('list-minor.html') }],
    ]);
    const rows = await dc.listGallery('laptop', { search: '맥북', limit: 5 });
    assert.equal(rows.length, 1);
    assert.match(calls[1].url, /^https:\/\/gall\.dcinside\.com\/mgallery\/board\/lists\?id=laptop&page=1&s_type=search_subject_memo&s_keyword=/);
});

test('listGallery falls back to /mini/ on 404, then reports NOT_FOUND', async () => {
    stubFetch([
        [(u) => u.includes('/mini/'), { body: fixture('list-general.html') }],
        [() => true, { status: 404, body: 'nope' }],
    ]);
    assert.equal((await dc.listGallery('shaving')).length, 2);

    stubFetch([[() => true, { status: 404, body: 'nope' }]]);
    await assert.rejects(dc.listGallery('ghost'), { code: 'NOT_FOUND' });
});

test('listGallery reports EMPTY for zero rows and honours limit', async () => {
    stubFetch([[() => true, { body: '<table class="gall_list"><tbody></tbody></table>' }]]);
    await assert.rejects(dc.listGallery('shaving', { search: 'zz' }), { code: 'EMPTY', message: /for "zz"/ });
    stubFetch([[() => true, { body: fixture('list-general.html') }]]);
    assert.equal((await dc.listGallery('shaving', { limit: 1 })).length, 1);
});

test('request retries once on 5xx, then returns the second response', async () => {
    let n = 0;
    globalThis.fetch = async () => new Response('x', { status: n++ === 0 ? 503 : 200 });
    assert.equal((await dc.request('https://gall.dcinside.com/')).status, 200);
    assert.equal(n, 2);
});

test('request raises NETWORK after two thrown fetches', async () => {
    globalThis.fetch = async () => { throw new Error('ECONNRESET'); };
    await assert.rejects(dc.request('https://gall.dcinside.com/'), { code: 'NETWORK' });
});

test('getPage raises AUTH on a login redirect', async () => {
    stubFetch([[() => true, { status: 302, headers: { location: 'https://sign.dcinside.com/login' } }]]);
    await assert.rejects(dc.getPage('https://gall.dcinside.com/board/lists/?id=x'), { code: 'AUTH' });
});

test('readPost returns POST + cleaned comments with token + AJAX headers', async () => {
    stubFetch([
        [(u, i) => u.endsWith('/board/comment/') && i.method === 'POST', { body: fixture('comments.json') }],
        [(u) => u.includes('/board/view/'), { body: fixture('view-general.html') }],
    ]);
    const rows = await dc.readPost('https://gall.dcinside.com/board/view/?id=shaving&no=39837', { commentLimit: 3 });
    assert.deepEqual(rows.map((r) => r.type), ['POST', 'COMMENT', 'COMMENT', 'REPLY']);
    assert.equal(rows[0].url, 'https://gall.dcinside.com/board/view/?id=shaving&no=39837');
    assert.equal(rows[3].parentId, '103924');
    const post = calls.find((c) => c.init.method === 'POST');
    const body = new URLSearchParams(String(post.init.body));
    assert.equal(body.get('e_s_n_o'), '0f317ce69463bdf3');
    assert.equal(body.get('_GALLTYPE_'), 'G');
    assert.equal(post.init.headers['X-Requested-With'], 'XMLHttpRequest');
});

test('readPost pages comments until the limit and stops on a repeated page', async () => {
    stubFetch([
        [(u, i) => i.method === 'POST', { body: fixture('comments.json') }], // same page every time
        [() => true, { body: fixture('view-general.html') }],
    ]);
    const rows = await dc.readPost('https://gall.dcinside.com/board/view/?id=shaving&no=39837', { commentLimit: 50 });
    assert.equal(rows.length, 1 + 4);
    assert.equal(calls.filter((c) => c.init.method === 'POST').length, 2);
});

test('readPost skips the comment API when comment-limit is 0 and truncates content', async () => {
    stubFetch([[() => true, { body: fixture('view-general.html') }]]);
    const rows = await dc.readPost('https://gall.dcinside.com/board/view/?id=shaving&no=39837', { commentLimit: 0, contentLimit: 100 });
    assert.equal(rows.length, 1);
    assert.equal(calls.length, 1);
});

test('readPost maps missing posts to NOT_FOUND and non-JSON comments to BLOCKED', async () => {
    stubFetch([[() => true, { status: 404, body: 'gone' }]]);
    await assert.rejects(dc.readPost('https://gall.dcinside.com/board/view/?id=shaving&no=1'), { code: 'NOT_FOUND' });

    stubFetch([
        [(u, i) => i.method === 'POST', { body: '정상적인 접근이 아닙니다.' }],
        [() => true, { body: fixture('view-general.html') }],
    ]);
    await assert.rejects(dc.readPost('https://gall.dcinside.com/board/view/?id=shaving&no=39837'), { code: 'BLOCKED' });
});
```

- [ ] **Step 3: 실패 확인**

Run: `cd ~/.ai-skills/.claude/worktrees/ask-dc-https/ask-dc && node --test tests/http.test.mjs`
Expected: FAIL — `Cannot find module '.../adapter/http.js'`

- [ ] **Step 4: 구현** — `ask-dc/adapter/http.js`:
```js
// DCInside read backend over plain HTTPS. Imports nothing from OpenCLI so the
// standalone CLI (scripts/dc.mjs) runs without it; list.js/read.js wrap it.

export const DCINSIDE_ORIGIN = 'https://gall.dcinside.com';
const USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36';
const GALLERY_ID = /^[A-Za-z0-9_]{1,64}$/;
const PATH_PREFIX = { G: '', M: '/mgallery', MI: '/mini' };
const MAX_COMMENT_PAGES = 20;

// Mutable so tests can drop the delays to zero.
export const timing = { gapMs: 300, retryDelayMs: 1000 };

export class DcError extends Error {
    constructor(code, message) {
        super(message);
        this.name = 'DcError';
        this.code = code; // ARG | EMPTY | NOT_FOUND | AUTH | BLOCKED | NETWORK
    }
}

// ---------- validation & URLs ----------

export function requireGalleryId(value) {
    let galleryId = String(value ?? '').trim();
    if (galleryId === 'ibook') galleryId = 'macbook';
    if (!GALLERY_ID.test(galleryId)) {
        throw new DcError('ARG', 'galleryId must contain 1-64 letters, digits, or underscores');
    }
    return galleryId;
}

export function requireBoundedInteger(value, defaultValue, minimum, maximum, label) {
    const number = Number(value ?? defaultValue);
    if (!Number.isInteger(number)) throw new DcError('ARG', `${label} must be an integer`);
    if (number < minimum || number > maximum) {
        throw new DcError('ARG', `${label} must be between ${minimum} and ${maximum}`);
    }
    return number;
}

export function galleryTypeFromPath(pathname) {
    if (pathname.startsWith('/mgallery/')) return 'M';
    if (pathname.startsWith('/mini/')) return 'MI';
    return 'G';
}

export function listUrl(galleryId, galleryType, page, { head, recommend, sort, search, searchType } = {}) {
    const params = new URLSearchParams({ id: galleryId, page: String(page) });
    if (head) params.set('search_head', String(head));
    if (recommend) params.set('exception_mode', 'recommend');
    if (sort) params.set('sort_type', String(sort));
    if (search) {
        params.set('s_type', searchType ? String(searchType) : 'search_subject_memo');
        params.set('s_keyword', String(search));
    }
    return `${DCINSIDE_ORIGIN}${PATH_PREFIX[galleryType]}/board/lists/?${params}`;
}

export function viewUrl(galleryId, galleryType, postId) {
    return `${DCINSIDE_ORIGIN}${PATH_PREFIX[galleryType]}/board/view/?id=${encodeURIComponent(galleryId)}&no=${postId}`;
}

export function parsePostUrl(value) {
    let input;
    try {
        input = new URL(String(value ?? '').trim());
    } catch {
        throw new DcError('ARG', 'postUrl must be a complete DCInside post URL');
    }
    if (input.hostname !== 'gall.dcinside.com' || !/^\/(?:mgallery\/|mini\/)?board\/view\/?$/.test(input.pathname)) {
        throw new DcError('ARG', 'postUrl must be a gall.dcinside.com /board/view/ URL');
    }
    const galleryId = requireGalleryId(input.searchParams.get('id'));
    const postId = input.searchParams.get('no') ?? '';
    if (!/^[0-9]+$/.test(postId)) throw new DcError('ARG', 'postUrl must contain a numeric post number');
    return { galleryId, postId, galleryType: galleryTypeFromPath(input.pathname) };
}

export function isLoginUrl(url) {
    const isDcinsideHost = url.hostname === 'dcinside.com' || url.hostname.endsWith('.dcinside.com');
    const isLoginHost = url.hostname === 'login.dcinside.com' || url.hostname === 'sign.dcinside.com';
    return isDcinsideHost && (isLoginHost || /^\/(?:member\/)?login(?:\/|$)/i.test(url.pathname));
}

// ---------- HTML helpers ----------

const NAMED_ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };

export function decodeEntities(value) {
    return String(value).replace(/&(#x[0-9a-f]+|#[0-9]+|[a-z]+);/gi, (match, entity) => {
        if (entity[0] !== '#') return NAMED_ENTITIES[entity.toLowerCase()] ?? match;
        const codePoint = entity[1].toLowerCase() === 'x' ? parseInt(entity.slice(2), 16) : parseInt(entity.slice(1), 10);
        return Number.isFinite(codePoint) && codePoint <= 0x10ffff ? String.fromCodePoint(codePoint) : match;
    });
}

export function htmlToText(html) {
    return decodeEntities(String(html ?? '')
        .replace(/<(script|style)\b[\s\S]*?<\/\1\s*>/gi, ' ')
        .replace(/<(?:br|\/p|\/div|\/li|\/h[1-6])\b[^>]*>/gi, ' ')
        .replace(/<[^>]*>/g, ''))
        .replace(/\s+/g, ' ')
        .trim();
}

export function attr(tag, name) {
    const match = String(tag).match(new RegExp(`\\s${name}\\s*=\\s*(?:"([^"]*)"|'([^']*)')`, 'i'));
    return match ? decodeEntities(match[1] ?? match[2]) : null;
}

const integerOrNull = (value) => {
    const digits = String(value ?? '').replace(/[^0-9]/g, '');
    return digits ? Number(digits) : null;
};

const openingTag = (html) => html.slice(0, html.indexOf('>') + 1);

function cell(rowHtml, className) {
    const re = new RegExp(`<td\\b[^>]*\\sclass="(?:[^"]*\\s)?${className}(?:\\s[^"]*)?"[^>]*>([\\s\\S]*?)</td>`, 'i');
    const match = rowHtml.match(re);
    return match ? { tag: openingTag(match[0]), inner: match[1] } : null;
}

function balancedDiv(html, start) {
    const re = /<div\b|<\/div\s*>/gi;
    re.lastIndex = start;
    let depth = 0;
    let match;
    while ((match = re.exec(html))) {
        depth += match[0][1] === '/' ? -1 : 1;
        if (depth === 0) return html.slice(start, re.lastIndex);
    }
    return html.slice(start);
}

function hiddenInput(html, name) {
    for (const [tag] of html.matchAll(/<input\b[^>]*>/gi)) {
        if (attr(tag, 'name') === name || attr(tag, 'id') === name) return attr(tag, 'value');
    }
    return null;
}

export function jsRedirectTarget(body) {
    if (body.length > 1000) return null;
    const match = body.match(/location\.replace\(\s*["']([^"']+)["']\s*\)/);
    return match ? new URL(match[1], DCINSIDE_ORIGIN) : null;
}

// ---------- parsers ----------

export function parseListHtml(html, { includeNotices = false } = {}) {
    const rows = [];
    for (const [rowHtml] of html.matchAll(/<tr\b[^>]*\sclass="ub-content[^"]*"[^>]*>[\s\S]*?<\/tr>/gi)) {
        const title = cell(rowHtml, 'gall_tit');
        const anchor = title?.inner.match(/<a\b[^>]*\shref="([^"]*\/board\/view\/[^"]*)"[^>]*>([\s\S]*?)<\/a>/i);
        if (!anchor) continue;
        const href = new URL(decodeEntities(anchor[1]), DCINSIDE_ORIGIN);
        const postId = href.searchParams.get('no') ?? '';
        const galleryId = href.searchParams.get('id') ?? '';
        const isNotice = attr(openingTag(rowHtml), 'data-type') === 'icon_notice'
            || htmlToText(cell(rowHtml, 'gall_num')?.inner) === '공지';
        if (!/^[0-9]+$/.test(postId) || !galleryId || (!includeNotices && isNotice)) continue;

        const writer = cell(rowHtml, 'gall_writer');
        const date = cell(rowHtml, 'gall_date');
        const replyNum = title.inner.match(/<span class="reply_num">([^<]*)<\/span>/i);
        rows.push({
            rank: rows.length + 1,
            postId,
            title: htmlToText(anchor[2]),
            author: (writer && attr(writer.tag, 'data-nick')) ?? htmlToText(writer?.inner),
            publishedAt: (date && attr(date.tag, 'title')) ?? htmlToText(date?.inner),
            commentCount: integerOrNull(replyNum?.[1]) ?? 0,
            viewCount: integerOrNull(htmlToText(cell(rowHtml, 'gall_count')?.inner)),
            recommendCount: integerOrNull(htmlToText(cell(rowHtml, 'gall_recommend')?.inner)),
            isNotice,
            url: viewUrl(galleryId, galleryTypeFromPath(href.pathname), postId),
        });
    }
    return rows;
}

export function parseViewHtml(html) {
    const headStart = html.search(/<div\b[^>]*\sclass="gallview_head\b/i);
    if (headStart < 0) return null;
    const head = balancedDiv(html, headStart);
    const title = htmlToText(head.match(/<span class="title_subject">([\s\S]*?)<\/span>/i)?.[1]);
    if (!title) return null;
    const writerTag = head.match(/<div\b[^>]*\sclass="gall_writer\b[^"]*"[^>]*>/i)?.[0] ?? '';
    const bodyStart = html.search(/<div\b[^>]*\sclass="write_div\b/i);
    const recommendText = html.match(/id="recommend_view_up_[0-9]+"[^>]*>\s*([0-9,]+)/i)?.[1]
        ?? head.match(/<span class="gall_reply_num">([^<]*)<\/span>/i)?.[1];
    return {
        title,
        author: attr(writerTag, 'data-nick') ?? '',
        publishedAt: head.match(/<span class="gall_date" title="([^"]*)"/i)?.[1] ?? '',
        views: integerOrNull(head.match(/<span class="gall_count">([^<]*)<\/span>/i)?.[1]),
        recommendations: integerOrNull(recommendText),
        content: bodyStart < 0 ? '' : htmlToText(balancedDiv(html, bodyStart)),
        esno: hiddenInput(html, 'e_s_n_o'),
        gallType: hiddenInput(html, '_GALLTYPE_'),
    };
}

export function normalizeComment(raw) {
    if (!raw || raw.nicktype === 'COMMENT_BOY' || raw.del_yn === 'Y') return null;
    if (!/^[1-9][0-9]*$/.test(String(raw.no))) return null;
    const memo = String(raw.memo ?? '').replace(/<(?:img|video)\b[^>]*>/gi, (tag) => {
        const label = attr(tag, 'conalt') || attr(tag, 'alt') || attr(tag, 'title');
        return / class="[^"]*dccon/i.test(tag) || label ? ` [디시콘: ${label || '?'}] ` : ' ';
    });
    const content = htmlToText(memo).replace(/\s*-\s*dc App$/, '');
    if (!content) return null;
    const isReply = Number(raw.depth) > 0;
    return {
        commentId: String(raw.no),
        type: isReply ? 'REPLY' : 'COMMENT',
        parentId: isReply && raw.c_no ? String(raw.c_no) : null,
        author: String(raw.name ?? ''),
        publishedAt: String(raw.reg_date ?? ''),
        content,
    };
}

// ---------- transport ----------

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let lastRequestAt = 0;

export async function request(url, init = {}) {
    for (let attempt = 0; ; attempt += 1) {
        const wait = lastRequestAt + timing.gapMs - Date.now();
        if (wait > 0) await sleep(wait);
        lastRequestAt = Date.now();
        let response;
        try {
            response = await fetch(url, { redirect: 'manual', ...init, headers: { 'User-Agent': USER_AGENT, ...init.headers } });
        } catch (error) {
            if (attempt === 0) { await sleep(timing.retryDelayMs); continue; }
            throw new DcError('NETWORK', `Request failed for ${url}: ${error?.message ?? error}`);
        }
        if ((response.status === 429 || response.status >= 500) && attempt === 0) {
            await sleep(timing.retryDelayMs);
            continue;
        }
        return { status: response.status, location: response.headers.get('location'), body: await response.text() };
    }
}

// GET that follows HTTP redirects and DCInside's JS `location.replace` redirects.
// DCInside drops the query string on JS redirects, so keep ours and take only its path.
export async function getPage(url) {
    let target = new URL(url);
    for (let hop = 0; hop < 4; hop += 1) {
        const response = await request(target.href);
        let next = null;
        if (response.status >= 300 && response.status < 400 && response.location) {
            next = new URL(response.location, target);
        } else {
            const jsTarget = jsRedirectTarget(response.body);
            if (jsTarget) next = isLoginUrl(jsTarget) ? jsTarget : new URL(`${jsTarget.pathname}${target.search}`, DCINSIDE_ORIGIN);
        }
        if (!next) return { url: target, status: response.status, body: response.body };
        if (isLoginUrl(next)) throw new DcError('AUTH', `DCInside requires login for ${url}`);
        target = next;
    }
    throw new DcError('BLOCKED', `Too many redirects for ${url}`);
}

// Minor galleries JS-redirect from the general path, but mini galleries answer 404 there.
async function getGalleryPage(buildUrl, galleryType) {
    const response = await getPage(buildUrl(galleryType));
    if (response.status === 404 && galleryType === 'G') return getPage(buildUrl('MI'));
    return response;
}

export async function fetchCommentPage({ galleryId, postId, gallType, esno, referer, page }) {
    const body = new URLSearchParams({
        id: galleryId, no: postId, cmt_id: galleryId, cmt_no: postId,
        focus_cno: '', focus_pno: '', e_s_n_o: esno, comment_page: String(page),
        sort: '', prevCnt: '', board_type: '', _GALLTYPE_: gallType,
    });
    const response = await request(`${DCINSIDE_ORIGIN}/board/comment/`, {
        method: 'POST',
        body,
        headers: { 'X-Requested-With': 'XMLHttpRequest', Referer: referer },
    });
    try {
        return JSON.parse(response.body);
    } catch {
        throw new DcError('BLOCKED', `Comment API returned non-JSON (HTTP ${response.status}): ${response.body.slice(0, 80)}`);
    }
}

// ---------- commands ----------

export async function listGallery(galleryId, options = {}) {
    const id = requireGalleryId(galleryId);
    const page = requireBoundedInteger(options.page, 1, 1, 1000, 'page');
    const limit = requireBoundedInteger(options.limit, 20, 1, 50, 'limit');
    const response = await getGalleryPage((type) => listUrl(id, type, page, options), options.galleryType ?? 'G');
    if (response.status === 404) throw new DcError('NOT_FOUND', `Gallery "${id}" does not exist`);
    if (response.status !== 200) throw new DcError('BLOCKED', `Gallery list returned HTTP ${response.status}`);
    const rows = parseListHtml(response.body, { includeNotices: Boolean(options.includeNotices) });
    if (rows.length === 0) throw new DcError('EMPTY', `No posts in gallery "${id}" page ${page}${options.search ? ` for "${options.search}"` : ''}`);
    return rows.slice(0, limit);
}

export async function readPost(postUrl, options = {}) {
    const { galleryId, postId, galleryType } = parsePostUrl(postUrl);
    const commentLimit = requireBoundedInteger(options.commentLimit, 20, 0, 50, 'comment-limit');
    const contentLimit = requireBoundedInteger(options.contentLimit, 6000, 100, 10000, 'content-limit');
    const truncate = (value) => (value.length <= contentLimit ? value : `${value.slice(0, contentLimit - 1)}…`);

    const response = await getGalleryPage((type) => viewUrl(galleryId, type, postId), galleryType);
    const url = viewUrl(galleryId, galleryTypeFromPath(response.url.pathname), postId);
    const view = response.status === 200 ? parseViewHtml(response.body) : null;
    if (!view) throw new DcError('NOT_FOUND', `Post is unavailable or removed: ${url}`);

    const rows = [{
        type: 'POST', postId, parentId: null, author: view.author, publishedAt: view.publishedAt,
        title: view.title, content: truncate(view.content), views: view.views,
        recommendations: view.recommendations, url,
    }];
    if (commentLimit === 0) return rows;
    if (!view.esno) throw new DcError('BLOCKED', `Comment token (e_s_n_o) missing on ${url}`);

    const seen = new Set();
    for (let page = 1; page <= MAX_COMMENT_PAGES && rows.length - 1 < commentLimit; page += 1) {
        const data = await fetchCommentPage({
            galleryId, postId, gallType: view.gallType || galleryTypeFromPath(response.url.pathname),
            esno: view.esno, referer: url, page,
        });
        let added = 0;
        for (const raw of Array.isArray(data?.comments) ? data.comments : []) {
            const comment = normalizeComment(raw);
            if (!comment || seen.has(comment.commentId)) continue;
            seen.add(comment.commentId);
            added += 1;
            rows.push({
                type: comment.type, postId, parentId: comment.parentId, author: comment.author,
                publishedAt: comment.publishedAt, title: '', content: truncate(comment.content),
                views: null, recommendations: null, url,
            });
            if (rows.length - 1 >= commentLimit) break;
        }
        if (added === 0) break;
    }
    return rows;
}
```

- [ ] **Step 5: 통과 확인**

Run: `node --test tests/http.test.mjs`
Expected: `# pass 22`, `# fail 0`

- [ ] **Step 6: 커밋**
```bash
git add ask-dc/adapter/http.js ask-dc/tests/http.test.mjs ask-dc/tests/fixtures
git commit -m "feat(ask-dc): add dependency-free HTTPS core for DCInside list/read

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: 독립 CLI `scripts/dc.mjs`

**Files:**
- Create: `ask-dc/scripts/dc.mjs`
- Test: `ask-dc/tests/cli.test.mjs`

**Interfaces:**
- Consumes: `DcError`, `listGallery`, `readPost` from `../adapter/http.js` (Task 1)
- Produces: `node ask-dc/scripts/dc.mjs list|read ...` — stdout JSON 배열, stderr `{"error":{code,message}}`, 종료 코드 표(Global Constraints)

- [ ] **Step 1: 실패하는 테스트 작성** — `ask-dc/tests/cli.test.mjs`:
```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const CLI = fileURLToPath(new URL('../scripts/dc.mjs', import.meta.url));
const run = (...args) => spawnSync(process.execPath, [CLI, ...args], { encoding: 'utf8' });

for (const [label, args] of [
    ['no command', []],
    ['unknown command', ['write', 'x']],
    ['unknown option', ['list', 'shaving', '--bogus']],
    ['missing gallery', ['list']],
    ['limit out of range', ['list', 'shaving', '--limit', '99']],
    ['bad post url', ['read', 'https://example.com/']],
]) {
    test(`argument error exits 2: ${label}`, () => {
        const result = run(...args);
        assert.equal(result.status, 2, result.stderr);
        assert.equal(result.stdout, '');
        assert.equal(JSON.parse(result.stderr).error.code, 'ARG');
    });
}
```

- [ ] **Step 2: 실패 확인**

Run: `node --test tests/cli.test.mjs`
Expected: FAIL — status가 2가 아님 (스크립트 없음 → Node가 1로 종료)

- [ ] **Step 3: 구현** — `ask-dc/scripts/dc.mjs`:
```js
#!/usr/bin/env node
// Standalone DCInside reader for the ask-dc skill. Needs only Node 18+ (built-in fetch).
//   node dc.mjs list <galleryId> [--search K] [--recommend] [--page N] [--limit N] ...
//   node dc.mjs read <postUrl> [--comment-limit N] [--content-limit N]
// Prints a JSON array on stdout. On failure prints {"error":{code,message}} on stderr.
import { parseArgs } from 'node:util';
import { DcError, listGallery, readPost } from '../adapter/http.js';

const EXIT_CODES = { ARG: 2, EMPTY: 3, NOT_FOUND: 4, AUTH: 5, BLOCKED: 5, NETWORK: 1 };

const USAGE = `usage:
  dc.mjs list <galleryId> [--search <keyword>] [--search-type <type>] [--recommend]
                          [--page <1-1000>] [--limit <1-50>] [--head <id>] [--sort <type>]
                          [--include-notices] [--mgallery | --mini]
  dc.mjs read <postUrl> [--comment-limit <0-50>] [--content-limit <100-10000>]`;

const LIST_OPTIONS = {
    search: { type: 'string' },
    'search-type': { type: 'string' },
    recommend: { type: 'boolean' },
    page: { type: 'string' },
    limit: { type: 'string' },
    head: { type: 'string' },
    sort: { type: 'string' },
    'include-notices': { type: 'boolean' },
    mgallery: { type: 'boolean' },
    mini: { type: 'boolean' },
};

const READ_OPTIONS = {
    'comment-limit': { type: 'string' },
    'content-limit': { type: 'string' },
};

function parse(args, options) {
    const { values, positionals } = parseArgs({ args, options, allowPositionals: true, strict: true });
    if (positionals.length !== 1) throw new DcError('ARG', `expected exactly one positional argument\n${USAGE}`);
    return { values, target: positionals[0] };
}

async function run([command, ...args]) {
    if (command === 'list') {
        const { values, target } = parse(args, LIST_OPTIONS);
        return listGallery(target, {
            search: values.search,
            searchType: values['search-type'],
            recommend: values.recommend,
            page: values.page,
            limit: values.limit,
            head: values.head,
            sort: values.sort,
            includeNotices: values['include-notices'],
            galleryType: values.mgallery ? 'M' : values.mini ? 'MI' : undefined,
        });
    }
    if (command === 'read') {
        const { values, target } = parse(args, READ_OPTIONS);
        return readPost(target, {
            commentLimit: values['comment-limit'],
            contentLimit: values['content-limit'],
        });
    }
    throw new DcError('ARG', USAGE);
}

try {
    const rows = await run(process.argv.slice(2));
    process.stdout.write(`${JSON.stringify(rows, null, 2)}\n`);
} catch (error) {
    const code = error instanceof DcError ? error.code
        : String(error?.code ?? '').startsWith('ERR_PARSE_ARGS') ? 'ARG'
        : 'NETWORK';
    process.stderr.write(`${JSON.stringify({ error: { code, message: error?.message ?? String(error) } })}\n`);
    process.exitCode = EXIT_CODES[code] ?? 1;
}
```

- [ ] **Step 4: 통과 확인**

Run: `node --test tests/cli.test.mjs`
Expected: `# pass 6`

- [ ] **Step 5: 커밋**
```bash
git add ask-dc/scripts/dc.mjs ask-dc/tests/cli.test.mjs
git commit -m "feat(ask-dc): add standalone dc.mjs CLI over the HTTPS core

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: OpenCLI 래퍼를 HTTPS 코어로 전환

**Files:**
- Modify (전체 교체): `ask-dc/adapter/list.js`, `ask-dc/adapter/read.js`, `ask-dc/adapter/common.js`
- Delete: `ask-dc/adapter/parser.js` (브라우저 DOM 파서, 사용처 없어짐 — `write.js`는 import하지 않음)
- Modify (전체 교체): `ask-dc/tests/verify_setup.sh`
- Test: `ask-dc/tests/opencli.test.mjs`

**Interfaces:**
- Consumes: `listGallery`, `readPost`, `DcError`, `requireGalleryId`, `requireBoundedInteger`, `isLoginUrl`, `DCINSIDE_ORIGIN` from `./http.js`
- Produces: `common.js` exports `DCINSIDE_ORIGIN`, `toOpencliError(error, command?)`, `requireGalleryId`, `requireBoundedInteger` (OpenCLI `ArgumentError`를 던짐 — `write.js` 호환), `mainGalleryWriteUrl`, `navigateToDcinside` (write.js가 쓰는 시그니처 그대로). `mainGalleryListUrl`, `canonicalPostUrl`은 제거.

- [ ] **Step 1: worktree에 OpenCLI shim 연결** (gitignore 대상, 테스트 전용)
```bash
mkdir -p ask-dc/adapter/node_modules/@jackwener
ln -sfn "$(readlink ~/.ai-skills/ask-dc/adapter/node_modules/@jackwener/opencli)" ask-dc/adapter/node_modules/@jackwener/opencli
```

- [ ] **Step 2: 실패하는 테스트 작성** — `ask-dc/tests/opencli.test.mjs`:
```js
// Needs the OpenCLI ESM shim (adapter/node_modules/@jackwener/opencli, created by scripts/setup.sh).
import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { getRegistry } from '../adapter/node_modules/@jackwener/opencli/dist/src/registry.js';
import { timing } from '../adapter/http.js';
import '../adapter/list.js';
import '../adapter/read.js';

const fixture = (name) => readFileSync(new URL(`./fixtures/${name}`, import.meta.url), 'utf8');
const realFetch = globalThis.fetch;
timing.gapMs = 0;
timing.retryDelayMs = 0;
afterEach(() => { globalThis.fetch = realFetch; });

test('list and read register as browserless PUBLIC commands', () => {
    for (const name of ['dcinside/list', 'dcinside/read']) {
        const cmd = getRegistry().get(name);
        assert.ok(cmd, `${name} registered`);
        assert.equal(cmd.strategy, 'public');
        assert.equal(cmd.browser, false);
    }
});

test('list func returns rows from the HTTP core', async () => {
    globalThis.fetch = async () => new Response(fixture('list-general.html'));
    const rows = await getRegistry().get('dcinside/list').func({ galleryId: 'shaving', limit: 1 });
    assert.equal(rows.length, 1);
    assert.equal(rows[0].postId, '40288');
});

test('errors are mapped to OpenCLI error classes', async () => {
    globalThis.fetch = async () => new Response('<table class="gall_list"></table>');
    await assert.rejects(getRegistry().get('dcinside/list').func({ galleryId: 'shaving' }), { name: 'EmptyResultError' });
    await assert.rejects(getRegistry().get('dcinside/read').func({ postUrl: 'nope' }), { name: 'ArgumentError' });
});
```

- [ ] **Step 3: 실패 확인**

Run: `node --test tests/opencli.test.mjs`
Expected: FAIL — `strategy` 가 `'ui'` (기존 브라우저 래퍼)

- [ ] **Step 4: 구현** — `ask-dc/adapter/common.js`:
```js
import { ArgumentError, AuthRequiredError, CommandExecutionError, EmptyResultError } from '@jackwener/opencli/errors';
import * as http from './http.js';

export const DCINSIDE_ORIGIN = http.DCINSIDE_ORIGIN;

// Maps the transport-neutral DcError from http.js onto OpenCLI's error classes.
export function toOpencliError(error, command) {
    if (!(error instanceof http.DcError)) return error;
    switch (error.code) {
        case 'ARG': return new ArgumentError(error.message);
        case 'EMPTY': return new EmptyResultError(command, error.message);
        case 'AUTH': return new AuthRequiredError('gall.dcinside.com', error.message);
        default: return new CommandExecutionError(error.message);
    }
}

export function requireGalleryId(value) {
    try {
        return http.requireGalleryId(value);
    } catch (error) {
        throw toOpencliError(error);
    }
}

export function requireBoundedInteger(value, defaultValue, minimum, maximum, label) {
    try {
        return http.requireBoundedInteger(value, defaultValue, minimum, maximum, label);
    } catch (error) {
        throw toOpencliError(error);
    }
}

export function mainGalleryWriteUrl(galleryId, { isMinor = false } = {}) {
    const id = encodeURIComponent(requireGalleryId(galleryId));
    const prefix = isMinor ? '/mgallery/board/write/' : '/board/write/';
    return `${DCINSIDE_ORIGIN}${prefix}?id=${id}`;
}

export async function navigateToDcinside(page, url, label, { checkAuth = true } = {}) {
    try {
        await page.goto(url);
        await page.wait(2);
    } catch (error) {
        throw new CommandExecutionError(`${label} navigation failed: ${error?.message ?? error}`);
    }

    if (!checkAuth) return;

    let location;
    let hasLoginForm;
    try {
        location = await page.evaluate('window.location.href');
        hasLoginForm = await page.evaluate('Boolean(document.querySelector(\'form[action*="login" i], form#login_form, form[name*="login" i], form input[type="password"]\'))');
    } catch (error) {
        throw new CommandExecutionError(`${label} page inspection failed: ${error?.message ?? error}`);
    }
    let isLoginRedirect = false;
    try {
        isLoginRedirect = http.isLoginUrl(new URL(location));
    } catch {
        isLoginRedirect = false;
    }
    if (isLoginRedirect || hasLoginForm) {
        throw new AuthRequiredError('gall.dcinside.com', 'Log in manually in the connected Chrome profile, then retry');
    }
}
```

`ask-dc/adapter/list.js`:
```js
import { cli, Strategy } from '@jackwener/opencli/registry';
import { listGallery } from './http.js';
import { toOpencliError } from './common.js';

cli({
    site: 'dcinside',
    name: 'list',
    access: 'read',
    description: 'Read one page of a DCInside gallery (general, minor, or mini) over HTTPS',
    domain: 'gall.dcinside.com',
    strategy: Strategy.PUBLIC,
    browser: false,
    args: [
        { name: 'galleryId', type: 'string', required: true, positional: true, help: 'Gallery ID, for example programming' },
        { name: 'page', type: 'int', default: 1, help: 'Gallery page, 1-1000' },
        { name: 'limit', type: 'int', default: 20, help: 'Rows to return, 1-50' },
        { name: 'include-notices', type: 'bool', default: false, help: 'Include pinned notice rows' },
        { name: 'head', type: 'string', help: 'Head category filter ID (e.g. 70 for app)' },
        { name: 'recommend', type: 'bool', default: false, help: 'Show only recommend (concept) posts' },
        { name: 'sort', type: 'string', help: 'Sort type (e.g. N for new)' },
        { name: 'search', type: 'string', help: 'Search keyword' },
        { name: 'search-type', type: 'string', default: 'search_subject_memo', help: 'Search type (e.g. search_subject_memo, search_name)' },
        { name: 'mgallery', type: 'bool', default: false, help: 'Hint: minor gallery (auto-detected when omitted)' },
    ],
    columns: ['rank', 'postId', 'title', 'author', 'publishedAt', 'commentCount', 'viewCount', 'recommendCount', 'isNotice', 'url'],
    func: async (args) => {
        try {
            return await listGallery(args.galleryId, {
                page: args.page,
                limit: args.limit,
                includeNotices: Boolean(args['include-notices']),
                head: args.head,
                recommend: Boolean(args.recommend),
                sort: args.sort,
                search: args.search,
                searchType: args['search-type'],
                galleryType: args.mgallery ? 'M' : undefined,
            });
        } catch (error) {
            throw toOpencliError(error, 'dcinside list');
        }
    },
});
```

`ask-dc/adapter/read.js`:
```js
import { cli, Strategy } from '@jackwener/opencli/registry';
import { readPost } from './http.js';
import { toOpencliError } from './common.js';

cli({
    site: 'dcinside',
    name: 'read',
    access: 'read',
    description: 'Read one DCInside post with its comments and replies over HTTPS',
    domain: 'gall.dcinside.com',
    strategy: Strategy.PUBLIC,
    browser: false,
    args: [
        { name: 'postUrl', type: 'string', required: true, positional: true, help: 'Full DCInside post URL (/board/view/, /mgallery/board/view/, or /mini/board/view/)' },
        { name: 'comment-limit', type: 'int', default: 20, help: 'Comments and replies to return, 0-50' },
        { name: 'content-limit', type: 'int', default: 6000, help: 'Maximum characters per post or comment, 100-10000' },
    ],
    columns: ['type', 'postId', 'parentId', 'author', 'publishedAt', 'title', 'content', 'views', 'recommendations', 'url'],
    func: async (args) => {
        try {
            return await readPost(args.postUrl, {
                commentLimit: args['comment-limit'],
                contentLimit: args['content-limit'],
            });
        } catch (error) {
            throw toOpencliError(error, 'dcinside read');
        }
    },
});
```

```bash
git rm ask-dc/adapter/parser.js
```

`ask-dc/tests/verify_setup.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ADAPTER_DIR="${SKILL_DIR}/adapter"

echo "Running DCInside adapter verification tests..."

# Test 1: Check adapter and CLI files exist
for f in adapter/http.js adapter/common.js adapter/list.js adapter/read.js adapter/write.js scripts/dc.mjs; do
    if [ ! -f "${SKILL_DIR}/${f}" ]; then
        echo "FAIL: Missing file ${SKILL_DIR}/${f}" >&2
        exit 1
    fi
done
echo "PASS: Adapter and CLI files exist."

# Test 2: The HTTP core and standalone CLI must load without OpenCLI
node -e "
import('${ADAPTER_DIR}/http.js').then(() => {
    console.log('PASS: http.js loads without OpenCLI');
}).catch(err => {
    console.error('FAIL: http.js failed to load:', err);
    process.exit(1);
});
"
set +e
node "${SKILL_DIR}/scripts/dc.mjs" >/dev/null 2>&1
code=$?
set -e
if [ "$code" -ne 2 ]; then
    echo "FAIL: dc.mjs without arguments should exit 2 (usage), got ${code}" >&2
    exit 1
fi
echo "PASS: dc.mjs prints usage and exits 2."

# Test 3: Check OpenCLI subcommands (write-dc still depends on them)
output=$(opencli dcinside --help)
if echo "$output" | grep -q "list" && echo "$output" | grep -q "read" && echo "$output" | grep -q "write"; then
    echo "PASS: opencli dcinside exposes list, read, and write subcommands."
else
    echo "FAIL: Missing subcommands in opencli dcinside --help output" >&2
    exit 1
fi

echo "All tests passed successfully!"
```

- [ ] **Step 5: 통과 확인**

Run: `node --test tests/*.test.mjs && node -e "import('./adapter/write.js').then(()=>console.log('write.js loads'))"`
Expected: `# pass 31`, `write.js loads`

- [ ] **Step 6: 커밋**
```bash
git add -A ask-dc/adapter ask-dc/tests
git commit -m "refactor(ask-dc): run opencli dcinside list/read over HTTPS core

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: SKILL.md·어댑터 문서 갱신 + 실사이트 스모크

**Files:**
- Modify: `ask-dc/SKILL.md` (라인 13, 18, 섹션 0 전체(25-47), 75, 101-106, 114, 120, 129, 131)
- Modify: `ask-dc/adapter/docs/endpoints.json` (전체 교체), `ask-dc/adapter/docs/notes.md` (2026-09-27 항목 추가)
- Create: `ask-dc/tests/smoke.sh`

**Interfaces:**
- Consumes: `scripts/dc.mjs` (Task 2), opencli 래퍼 (Task 3)
- Produces: 에이전트가 따르는 명령 = `node <skill-dir>/scripts/dc.mjs list|read ...`

- [ ] **Step 1: 스모크 스크립트 작성** — `ask-dc/tests/smoke.sh` (`chmod +x`):
```bash
#!/usr/bin/env bash
# Live checks against gall.dcinside.com. Run manually; needs network.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DC=(node "${DIR}/scripts/dc.mjs")
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }
count() { node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>console.log(JSON.parse(s).length))'; }
field() { node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>console.log(JSON.parse(s)[Number(process.argv[1])][process.argv[2]]))' "$1" "$2"; }

n=$("${DC[@]}" list shaving --search 브라운 --recommend --limit 5 | count); [ "$n" -ge 1 ] && pass "general search+recommend ($n rows)" || fail "general search"
url=$("${DC[@]}" list laptop --limit 3 | field 0 url); [[ "$url" == *"/mgallery/board/view/"* ]] && pass "minor auto-detect ($url)" || fail "minor auto-detect: $url"
url=$("${DC[@]}" list soopstreaming --limit 3 | field 0 url); [[ "$url" == *"/mini/board/view/"* ]] && pass "mini auto-detect" || fail "mini auto-detect: $url"
n=$("${DC[@]}" read "https://gall.dcinside.com/board/view/?id=shaving&no=39837" --comment-limit 5 | count); [ "$n" -ge 2 ] && pass "read general with comments ($n rows)" || fail "read general"
big=$("${DC[@]}" list dcbest --limit 30 | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s).sort((a,b)=>b.commentCount-a.commentCount)[0];console.log(r.url)})')
n=$("${DC[@]}" read "$big" --comment-limit 50 | count); [ "$n" -ge 40 ] && pass "comment paging ($n rows from $big)" || fail "comment paging: $n rows"
set +e; "${DC[@]}" read "https://gall.dcinside.com/board/view/?id=shaving&no=99999999" >/dev/null 2>&1; code=$?; set -e
[ "$code" -eq 4 ] && pass "missing post exits 4" || fail "missing post exit $code"
set +e; "${DC[@]}" list shaving --search 존재하지않는검색어zzqx >/dev/null 2>&1; code=$?; set -e
[ "$code" -eq 3 ] && pass "zero results exits 3" || fail "zero results exit $code"
if command -v opencli >/dev/null 2>&1; then
  opencli dcinside list shaving --limit 2 -f yaml >/dev/null && pass "opencli dcinside list (browserless)" || fail "opencli list"
fi
echo "All smoke checks passed."
```

- [ ] **Step 2: 스모크 실행**

Run: `bash ask-dc/tests/smoke.sh`
Expected: 7개 `PASS:` + `All smoke checks passed.` (opencli 줄은 main 링크를 가리키므로 병합 후 Task 5에서 재확인)

- [ ] **Step 3: SKILL.md 패치** — 아래 두 파일을 scratchpad에 만든 뒤 실행 (`python3 patch_skill.py ask-dc/SKILL.md section0.md`). 스크립트는 각 치환이 정확히 1번 일어나는지 assert한다.

`section0.md` (섹션 0 전체를 대체):
```markdown
## 0. 실행 환경 (Setup)

본 스킬의 조회 기능은 Node.js 내장 `fetch`로 `gall.dcinside.com`에 HTTPS 요청을 보내는 독립 CLI(`scripts/dc.mjs`)로 동작합니다. 브라우저, Chrome 연결, OpenCLI 설치가 **필요 없습니다**.

- **요구 사항**: Node.js 18 이상 (`node -v`)
- **실행 경로**: 아래 명령의 `<skill-dir>`는 이 스킬의 Base directory입니다 (예: `~/.claude/skills/ask-dc`).
- **출력**: 성공 시 stdout에 JSON 배열. 실패 시 stderr에 `{"error":{"code","message"}}`를 출력하고 아래 종료 코드로 끝납니다.

| 종료 코드 | code | 의미 | 대응 |
| :--- | :--- | :--- | :--- |
| 0 | - | 성공 | - |
| 2 | `ARG` | 인자 오류 | 명령을 고쳐 다시 실행 |
| 3 | `EMPTY` | 결과 0건 | Step 3의 검색어 완화 / 일반 글 보조 수집 규칙 적용 |
| 4 | `NOT_FOUND` | 갤러리·게시글 없음(삭제 포함) | 갤러리 ID 재확인, 삭제된 글은 제외 |
| 5 | `AUTH` / `BLOCKED` | 로그인 필요 또는 비정상 응답 | 잠시 후 1회 재시도, 계속되면 해당 글 제외 |
| 1 | `NETWORK` | 네트워크 오류 | 1회 재시도 |

- **갤러리 유형 자동 판별**: 일반·마이너·미니 갤러리를 자동으로 판별합니다. `--mgallery` / `--mini`는 요청 1회를 아끼는 선택적 힌트입니다.
- `opencli dcinside list/read`도 같은 HTTPS 코어로 동작합니다(agent-reach 호환). 브라우저와 `scripts/setup.sh`가 필요한 것은 `write-dc`의 글쓰기(`opencli dcinside write`)뿐입니다.
- 동작 확인: `node --test <skill-dir>/tests/*.test.mjs` (오프라인), `bash <skill-dir>/tests/smoke.sh` (실제 사이트)

---
```

`patch_skill.py`:
```python
# Applies the ask-dc SKILL.md edits for the HTTPS backend. Usage: python3 patch_skill.py <SKILL.md> <section0.md>
import re, sys
path, section0_path = sys.argv[1], sys.argv[2]
s = open(path, encoding='utf-8').read()
section0 = open(section0_path, encoding='utf-8').read()

def sub(old, new, count=1):
    global s
    assert s.count(old) == count, f'expected {count}x: {old[:60]!r} (found {s.count(old)})'
    s = s.replace(old, new)

sub('디시인사이드 로컬 OpenCLI 어댑터(`opencli dcinside`)를 활용하여',
    '디시인사이드 HTTPS 수집기(`scripts/dc.mjs`)를 활용하여')
sub('2. **OpenCLI 어댑터 최우선 사용**: `opencli dcinside list <galleryId>` 및 `opencli dcinside read "<postUrl>"`을 기본 수집 도구로 사용합니다.',
    '2. **HTTPS 수집기 사용**: `node <skill-dir>/scripts/dc.mjs list <galleryId>` 및 `node <skill-dir>/scripts/dc.mjs read "<postUrl>"`을 기본 수집 도구로 사용합니다. 브라우저·OpenCLI가 필요 없습니다.')
s, n = re.subn(r'## 0\. 사전 점검 및 환경 설정 \(Setup & Self-Healing\)\n[\s\S]*?\n---\n', lambda _: section0, s, count=1)
assert n == 1, 'section 0 not found'
sub('-> **마이너 갤러리**이므로 `opencli dcinside list` 실행 시 반드시 `--mgallery` 플래그를 추가합니다.',
    '-> **마이너 갤러리**입니다. 자동 판별되므로 `--mgallery`는 선택 사항이지만, 알고 있으면 붙여 요청 1회를 아낍니다. (`/mini/` 경로는 미니 갤러리, `--mini`)')
sub('''# 일반 갤러리
opencli dcinside list <galleryId> --search "<키워드>" --limit 20 -f yaml

# 마이너 갤러리 (--mgallery 추가)
opencli dcinside list <galleryId> --search "<키워드>" --mgallery --limit 20 -f yaml''',
    '''# 일반·마이너·미니 모두 동일 (갤러리 유형 자동 판별, --mgallery/--mini는 선택 힌트)
node <skill-dir>/scripts/dc.mjs list <galleryId> --search "<키워드>" --limit 20''')
sub('opencli dcinside list <galleryId> --search "<키워드>" [--mgallery] --recommend --limit 20 -f yaml',
    'node <skill-dir>/scripts/dc.mjs list <galleryId> --search "<키워드>" --recommend --limit 20')
sub('    opencli dcinside list <galleryId> --search "<키워드>" [--mgallery] --limit 20 -f yaml',
    '    node <skill-dir>/scripts/dc.mjs list <galleryId> --search "<키워드>" --limit 20')
sub('opencli dcinside read "<postUrl>" --comment-limit 20 -f yaml',
    'node <skill-dir>/scripts/dc.mjs read "<postUrl>" --comment-limit 20')
sub('* **주의**: `opencli dcinside read`에는 반드시 전체 URL(`https://gall.dcinside.com/...`)을 전달해야 합니다.',
    '* **주의**: `read`에는 목록 결과의 `url` 필드(전체 URL `https://gall.dcinside.com/...`)를 그대로 전달합니다. 댓글이 50개를 넘는 글도 `--comment-limit`(최대 50)까지 자동으로 여러 페이지를 수집합니다.')
assert 'opencli dcinside list <' not in s and 'opencli dcinside read "' not in s, 'leftover opencli read commands'
open(path, 'w', encoding='utf-8').write(s)
print('patched', path)
```

- [ ] **Step 4: 어댑터 문서 갱신**

`ask-dc/adapter/docs/endpoints.json`:
```json
{
  "gallery-list": {
    "url": "https://gall.dcinside.com/{,mgallery/,mini/}board/lists/",
    "method": "GET",
    "params": {
      "required": [
        "id"
      ],
      "optional": [
        "page",
        "search_head",
        "exception_mode=recommend",
        "sort_type",
        "s_type",
        "s_keyword"
      ]
    },
    "response": "Server-rendered HTML; rows are <tr class=\"ub-content ...\"> inside .gall_list",
    "verified_at": "2026-09-27",
    "notes": "Minor galleries on the general path answer 200 with a tiny <script>location.replace(...)</script> that drops the query string; mini galleries answer 404 on the general path. Search scans only the newest block of posts (search_pos pages further back; not used)."
  },
  "gallery-post": {
    "url": "https://gall.dcinside.com/{,mgallery/,mini/}board/view/",
    "method": "GET",
    "params": {
      "required": [
        "id",
        "no"
      ],
      "optional": []
    },
    "response": "Server-rendered HTML: .gallview_head, .write_div, hidden inputs e_s_n_o and _GALLTYPE_ (G | M | MI). Comments are NOT in this HTML.",
    "verified_at": "2026-09-27",
    "notes": "Missing posts return 404."
  },
  "post-comments": {
    "url": "https://gall.dcinside.com/board/comment/",
    "method": "POST",
    "params": {
      "required": [
        "id",
        "no",
        "cmt_id",
        "cmt_no",
        "e_s_n_o",
        "comment_page",
        "_GALLTYPE_"
      ],
      "optional": [
        "sort",
        "focus_cno",
        "focus_pno",
        "prevCnt",
        "board_type"
      ]
    },
    "headers": [
      "X-Requested-With: XMLHttpRequest",
      "Referer: <view url>"
    ],
    "response": "JSON {total_cnt, comments:[{no, name, memo(html), reg_date, depth, c_no, nicktype, del_yn}], pagination}",
    "verified_at": "2026-09-27",
    "notes": "Same endpoint for all gallery types. Without e_s_n_o the body is '정상적인 접근이 아닙니다.'. The token is not post-bound. ~100 comments per page. Rows with nicktype COMMENT_BOY / no 0 are ads; del_yn Y are deleted."
  },
  "general-gallery-post-write": {
    "url": "https://gall.dcinside.com/board/write/",
    "method": "POST",
    "params": {
      "required": [
        "id",
        "title",
        "content"
      ],
      "optional": [
        "name",
        "password",
        "head",
        "mgallery",
        "no-submit",
        "wait-timeout"
      ]
    },
    "response": "Redirect to https://gall.dcinside.com/board/view/?id=...&no=...",
    "verified_at": "2026-09-07",
    "notes": "UI strategy with SmartEditor iframe/textarea injection, alert suppression, and CAPTCHA handling."
  }
}
```

`ask-dc/adapter/docs/notes.md` 끝에 추가:
```markdown
## 2026-09-27

- Strategy for `list`/`read` is now `PUBLIC` (`browser: false`): both are plain HTTPS requests handled by `adapter/http.js`, shared with the standalone CLI `scripts/dc.mjs`. `write` stays `UI`.
- List and post pages are server-rendered; comments come from `POST /board/comment/` (JSON) using the `e_s_n_o` and `_GALLTYPE_` hidden inputs from the post page. See `endpoints.json`.
- Gallery type detection: minor galleries JS-redirect (`location.replace`, query dropped) from the general path; mini galleries 404 there, so the core retries `/mini/` once on 404.
- Requests are sequential with a 300 ms gap and one retry on 429/5xx/network errors. 40 requests at 8-way concurrency all returned 200 during probing.
```

- [ ] **Step 5: 확인**

Run: `grep -n "opencli dcinside" ask-dc/SKILL.md`
Expected: 섹션 0의 호환 안내 한 줄(`opencli dcinside list/read`도 … / `opencli dcinside write`)만 남음.

- [ ] **Step 6: 커밋**
```bash
git add ask-dc/SKILL.md ask-dc/adapter/docs ask-dc/tests/smoke.sh
git commit -m "docs(ask-dc): switch skill workflow to dc.mjs HTTPS collector

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: main 병합 + 병합 후 검증

**Files:** 없음 (git 작업)

- [ ] **Step 1: 병합**
```bash
cd ~/.ai-skills
git status --short            # 비어 있어야 함
git merge --ff-only feat/ask-dc-https
```
Expected: fast-forward. (실패하면 main이 앞서간 것 → `git merge --no-ff feat/ask-dc-https`로 병합하고 충돌 확인)

- [ ] **Step 2: 병합 후 검증** (이제 `~/.opencli/clis/dcinside` 링크가 새 코드를 가리킴)
```bash
cd ~/.ai-skills/ask-dc
node --test tests/*.test.mjs
bash tests/verify_setup.sh
bash tests/smoke.sh
opencli dcinside read "https://gall.dcinside.com/board/view/?id=shaving&no=39837" --comment-limit 3 -f yaml
```
Expected: 31 pass, verify_setup 전부 PASS, smoke 8개 PASS(opencli 포함), 마지막 명령이 Chrome 없이 POST 1행 + 댓글 3행 출력.

- [ ] **Step 3: 정리**
```bash
git worktree remove .claude/worktrees/ask-dc-https --force   # node_modules shim 링크 때문에 --force
git branch -d feat/ask-dc-https
```
push는 하지 않는다 (N2).

---

## Appendix A. 설계 요약 (grill-yourself, 2026-09-27)

- 접근 B: 의존성 없는 HTTP 코어 1개를 독립 CLI와 OpenCLI 래퍼가 공유. (A: 기능 이중화, C: agent-reach의 `opencli dcinside list/read` 안내가 깨짐 — `agent-reach/references/social.md:113-115`)
- 목록·본문은 서버 렌더링 HTML, 댓글은 `POST /board/comment/` JSON (`e_s_n_o`, `_GALLTYPE_`, `X-Requested-With`, `Referer` 필요).
- 갤러리 유형: 마이너는 JS 리다이렉트(쿼리 소실), 미니는 일반 경로에서 404 → `/mini/` 재시도. 출력 URL은 실제 유형 경로.
- 댓글 필터: `COMMENT_BOY`/`no:0` 광고, `del_yn:Y` 삭제, 빈 내용 제거. 디시콘 → `[디시콘: 라벨]`, 멘션 → 텍스트, ` - dc App` 제거. `depth>0` → REPLY, `parentId = c_no`.
- 본문: `write_div` 균형 div 추출 → 스크립트 제거·엔티티 디코드·공백 병합(기존 결과와 동일한 형태).
- 제외: 검색 구간 확장(`search_pos`), 로그인 필요 갤러리 지원, write 경로, codex worktree 사본.
