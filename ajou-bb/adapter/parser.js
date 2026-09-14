import path from 'node:path';

/**
 * Blackboard Learn Ultra Data Normalization and PII Redaction Engine.
 *
 * Transforms raw Blackboard REST API payloads (v1, v2, v3, and Ultra SPA endpoints)
 * into standardized, deterministic snake_case schema objects, and provides deep PII redaction
 * and safe error boundaries.
 */

export class CommandExecutionError extends Error {
    constructor(message, options = {}) {
        super(message);
        this.name = 'CommandExecutionError';
        if (options.code) this.code = options.code;
        if (options.cause) this.cause = options.cause;
    }
}

/**
 * Strips HTML tags and unescapes common HTML entities.
 */
function stripHtml(html) {
    if (!html || typeof html !== 'string') return '';
    return html
        .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
        .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
        .replace(/<br\s*[\/]?>/gi, '\n')
        .replace(/<\/p>/gi, '\n')
        .replace(/<[^>]+>/g, '')
        .replace(/&nbsp;/g, ' ')
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/\n{3,}/g, '\n\n')
        .trim();
}

/**
 * Formats a person's name honoring Korean/CJK and Western conventions.
 */
function formatFullName(lastName, firstName, rawName = {}) {
    if (rawName?.display && typeof rawName.display === 'string' && rawName.display.trim()) {
        return rawName.display.trim();
    }
    const last = (lastName ?? '').trim();
    const first = (firstName ?? '').trim();
    if (!last && !first) return '';
    if (!last) return first;
    if (!first) return last;

    const hasCJK = /[\uAC00-\uD7A3\u3040-\u30FF\u4E00-\u9FFF]/.test(last + first);
    if (hasCJK) {
        return `${last}${first}`;
    }
    return `${first} ${last}`.trim();
}

/**
 * Extracts course code from courseId or courseCode strings (e.g. 'F028-2026-2-A001' -> 'F028').
 */
function extractCourseCode(rawCourse) {
    if (rawCourse?.courseCode && typeof rawCourse.courseCode === 'string' && rawCourse.courseCode.trim()) {
        return rawCourse.courseCode.trim();
    }
    if (rawCourse?.course_code && typeof rawCourse.course_code === 'string' && rawCourse.course_code.trim()) {
        return rawCourse.course_code.trim();
    }
    const rawId = rawCourse?.courseId ?? rawCourse?.course_id ?? '';
    if (!rawId || typeof rawId !== 'string') return '';
    const match = rawId.trim().match(/^([A-Za-z0-9]+)(?:[-_].*)?$/);
    return match ? match[1] : rawId.trim();
}

/**
 * Normalizes raw user profile payload to UserProfileRecord.
 */
export function normalizeUserProfile(rawUser) {
    const raw = rawUser ?? {};
    const rawName = raw.name ?? {};
    const rawContact = raw.contact ?? {};

    const userId = String(raw.id ?? raw.userId ?? raw.user_id ?? '').trim();
    const userName = String(raw.userName ?? raw.username ?? raw.user_name ?? '').trim();
    const studentNumber = String(
        raw.studentId
        ?? raw.student_id
        ?? raw.student_number
        ?? raw.externalId
        ?? raw.external_id
        ?? (/^\d{8,10}$/.test(userName) ? userName : ''),
    ).trim();

    const firstName = String(rawName.given ?? rawName.first ?? raw.firstName ?? raw.first_name ?? '').trim();
    const lastName = String(rawName.family ?? rawName.last ?? raw.lastName ?? raw.last_name ?? '').trim();
    const fullName = formatFullName(lastName, firstName, rawName);
    const email = String(rawContact.email ?? raw.email ?? '').trim();

    return {
        user_id: userId,
        user_name: userName,
        student_number: studentNumber,
        first_name: firstName,
        last_name: lastName,
        full_name: fullName,
        email,
    };
}

/**
 * Normalizes raw course payload to CourseRecord.
 */
