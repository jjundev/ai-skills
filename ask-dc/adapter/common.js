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
