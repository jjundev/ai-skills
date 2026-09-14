import {
    ArgumentError,
    AuthRequiredError,
    CommandExecutionError,
    EmptyResultError,
} from '@jackwener/opencli/errors';
import {
    normalizeAnalyticsData,
    normalizeContentItem,
    normalizeCourse,
    redactDeep,
    withRedactedErrors,
} from './parser.js';

export {
    ArgumentError,
    AuthRequiredError,
    CommandExecutionError,
    EmptyResultError,
    redactDeep,
    withRedactedErrors,
};

export const AJOU_BB_HOST = 'eclass2.ajou.ac.kr';
export const AJOU_BB_ORIGIN = `https://${AJOU_BB_HOST}`;
export const AJOU_BB_COURSE_URL = `${AJOU_BB_ORIGIN}/ultra/course`;
export const DEFAULT_TIMEOUT_MS = 15000;

/**
 * Validates and normalizes academic term strings (e.g. '2026-2', '2026-1', '2026-summer', '2026-winter').
 */
export function requireTerm(value) {
    if (value === undefined || value === null || value === '') return null;
    const raw = String(value).trim();
    if (!raw) return null;

    // Direct standard patterns
    const match = raw.match(/^(\d{4})\s*(?:년(?:도)?)?\s*[-_/\s.]?\s*(\d+|summer|winter|spring|fall|여름학기|겨울학기|1학기|2학기)$/i);
    if (!match) {
        throw new ArgumentError(
            `Invalid term format: "${value}". Expected format like "2026-1", "2026-2", "2026-summer", or "2026-winter".`,
        );
    }

    const year = match[1];
    let sem = match[2].toLowerCase();

    if (sem === '1' || sem === '1학기' || sem === 'spring') {
        return `${year}-1`;
    }
    if (sem === '2' || sem === '2학기' || sem === 'fall') {
        return `${year}-2`;
    }
    if (sem === 'summer' || sem === '여름학기') {
        return `${year}-summer`;
    }
    if (sem === 'winter' || sem === '겨울학기') {
        return `${year}-winter`;
    }

    throw new ArgumentError(
        `Invalid term semester: "${value}". Expected 1, 2, summer, or winter.`,
    );
}

/**
 * Validates that an option value is a strictly positive integer (> 0).
 */
export function requirePositiveInt(value, name) {
    if (value === undefined || value === null || value === '') return null;
    const num = Number(value);
    if (!Number.isInteger(num) || num <= 0) {
        throw new ArgumentError(`--${name} must be a positive integer, got "${value}"`);
    }
    return num;
}

/**
 * Inspects page DOM to confirm that the user has an active authenticated Blackboard Ultra session.
 */
export async function requireAuthenticatedSession(page) {
    const script = `(() => { /* __AJOU_BB_AUTH_CHECK__ */
        const href = location.href || '';
        const hostname = location.hostname || '';
        const pathname = location.pathname || '';
        const isLoginPage = pathname.includes('/webapps/login')
            || pathname.includes('/login')
            || Boolean(document.querySelector('#login-page, #loginForm, input[name="user_id"], input[type="password"]'));
        const hasUltraApp = Boolean(document.querySelector('bb-base, ultra-root, #main-content, #main-heading, [role="navigation"], .base-navigation'));
        const hasUserMenu = Boolean(document.querySelector('#user-menu, [aria-label*="User Menu"], [aria-label*="사용자 메뉴"], button.avatar-button, .user-avatar, #global-nav-link'));
        return {
            href,
            hostname,
            pathname,
            isLoginPage,
            hasUltraApp,
            hasUserMenu,
        };
    })()`;

    let meta;
    try {
        meta = await page.evaluate(script);
    } catch (error) {
        throw new CommandExecutionError(`Failed to inspect Blackboard Ultra page state: ${error?.message ?? error}`);
    }

    if (!meta) {
        throw new CommandExecutionError('Failed to inspect Blackboard Ultra page state');
    }

    let hostname = meta.hostname;
    if (!hostname && meta.href) {
        try {
            hostname = new URL(meta.href).hostname;
        } catch {
            hostname = '';
        }
    }

    if (hostname && hostname !== AJOU_BB_HOST) {
        throw new AuthRequiredError(
            AJOU_BB_HOST,
            `Connected browser tab is at "${hostname}" instead of "${AJOU_BB_HOST}". Please log in manually at ${AJOU_BB_COURSE_URL} and retry.`,
        );
    }

    if (meta.isLoginPage || (!meta.hasUltraApp && !meta.hasUserMenu && String(meta.pathname || '').includes('/login'))) {
        throw new AuthRequiredError(
            AJOU_BB_HOST,
            'Blackboard Ultra session is not authenticated. Please log in manually in Chrome, then retry.',
        );
    }

    return { authenticated: true, href: meta.href };
}

