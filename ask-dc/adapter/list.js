import { cli, Strategy } from '@jackwener/opencli/registry';
import { CommandExecutionError, EmptyResultError } from '@jackwener/opencli/errors';
import { extractListFromDocument } from './parser.js';
import { mainGalleryListUrl, navigateToDcinside, requireBoundedInteger, requireGalleryId } from './common.js';

cli({
    site: 'dcinside',
    name: 'list',
    access: 'read',
    description: 'Read one page of a DCInside general gallery',
    domain: 'gall.dcinside.com',
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    args: [
        { name: 'galleryId', type: 'string', required: true, positional: true, help: 'General gallery ID, for example programming' },
        { name: 'page', type: 'int', default: 1, help: 'Gallery page, 1-1000' },
        { name: 'limit', type: 'int', default: 20, help: 'Rows to return, 1-50' },
        { name: 'include-notices', type: 'bool', default: false, help: 'Include pinned notice rows' },
        { name: 'head', type: 'string', help: 'Head category filter ID (e.g. 70 for app)' },
        { name: 'recommend', type: 'bool', default: false, help: 'Show only recommend (concept) posts' },
        { name: 'sort', type: 'string', help: 'Sort type (e.g. N for new)' },
        { name: 'search', type: 'string', help: 'Search keyword' },
        { name: 'search-type', type: 'string', default: 'search_subject_memo', help: 'Search type (e.g. search_subject_memo, search_name)' },
        { name: 'mgallery', type: 'bool', default: false, help: 'Target minor gallery (mgallery)' },
    ],
    columns: ['rank', 'postId', 'title', 'author', 'publishedAt', 'commentCount', 'viewCount', 'recommendCount', 'isNotice', 'url'],
    func: async (page, args) => {
        const galleryId = requireGalleryId(args.galleryId);
        const pageNumber = requireBoundedInteger(args.page, 1, 1, 1000, 'page');
        const limit = requireBoundedInteger(args.limit, 20, 1, 50, 'limit');
        const includeNotices = Boolean(args['include-notices']);
        const head = args.head ? String(args.head) : undefined;
        const recommend = Boolean(args.recommend);
        const sort = args.sort ? String(args.sort) : undefined;
        const search = args.search ? String(args.search) : undefined;
        const searchType = args['search-type'] ? String(args['search-type']) : 'search_subject_memo';
        const isMinor = Boolean(args.mgallery);
        let url = mainGalleryListUrl(galleryId, pageNumber, { head, recommend, sort, search, searchType, isMinor });

        await navigateToDcinside(page, url, 'DCInside gallery list');

        if (search) {
            const currentUrl = await page.evaluate('window.location.href');
            if (!currentUrl.includes('s_keyword=')) {
                const isCurrentMinor = currentUrl.includes('/mgallery/');
                const targetUrl = mainGalleryListUrl(galleryId, pageNumber, { head, recommend, sort, search, searchType, isMinor: isCurrentMinor });
                await page.goto(targetUrl);
                await page.wait(2);
            }
        }
        let rows;
        try {
            rows = await page.evaluate(
                `(${extractListFromDocument.toString()})(document, ${JSON.stringify({ includeNotices })})`,
            );
        } catch (error) {
            throw new CommandExecutionError(`DCInside gallery DOM extraction failed: ${error?.message ?? error}`);
        }

        if (!Array.isArray(rows) || rows.length === 0) {
            throw new EmptyResultError('dcinside list', `No readable rows in general gallery "${galleryId}" page ${pageNumber}`);
        }
        return rows.slice(0, limit);
    },
});
