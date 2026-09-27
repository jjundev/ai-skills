import { cli, Strategy } from '@jackwener/opencli/registry';
import { listGallery } from './http.js';
import { toOpencliError } from './common.js';

cli({
    site: 'dcinside',
    name: 'list',
    access: 'read',
    description: 'Read one page of a DCInside gallery (general, minor, or mini) over HTTPS',
    domain: 'gall.dcinside.com',
    strategy: Strategy.PUBLIC,
    browser: false,
    args: [
        { name: 'galleryId', type: 'string', required: true, positional: true, help: 'Gallery ID, for example programming' },
        { name: 'page', type: 'int', default: 1, help: 'Gallery page, 1-1000' },
        { name: 'limit', type: 'int', default: 20, help: 'Rows to return, 1-50' },
        { name: 'include-notices', type: 'bool', default: false, help: 'Include pinned notice rows' },
        { name: 'head', type: 'string', help: 'Head category filter ID (e.g. 70 for app)' },
        { name: 'recommend', type: 'bool', default: false, help: 'Show only recommend (concept) posts' },
        { name: 'sort', type: 'string', help: 'Sort type (e.g. N for new)' },
        { name: 'search', type: 'string', help: 'Search keyword' },
        { name: 'search-type', type: 'string', default: 'search_subject_memo', help: 'Search type (e.g. search_subject_memo, search_name)' },
        { name: 'mgallery', type: 'bool', default: false, help: 'Hint: minor gallery (auto-detected when omitted)' },
    ],
    columns: ['rank', 'postId', 'title', 'author', 'publishedAt', 'commentCount', 'viewCount', 'recommendCount', 'isNotice', 'url'],
    func: async (args) => {
        try {
            return await listGallery(args.galleryId, {
                page: args.page,
                limit: args.limit,
                includeNotices: Boolean(args['include-notices']),
                head: args.head,
                recommend: Boolean(args.recommend),
                sort: args.sort,
                search: args.search,
                searchType: args['search-type'],
                galleryType: args.mgallery ? 'M' : undefined,
            });
        } catch (error) {
            throw toOpencliError(error, 'dcinside list');
        }
    },
});