/**
 * Navigates to Blackboard Ultra home/course view and asserts active authentication.
 */
export async function navigateHome(page) {
    try {
        if (typeof page.goto === 'function') {
            await page.goto(AJOU_BB_COURSE_URL, { waitUntil: 'load', settleMs: 1200 });
        }
        if (typeof page.wait === 'function') {
            await page.wait(0.5);
        }
    } catch (error) {
        if (error instanceof AuthRequiredError) throw error;
        throw new CommandExecutionError(`Navigation to Blackboard Ultra failed: ${error?.message ?? error}`);
    }
    return requireAuthenticatedSession(page);
}

/**
 * Builds the in-page JavaScript string to execute a same-origin fetch with active cookies.
 */
export function buildBbFetchScript(endpoint, options = {}) {
    return `(async () => { /* __AJOU_BB_FETCH__ */
        try {
            const rawEndpoint = ${JSON.stringify(endpoint)};
            const reqOptions = ${JSON.stringify(options)};
            const baseOrigin = 'https://eclass2.ajou.ac.kr';
            let url = rawEndpoint;
            if (!rawEndpoint.startsWith('http://') && !rawEndpoint.startsWith('https://')) {
                const currentOrigin = (typeof location !== 'undefined' && location.origin && location.origin !== 'null' && location.origin.startsWith('http'))
                    ? location.origin
                    : baseOrigin;
                url = new URL(rawEndpoint, currentOrigin).href;
            }
            const headers = {
                'Accept': 'application/json, text/plain, */*',
                ...(reqOptions.headers || {}),
            };
            if (reqOptions.body && typeof reqOptions.body === 'object' && !headers['Content-Type']) {
                headers['Content-Type'] = 'application/json';
            }
            const fetchOptions = {
                method: (reqOptions.method || 'GET').toUpperCase(),
                headers,
                credentials: 'include',
                cache: reqOptions.cache || 'no-cache',
            };
            if (reqOptions.body) {
                fetchOptions.body = typeof reqOptions.body === 'string'
                    ? reqOptions.body
                    : JSON.stringify(reqOptions.body);
            }

            const response = await fetch(url, fetchOptions);
            const status = response.status;
            const statusText = response.statusText;

            if (status === 401 || status === 403) {
                return { __status: status, __error: 'auth', __statusText: statusText };
            }

            let parsedBody = null;
            const text = await response.text();
            if (text && text.trim()) {
                try {
                    parsedBody = JSON.parse(text);
                } catch (parseErr) {
                    parsedBody = text;
                }
            }

            if (!response.ok) {
                let errorMsg = 'HTTP ' + status;
                if (parsedBody && typeof parsedBody === 'object') {
                    errorMsg = parsedBody.message
                        || parsedBody.error
                        || parsedBody.developerMessage
                        || parsedBody.error_description
                        || JSON.stringify(parsedBody);
                } else if (typeof parsedBody === 'string' && parsedBody.trim()) {
                    errorMsg = parsedBody.slice(0, 300);
                }
                return { __status: status, __error: errorMsg, __statusText: statusText };
            }

            return { __status: status, __data: parsedBody };
        } catch (err) {
            return { __status: null, __error: err?.message || String(err) };
        }
    })()`;
}

/**
 * Executes a session-authenticated REST fetch inside page.evaluate().
 */