export function normalizeCourse(rawCourse, rawMembership = null) {
    const raw = rawCourse ?? {};
    const mem = rawMembership ?? {};

    const courseId = String(raw.id ?? raw.courseId ?? raw.course_id ?? '').trim();
    const courseCode = extractCourseCode(raw);
    const courseName = String(raw.name ?? raw.title ?? raw.course_name ?? '').trim();
    let termId = raw.termId ?? raw.term_id ?? raw.term?.id ?? null;
    let termName = raw.termName ?? raw.term_name ?? raw.term?.name ?? (termId ? String(termId) : null);
    const role = String(mem.courseRoleId ?? mem.role ?? raw.role ?? 'Student').trim();

    // Ajou course code pattern recognition: e.g. 2026U0002003... -> 2026년 2학기 (2026-2)
    const ajouCodeMatch = courseCode.match(/^(\d{4})[A-Za-z]\d{4}(\d{3})/);
    if (ajouCodeMatch) {
        const year = ajouCodeMatch[1];
        const semCode = ajouCodeMatch[2];
        let semName = '';
        let semShort = '';
        if (semCode === '001') {
            semName = `${year}년 1학기`;
            semShort = `${year}-1`;
        } else if (semCode === '003') {
            semName = `${year}년 2학기`;
            semShort = `${year}-2`;
        } else if (semCode === '002') {
            semName = `${year}년 하계계절`;
            semShort = `${year}-summer`;
        } else if (semCode === '004') {
            semName = `${year}년 동계계절`;
            semShort = `${year}-winter`;
        }
        if (semShort) {
            termName = semName;
            if (!termId || String(termId).startsWith('_')) {
                termId = semShort;
            }
        }
    }

    let isActive = true;
    if (raw.is_active !== undefined) {
        isActive = Boolean(raw.is_active);
    } else if (raw.availability?.available !== undefined) {
        const avail = String(raw.availability.available).toLowerCase();
        isActive = avail === 'yes' || avail === 'true';
    }
    if (mem.availability?.available !== undefined) {
        const memAvail = String(mem.availability.available).toLowerCase();
        if (memAvail === 'no' || memAvail === 'false' || memAvail === 'disabled') {
            isActive = false;
        }
    }

    return {
        course_id: courseId,
        course_code: courseCode,
        course_name: courseName,
        term_id: termId,
        term_name: termName,
        role,
        is_active: isActive,
    };
}

/**
 * Maps Blackboard contentHandler and MIME representations to standardized content types.
 */
function resolveContentType(rawContent) {
    const rawHandler = String(
        rawContent?.contentHandler?.id
        ?? rawContent?.content_type
        ?? rawContent?.contentType
        ?? rawContent?.type
        ?? '',
    ).toLowerCase();

    if (rawHandler.includes('folder') || rawHandler.includes('lesson')) return 'folder';
    if (rawHandler.includes('assignment') || rawHandler.includes('asg-test') || rawHandler.includes('assessment')) return 'assignment';
    if (rawHandler.includes('file') || rawHandler.includes('attachment')) return 'file';
    if (rawHandler.includes('document') || rawHandler.includes('courselink')) return 'document';
    if (rawHandler.includes('externallink') || rawHandler.includes('url') || rawHandler.includes('link')) return 'link';
    if (rawHandler.includes('video') || rawHandler.includes('panopto') || rawHandler.includes('kollus') || rawHandler.includes('media')) return 'video';
    return 'other';
}

/**
 * Normalizes a single content item payload to ContentNode.
 */
