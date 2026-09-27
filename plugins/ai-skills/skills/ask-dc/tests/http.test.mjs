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
    assert.equal(rows[1].commentCount, 2); // "[2/1]" = 2 comments / 1 voice reply
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

test('readPost does not report a missing general post under /mini/', async () => {
    stubFetch([[() => true, { status: 404, body: 'gone' }]]);
    await assert.rejects(
        dc.readPost('https://gall.dcinside.com/board/view/?id=shaving&no=99999999'),
        { code: 'NOT_FOUND', message: /\/board\/view\/\?id=shaving&no=99999999$/ },
    );
    assert.deepEqual(calls.map((c) => new URL(c.url).pathname), ['/board/view/', '/mini/board/view/']);
});

test('readPost skips the /mini/ retry after a minor-gallery redirect 404s', async () => {
    stubFetch([
        [(u) => u.startsWith('https://gall.dcinside.com/board/view/'), { body: '<script>location.replace("https://gall.dcinside.com/mgallery/board/view?id=laptop&no=1");</script>' }],
        [() => true, { status: 404, body: 'gone' }],
    ]);
    await assert.rejects(dc.readPost('https://gall.dcinside.com/board/view/?id=laptop&no=1'), { code: 'NOT_FOUND', message: /\/mgallery\// });
    assert.equal(calls.length, 2);
});

test('readPost keeps paging past a page of only deleted comments and ads', async () => {
    const { comments } = JSON.parse(fixture('comments.json'));
    const page1 = { comments: comments.filter((c) => c.del_yn === 'Y' || c.nicktype === 'COMMENT_BOY') };
    const page2 = { comments: comments.slice(0, 2) };
    stubFetch([
        [(u, i) => i.method === 'POST' && String(i.body).includes('comment_page=1'), { body: JSON.stringify(page1) }],
        [(u, i) => i.method === 'POST' && String(i.body).includes('comment_page=2'), { body: JSON.stringify(page2) }],
        [(u, i) => i.method === 'POST', { body: JSON.stringify({ comments: [] }) }],
        [() => true, { body: fixture('view-general.html') }],
    ]);
    const rows = await dc.readPost('https://gall.dcinside.com/board/view/?id=shaving&no=39837', { commentLimit: 10 });
    assert.deepEqual(rows.slice(1).map((r) => r.author), ['면갤러1', 'ㅇㅇ']);
});