export async function fetchBbRest(page, endpoint, options = {}) {
    if (page && typeof page.evaluate === 'function') {
        const currentHost = await page.evaluate('location.hostname || ""').catch(() => '');
        if (currentHost !== AJOU_BB_HOST && typeof page.goto === 'function') {
            await navigateHome(page);
        }
    }

    let fullEndpoint = endpoint;
    if (options.params && typeof options.params === 'object') {
        const searchParams = new URLSearchParams();
        for (const [k, v] of Object.entries(options.params)) {
            if (v !== undefined && v !== null) {
                searchParams.set(k, String(v));
            }
        }
        const queryString = searchParams.toString();
        if (queryString) {
            fullEndpoint += (fullEndpoint.includes('?') ? '&' : '?') + queryString;
        }
    }

    const script = buildBbFetchScript(fullEndpoint, options);
    let result;
    try {
        result = await page.evaluate(script);
    } catch (error) {
        throw new CommandExecutionError(`Failed to execute in-page fetch for ${endpoint}: ${error?.message ?? error}`);
    }

    if (!result) {
        throw new CommandExecutionError(`Failed to receive response for endpoint: ${endpoint}`);
    }

    if (result.__status === 401 || result.__status === 403 || result.__error === 'auth') {
        throw new AuthRequiredError(
            AJOU_BB_HOST,
            `Blackboard Ultra session expired or unauthorized (HTTP ${result.__status ?? '401/403'}). Please log in again in Chrome.`,
        );
    }

    if (result.__error) {
        throw new CommandExecutionError(
            `Blackboard REST API error (${endpoint}): ${result.__error}`,
        );
    }

    return result.__data;
}

/**
 * Builds the in-page JavaScript string to execute an authenticated fetch for a binary URL
 * and converts ArrayBuffer into a Base64 string.
 */
export function buildBbBinaryFetchScript(fileUrl) {
    return `(async () => { /* __AJOU_BB_BINARY_FETCH__ */
        let url = ${JSON.stringify(fileUrl)};
        const baseOrigin = 'https://eclass2.ajou.ac.kr';
        try {
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                const currentOrigin = (typeof location !== 'undefined' && location.origin && location.origin !== 'null' && location.origin.startsWith('http'))
                    ? location.origin
                    : baseOrigin;
                url = new URL(url, currentOrigin).href;
            }

            const fetchBinary = async (targetUrl) => {
                const response = await fetch(targetUrl, {
                    method: 'GET',
                    credentials: 'include',
                });
                if (response.status === 401 || response.status === 403) {
                    return { __status: response.status, __error: 'auth', __statusText: response.statusText };
                }
                if (!response.ok) {
                    return { __status: response.status, __error: 'HTTP ' + response.status + ' (' + response.statusText + ')' };
                }
                const ab = await response.arrayBuffer();
                return { __status: response.status, __arrayBuffer: ab };
            };

            const getBufferViaXhr = (targetUrl) => new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open('GET', targetUrl, true);
                xhr.responseType = 'arraybuffer';
                xhr.withCredentials = true;
                xhr.onload = () => {
                    if (xhr.status === 401 || xhr.status === 403) {
                        resolve({ __status: xhr.status, __error: 'auth', __statusText: xhr.statusText });
                    } else if (xhr.status >= 200 && xhr.status < 300) {
                        resolve({ __status: xhr.status, __arrayBuffer: xhr.response });
                    } else {
                        resolve({ __status: xhr.status, __error: 'HTTP ' + xhr.status + ' (' + xhr.statusText + ')' });
                    }
                };
                xhr.onerror = (e) => reject(new Error('XHR error: ' + (xhr.statusText || 'failed')));
                xhr.send();
            });

            let res = null;
            let lastErr = null;

            // Try 1: fetch with credentials
            try {
                res = await fetchBinary(url);
            } catch (err1) {
                lastErr = err1;
            }

            // Try 2: XHR if fetch failed
            if (!res || res.__error) {
                try {
                    const xhrRes = await getBufferViaXhr(url);
                    if (xhrRes && !xhrRes.__error) res = xhrRes;
                } catch (err2) {
                    lastErr = err2;
                }
            }

            if (!res || !res.__arrayBuffer) {
                return {
                    __status: res?.__status ?? null,
                    __error: (res?.__error || lastErr?.message || 'Download failed') + ' [URL: ' + url + ', Loc: ' + (typeof location !== 'undefined' ? location.href : 'none') + ']',
                };
            }

            const bytes = new Uint8Array(res.__arrayBuffer);
            const sizeBytes = bytes.byteLength;
            let binary = '';
            const chunkSize = 8192;
            for (let i = 0; i < bytes.length; i += chunkSize) {
                const chunk = bytes.subarray(i, i + chunkSize);
                binary += String.fromCharCode.apply(null, chunk);
            }
            const base64 = btoa(binary);

            return {
                __status: res.__status || 200,
                __base64: base64,
                __sizeBytes: sizeBytes,
            };
        } catch (err) {
            return {
                __status: null,
                __error: (err?.name || 'Error') + ': ' + (err?.message || String(err)) + ' [URL: ' + url + ']',
            };
        }
    })()`;
}

