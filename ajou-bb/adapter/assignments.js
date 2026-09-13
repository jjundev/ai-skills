import { cli, Strategy } from '@jackwener/opencli/registry';
import {
    AJOU_BB_HOST,
    ArgumentError,
    EmptyResultError,
    fetchBbRest,
    resolveCourseId,
    withRedactedErrors,
} from './common.js';
import {
    normalizeAssignment,
    redactDeep,
} from './parser.js';

/**
 * Pure filter helper for AssignmentRecord arrays.
 */
export function filterAssignments(assignments, options = {}) {
    if (!Array.isArray(assignments)) return [];
    let list = assignments;

    if (options.pending) {
        list = list.filter((item) => {
            const isSub = item.is_submitted !== undefined ? item.is_submitted : item.submitted;
            return isSub === false;
        });
    } else if (options.submitted) {
        list = list.filter((item) => {
            const isSub = item.is_submitted !== undefined ? item.is_submitted : item.submitted;
            return isSub === true;
        });
    }

    if (options.limit && Number(options.limit) > 0) {
        list = list.slice(0, Number(options.limit));
    }

    return list;
}

/**
 * Lists assignments, quizzes, and submission statuses for a specified course.
 */
export async function listAssignments(page, args = {}) {
    const courseQuery = args.course || args._?.[0];
    if (!courseQuery || typeof courseQuery !== 'string' || !courseQuery.trim()) {
        throw new ArgumentError('Course name or ID is required (e.g. "회로이론" or "_12345_1")');
    }

    const course = await resolveCourseId(page, courseQuery);
    const pending = Boolean(args.pending);
    const submitted = Boolean(args.submitted);
    const includeSensitive = Boolean(args?.['include-sensitive']);

    const [columnsRaw, gradesRaw] = await Promise.all([
        fetchBbRest(page, `/learn/api/public/v2/courses/${course.course_id}/gradebook/columns`),
        fetchBbRest(page, `/learn/api/public/v2/courses/${course.course_id}/gradebook/users/me`).catch(() => []),
    ]);

    const rawColumns = Array.isArray(columnsRaw)
        ? columnsRaw
        : (Array.isArray(columnsRaw?.results) ? columnsRaw.results : []);

    const rawGrades = Array.isArray(gradesRaw)
        ? gradesRaw
        : (Array.isArray(gradesRaw?.results) ? gradesRaw.results : []);

    const gradesByColId = new Map();
    for (const g of rawGrades) {
        const cId = String(g.columnId ?? g.column_id ?? '');
        if (cId) gradesByColId.set(cId, g);
    }

    const validColumns = rawColumns.filter((col) => {
        const cat = String(col.formula?.category ?? col.category ?? '').toLowerCase();
        if (cat === 'total') return false;
        return true;
    });

    const normalized = validColumns.map((col) => {
        const colId = String(col.id ?? col.column_id ?? '');
        const grade = gradesByColId.get(colId) || null;
        return normalizeAssignment(col, grade);
    });

    let filtered = filterAssignments(normalized, { pending, submitted });

    filtered.sort((a, b) => {
        if (!a.due_date && !b.due_date) return (a.title || '').localeCompare(b.title || '');
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
    });

    if (filtered.length === 0) {
        const qualifier = pending ? ' (pending only)' : (submitted ? ' (submitted only)' : '');
        throw new EmptyResultError(
            'ajou-bb assignments',
            `No assignments found for course "${course.course_name}"${qualifier}`,
        );
    }

    return redactDeep(filtered, { includeSensitive });
}

cli({
    site: 'ajou-bb',
    name: 'assignments',
    access: 'read',
    description: 'List course assignments, quizzes, due dates, and submission statuses',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'course', type: 'string', positional: true, required: true, help: 'Course name, code, or course ID' },
        { name: 'pending', type: 'bool', default: false, help: 'Show only pending / unsubmitted assignments' },
        { name: 'submitted', type: 'bool', default: false, help: 'Show only submitted assignments' },
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include identity fields while still redacting secrets' },
    ],
    columns: ['assignment_id', 'title', 'due_date', 'status', 'score', 'possible_points', 'is_submitted', 'submitted_at'],
    func: (page, args) => withRedactedErrors(() => listAssignments(page, args)),
});
