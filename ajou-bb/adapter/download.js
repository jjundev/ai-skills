import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { cli, Strategy } from '@jackwener/opencli/registry';
import {
    AJOU_BB_HOST,
    ArgumentError,
    EmptyResultError,
    collectDownloadableFiles,
    fetchBbBinary,
    fetchBbRest,
    fetchContentHierarchy,
    requirePositiveInt,
    resolveCourseId,
    withRedactedErrors,
} from './common.js';
import {
    extractAnnouncementAttachments,
    redactDeep,
} from './parser.js';

/**
 * Sanitizes file/folder names by removing/replacing illegal filesystem characters.
 * Replaces [\\/:*?"<>|\0] with '_' and normalizes multiple spaces.
 */
export function sanitizeFileName(name) {
    if (name === undefined || name === null) return 'unnamed';
    const str = String(name).trim();
    if (!str) return 'unnamed';
    const sanitized = str
        .replace(/[\\/:*?"<>|\0]/g, '_')
        .replace(/\s+/g, ' ')
        .trim();
    if (!sanitized || sanitized.replace(/_/g, '').trim() === '') return 'unnamed';
    return sanitized;
}

/**
 * Resolves the destination directory for downloads.
 * Handles relative paths, home directory tildes (~), and defaults to ./downloads/<course_name>/.
 */
export function resolveOutDir(outArg, courseName) {
    if (!outArg || typeof outArg !== 'string' || !outArg.trim()) {
        return path.join(process.cwd(), 'downloads', sanitizeFileName(courseName));
    }
    const cleanOut = outArg.trim();
    if (cleanOut === '~') {
        return os.homedir();
    }
    if (cleanOut.startsWith('~/') || cleanOut.startsWith('~\\')) {
        return path.join(os.homedir(), cleanOut.slice(2));
    }
    return path.resolve(process.cwd(), cleanOut);
}

/**
 * Pure function to filter a list of downloadable files based on options.
 */
export function filterFilesForDownload(files, options = {}) {
    if (!Array.isArray(files) || files.length === 0) return [];
    const { query, contentId, all } = options;

    if (contentId) {
        const cleanId = String(contentId).trim();
        return files.filter((f) => f && String(f.content_id) === cleanId);
    }

    if (query && typeof query === 'string' && query.trim()) {
        const q = query.trim().toLowerCase();
        return files.filter((f) => {
            if (!f) return false;
            const name = (f.file_name || '').toLowerCase();
            const title = (f.title || '').toLowerCase();
            return name.includes(q) || title.includes(q);
        });
    }

    if (all === true) {
        return [...files];
    }

    return [];
}

/**
 * Fetches announcement attachments for a course and returns normalized downloadable file records.
 */
export async function fetchAnnouncementFiles(page, courseId) {
    try {
        const rawData = await fetchBbRest(page, `/learn/api/public/v1/courses/${courseId}/announcements`, {
            params: { limit: 100 },
        });
        const rawList = Array.isArray(rawData) ? rawData : (Array.isArray(rawData?.results) ? rawData.results : []);
        const files = [];

        for (const raw of rawList) {
            const bodyHtml = raw.body ?? raw.body_html ?? '';
            const attachments = extractAnnouncementAttachments(bodyHtml, raw.attachments);
            const annId = raw.id || raw.announcement_id || 'item';
            for (let idx = 0; idx < attachments.length; idx++) {
                const att = attachments[idx];
                files.push({
                    content_id: `announcement_${annId}_${idx}`,
                    title: raw.title ? `[공지] ${raw.title} - ${att.file_name}` : att.file_name,
                    file_name: att.file_name,
                    file_url: att.file_url,
                    size_bytes: att.file_size,
                    source: 'announcement',
                });
            }
        }
        return files;
    } catch {
        return [];
    }
}

/**
 * Downloads lecture notes, PDFs, and attached files from a Blackboard course.
 */
export async function downloadCommand(page, args = {}) {
    const courseQuery = args.course || args._?.[0];
    if (!courseQuery || typeof courseQuery !== 'string' || !courseQuery.trim()) {
        throw new ArgumentError('Course name, code, or course ID is required (e.g. "회로이론" or "_12345_1")');
    }

    const course = await resolveCourseId(page, courseQuery);
    const depth = args.depth !== undefined ? (requirePositiveInt(args.depth, 'depth') || 3) : 3;
    const includeSensitive = Boolean(args?.['include-sensitive']);
    const overwrite = Boolean(args?.overwrite);
    const query = args.query ? String(args.query).trim() : null;
    const contentId = (args['content-id'] || args.contentId) ? String(args['content-id'] || args.contentId).trim() : null;
    const all = Boolean(args.all);

    const announcementsOnly = Boolean(args.announcements);
    let availableFiles = [];

    if (announcementsOnly) {
        availableFiles = await fetchAnnouncementFiles(page, course.course_id);
    } else {
        const tree = await fetchContentHierarchy(page, course.course_id, null, 1, depth);
        availableFiles = collectDownloadableFiles(tree);
        if (all || query || (contentId && String(contentId).startsWith('announcement_'))) {
            const annFiles = await fetchAnnouncementFiles(page, course.course_id);
            availableFiles = [...availableFiles, ...annFiles];
        }
    }

    const effectiveAll = all || (announcementsOnly && !query && !contentId);
    const targetFiles = filterFilesForDownload(availableFiles, { query, contentId, all: effectiveAll });

    if (targetFiles.length === 0) {
        const queryDesc = contentId
            ? `content ID "${contentId}"`
            : (query ? `query "${query}"` : 'the specified filter (use --all to download all files)');
        throw new EmptyResultError(
            'ajou-bb download',
            `No downloadable files found matching ${queryDesc} in course "${course.course_name}"`,
        );
    }

    const resolvedOutDir = resolveOutDir(args.out, course.course_name);
    const results = [];

    for (const file of targetFiles) {
        let downloadUrl = file.file_url;
        let actualFileName = file.file_name || file.title || 'download';

        if (file.content_id && !String(file.content_id).startsWith('announcement_')) {
            try {
                const attList = await fetchBbRest(page, `/learn/api/public/v1/courses/${course.course_id}/contents/${file.content_id}/attachments`);
                const attachments = Array.isArray(attList?.results) ? attList.results : (Array.isArray(attList) ? attList : []);
                if (attachments.length > 0) {
                    const firstAtt = attachments[0];
                    if (firstAtt.id) {
                        downloadUrl = `/learn/api/public/v1/courses/${course.course_id}/contents/${file.content_id}/attachments/${firstAtt.id}/download`;
                    }
                    if (firstAtt.fileName) {
                        actualFileName = firstAtt.fileName;
                    }
                }
            } catch {
                // Fallback to original file_url
            }
        }

        const fileName = sanitizeFileName(actualFileName);
        const destPath = path.join(resolvedOutDir, fileName);

        let exists = false;
        let existingStat = null;
        try {
            existingStat = await fs.stat(destPath);
            exists = true;
        } catch {
            exists = false;
        }

        if (exists && !overwrite) {
            results.push({
                file_name: fileName,
                file_size: existingStat?.size ?? file.size_bytes ?? null,
                destination_path: destPath,
                content_id: file.content_id ?? null,
                status: 'skipped (already exists)',
            });
            continue;
        }

        const buffer = await fetchBbBinary(page, downloadUrl);
        await fs.mkdir(resolvedOutDir, { recursive: true });
        await fs.writeFile(destPath, buffer);

        results.push({
            file_name: fileName,
            file_size: buffer.byteLength,
            destination_path: destPath,
            content_id: file.content_id ?? null,
            status: exists ? 'overwritten' : 'downloaded',
        });
    }

    return redactDeep(results, { includeSensitive });
}

cli({
    site: 'ajou-bb',
    name: 'download',
    access: 'read',
    description: 'Download lecture notes, PDFs, and attached files from a course',
    domain: AJOU_BB_HOST,
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    siteSession: 'persistent',
    args: [
        { name: 'course', type: 'string', positional: true, required: true, help: 'Course name, code, or course ID' },
        { name: 'query', type: 'string', help: 'Filter files by keyword or file name (e.g. Lec1)' },
        { name: 'content-id', type: 'string', help: 'Download specific file by Blackboard content ID' },
        { name: 'all', type: 'bool', default: false, help: 'Download all files in the course content tree' },
        { name: 'announcements', type: 'bool', default: false, help: 'Download only files attached to course announcements' },
        { name: 'out', type: 'string', help: 'Destination directory path (default ./downloads/<course_name>/)' },
        { name: 'depth', type: 'int', default: 3, help: 'Hierarchy traversal depth (default 3)' },
        { name: 'overwrite', type: 'bool', default: false, help: 'Overwrite existing files if already present' },
        { name: 'include-sensitive', type: 'bool', default: false, help: 'Include identity fields while still redacting secrets' },
    ],
    columns: ['file_name', 'file_size', 'destination_path', 'content_id', 'status'],
    func: (page, args) => withRedactedErrors(() => downloadCommand(page, args)),
});
