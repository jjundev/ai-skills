import { cli, Strategy } from '@jackwener/opencli/registry';
import {
    AJOU_BB_HOST,
    EmptyResultError,
    fetchBbRest,
    fetchUserCourses,
    requireTerm,
    resolveCourseId,
    withRedactedErrors,
} from './common.js';
import {
    normalizeGradeItem,
    redactDeep,
} from './parser.js';

/**
 * Retrieves itemized grades for a specific course or grade summaries across active enrolled courses.
 */
export async function getGrades(page, args = {}) {
    const courseQuery = args.course || args._?.[0];
    const includeSensitive = Boolean(args?.['include-sensitive']);

    if (courseQuery && typeof courseQuery === 'string' && courseQuery.trim()) {
        const course = await resolveCourseId(page, courseQuery.trim());
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

        const items = rawColumns.map((col) => {
            const colId = String(col.id ?? col.column_id ?? '');
            const grade = gradesByColId.get(colId) || null;
            return normalizeGradeItem({ ...col, courseId: course.course_id, course_id: course.course_id }, grade);
        });

        if (items.length === 0) {
            throw new EmptyResultError(
                'ajou-bb grades',
                `No gradebook entries found for course "${course.course_name}"`,
            );
        }

        return redactDeep(items, { includeSensitive });
    }

    // Global / Multi-course mode
    const term = requireTerm(args.term);
    const courses = await fetchUserCourses(page, { term, all: false });

    if (!Array.isArray(courses) || courses.length === 0) {
        const msg = term
            ? `No enrolled courses found for term "${term}"`
            : 'No enrolled courses found for the active Blackboard session';
        throw new EmptyResultError('ajou-bb grades', msg);
    }

    const aggregated = [];

    for (const c of courses) {
        try {
            const [columnsRaw, gradesRaw] = await Promise.all([
                fetchBbRest(page, `/learn/api/public/v2/courses/${c.course_id}/gradebook/columns`),
                fetchBbRest(page, `/learn/api/public/v2/courses/${c.course_id}/gradebook/users/me`).catch(() => []),
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

            const totalCol = rawColumns.find((col) => {
                const cat = String(col.formula?.category ?? col.category ?? '').toLowerCase();
                return cat === 'total' || col.externalGrade === true || /total|총점|최종/i.test(col.name || '');
            });

            if (totalCol) {
                const cId = String(totalCol.id ?? totalCol.column_id ?? '');
                const grade = gradesByColId.get(cId) || null;
                aggregated.push(normalizeGradeItem({
                    ...totalCol,
                    courseId: c.course_id,
                    course_id: c.course_id,
                    item_name: `${c.course_name} (${totalCol.name || 'Total'})`,
                }, grade));
            } else if (rawColumns.length > 0) {
                for (const col of rawColumns) {
                    const cId = String(col.id ?? col.column_id ?? '');
                    const grade = gradesByColId.get(cId) || null;
                    aggregated.push(normalizeGradeItem({
                        ...col,
                        courseId: c.course_id,
                        course_id: c.course_id,
                    }, grade));
                }
            }
        } catch {
            // Ignore single course failure in multi-course loop
        }
    }

    if (aggregated.length === 0) {
        throw new EmptyResultError(
            'ajou-bb grades',
            'No grade records found across enrolled courses',
        );
    }

    return redactDeep(aggregated, { includeSensitive });
}

cli({
    site: 'ajou-bb',
    name: 'grades',
    access: 'read',
    description: 'Get itemized grades, scores, weights, and feedback for a course or all active courses',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'course', type: 'string', positional: true, required: false, help: 'Course name, code, or course ID (optional)' },
        { name: 'term', type: 'string', help: 'Academic term filter when querying all courses (e.g. 2026-2)' },
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include identity fields while still redacting secrets' },
    ],
    columns: ['column_id', 'course_id', 'item_name', 'category', 'score', 'possible_points', 'text_grade', 'weight', 'graded_at'],
    func: (page, args) => withRedactedErrors(() => getGrades(page, args)),
});
