// DCInside read backend over plain HTTPS. Imports nothing from OpenCLI so the
// standalone CLI (scripts/dc.mjs) runs without it; list.js/read.js wrap it.
import http from 'node:http';
import https from 'node:https';
import tls from 'node:tls';

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
            // "[12/3]" = comments / voice replies; only the first number is the comment count.
            commentCount: integerOrNull(replyNum?.[1].match(/[0-9][0-9,]*/)?.[0]) ?? 0,
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

// Built-in fetch ignores HTTPS_PROXY; behind a mandatory proxy (corporate networks,
// cloud sandboxes) it gets an empty 200. Tunnel through the proxy with CONNECT instead.
const nativeFetch = globalThis.fetch;

function proxyFor(url) {
    const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
    if (!proxy) return null;
    const noProxy = (process.env.NO_PROXY || process.env.no_proxy || '').split(',').map((s) => s.trim()).filter(Boolean);
    const host = url.hostname;
    if (noProxy.some((rule) => rule === '*' || host === rule.replace(/^\*?\./, '') || host.endsWith(rule.startsWith('.') ? rule : `.${rule.replace(/^\*\./, '')}`))) return null;
    return new URL(proxy);
}

// One-shot agent that hands https.request the already-tunneled socket.
function tunnelAgent(socket, servername) {
    const agent = new https.Agent({ keepAlive: false });
    agent.createConnection = () => tls.connect({ socket, servername, ALPNProtocols: ['http/1.1'] });
    return agent;
}

function proxiedRequest(url, proxy, { method = 'GET', body, headers = {} }) {
    return new Promise((resolve, reject) => {
        const auth = proxy.username ? { 'Proxy-Authorization': `Basic ${Buffer.from(`${decodeURIComponent(proxy.username)}:${decodeURIComponent(proxy.password)}`).toString('base64')}` } : {};
        const connect = http.request({ host: proxy.hostname, port: proxy.port || 80, method: 'CONNECT', path: `${url.hostname}:${url.port || 443}`, headers: auth });
        connect.on('error', reject);
        connect.on('connect', (res, socket) => {
            socket.on('error', reject);
            if (res.statusCode !== 200) { socket.destroy(); reject(new Error(`Proxy CONNECT returned HTTP ${res.statusCode}`)); return; }
            const payload = body === undefined ? undefined : String(body);
            const req = https.request(url, {
                method,
                headers: payload === undefined ? headers : { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'Content-Length': Buffer.byteLength(payload), ...headers },
                agent: tunnelAgent(socket, url.hostname),
            }, (response) => {
                const chunks = [];
                response.on('data', (chunk) => chunks.push(chunk));
                response.on('end', () => resolve({
                    status: response.statusCode,
                    location: response.headers.location ?? null,
                    body: Buffer.concat(chunks).toString('utf8'),
                }));
                response.on('error', reject);
            });
            req.on('error', reject);
            req.end(payload);
        });
        connect.end();
    });
}

// Tests stub globalThis.fetch; only take the proxy path when fetch is the real one.
async function send(url, init) {
    const target = new URL(url);
    const proxy = globalThis.fetch === nativeFetch ? proxyFor(target) : null;
    if (proxy) return proxiedRequest(target, proxy, init);
    const response = await fetch(url, { redirect: 'manual', ...init });
    return { status: response.status, location: response.headers.get('location'), body: await response.text() };
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let lastRequestAt = 0;

export async function request(url, init = {}) {
    for (let attempt = 0; ; attempt += 1) {
        const wait = lastRequestAt + timing.gapMs - Date.now();
        if (wait > 0) await sleep(wait);
        lastRequestAt = Date.now();
        let response;
        try {
            response = await send(url, { ...init, headers: { 'User-Agent': USER_AGENT, ...init.headers } });
        } catch (error) {
            if (attempt === 0) { await sleep(timing.retryDelayMs); continue; }
            throw new DcError('NETWORK', `Request failed for ${url}: ${error?.message ?? error}`);
        }
        if ((response.status === 429 || response.status >= 500) && attempt === 0) {
            await sleep(timing.retryDelayMs);
            continue;
        }
        // An empty 200 means something between us and DCInside swallowed the page.
        if (response.status === 200 && response.body.length === 0) {
            throw new DcError('BLOCKED', `Empty response from ${url} (check HTTPS_PROXY / network)`);
        }
        return response;
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
        if (!next) return { url: target, status: response.status, body: response.body, redirected: hop > 0 };
        if (isLoginUrl(next)) throw new DcError('AUTH', `DCInside requires login for ${url}`);
        target = next;
    }
    throw new DcError('BLOCKED', `Too many redirects for ${url}`);
}

// Minor galleries JS-redirect from the general path, but mini galleries answer 404 there.
// Only an un-redirected general-path 404 may be a mini gallery; if /mini/ also 404s,
// report the original response so errors name the path that was asked for.
async function getGalleryPage(buildUrl, galleryType) {
    const response = await getPage(buildUrl(galleryType));
    if (response.status !== 404 || galleryType !== 'G' || response.redirected) return response;
    const mini = await getPage(buildUrl('MI'));
    return mini.status === 404 ? response : mini;
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
        // Count unseen raw ids (deleted ones included) so a page of only deleted
        // comments does not end paging early; ads carry no id and never count.
        let fresh = 0;
        for (const raw of Array.isArray(data?.comments) ? data.comments : []) {
            const rawId = String(raw?.no ?? '');
            if (/^[1-9][0-9]*$/.test(rawId)) {
                if (seen.has(rawId)) continue;
                seen.add(rawId);
                fresh += 1;
            }
            const comment = normalizeComment(raw);
            if (!comment) continue;
            rows.push({
                type: comment.type, postId, parentId: comment.parentId, author: comment.author,
                publishedAt: comment.publishedAt, title: '', content: truncate(comment.content),
                views: null, recommendations: null, url,
            });
            if (rows.length - 1 >= commentLimit) break;
        }
        if (fresh === 0) break;
    }
    return rows;
}
