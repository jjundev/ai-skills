import { cli, Strategy } from '@jackwener/opencli/registry';
import {
    AJOU_BB_HOST,
    EmptyResultError,
    fetchUserCourses,
    requireTerm,
    withRedactedErrors,
} from './common.js';
import { redactDeep } from './parser.js';

/**
 * Pure filter helper for CourseRecord arrays based on academic term and active state.
 */
export function filterCoursesByTerm(courses, options = {}) {
    if (!Array.isArray(courses)) return [];
    let list = courses;

    if (options.term) {
        const termFilter = String(options.term).trim().toLowerCase();
        list = list.filter((c) => {
            const tId = c.term_id ? String(c.term_id).toLowerCase() : '';
            const tName = c.term_name ? String(c.term_name).toLowerCase() : '';
            return tId.includes(termFilter) || tName.includes(termFilter);
        });
    }

    if (options.all !== true && options.includeInactive !== true) {
        list = list.filter((c) => c.is_active !== false);
    }

    return list;
}

/**
 * Lists enrolled courses for the authenticated user with optional term filtering.
 */
export async function listCourses(page, args = {}) {
    const term = requireTerm(args.term);
    const all = Boolean(args.all);
    const includeSensitive = Boolean(args?.['include-sensitive']);

    const courses = await fetchUserCourses(page, { term, all });
    if (!Array.isArray(courses) || courses.length === 0) {
        const msg = term
            ? `No enrolled courses found for term "${term}"`
            : 'No enrolled courses found for the active Blackboard session';
        throw new EmptyResultError('ajou-bb courses', msg);
    }

    const sorted = [...courses].sort((a, b) => {
        const termA = String(a.term_id || a.term_name || '');
        const termB = String(b.term_id || b.term_name || '');
        const termCmp = termB.localeCompare(termA);
        if (termCmp !== 0) return termCmp;
        const nameA = String(a.course_name || '');
        const nameB = String(b.course_name || '');
        return nameA.localeCompare(nameB);
    });

    return redactDeep(sorted, { includeSensitive });
}

cli({
    site: 'ajou-bb',
    name: 'courses',
    access: 'read',
    description: 'List enrolled Blackboard courses for the active session',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'term', type: 'string', help: 'Academic term filter (e.g. 2026-2, 2026-1, 2026-summer)' },
        { name: 'all', type: 'bool', default: false, help: 'Include past/inactive courses across all terms' },
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include identity fields while still redacting secrets' },
    ],
    columns: ['course_id', 'course_code', 'course_name', 'term_id', 'term_name', 'role', 'is_active'],
    func: (page, args) => withRedactedErrors(() => listCourses(page, args)),
});
