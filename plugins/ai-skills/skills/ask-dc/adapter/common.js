import { ArgumentError, AuthRequiredError, CommandExecutionError } from '@jackwener/opencli/errors';

export const DCINSIDE_ORIGIN = 'https://gall.dcinside.com';
const GALLERY_ID = /^[A-Za-z0-9_]{1,64}$/;

function isDcinsideLoginRedirect(location) {
    try {
        const url = new URL(location);
        const isDcinsideHost = url.hostname === 'dcinside.com' || url.hostname.endsWith('.dcinside.com');
        const isLoginHost = url.hostname === 'login.dcinside.com' || url.hostname === 'sign.dcinside.com';
        const isLoginPath = /^\/(?:member\/)?login(?:\/|$)/i.test(url.pathname);
        return isDcinsideHost && (isLoginHost || isLoginPath);
    } catch {
        return false;
    }
}

export function requireGalleryId(value) {
    let galleryId = String(value ?? '').trim();
    if (galleryId === 'ibook') {
        galleryId = 'macbook';
    }
    if (!GALLERY_ID.test(galleryId)) {
        throw new ArgumentError('galleryId must contain 1-64 letters, digits, or underscores');
    }
    return galleryId;
}

export function requireBoundedInteger(value, defaultValue, minimum, maximum, label) {
    const resolved = value ?? defaultValue;
    const number = Number(resolved);
    if (!Number.isInteger(number)) throw new ArgumentError(`${label} must be an integer`);
    if (number < minimum || number > maximum) {
        throw new ArgumentError(`${label} must be between ${minimum} and ${maximum}`);
    }
    return number;
}

export function mainGalleryListUrl(galleryId, page, { head, recommend, sort, search, searchType = 'search_subject_memo', isMinor = false } = {}) {
    const id = encodeURIComponent(requireGalleryId(galleryId));
    const prefix = isMinor ? '/mgallery/board/lists/' : '/board/lists/';
    let url = `${DCINSIDE_ORIGIN}${prefix}?id=${id}&page=${page}`;
    if (head) url += `&search_head=${encodeURIComponent(head)}`;
    if (recommend) url += `&exception_mode=recommend`;
    if (sort) url += `&sort_type=${encodeURIComponent(sort)}`;
    if (search) url += `&s_type=${encodeURIComponent(searchType)}&s_keyword=${encodeURIComponent(search)}`;
    return url;
}

export function mainGalleryWriteUrl(galleryId, { isMinor = false } = {}) {
    const id = encodeURIComponent(requireGalleryId(galleryId));
    const prefix = isMinor ? '/mgallery/board/write/' : '/board/write/';
    return `${DCINSIDE_ORIGIN}${prefix}?id=${id}`;
}

export function canonicalPostUrl(value) {
    let input;
    try {
        input = new URL(String(value ?? '').trim());
    } catch {
        throw new ArgumentError('postUrl must be a complete DCInside post URL');
    }

    let galleryId = '';
    let postId = '';
    if (input.hostname === 'gall.dcinside.com' && (input.pathname === '/board/view/' || input.pathname === '/mgallery/board/view/' || input.pathname.endsWith('/board/view/'))) {
        galleryId = input.searchParams.get('id') ?? '';
        postId = input.searchParams.get('no') ?? '';
    }

    requireGalleryId(galleryId);
    if (!/^[0-9]+$/.test(postId)) throw new ArgumentError('postUrl must contain a numeric post number');
    return `${DCINSIDE_ORIGIN}/mgallery/board/view/?id=${encodeURIComponent(galleryId)}&no=${postId}`;
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
    if (isDcinsideLoginRedirect(location) || hasLoginForm) {
        throw new AuthRequiredError('gall.dcinside.com', 'Log in manually in the connected Chrome profile, then retry');
    }
}