/**
 * Executes a session-authenticated binary fetch inside page.evaluate() or via session cookies and returns a Node.js Buffer.
 */
export async function fetchBbBinary(page, fileUrl) {
    if (!fileUrl || typeof fileUrl !== 'string' || !fileUrl.trim()) {
        throw new ArgumentError('File URL is required');
    }

    const cleanUrl = fileUrl.trim();
    const fullUrl = cleanUrl.startsWith('http://') || cleanUrl.startsWith('https://')
        ? cleanUrl
        : ('https://' + AJOU_BB_HOST + (cleanUrl.startsWith('/') ? '' : '/') + cleanUrl);

    // Strategy 1: Ultra redirect resolver (navigates browser to resolve S3/Xythos presigned direct download link)
    if (page && fullUrl.includes('/ultra/redirect') && typeof page.goto === 'function') {
        try {
            await page.goto(fullUrl, { waitUntil: 'domcontentloaded', timeout: DEFAULT_TIMEOUT_MS });
            let finalUrl = await page.evaluate('location.href').catch(() => '');
            for (let i = 0; i < 10 && (!finalUrl || finalUrl.includes('/ultra/redirect')); i++) {
                await new Promise((r) => setTimeout(r, 400));
                finalUrl = await page.evaluate('location.href').catch(() => '');
            }
            if (finalUrl && (finalUrl.includes('files.blackboard.com') || finalUrl.includes('bbcswebdav') || finalUrl.includes('X-Amz-Signature'))) {
                const s3Resp = await fetch(finalUrl, { redirect: 'follow' });
                if (s3Resp.ok) {
                    const ab = await s3Resp.arrayBuffer();
                    if (ab && ab.byteLength > 0) {
                        return Buffer.from(ab);
                    }
                }
            }
        } catch {
            // Fall through to session fetch
        }
    }

    // Strategy 2: Session-cookie authenticated fetch via Node.js (bypasses in-page CSP locks)
    if (page) {
        try {
            let cookieHeader = '';
            if (typeof page.getCookies === 'function') {
                const cookies = await page.getCookies({ url: 'https://' + AJOU_BB_HOST }).catch(() => []);
                if (Array.isArray(cookies) && cookies.length > 0) {
                    cookieHeader = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
                }
            } else if (typeof page.cookies === 'function') {
                const cookies = await page.cookies('https://' + AJOU_BB_HOST).catch(() => []);
                if (Array.isArray(cookies) && cookies.length > 0) {
                    cookieHeader = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
                }
            }
            if (!cookieHeader && typeof page.evaluate === 'function') {
                const docCookie = await page.evaluate('document.cookie || ""').catch(() => '');
                if (typeof docCookie === 'string' && docCookie.trim()) {
                    cookieHeader = docCookie.trim();
                }
            }

            if (typeof cookieHeader === 'string' && cookieHeader.trim().length > 0) {
                const userAgent = typeof page.evaluate === 'function'
                    ? await page.evaluate('navigator.userAgent').catch(() => '')
                    : 'Mozilla/5.0';

                const headers = {
                    'User-Agent': userAgent || 'Mozilla/5.0',
                    'Referer': AJOU_BB_COURSE_URL,
                    'Accept': '*/*',
                    'Cookie': cookieHeader,
                };

                const nodeResp = await fetch(fullUrl, {
                    headers,
                    redirect: 'follow',
                });

                if (nodeResp.status === 401 || nodeResp.status === 403) {
                    throw new AuthRequiredError(
                        AJOU_BB_HOST,
                        `Blackboard Ultra session expired or unauthorized (HTTP ${nodeResp.status}). Please log in again in Chrome.`,
                    );
                }

                if (nodeResp.ok) {
                    const contentType = nodeResp.headers.get('content-type') || '';
                    const ab = await nodeResp.arrayBuffer();
                    const isHtml = contentType.includes('text/html') || (ab.byteLength > 0 && /<!doctype|<html/i.test(Buffer.from(ab.slice(0, 256)).toString('utf8')));
                    if (ab && ab.byteLength > 0 && !isHtml) {
                        return Buffer.from(ab);
                    }
                }
            }
        } catch (nodeErr) {
            if (nodeErr instanceof AuthRequiredError) throw nodeErr;
            // Fall through to in-page strategies
        }
    }

    // Strategy 2: in-page fetch / XHR script execution
    const script = buildBbBinaryFetchScript(cleanUrl);
    let result = null;
    try {
        result = await page.evaluate(script);
    } catch {
        result = null;
    }

    if (result && typeof result.__base64 === 'string' && !result.__error) {
        return Buffer.from(result.__base64, 'base64');
    }

    // Strategy 3: Direct browser navigation with native response buffer extraction
    if (page && typeof page.goto === 'function') {
        try {
            const resp = await page.goto(cleanUrl, { waitUntil: 'domcontentloaded', timeout: DEFAULT_TIMEOUT_MS });
            if (resp && typeof resp.buffer === 'function') {
                const buf = await resp.buffer();
                if (buf && buf.length > 0) return buf;
            }
            if (resp && typeof resp.body === 'function') {
                const buf = await resp.body();
                if (buf && buf.length > 0) return Buffer.from(buf);
            }
            const inDocResult = await page.evaluate(script);
            if (inDocResult && typeof inDocResult.__base64 === 'string' && !inDocResult.__error) {
                return Buffer.from(inDocResult.__base64, 'base64');
            }
        } catch {
            // Fall through to error
        }
    }

    if (result && (result.__status === 401 || result.__status === 403 || result.__error === 'auth')) {
        throw new AuthRequiredError(
            AJOU_BB_HOST,
            `Blackboard Ultra session expired or unauthorized (HTTP ${result.__status ?? '401/403'}). Please log in again in Chrome.`,
        );
    }

    throw new CommandExecutionError(
        `Blackboard binary download error (${cleanUrl}): ${result?.__error || 'Download failed'}`,
    );
}

