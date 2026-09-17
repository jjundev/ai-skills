import assert from 'node:assert/strict';
import test from 'node:test';
import { requireTerm } from '../adapter/common.js';
import { filterFilesForDownload, resolveOutDir, sanitizeFileName } from '../adapter/download.js';

test('normalizes academic terms', () => {
  assert.equal(requireTerm('2026년 2학기'), '2026-2');
  assert.equal(requireTerm('2026-summer'), '2026-summer');
  assert.throws(() => requireTerm('2026-3'), /Invalid term semester/);
});

test('does not widen a requested download', () => {
  const files = [{ content_id: '_a', file_name: '1주차.pdf', title: '1주차' }, { content_id: '_b', file_name: '2주차.pdf', title: '2주차' }];
  assert.deepEqual(filterFilesForDownload(files, { query: '2주차' }), [files[1]]);
  assert.deepEqual(filterFilesForDownload(files, {}), []);
});

test('keeps current download behavior', () => {
  assert.equal(sanitizeFileName('  1주차: 회로?  '), '1주차_ 회로_');
  assert.match(resolveOutDir(undefined, '회로이론'), /downloads\/회로이론$/);
});

test('extracts multiple attachments from assignment instructions and collects them for download', async () => {
  const { collectDownloadableFiles } = await import('../adapter/common.js');
  const { normalizeContentItem } = await import('../adapter/parser.js');
  const rawItem = {
    id: '_100',
    title: '과제/실습 1',
    contentHandler: {
      id: 'resource/x-bb-asmt-test-link',
      instructions: '<p><a href="https://example.com/p1.pdf" data-bbfile="{&quot;fileName&quot;:&quot;Practice 1.pdf&quot;,&quot;resourceUrl&quot;:&quot;https://example.com/p1.pdf&quot;}">Practice 1.pdf</a></p>' +
        '<p><a href="https://example.com/p1.c" data-bbfile="{&quot;fileName&quot;:&quot;Practice 1.c&quot;,&quot;resourceUrl&quot;:&quot;https://example.com/p1.c&quot;}">Practice 1.c</a></p>',
    },
  };
  const node = normalizeContentItem(rawItem);
  assert.equal(node.content_type, 'assignment');
  assert.equal(node.attachments.length, 2);
  const files = collectDownloadableFiles([node]);
  assert.equal(files.length, 2);
  assert.equal(files[0].file_name, 'Practice 1.pdf');
  assert.equal(files[1].file_name, 'Practice 1.c');
});

