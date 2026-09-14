import { cli, Strategy } from '@jackwener/opencli/registry';
import {
    AJOU_BB_HOST,
    ArgumentError,
    EmptyResultError,
    fetchBbRest,
    requirePositiveInt,
    resolveCourseId,
    withRedactedErrors,
} from './common.js';
import {
    normalizeCalendarItem,
    redactDeep,
} from './parser.js';

/**
 * Computes ISO date window (since, until) for calendar queries.
 */
export function computeCalendarWindow(options = {}) {
    if (options.month) {
        const rawMonth = String(options.month).trim();
        const match = rawMonth.match(/^(\d{4})-(\d{2})$/);
        if (!match) {
            throw new ArgumentError(`Invalid month format: "${options.month}". Expected format YYYY-MM (e.g. 2026-09)`);
        }
        const year = Number(match[1]);
        const month = Number(match[2]);
        if (month < 1 || month > 12) {
            throw new ArgumentError(`Invalid month number: "${options.month}". Month must be between 01 and 12`);
        }

        const since = new Date(Date.UTC(year, month - 1, 1, 0, 0, 0, 0)).toISOString();
        const until = new Date(Date.UTC(year, month, 0, 23, 59, 59, 999)).toISOString();
        return { since, until };
    }

    const days = options.days !== undefined ? (requirePositiveInt(options.days, 'days') || 14) : 14;
    const base = options.now instanceof Date ? options.now : new Date();

    const since = new Date(Date.UTC(base.getUTCFullYear(), base.getUTCMonth(), base.getUTCDate(), 0, 0, 0, 0)).toISOString();
    const until = new Date(Date.UTC(base.getUTCFullYear(), base.getUTCMonth(), base.getUTCDate() + days, 23, 59, 59, 999)).toISOString();

    return { since, until };
}

/**
 * Queries upcoming calendar events, deadlines, and exams.
 */
export async function getCalendar(page, args = {}) {
    const { since, until } = computeCalendarWindow(args);
    const includeSensitive = Boolean(args?.['include-sensitive']);

    const queryParams = { since, until };

    if (args.course) {
        const resolved = await resolveCourseId(page, args.course);
        queryParams.courseId = resolved.course_id;
    }

    const rawData = await fetchBbRest(page, '/learn/api/public/v1/calendars/items', {
        params: queryParams,
    });

    const rawList = Array.isArray(rawData)
        ? rawData
        : (Array.isArray(rawData?.results) ? rawData.results : []);

    const normalized = rawList.map(normalizeCalendarItem);

    const sorted = [...normalized].sort((a, b) => {
        const timeA = a.start_time ? new Date(a.start_time).getTime() : 0;
        const timeB = b.start_time ? new Date(b.start_time).getTime() : 0;
        return timeA - timeB;
    });

    if (sorted.length === 0) {
        const timeframe = args.month ? `month ${args.month}` : `next ${args.days || 14} days`;
        throw new EmptyResultError('ajou-bb calendar', `No calendar events found for ${timeframe}`);
    }

    return redactDeep(sorted, { includeSensitive });
}

cli({
    site: 'ajou-bb',
    name: 'calendar',
    access: 'read',
    description: 'Query upcoming calendar deadlines, exams, and schedule items',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'days', type: 'int', default: 14, help: 'Number of days ahead to search (default 14)' },
        { name: 'month', type: 'string', help: 'Target month in YYYY-MM format (e.g. 2026-09)' },
        { name: 'course', type: 'string', help: 'Filter by course name, code, or course ID' },
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include identity fields while still redacting secrets' },
    ],
    columns: ['event_id', 'course_id', 'title', 'event_type', 'start_time', 'end_time', 'is_personal', 'description'],
    func: (page, args) => withRedactedErrors(() => getCalendar(page, args)),
});