/**
 * Resolves a query against a list of CourseRecord objects using exact ID, code, and fuzzy name matching.
 */
export function findMatchingCourse(courses, query) {
    if (!Array.isArray(courses) || courses.length === 0) return null;
    if (!query || typeof query !== 'string') return null;

    const cleanQuery = query.trim();
    if (!cleanQuery) return null;
    const lowerQuery = cleanQuery.toLowerCase();

    // 1. Exact course_id match
    const exactIdMatch = courses.find(
        (c) => c.course_id === cleanQuery || c.id === cleanQuery,
    );
    if (exactIdMatch) return exactIdMatch;

    // 2. Exact course_code match (case-insensitive)
    const exactCodeMatches = courses.filter(
        (c) => c.course_code && c.course_code.toLowerCase() === lowerQuery,
    );
    if (exactCodeMatches.length === 1) return exactCodeMatches[0];
    if (exactCodeMatches.length > 1) {
        const list = exactCodeMatches.map((c) => `${c.course_name} (${c.course_id})`).join(', ');
        throw new CommandExecutionError(
            `Multiple courses found matching course code "${cleanQuery}": ${list}. Please specify an exact course_id.`,
        );
    }

    // 3. Substring match on course_name (case-insensitive)
    const nameMatches = courses.filter(
        (c) => c.course_name && c.course_name.toLowerCase().includes(lowerQuery),
    );
    if (nameMatches.length === 1) return nameMatches[0];
    if (nameMatches.length > 1) {
        const list = nameMatches.map((c) => `${c.course_name} (${c.course_id})`).join(', ');
        throw new CommandExecutionError(
            `Multiple courses found matching "${cleanQuery}": ${list}. Please specify a more specific name, course_code, or exact course_id.`,
        );
    }

    // 4. Substring match on course_code (case-insensitive)
    const codeSubMatches = courses.filter(
        (c) => c.course_code && c.course_code.toLowerCase().includes(lowerQuery),
    );
    if (codeSubMatches.length === 1) return codeSubMatches[0];
    if (codeSubMatches.length > 1) {
        const list = codeSubMatches.map((c) => `${c.course_name} (${c.course_id})`).join(', ');
        throw new CommandExecutionError(
            `Multiple courses found matching "${cleanQuery}": ${list}. Please specify an exact course_id.`,
        );
    }

    return null;
}

/**
 * Retrieves and normalizes the user's courses list from Blackboard REST API.
 */
