import { cli, Strategy } from '@jackwener/opencli/registry';
import { CommandExecutionError, EmptyResultError } from '@jackwener/opencli/errors';
import { extractThreadFromDocument } from './parser.js';
import { canonicalPostUrl, navigateToDcinside, requireBoundedInteger } from './common.js';

cli({
    site: 'dcinside',
    name: 'read',
    access: 'read',
    description: 'Read one DCInside general-gallery post with visible comments and replies',
    domain: 'gall.dcinside.com',
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    args: [
        { name: 'postUrl', type: 'string', required: true, positional: true, help: 'Full desktop DCInside general-gallery post URL' },
        { name: 'comment-limit', type: 'int', default: 20, help: 'Visible comments and replies to return, 0-50' },
        { name: 'content-limit', type: 'int', default: 6000, help: 'Maximum characters per post or comment, 100-10000' },
    ],
    columns: ['type', 'postId', 'parentId', 'author', 'publishedAt', 'title', 'content', 'views', 'recommendations', 'url'],
    func: async (page, args) => {
        const url = canonicalPostUrl(args.postUrl);
        const commentLimit = requireBoundedInteger(args['comment-limit'], 20, 0, 50, 'comment-limit');
        const contentLimit = requireBoundedInteger(args['content-limit'], 6000, 100, 10000, 'content-limit');

        await navigateToDcinside(page, url, 'DCInside post');
        let rows;
        try {
            rows = await page.evaluate(
                `(${extractThreadFromDocument.toString()})(document, ${JSON.stringify(url)}, ${contentLimit})`,
            );
        } catch (error) {
            throw new CommandExecutionError(`DCInside post DOM extraction failed: ${error?.message ?? error}`);
        }

        if (!Array.isArray(rows) || rows.length === 0 || rows[0]?.type !== 'POST') {
            throw new EmptyResultError('dcinside read', 'Post is unavailable, removed, or its page layout changed');
        }
        return [rows[0], ...rows.slice(1, commentLimit + 1)];
    },
});
