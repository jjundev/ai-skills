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
    normalizeAnnouncement,
    redactDeep,
} from './parser.js';

/**
 * Lists announcements for a specified course with unread filtering and limit options.
 */
export async function listAnnouncements(page, args = {}) {
    const courseQuery = args.course || args._?.[0];
    if (!courseQuery || typeof courseQuery !== 'string' || !courseQuery.trim()) {
        throw new ArgumentError('Course name or ID is required (e.g. "회로이론" or "_12345_1")');
    }

    const course = await resolveCourseId(page, courseQuery);
    const unread = Boolean(args.unread);
    const limit = args.limit !== undefined ? (requirePositiveInt(args.limit, 'limit') || 20) : null;
    const includeSensitive = Boolean(args?.['include-sensitive']);

    const rawData = await fetchBbRest(page, `/learn/api/public/v1/courses/${course.course_id}/announcements`, {
        params: { limit: 100 },
    });

    const rawList = Array.isArray(rawData)
        ? rawData
        : (Array.isArray(rawData?.results) ? rawData.results : []);

    let items = rawList.map(normalizeAnnouncement);

    if (unread) {
        items = items.filter((a) => a.is_unread === true);
    }

    items.sort((a, b) => {
        const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return timeB - timeA;
    });

    if (limit && limit > 0) {
        items = items.slice(0, limit);
    }

    if (items.length === 0) {
        const qualifier = unread ? ' (unread only)' : '';
        throw new EmptyResultError(
            'ajou-bb announcements',
            `No announcements found for course "${course.course_name}"${qualifier}`,
        );
    }

    return redactDeep(items, { includeSensitive });
}

cli({
    site: 'ajou-bb',
    name: 'announcements',
    access: 'read',
    description: 'List course announcements with unread filtering',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'course', type: 'string', positional: true, required: true, help: 'Course name, code, or course ID' },
        { name: 'unread', type: 'bool', default: false, help: 'Show only unread announcements' },
        { name: 'limit', type: 'int', default: 20, help: 'Maximum number of announcements to return' },
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include identity fields while still redacting secrets' },
    ],
    columns: ['announcement_id', 'course_id', 'title', 'body_text', 'author_name', 'is_unread', 'has_attachments', 'created_at'],
    func: (page, args) => withRedactedErrors(() => listAnnouncements(page, args)),
});
