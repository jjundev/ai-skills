#!/usr/bin/env node
// Standalone DCInside reader for the ask-dc skill. Needs only Node 18+ (built-in fetch).
//   node dc.mjs list <galleryId> [--search K] [--recommend] [--page N] [--limit N] ...
//   node dc.mjs read <postUrl> [--comment-limit N] [--content-limit N]
// Prints a JSON array on stdout. On failure prints {"error":{code,message}} on stderr.
import { parseArgs } from 'node:util';
import { DcError, listGallery, readPost } from '../adapter/http.js';

const EXIT_CODES = { ARG: 2, EMPTY: 3, NOT_FOUND: 4, AUTH: 5, BLOCKED: 5, NETWORK: 1 };

const USAGE = `usage:
  dc.mjs list <galleryId> [--search <keyword>] [--search-type <type>] [--recommend]
                          [--page <1-1000>] [--limit <1-50>] [--head <id>] [--sort <type>]
                          [--include-notices] [--mgallery | --mini]
  dc.mjs read <postUrl> [--comment-limit <0-50>] [--content-limit <100-10000>]`;

const LIST_OPTIONS = {
    search: { type: 'string' },
    'search-type': { type: 'string' },
    recommend: { type: 'boolean' },
    page: { type: 'string' },
    limit: { type: 'string' },
    head: { type: 'string' },
    sort: { type: 'string' },
    'include-notices': { type: 'boolean' },
    mgallery: { type: 'boolean' },
    mini: { type: 'boolean' },
};

const READ_OPTIONS = {
    'comment-limit': { type: 'string' },
    'content-limit': { type: 'string' },
};

function parse(args, options) {
    const { values, positionals } = parseArgs({ args, options, allowPositionals: true, strict: true });
    if (positionals.length !== 1) throw new DcError('ARG', `expected exactly one positional argument\n${USAGE}`);
    return { values, target: positionals[0] };
}

async function run([command, ...args]) {
    if (command === 'list') {
        const { values, target } = parse(args, LIST_OPTIONS);
        return listGallery(target, {
            search: values.search,
            searchType: values['search-type'],
            recommend: values.recommend,
            page: values.page,
            limit: values.limit,
            head: values.head,
            sort: values.sort,
            includeNotices: values['include-notices'],
            galleryType: values.mgallery ? 'M' : values.mini ? 'MI' : undefined,
        });
    }
    if (command === 'read') {
        const { values, target } = parse(args, READ_OPTIONS);
        return readPost(target, {
            commentLimit: values['comment-limit'],
            contentLimit: values['content-limit'],
        });
    }
    throw new DcError('ARG', USAGE);
}

try {
    const rows = await run(process.argv.slice(2));
    process.stdout.write(`${JSON.stringify(rows, null, 2)}\n`);
} catch (error) {
    const code = error instanceof DcError ? error.code
        : String(error?.code ?? '').startsWith('ERR_PARSE_ARGS') ? 'ARG'
        : 'NETWORK';
    process.stderr.write(`${JSON.stringify({ error: { code, message: error?.message ?? String(error) } })}\n`);
    process.exitCode = EXIT_CODES[code] ?? 1;
}
