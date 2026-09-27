import { cli, Strategy } from '@jackwener/opencli/registry';
import { readPost } from './http.js';
import { toOpencliError } from './common.js';

cli({
    site: 'dcinside',
    name: 'read',
    access: 'read',
    description: 'Read one DCInside post with its comments and replies over HTTPS',
    domain: 'gall.dcinside.com',
    strategy: Strategy.PUBLIC,
    browser: false,
    args: [
        { name: 'postUrl', type: 'string', required: true, positional: true, help: 'Full DCInside post URL (/board/view/, /mgallery/board/view/, or /mini/board/view/)' },
        { name: 'comment-limit', type: 'int', default: 20, help: 'Comments and replies to return, 0-50' },
        { name: 'content-limit', type: 'int', default: 6000, help: 'Maximum characters per post or comment, 100-10000' },
    ],
    columns: ['type', 'postId', 'parentId', 'author', 'publishedAt', 'title', 'content', 'views', 'recommendations', 'url'],
    func: async (args) => {
        try {
            return await readPost(args.postUrl, {
                commentLimit: args['comment-limit'],
                contentLimit: args['content-limit'],
            });
        } catch (error) {
            throw toOpencliError(error, 'dcinside read');
        }
    },
});
