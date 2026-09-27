import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const CLI = fileURLToPath(new URL('../scripts/dc.mjs', import.meta.url));
const run = (...args) => spawnSync(process.execPath, [CLI, ...args], { encoding: 'utf8' });

for (const [label, args] of [
    ['no command', []],
    ['unknown command', ['write', 'x']],
    ['unknown option', ['list', 'shaving', '--bogus']],
    ['missing gallery', ['list']],
    ['limit out of range', ['list', 'shaving', '--limit', '99']],
    ['bad post url', ['read', 'https://example.com/']],
]) {
    test(`argument error exits 2: ${label}`, () => {
        const result = run(...args);
        assert.equal(result.status, 2, result.stderr);
        assert.equal(result.stdout, '');
        assert.equal(JSON.parse(result.stderr).error.code, 'ARG');
    });
}
