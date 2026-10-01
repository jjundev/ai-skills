import test from 'node:test';
import assert from 'node:assert/strict';

test('session staleness detection flags tokens older than 600 seconds', () => {
    const now = 1790856000;
    const freshTokenTime = 1790855800; // 200s ago
    const staleTokenTime = 1790854000; // 2000s ago

    const isStale = (tokenTime) => (now - tokenTime) > 600;

    assert.equal(isStale(freshTokenTime), false);
    assert.equal(isStale(staleTokenTime), true);
});
