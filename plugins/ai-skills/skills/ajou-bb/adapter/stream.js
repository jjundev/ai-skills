import { cli, Strategy } from '@jackwener/opencli/registry';
import {
    AJOU_BB_HOST,
    EmptyResultError,
    fetchBbRest,
    requirePositiveInt,
    withRedactedErrors,
} from './common.js';
import {
    normalizeStreamItem,
    redactDeep,
} from './parser.js';

/**
 * Pure filter helper for StreamRecord arrays.
 */
export function filterStreamItems(items, options = {}) {
    if (!Array.isArray(items)) return [];
    let list = items;

    if (options.category) {
        const catFilter = String(options.category).trim().toLowerCase();
        list = list.filter((item) => {
            const cat = item.category ? String(item.category).toLowerCase() : '';
            return cat === catFilter || cat.includes(catFilter);
        });
    }

    if (options.limit && Number(options.limit) > 0) {
        list = list.slice(0, Number(options.limit));
    }

    return list;
}

/**
 * Retrieves global Blackboard activity stream (deadlines, announcements, grades).
 */
export async function getStream(page, args = {}) {
    const limit = requirePositiveInt(args.limit, 'limit') || 20;
    const category = args.category ? String(args.category).trim() : null;
    const includeSensitive = Boolean(args?.['include-sensitive']);

    const rawData = await fetchBbRest(page, '/learn/api/public/v1/users/me/stream', {
        params: { limit: Math.max(limit, 50) },
    });

    const rawList = Array.isArray(rawData)
        ? rawData
        : (Array.isArray(rawData?.results) ? rawData.results : []);

    const normalized = rawList.map(normalizeStreamItem);
    const filtered = filterStreamItems(normalized, { category, limit });

    if (filtered.length === 0) {
        const msg = category
            ? `No activity stream items found for category "${category}"`
            : 'No activity stream items found for the active Blackboard session';
        throw new EmptyResultError('ajou-bb stream', msg);
    }

    return redactDeep(filtered, { includeSensitive });
}

cli({
    site: 'ajou-bb',
    name: 'stream',
    access: 'read',
    description: 'Get global activity stream (deadlines, announcements, grades)',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'limit', type: 'int', default: 20, help: 'Maximum number of stream items to return' },
        { name: 'category', type: 'string', help: 'Filter by category (due_soon, new_announcement, grade_posted, activity)' },
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include identity fields while still redacting secrets' },
    ],
    columns: ['stream_id', 'course_id', 'category', 'title', 'summary', 'timestamp', 'item_url'],
    func: (page, args) => withRedactedErrors(() => getStream(page, args)),
});
