export function extractListFromDocument(doc, { includeNotices = false } = {}) {
    const text = (element) => String(element?.textContent ?? '').replace(/\s+/g, ' ').trim();
    const integerOrNull = (value) => {
        const digits = String(value ?? '').replace(/[^0-9]/g, '');
        return digits ? Number(digits) : null;
    };
    const rows = [];

    for (const row of doc.querySelectorAll('.gall_list tbody tr.ub-content')) {
        const titleAnchor = row.querySelector('.gall_tit a[href*="/board/view/"]');
        const rawHref = titleAnchor?.getAttribute('href') ?? '';
        const url = rawHref ? new URL(rawHref, 'https://gall.dcinside.com') : null;
        const postId = url?.searchParams.get('no') ?? String(row.dataset.no ?? '');
        const galleryId = url?.searchParams.get('id') ?? '';
        const isNotice = row.dataset.type === 'icon_notice' || text(row.querySelector('.gall_num')) === '공지';

        if (!titleAnchor || !/^[0-9]+$/.test(postId) || !galleryId || (!includeNotices && isNotice)) continue;

        const titleNode = titleAnchor.cloneNode(true);
        titleNode.querySelectorAll('.reply_num, .reply_numbox').forEach((node) => node.remove());
        const authorNode = row.querySelector('.gall_writer');
        const dateNode = row.querySelector('.gall_date');
        const replyText = text(row.querySelector('.reply_num'));

        rows.push({
            rank: rows.length + 1,
            postId,
            title: text(titleNode),
            author: String(authorNode?.dataset.nick ?? text(authorNode)),
            publishedAt: String(dateNode?.getAttribute('title') ?? text(dateNode)),
            commentCount: integerOrNull(replyText) ?? 0,
            viewCount: integerOrNull(text(row.querySelector('.gall_count'))),
            recommendCount: integerOrNull(text(row.querySelector('.gall_recommend'))),
            isNotice,
            url: `https://gall.dcinside.com/board/view/?id=${encodeURIComponent(galleryId)}&no=${postId}`,
        });
    }

    return rows;
}

export function extractThreadFromDocument(doc, canonicalUrl, contentLimit) {
    const text = (element) => String(element?.textContent ?? '').replace(/\s+/g, ' ').trim();
    const truncate = (value) => value.length <= contentLimit ? value : `${value.slice(0, contentLimit - 1)}…`;
    const integerOrNull = (value) => {
        const digits = String(value ?? '').replace(/[^0-9]/g, '');
        return digits ? Number(digits) : null;
    };
    const parsedUrl = new URL(canonicalUrl);
    const postId = parsedUrl.searchParams.get('no') ?? '';
    const header = doc.querySelector('.gallview_head');
    const title = text(header?.querySelector('.title_subject')) || text(header?.querySelector('h3.title'));
    const writer = header?.querySelector('.gall_writer');
    const content = truncate(text(doc.querySelector('.writing_view_box .write_div')));

    if (!header || !title || !/^[0-9]+$/.test(postId)) return [];

    const rows = [{
        type: 'POST',
        postId,
        parentId: null,
        author: String(writer?.dataset.nick ?? text(writer?.querySelector('.nickname'))),
        publishedAt: String(writer?.querySelector('.gall_date')?.getAttribute('title') ?? text(writer?.querySelector('.gall_date'))),
        title,
        content,
        views: integerOrNull(text(writer?.querySelector('.gall_count')) || text(header.querySelector('.gall_count'))),
        recommendations: integerOrNull(text(writer?.querySelector('.gall_recommend')) || text(header.querySelector('.gall_recommend'))),
        url: canonicalUrl,
    }];

    for (const item of doc.querySelectorAll('.comment_box li[id^="comment_li_"], .comment_box li[id^="reply_li_"]')) {
        if (item.classList.contains('dory')) continue;
        const isReply = item.id.startsWith('reply_li_');
        const info = item.querySelector(isReply ? ':scope > .reply_info' : ':scope > .cmt_info');
        const commentId = String(info?.dataset.no ?? item.id.replace(/^(comment|reply)_li_/, ''));
        const authorNode = info?.querySelector('.gall_writer');
        const contentNode = info?.querySelector('.cmt_txtbox .usertxt');
        const dcconLabel = [...(info?.querySelectorAll('[conalt], [alt]') ?? [])]
            .map((node) => node.getAttribute('conalt') || node.getAttribute('alt') || '')
            .find(Boolean);
        const commentContent = text(contentNode) || (dcconLabel ? `[디시콘: ${dcconLabel}]` : '');

        if (!/^[0-9]+$/.test(commentId) || !commentContent) continue;

        rows.push({
            type: isReply ? 'REPLY' : 'COMMENT',
            postId,
            parentId: isReply ? String(item.closest('.reply_list')?.getAttribute('p-no') ?? '') || null : null,
            author: String(authorNode?.dataset.nick ?? text(authorNode?.querySelector('.nickname'))),
            publishedAt: text(info?.querySelector('.date_time')),
            title: '',
            content: truncate(commentContent),
            views: null,
            recommendations: null,
            url: canonicalUrl,
        });
    }

    return rows;
}
