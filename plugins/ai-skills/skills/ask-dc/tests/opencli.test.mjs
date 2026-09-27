// Needs the OpenCLI ESM shim (adapter/node_modules/@jackwener/opencli, created by scripts/setup.sh).
import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { getRegistry } from '../adapter/node_modules/@jackwener/opencli/dist/src/registry.js';
import { timing } from '../adapter/http.js';
import '../adapter/list.js';
import '../adapter/read.js';

const fixture = (name) => readFileSync(new URL(`./fixtures/${name}`, import.meta.url), 'utf8');
const realFetch = globalThis.fetch;
timing.gapMs = 0;
timing.retryDelayMs = 0;
afterEach(() => { globalThis.fetch = realFetch; });

test('list and read register as browserless PUBLIC commands', () => {
    for (const name of ['dcinside/list', 'dcinside/read']) {
        const cmd = getRegistry().get(name);
        assert.ok(cmd, `${name} registered`);
        assert.equal(cmd.strategy, 'public');
        assert.equal(cmd.browser, false);
    }
});

test('list func returns rows from the HTTP core', async () => {
    globalThis.fetch = async () => new Response(fixture('list-general.html'));
    const rows = await getRegistry().get('dcinside/list').func({ galleryId: 'shaving', limit: 1 });
    assert.equal(rows.length, 1);
    assert.equal(rows[0].postId, '40288');
});

test('errors are mapped to OpenCLI error classes', async () => {
    globalThis.fetch = async () => new Response('<table class="gall_list"></table>');
    await assert.rejects(getRegistry().get('dcinside/list').func({ galleryId: 'shaving' }), { name: 'EmptyResultError' });
    await assert.rejects(getRegistry().get('dcinside/read').func({ postUrl: 'nope' }), { name: 'ArgumentError' });
});