export async function fetchUserCourses(page, options = {}) {
    let rawData;
    try {
        rawData = await fetchBbRest(page, '/learn/api/public/v1/users/me/courses', {
            params: { expand: 'course', limit: 100 },
            ...options,
        });
    } catch (err) {
        // Fallback to /learn/api/public/v1/courses if user-specific endpoint differs
        rawData = await fetchBbRest(page, '/learn/api/public/v1/courses', {
            params: { limit: 100 },
            ...options,
        });
    }

    const rawList = Array.isArray(rawData)
        ? rawData
        : (Array.isArray(rawData?.results) ? rawData.results : []);

    let courses = rawList.map((item) => normalizeCourse(item.course || item, item));

    if (options.term) {
        const termFilter = String(options.term).trim().toLowerCase();
        courses = courses.filter(
            (c) => (c.term_id && String(c.term_id).toLowerCase().includes(termFilter))
                || (c.term_name && String(c.term_name).toLowerCase().includes(termFilter))
                || (c.course_code && String(c.course_code).toLowerCase().includes(termFilter))
                || (c.course_name && String(c.course_name).toLowerCase().includes(termFilter)),
        );
    }

    if (options.includeInactive !== true && options.all !== true) {
        courses = courses.filter((c) => c.is_active !== false);
    }

    return courses;
}

/**
 * Resolves a user-provided string to a single CourseRecord or throws a descriptive error.
 */
export async function resolveCourseId(page, courseQuery, options = {}) {
    if (!courseQuery || typeof courseQuery !== 'string' || !courseQuery.trim()) {
        throw new ArgumentError('Course query/ID is required');
    }

    const cleanQuery = courseQuery.trim();
    const courses = await fetchUserCourses(page, { includeInactive: true, ...options });
    const match = findMatchingCourse(courses, cleanQuery);

    if (!match) {
        throw new CommandExecutionError(
            `No course found matching "${cleanQuery}". Run \`opencli ajou-bb courses\` to see all available courses.`,
        );
    }

    return match;
}

/**
 * Recursively fetches course content hierarchy up to maxDepth.
 */
export async function fetchContentHierarchy(page, courseId, parentId = null, currentDepth = 1, maxDepth = 2) {
    const endpoint = parentId
        ? `/learn/api/public/v1/courses/${courseId}/contents/${parentId}/children`
        : `/learn/api/public/v1/courses/${courseId}/contents`;

    const rawData = await fetchBbRest(page, endpoint, {
        params: { limit: 100 },
    });

    const rawList = Array.isArray(rawData)
        ? rawData
        : (Array.isArray(rawData?.results) ? rawData.results : []);

    const items = rawList.map(normalizeContentItem);

    if (currentDepth < maxDepth) {
        for (const item of items) {
            const shouldTraverse = item.content_type === 'folder'
                || item.has_children
                || (!item.file_url && (item.content_type === 'document' || item.content_type === 'file'));

            if (shouldTraverse) {
                try {
                    const children = await fetchContentHierarchy(
                        page,
                        courseId,
                        item.content_id,
                        currentDepth + 1,
                        maxDepth,
                    );
                    if (children && children.length > 0) {
                        item.children = children;
                    }
                } catch {
                    // Ignore errors for individual subfolder traversal
                }
            }

            // If item is a file/document but missing file_url, query single item details or set launchFile.jsp
            if (!item.file_url && (item.content_type === 'file' || item.content_type === 'document' || Boolean(item.file_name))) {
                try {
                    const singleData = await fetchBbRest(
                        page,
                        `/learn/api/public/v1/courses/${courseId}/contents/${item.content_id}`,
                    );
                    const normalized = normalizeContentItem(singleData);
                    if (normalized.file_url) item.file_url = normalized.file_url;
                    if (normalized.file_name) item.file_name = normalized.file_name;
                    if (normalized.description) item.description = normalized.description;
                } catch {
                    // Ignore single item fetch error
                }

                if (!item.file_url) {
                    item.file_url = `https://${AJOU_BB_HOST}/webapps/blackboard/content/launchFile.jsp?course_id=${courseId}&content_id=${item.content_id}`;
                }
            }
        }
    }

    return items;
}

/**
 * Recursively extracts flat list of downloadable file items from a nested content tree.
 */
