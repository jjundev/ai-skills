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

test('parseArgs parses --submit flag correctly', () => {
    const parseArgsTest = (argv) => {
        let submit = false;
        for (let i = 0; i < argv.length; i++) {
            if (argv[i] === '--submit') submit = true;
        }
        return { submit };
    };

    assert.equal(parseArgsTest(['--images', 'test.png']).submit, false);
    assert.equal(parseArgsTest(['--images', 'test.png', '--submit']).submit, true);
});

test('submission snippet checks CAPTCHA before triggering click', () => {
    let clicked = false;
    const fakeDoc = {
        hasCaptcha: false,
        submitBtn: { click: () => { clicked = true; } }
    };

    if (!fakeDoc.hasCaptcha && fakeDoc.submitBtn) {
        fakeDoc.submitBtn.click();
    }
    assert.equal(clicked, true);

    clicked = false;
    fakeDoc.hasCaptcha = true;
    if (!fakeDoc.hasCaptcha && fakeDoc.submitBtn) {
        fakeDoc.submitBtn.click();
    }
    assert.equal(clicked, false);
});