export function normalizeContentItem(rawContent) {
    const raw = rawContent ?? {};
    const contentId = String(raw.id ?? raw.content_id ?? '').trim();
    const title = String(raw.title ?? raw.name ?? '').trim();
    const contentType = resolveContentType(raw);
    const description = raw.description ?? raw.body ?? null;
    const hasChildren = Boolean(
        raw.hasChildren
        ?? raw.has_children
        ?? (Array.isArray(raw.children) && raw.children.length > 0),
    );

    let fileName = raw.attachment?.fileName
        ?? raw.fileName
        ?? raw.file_name
        ?? raw.file?.name
        ?? null;

    let fileUrl = raw.attachment?.url
        ?? raw.attachment?.permanentUrl
        ?? raw.fileUrl
        ?? raw.file_url
        ?? null;

    let cleanDescription = description;
    let finalTitle = title;
    let finalType = contentType;

    // Parse Ultra embedded document files (data-bbfile) and bbcswebdav links
    if (description && typeof description === 'string') {
        if (description.includes('data-bbfile')) {
            try {
                const attrMatch = description.match(/data-bbfile\s*=\s*(["'])([\s\S]*?)\1/i);
                if (attrMatch && attrMatch[2]) {
                    let jsonStr = attrMatch[2]
                        .replace(/&quot;/g, '"')
                        .replace(/&amp;/g, '&')
                        .replace(/&#39;/g, "'")
                        .replace(/&lt;/g, '<')
                        .replace(/&gt;/g, '>');
                    if (jsonStr.startsWith('"') && jsonStr.endsWith('"')) {
                        jsonStr = jsonStr.slice(1, -1);
                    }
                    const bbfile = JSON.parse(jsonStr);
                    if (bbfile.displayName || bbfile.linkName) {
                        fileName = fileName || bbfile.displayName || bbfile.linkName;
                    }
                    if (bbfile.viewerUrl || bbfile.resourceUrl) {
                        const rawFileUrl = String(bbfile.viewerUrl || bbfile.resourceUrl);
                        fileUrl = fileUrl || rawFileUrl.replaceAll('&amp;', '&');
                    }
                    if (finalTitle === 'ultraDocumentBody' && fileName) {
                        finalTitle = fileName;
                    }
                    if (finalType === 'document' && fileName && /\.(pdf|pptx?|docx?|zip|hwp|ipynb)$/i.test(fileName)) {
                        finalType = 'file';
                    }
                }
            } catch {
                // Ignore JSON parse errors on malformed HTML
            }
        }

        // Fallback for bbcswebdav direct href if fileUrl still empty
        if (!fileUrl && description.includes('/bbcswebdav/')) {
            const hrefMatch = description.match(/href\s*=\s*(["'])([^"']*\/bbcswebdav\/[^"']*)\1/i);
            if (hrefMatch && hrefMatch[2]) {
                fileUrl = hrefMatch[2].replaceAll('&amp;', '&');
                if (finalType === 'document') finalType = 'file';
            }
        }
    }

    if (fileUrl && typeof fileUrl === 'string') {
        fileUrl = fileUrl.replaceAll('&amp;', '&');
    }

    let webLink = raw.contentHandler?.url
        ?? raw.webLink
        ?? raw.web_link
        ?? raw.url
        ?? (Array.isArray(raw.links) ? raw.links.find((l) => l?.rel === 'alternate' || l?.href)?.href ?? null : null);

    if (webLink && typeof webLink === 'string') {
        webLink = webLink.replaceAll('&amp;', '&');
    }

    // Auto-detect direct file attachments named like document.pdf
    const hasFileExt = /\.(pdf|pptx?|docx?|zip|hwp|ipynb|txt|xlsx?|csv|mp4|mov)$/i.test(finalTitle);
    if ((hasFileExt || finalType === 'file') && !fileName) {
        fileName = finalTitle;
        finalType = 'file';
    }
    if (!fileUrl && (finalType === 'file' || fileName) && webLink) {
        fileUrl = webLink;
    }

    const createdAt = raw.created ?? raw.createdAt ?? raw.created_at ?? null;
    const modifiedAt = raw.modified ?? raw.modifiedAt ?? raw.modified_at ?? null;

    const node = {
        content_id: contentId,
        title: finalTitle,
        content_type: finalType,
        description: cleanDescription,
        has_children: hasChildren,
        file_name: fileName,
        file_url: fileUrl,
        web_link: webLink,
        created_at: createdAt,
        modified_at: modifiedAt,
    };

    if (Array.isArray(raw.children) && raw.children.length > 0) {
        node.children = raw.children.map(normalizeContentItem);
    }

    return node;
}

/**
 * Normalizes an array of content tree nodes.
 */
export function normalizeContentTree(rawContents) {
    if (!Array.isArray(rawContents)) return [];
    return rawContents.map(normalizeContentItem);
}

/**
 * Extracts attached file metadata from announcement body HTML or raw attachments list.
 */
export function extractAnnouncementAttachments(bodyHtml, rawAttachments = []) {
    const attachments = [];
    const seenUrls = new Set();

    const markUrl = (urlStr) => {
        if (!urlStr || typeof urlStr !== 'string') return;
        const clean = urlStr.trim();
        seenUrls.add(clean);
        try {
            const parsed = new URL(clean, 'https://eclass2.ajou.ac.kr');
            seenUrls.add(parsed.href);
            if (parsed.pathname && parsed.pathname !== '/') {
                seenUrls.add(parsed.pathname);
            }
        } catch {
            // ignore URL parse errors
        }
    };

    const hasUrl = (urlStr) => {
        if (!urlStr || typeof urlStr !== 'string') return false;
        const clean = urlStr.trim();
        if (seenUrls.has(clean)) return true;
        try {
            const parsed = new URL(clean, 'https://eclass2.ajou.ac.kr');
            if (seenUrls.has(parsed.href)) return true;
            if (parsed.pathname && parsed.pathname !== '/' && seenUrls.has(parsed.pathname)) return true;
        } catch {
            // ignore
        }
        return false;
    };

    if (Array.isArray(rawAttachments)) {
        for (const att of rawAttachments) {
            if (!att) continue;
            const url = att.url || att.downloadUrl || att.fileUrl || att.resourceUrl;
            if (url && !hasUrl(url)) {
                markUrl(url);
                attachments.push({
                    file_name: String(att.fileName || att.name || att.title || 'attachment').trim(),
                    file_size: typeof att.fileSize === 'number' ? att.fileSize : (typeof att.size === 'number' ? att.size : null),
                    file_url: String(url).trim(),
                    mime_type: att.mimeType || att.contentType || null,
                });
            }
        }
    }

    if (typeof bodyHtml === 'string' && bodyHtml.trim()) {
        const bbFileRegex = /<a\b[^>]*\bdata-bbfile\s*=\s*(["'])([\s\S]*?)\1[^>]*>([\s\S]*?)<\/a>/gi;
        let match;
        while ((match = bbFileRegex.exec(bodyHtml)) !== null) {
            try {
                let decodedJson = match[2]
                    .replace(/&amp;/g, '&')
                    .replace(/&quot;/g, '"')
                    .replace(/&#39;/g, "'")
                    .replace(/&lt;/g, '<')
                    .replace(/&gt;/g, '>');
                if (decodedJson.includes('&quot;')) {
                    decodedJson = decodedJson.replace(/&quot;/g, '"');
                }
                decodedJson = decodedJson.trim();
                if (decodedJson.startsWith('"') && decodedJson.endsWith('"')) {
                    decodedJson = decodedJson.slice(1, -1);
                }
                const parsed = JSON.parse(decodedJson);
                const fileUrl = parsed.resourceUrl || parsed.viewerUrl || parsed.downloadUrl || parsed.url;
                if (fileUrl && !hasUrl(fileUrl)) {
                    markUrl(fileUrl);
                    attachments.push({
                        file_name: String(parsed.fileName || parsed.displayName || parsed.linkName || stripHtml(match[3]) || 'attachment').trim(),
                        file_size: typeof parsed.fileSize === 'number' ? parsed.fileSize : (typeof parsed.size === 'number' ? parsed.size : null),
                        file_url: String(fileUrl).trim(),
                        mime_type: parsed.mimeType || parsed.contentType || null,
                    });
                }
            } catch {
                // Ignore parse errors and continue
            }
        }

        const hrefRegex = /<a\b[^>]*\bhref\s*=\s*(["'])([^"']*bbcswebdav[^"']*)\1[^>]*>([\s\S]*?)<\/a>/gi;
        while ((match = hrefRegex.exec(bodyHtml)) !== null) {
            if (match[0].includes('data-bbfile')) continue;
            const rawHref = match[2].replace(/&amp;/g, '&').trim();
            if (rawHref && !hasUrl(rawHref)) {
                markUrl(rawHref);
                const linkText = stripHtml(match[3]).trim();
                let inferredName = linkText;
                if (!inferredName || inferredName === rawHref || inferredName.includes('/bbcswebdav/')) {
                    try {
                        const parsedUrl = new URL(rawHref, 'https://eclass2.ajou.ac.kr');
                        const baseName = path.basename(parsedUrl.pathname) || 'attachment';
                        try {
                            inferredName = decodeURIComponent(baseName);
                        } catch {
                            inferredName = baseName;
                        }
                    } catch {
                        inferredName = 'attachment';
                    }
                }
                try {
                    inferredName = decodeURIComponent(inferredName);
                } catch {
                    // ignore
                }
                attachments.push({
                    file_name: inferredName,
                    file_size: null,
                    file_url: rawHref,
                    mime_type: null,
                });
            }
        }
    }

    return attachments;
}

/**
 * Normalizes raw announcement payload to AnnouncementRecord.
 */
export function normalizeAnnouncement(rawAnnouncement) {
    const raw = rawAnnouncement ?? {};
    const announcementId = String(raw.id ?? raw.announcement_id ?? '').trim();
    const courseId = raw.courseId ?? raw.course_id ?? null;
    const title = String(raw.title ?? '').trim();
    const bodyHtml = raw.body ?? raw.body_html ?? '';
    const bodyText = stripHtml(bodyHtml);

    let authorName = null;
    if (raw.creator?.name) {
        authorName = formatFullName(raw.creator.name.family, raw.creator.name.given, raw.creator.name);
    } else if (raw.creator?.userName) {
        authorName = String(raw.creator.userName).trim();
    } else if (raw.authorName || raw.author_name || raw.author) {
        authorName = String(raw.authorName ?? raw.author_name ?? raw.author).trim();
    }

    const isUnread = Boolean(raw.unread ?? raw.is_unread ?? false);
    const createdAt = raw.created ?? raw.createdAt ?? raw.created_at ?? null;
    const modifiedAt = raw.modified ?? raw.modifiedAt ?? raw.modified_at ?? null;

    const attachments = extractAnnouncementAttachments(bodyHtml, raw.attachments);
    const hasAttachments = Boolean(
        attachments.length > 0
        || raw.hasAttachments
        || (Array.isArray(raw.attachments) && raw.attachments.length > 0),
    );

    return {
        announcement_id: announcementId,
        course_id: courseId,
        title,
        body_text: bodyText,
        body_html: bodyHtml,
        author_name: authorName,
        is_unread: isUnread,
        created_at: createdAt,
        modified_at: modifiedAt,
        has_attachments: hasAttachments,
        attachments,
    };
}

/**
 * Normalizes gradebook column and submission grade to AssignmentRecord.
 */
export function normalizeAssignment(rawColumn, rawGrade = null) {
    const col = rawColumn ?? {};
    const grd = rawGrade ?? {};

    const columnId = String(col.id ?? col.column_id ?? '').trim();
    const assignmentId = String(col.contentId ?? col.content_id ?? col.assignmentId ?? col.assignment_id ?? columnId).trim();
    const courseId = col.courseId ?? col.course_id ?? null;
    const title = String(col.name ?? col.title ?? '').trim();
    const description = col.description ?? null;
    const dueDate = col.grading?.due ?? col.dueDate ?? col.due_date ?? null;

    const possiblePoints = col.score?.possible !== undefined && col.score?.possible !== null
        ? Number(col.score.possible)
        : (col.grading?.scorePossible !== undefined && col.grading?.scorePossible !== null
            ? Number(col.grading.scorePossible)
            : (col.possible_points !== undefined && col.possible_points !== null ? Number(col.possible_points) : null));

    const score = grd.score !== undefined && grd.score !== null
        ? Number(grd.score)
        : (grd.displayGrade?.score !== undefined && grd.displayGrade?.score !== null
            ? Number(grd.displayGrade.score)
            : null);

    const isSubmitted = Boolean(
        grd.status === 'Graded'
        || grd.status === 'NeedsGrading'
        || grd.submittedAt
        || grd.submitted_at
        || grd.lastAttemptDate
        || grd.is_submitted === true,
    );

    const submittedAt = grd.submittedAt ?? grd.submitted_at ?? grd.lastAttemptDate ?? null;
    const feedback = grd.feedback ?? grd.notes ?? null;

    let status = 'pending';
    if (grd.status === 'Graded' || score !== null) {
        status = 'graded';
    } else if (grd.status === 'NeedsGrading' || (isSubmitted && score === null)) {
        status = 'submitted';
    } else if (grd.status === 'InProgress') {
        status = 'in_progress';
    } else if (!isSubmitted && dueDate && new Date(dueDate).getTime() < Date.now()) {
        status = 'overdue';
    }

    return {
        assignment_id: assignmentId,
        column_id: columnId,
        course_id: courseId,
        title,
        description,
        due_date: dueDate,
        possible_points: possiblePoints,
        score,
        is_submitted: isSubmitted,
        submitted_at: submittedAt,
        feedback,
        status,
    };
}

/**
 * Normalizes gradebook column and user score to GradeRecord.
 */
export function normalizeGradeItem(rawColumn, rawGrade = null) {
    const col = rawColumn ?? {};
    const grd = rawGrade ?? {};

    const columnId = String(col.id ?? col.column_id ?? '').trim();
    const courseId = col.courseId ?? col.course_id ?? null;
    const itemName = String(col.name ?? col.item_name ?? col.title ?? '').trim();
    const category = col.formula?.category ?? col.category ?? col.score?.category ?? null;

    const possiblePoints = col.score?.possible !== undefined && col.score?.possible !== null
        ? Number(col.score.possible)
        : (col.grading?.scorePossible !== undefined && col.grading?.scorePossible !== null
            ? Number(col.grading.scorePossible)
            : (col.possible_points !== undefined && col.possible_points !== null ? Number(col.possible_points) : null));

    const score = grd.score !== undefined && grd.score !== null
        ? Number(grd.score)
        : (grd.displayGrade?.score !== undefined && grd.displayGrade?.score !== null
            ? Number(grd.displayGrade.score)
            : null);

    const textGrade = grd.displayGrade?.text
        ?? grd.text
        ?? (score !== null && score !== undefined ? String(score) : null);

    const weight = col.weight !== undefined && col.weight !== null
        ? Number(col.weight)
        : (col.grading?.weight !== undefined && col.grading?.weight !== null ? Number(col.grading.weight) : null);

    const feedback = grd.feedback ?? grd.notes ?? null;
    const gradedAt = grd.gradedAt ?? grd.graded_at ?? grd.modified ?? null;

    return {
        column_id: columnId,
        course_id: courseId,
        item_name: itemName,
        category,
        possible_points: possiblePoints,
        score,
        text_grade: textGrade,
        weight,
        feedback,
        graded_at: gradedAt,
    };
}

/**
 * Normalizes calendar event to CalendarRecord.
 */
export function normalizeCalendarItem(rawItem) {
    const raw = rawItem ?? {};
    const eventId = String(raw.id ?? raw.event_id ?? '').trim();
    const isPersonal = Boolean(raw.personal ?? raw.is_personal ?? (raw.type === 'Personal' || (!raw.courseId && !raw.calendarId)));
    const courseId = isPersonal ? null : (raw.courseId ?? raw.calendarId ?? raw.course_id ?? null);
    const title = String(raw.title ?? raw.name ?? '').trim();
    const description = raw.description ?? null;
    const startTime = raw.start ?? raw.startTime ?? raw.start_time ?? null;
    const endTime = raw.end ?? raw.endTime ?? raw.end_time ?? null;

    const typeStr = String(raw.type ?? raw.category ?? raw.event_type ?? title).toLowerCase();
    let eventType = 'general';
    if (typeStr.includes('assign') || typeStr.includes('과제')) {
        eventType = 'assignment';
    } else if (typeStr.includes('quiz') || typeStr.includes('test') || typeStr.includes('exam') || typeStr.includes('퀴즈') || typeStr.includes('시험')) {
        eventType = 'quiz';
    } else if (typeStr.includes('meeting') || typeStr.includes('lecture') || typeStr.includes('zoom') || typeStr.includes('오피스') || typeStr.includes('수업')) {
        eventType = 'meeting';
    }

    return {
        event_id: eventId,
        course_id: courseId,
        title,
        description,
        start_time: startTime,
        end_time: endTime,
        event_type: eventType,
        is_personal: isPersonal,
    };
}

/**
 * Normalizes activity stream entry to StreamRecord.
 */
export function normalizeStreamItem(rawEntry) {
    const raw = rawEntry ?? {};
    const streamId = String(raw.id ?? raw.stream_id ?? '').trim();
    const courseId = raw.courseId ?? raw.course_id ?? raw.extraData?.courseId ?? null;
    const title = String(raw.itemTitle ?? raw.title ?? raw.message ?? '').trim();
    const summary = raw.summary ?? raw.description ?? raw.body ?? null;
    const itemUrl = raw.itemUrl ?? raw.url ?? (Array.isArray(raw.links) ? raw.links.find((l) => l?.href)?.href ?? null : null);
    const timestamp = raw.timestamp ?? raw.created ?? raw.modified ?? null;

    const catStr = String(raw.type ?? raw.category ?? '').toLowerCase();
    let category = 'activity';
    if (catStr.includes('due') || catStr.includes('deadline') || catStr.includes('soon')) {
        category = 'due_soon';
    } else if (catStr.includes('announce') || catStr.includes('notice')) {
        category = 'new_announcement';
    } else if (catStr.includes('grade') || catStr.includes('score')) {
        category = 'grade_posted';
    }

    return {
        stream_id: streamId,
        course_id: courseId,
        category,
        title,
        summary,
        item_url: itemUrl,
        timestamp,
    };
}

const SENSITIVE_KEYS = new Set([
    'student_number',
    'student_id',
    'studentid',
    'email',
    'password',
    'token',
    'session_token',
    'auth_token',
    'cookie',
    'secret',
    'externalid',
    'external_id',
    'phone',
    'phonenumber',
    'phone_number',
]);

const EMAIL_PATTERN = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;
const STUDENT_ID_PATTERN = /\b(?:20\d{6,8}|\d{8,10})\b/g;
const PHONE_PATTERN = /\b01[016789]-?\d{3,4}-?\d{4}\b/g;
const JWT_PATTERN = /\b[A-Za-z0-9-_]{20,}\.[A-Za-z0-9-_]{20,}\.[A-Za-z0-9-_]{20,}\b/g;

/**
 * Sanitizes plain text by replacing sensitive patterns and protected values with [REDACTED].
 */
function sanitizeString(str, protectedSet) {
    if (typeof str !== 'string' || !str) return str;
    let text = str;
    if (protectedSet) {
        for (const pv of protectedSet) {
            if (pv && text.includes(pv)) {
                text = text.replaceAll(pv, '[REDACTED]');
            }
        }
    }
    return text
        .replace(JWT_PATTERN, '[REDACTED]')
        .replace(EMAIL_PATTERN, '[REDACTED]')
        .replace(STUDENT_ID_PATTERN, '[REDACTED]')
        .replace(PHONE_PATTERN, '[REDACTED]');
}

/**
 * Deep traversal redaction engine. Recursively redacts sensitive identifiers and patterns
 * unless options.includeSensitive === true.
 */
export function redactDeep(value, options = {}) {
    if (options.includeSensitive === true) {
        return value;
    }

    const protectedList = Array.isArray(options.protectedValues)
        ? options.protectedValues.map((v) => String(v).trim()).filter(Boolean)
        : [];
    const protectedSet = new Set(protectedList);
    const seen = new WeakMap();

    function traverse(item, keyContext = '') {
        if (item === null || item === undefined) return item;

        const type = typeof item;
        if (type === 'string') {
            if (protectedSet.has(item.trim())) {
                return '[REDACTED]';
            }
            if (SENSITIVE_KEYS.has(keyContext.toLowerCase())) {
                return '[REDACTED]';
            }
            return sanitizeString(item, protectedSet);
        }

        if (type === 'number' || type === 'bigint') {
            const strVal = String(item);
            if (protectedSet.has(strVal) || SENSITIVE_KEYS.has(keyContext.toLowerCase())) {
                return '[REDACTED]';
            }
            if (STUDENT_ID_PATTERN.test(strVal)) {
                return '[REDACTED]';
            }
            return item;
        }

        if (type === 'boolean' || type === 'symbol') {
            return item;
        }

        if (typeof item === 'object') {
            if (seen.has(item)) {
                return seen.get(item);
            }

            if (Array.isArray(item)) {
                const arrCopy = [];
                seen.set(item, arrCopy);
                for (const element of item) {
                    arrCopy.push(traverse(element, keyContext));
                }
                return arrCopy;
            }

            if (item instanceof Set) {
                const setCopy = new Set();
                seen.set(item, setCopy);
                for (const element of item) {
                    setCopy.add(traverse(element, keyContext));
                }
                return setCopy;
            }

            if (item instanceof Map) {
                const mapCopy = new Map();
                seen.set(item, mapCopy);
                for (const [k, v] of item.entries()) {
                    const keyStr = String(k);
                    mapCopy.set(traverse(k, keyContext), traverse(v, keyStr));
                }
                return mapCopy;
            }

            const objCopy = {};
            seen.set(item, objCopy);
            for (const [k, v] of Object.entries(item)) {
                const keyLower = k.toLowerCase();
                if (SENSITIVE_KEYS.has(keyLower) && v !== null && v !== undefined) {
                    objCopy[k] = '[REDACTED]';
                } else {
                    objCopy[k] = traverse(v, k);
                }
            }
            return objCopy;
        }

        return item;
    }

    return traverse(value);
}

/**
 * Higher-order wrapper that executes a command block and sanitizes any thrown error
 * so that no credentials, tokens, or PII leak into stderr or log outputs.
 */
export async function withRedactedErrors(fn, options = {}) {
    try {
        const result = fn();
        return result instanceof Promise ? await result : result;
    } catch (error) {
        const protectedList = Array.isArray(options.protectedValues)
            ? options.protectedValues.map((v) => String(v).trim()).filter(Boolean)
            : [];
        const protectedSet = new Set(protectedList);

        const rawMessage = error?.message ?? String(error);
        const rawStack = error?.stack ?? '';

        const sanitizedMessage = sanitizeString(rawMessage, protectedSet);
        const sanitizedStack = sanitizeString(rawStack, protectedSet);

        const cleanError = new CommandExecutionError(sanitizedMessage, {
            code: error?.code ?? 'COMMAND_EXECUTION_ERROR',
            cause: error?.cause ? sanitizeString(String(error.cause), protectedSet) : undefined,
        });
        cleanError.stack = sanitizedStack;
        throw cleanError;
    }
}

/**
 * Normalizes raw LTI statistics dashboard text/data from bbmanager.ajou.ac.kr.
 *
 * @param {Object} raw
 * @returns {Object} AnalyticsRecord
 */
export function normalizeAnalyticsData(raw) {
    if (!raw || typeof raw !== 'object') {
        throw new SchemaValidationError('Analytics raw payload must be an object');
    }

    const courseId = raw.courseId || raw.course_id || '';
    const courseTitle = String(raw.courseTitle || raw.course_title || '').trim();
    const bodyText = String(raw.bodyText || raw.body_text || '').replace(/\s+/g, ' ');

    let courseName = courseTitle;
    let term = '';
    let professor = '';
    let totalStudents = 0;

    const headerParts = courseTitle.split('|').map((p) => p.trim());
    if (headerParts.length >= 1) {
        const titleMatch = headerParts[0].match(/^(.*?)\s+(\d{4}학년도?\s*\d학기)/);
        if (titleMatch) {
            courseName = titleMatch[1].trim();
            term = titleMatch[2].trim();
        } else {
            courseName = headerParts[0];
        }
    }
    if (headerParts.length >= 2) {
        professor = headerParts[1].replace(/교수(님)?/g, '').trim();
    }
    if (headerParts.length >= 3) {
        const studMatch = headerParts[2].match(/(\d+)\s*명/);
        if (studMatch) totalStudents = parseInt(studMatch[1], 10);
    }

    // 1. Grade Distribution (수강생 학년)
    const gradeDist = {};
    const gradeMatches = bodyText.matchAll(/([1-4]학년)\s*(\d+(?:\.\d+)?%)/g);
    for (const match of gradeMatches) {
        gradeDist[match[1]] = match[2];
    }

    // 2. GPA Distribution (수강생 성적)
    const gpaDist = {};
    if (Array.isArray(raw.rawGpaData) && raw.rawGpaData.length > 0) {
        for (const item of raw.rawGpaData) {
            if (item.label) {
                const count = item.STD_CNT ?? 0;
                gpaDist[item.label] = `${item.value}% (${count}명)`;
            }
        }
    } else {
        const gpaRanges = [
            { label: '4.0 초과', regex: /4\.0\s*초과\s*(\d+(?:\.\d+)?%)/ },
            { label: '3.5 초과 4.0 이하', regex: /3\.5\s*초과\s*4\.0\s*이하\s*(\d+(?:\.\d+)?%)/ },
            { label: '3.0 초과 3.5 이하', regex: /3\.0\s*초과\s*3\.5\s*이하\s*(\d+(?:\.\d+)?%)/ },
            { label: '3.0 이하', regex: /3\.0\s*이하\s*(\d+(?:\.\d+)?%)/ },
        ];
        for (const range of gpaRanges) {
            const m = bodyText.match(range.regex);
            if (m) gpaDist[range.label] = m[1];
        }
    }

    // 3. Major Distribution (수강생 전공)
    const majorDist = {};
    const majorSection = bodyText.match(/수강생\s*전공\s*(.*?)(이전에\s*수강했던|수강생은|나의|$)/);
    if (majorSection) {
        const majorMatches = majorSection[1].matchAll(/([가-힣a-zA-Z\s]+(?:학과|학부|전공|과))\s*(\d+(?:\.\d+)?%)/g);
        for (const match of majorMatches) {
            majorDist[match[1].trim()] = match[2];
        }
    }

    // 4. Prerequisite Courses Top 5 (이전에 수강했던 과목 Top 5)
    const topPrerequisites = [];
    const prereqMatches = bodyText.matchAll(/\[([^\]]+)\]\s*(\d+(?:\.\d+)?%)/g);
    let rank = 1;
    for (const match of prereqMatches) {
        topPrerequisites.push({
            rank,
            course_name: match[1].trim(),
            percent: match[2],
        });
        rank += 1;
        if (topPrerequisites.length >= 5) break;
    }

    // 5. Access Statistics (접속 통계)
    const accessStats = {
        student_daily_avg_minutes: 0,
        student_daily_avg_count: 0.0,
        my_daily_avg_minutes: 0,
        my_daily_avg_count: 0.0,
    };

    const studentAccessMatch = bodyText.match(/수강생\s*접속\s*통계.*?하루\s*평균\s*접속\s*시간:\s*(\d+(?:\.\d+)?)\s*분.*?하루\s*평균\s*접속\s*횟수:\s*(\d+(?:\.\d+)?)\s*회/);
    if (studentAccessMatch) {
        accessStats.student_daily_avg_minutes = parseFloat(studentAccessMatch[1]);
        accessStats.student_daily_avg_count = parseFloat(studentAccessMatch[2]);
    }

    const myAccessMatch = bodyText.match(/나의\s*접속\s*통계.*?하루\s*평균\s*접속\s*시간:\s*(\d+(?:\.\d+)?)\s*분.*?하루\s*평균\s*접속\s*횟수:\s*(\d+(?:\.\d+)?)\s*회/);
    if (myAccessMatch) {
        accessStats.my_daily_avg_minutes = parseFloat(myAccessMatch[1]);
        accessStats.my_daily_avg_count = parseFloat(myAccessMatch[2]);
    }

    return {
        course_id: courseId,
        course_name: courseName,
        term: term || null,
        professor: professor || null,
        total_students: totalStudents,
        grade_distribution: gradeDist,
        gpa_distribution: gpaDist,
        major_distribution: majorDist,
        top_prerequisites: topPrerequisites,
        access_statistics: accessStats,
    };
}