export function collectDownloadableFiles(contentNodes) {
    if (!contentNodes) return [];
    const nodes = Array.isArray(contentNodes) ? contentNodes : [contentNodes];
    const files = [];

    for (const node of nodes) {
        if (!node || typeof node !== 'object') continue;

        let fileUrl = (node.file_url && typeof node.file_url === 'string' && node.file_url.trim()) ? node.file_url.trim() : null;
        if (!fileUrl && (node.content_type === 'file' || Boolean(node.file_name)) && node.web_link) {
            fileUrl = String(node.web_link).trim();
        }

        const isFile = node.content_type === 'file' || Boolean(node.file_name);

        if (fileUrl && isFile) {
            files.push({
                content_id: node.content_id ?? null,
                title: node.title ?? '',
                file_name: node.file_name || node.title || 'download',
                file_url: fileUrl,
                size_bytes: node.size_bytes ?? node.file_size ?? null,
            });
        }

        if (Array.isArray(node.children) && node.children.length > 0) {
            const childFiles = collectDownloadableFiles(node.children);
            files.push(...childFiles);
        }
    }

    return files;
}

/**
 * Fetches and parses the LTI Learning Statistics Dashboard for a given course.
 *
 * @param {Object} page - Browser Page Bridge
 * @param {string} courseId - Blackboard course ID (e.g. '_117116_1')
 * @param {string} [contentId] - Optional content node ID for the analytics chart
 * @returns {Promise<Object>} Normalized AnalyticsRecord
 */
export async function fetchCourseAnalytics(page, courseId, contentId = null) {
    if (!page) {
        throw new ArgumentError('Browser page instance is required');
    }
    if (!courseId || typeof courseId !== 'string' || !courseId.trim()) {
        throw new ArgumentError('Course ID is required');
    }

    let targetContentId = contentId;
    if (!targetContentId) {
        const rootContents = await fetchBbRest(page, `/learn/api/public/v1/courses/${courseId}/contents`);
        const items = Array.isArray(rootContents?.results) ? rootContents.results : (Array.isArray(rootContents) ? rootContents : []);
        const chartItem = items.find((i) => {
            const title = String(i.title || '');
            const handler = String(i.contentHandler?.id || i.contentHandler?.placementHandle || '');
            return title.includes('학습분석차트') || title.includes('Analytics Chart') || handler.includes('fs-statistics-dashboard');
        });

        if (!chartItem) {
            throw new EmptyResultError(`No learning analytics chart found for course ${courseId}`);
        }
        targetContentId = chartItem.id;
    }

    const ltiUrl = `https://${AJOU_BB_HOST}/webapps/blackboard/execute/blti/launchPlacement?blti_placement_id=_809_1&content_id=${targetContentId}&course_id=${courseId}&wrapped=true&from_ultra=true`;

    await page.goto(ltiUrl, { waitUntil: 'domcontentloaded', timeout: DEFAULT_TIMEOUT_MS });

    let currentUrl = await page.evaluate('location.href').catch(() => '');
    for (let i = 0; i < 15 && (!currentUrl || !currentUrl.includes('bbmanager.ajou.ac.kr')); i++) {
        await new Promise((r) => setTimeout(r, 400));
        currentUrl = await page.evaluate('location.href').catch(() => '');
    }

    if (!currentUrl.includes('bbmanager.ajou.ac.kr')) {
        const pageText = await page.evaluate('document.body ? document.body.innerText : ""').catch(() => '');
        if (pageText.includes('도구 제공자가 더 이상 존재하지 않습니다') || pageText.includes('오류')) {
            throw new CommandExecutionError(`Failed to load Learning Analytics: ${pageText.slice(0, 150)}`);
        }
    }

    const rawData = await page.evaluate((cid) => {
        const courseTitle = document.querySelector('.course_title, h1, h2, h3')?.innerText || '';
        const bodyText = document.body ? document.body.innerText : '';
        const html = document.documentElement ? document.documentElement.innerHTML : '';
        const match = html.match(/const data2\s*=\s*(\[[\s\S]*?\]);/);
        let rawGpaData = null;
        if (match) {
            try { rawGpaData = JSON.parse(match[1]); } catch {}
        }
        return {
            courseId: cid,
            courseTitle,
            bodyText,
            rawGpaData,
        };
    }, courseId);

    return normalizeAnalyticsData(rawData);
}


