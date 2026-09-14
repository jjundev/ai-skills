import { cli, Strategy } from '@jackwener/opencli/registry';
import {
    AJOU_BB_HOST,
    fetchBbRest,
    fetchUserCourses,
    navigateHome,
    withRedactedErrors,
} from './common.js';
import {
    normalizeUserProfile,
    redactDeep,
} from './parser.js';

/**
 * Checks active Blackboard session, verifies authentication, and retrieves student profile.
 */
export async function checkStatus(page, args = {}) {
    await navigateHome(page);
    const rawUser = await fetchBbRest(page, '/learn/api/public/v1/users/me');
    const profile = normalizeUserProfile(rawUser);

    const rawRole = Array.isArray(rawUser?.systemRoleIds) && rawUser.systemRoleIds.length > 0
        ? rawUser.systemRoleIds[0]
        : (profile.role || 'Student');
    const role = rawRole === 'User' ? 'Student' : rawRole;

    const record = {
        authenticated: true,
        server_status: 'ok',
        user_id: profile.user_id,
        user_name: profile.user_name,
        student_number: profile.student_number,
        full_name: profile.full_name,
        email: profile.email,
        role,
    };

    const includeSensitive = Boolean(args?.['include-sensitive']);
    const protectedValues = [profile.student_number, profile.email, profile.user_name].filter(Boolean);

    return [
        redactDeep(record, {
            includeSensitive,
            protectedValues,
        }),
    ];
}

cli({
    site: 'ajou-bb',
    name: 'status',
    access: 'read',
    description: 'Check authenticated Ajou Blackboard session and student profile',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include identity fields while still redacting secrets' },
    ],
    columns: ['authenticated', 'server_status', 'user_id', 'student_number', 'full_name', 'email', 'role'],
    func: (page, args) => withRedactedErrors(() => checkStatus(page, args)),
});
