/**
 * Course Learning Statistics & Analytics Command (`opencli ajou-bb analytics`)
 *
 * Direct LTI integration with Ajou University Learning Statistics Dashboard (`bbmanager.ajou.ac.kr`).
 */

import { cli, Strategy } from '@jackwener/opencli/registry';
import {
    AJOU_BB_HOST,
    fetchCourseAnalytics,
    fetchUserCourses,
    resolveCourseId,
    withRedactedErrors,
} from './common.js';
import { redactDeep } from './parser.js';

export async function getCourseAnalytics(page, args = {}) {
    const courseQuery = args.course ?? args._?.[0];
    const includeSensitive = Boolean(args['include-sensitive']);

    if (courseQuery) {
        const course = await resolveCourseId(page, courseQuery);
        const stats = await fetchCourseAnalytics(page, course.course_id);
        return redactDeep(stats, { includeSensitive });
    }

    // Omitted course: retrieve analytics for all active courses
    const courses = await fetchUserCourses(page, { term: args.term });
    const activeCourses = courses.filter((c) => c.is_active);
    const results = [];

    for (const course of activeCourses) {
        try {
            const stats = await fetchCourseAnalytics(page, course.course_id);
            results.push(stats);
        } catch {
            // Course may not have LTI analytics placement
        }
    }

    return redactDeep(results, { includeSensitive });
}

cli({
    site: 'ajou-bb',
    name: 'analytics',
    access: 'read',
    description: 'View course learning statistics, student demographics, GPA distribution, and access metrics',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'course', type: 'string', positional: true, help: 'Course name, code, or course ID (e.g. 전자회로2)' },
        { name: 'term', type: 'string', help: 'Semester term filter (e.g. 2026-2)' },
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include sensitive student fields' },
    ],
    columns: ['course_name', 'professor', 'total_students', 'grade_distribution', 'gpa_distribution', 'major_distribution', 'top_prerequisites'],
    func: (page, args) => withRedactedErrors(() => getCourseAnalytics(page, args)),
});
