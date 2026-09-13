import { cli, Strategy } from '@jackwener/opencli/registry';
import {
    AJOU_BB_HOST,
    ArgumentError,
    EmptyResultError,
    fetchContentHierarchy,
    requirePositiveInt,
    resolveCourseId,
    withRedactedErrors,
} from './common.js';
import {
    redactDeep,
} from './parser.js';

/**
 * Lists course content materials, files, folders, and links for a specified course.
 */
export async function listContents(page, args = {}) {
    const courseQuery = args.course || args._?.[0];
    if (!courseQuery || typeof courseQuery !== 'string' || !courseQuery.trim()) {
        throw new ArgumentError('Course name or ID is required (e.g. "회로이론" or "_12345_1")');
    }

    const course = await resolveCourseId(page, courseQuery);
    const depth = args.depth !== undefined ? (requirePositiveInt(args.depth, 'depth') || 2) : 2;
    const folderId = args.folder ? String(args.folder).trim() : null;
    const includeSensitive = Boolean(args?.['include-sensitive']);

    const contents = await fetchContentHierarchy(page, course.course_id, folderId, 1, depth);

    if (!Array.isArray(contents) || contents.length === 0) {
        const targetDesc = folderId
            ? `folder "${folderId}" in course "${course.course_name}"`
            : `course "${course.course_name}"`;
        throw new EmptyResultError('ajou-bb contents', `No contents found for ${targetDesc}`);
    }

    return redactDeep(contents, { includeSensitive });
}

cli({
    site: 'ajou-bb',
    name: 'contents',
    access: 'read',
    description: 'List course materials, folders, documents, and videos',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'course', type: 'string', positional: true, required: true, help: 'Course name, code, or course ID' },
        { name: 'folder', type: 'string', help: 'Subfolder ID to list contents from' },
        { name: 'depth', type: 'int', default: 2, help: 'Hierarchy traversal depth for nested folders (default 2)' },
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include identity fields while still redacting secrets' },
    ],
    columns: ['content_id', 'title', 'content_type', 'description', 'file_name', 'file_url', 'web_link', 'has_children', 'created_at'],
    func: (page, args) => withRedactedErrors(() => listContents(page, args)),
});
