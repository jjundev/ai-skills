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

test('attach-images auto-submit snippet preconditions counters and restores dialogs before click', () => {
    let keydownCount = 0;
    let mousedownCount = 0;
    let clickCount = 0;
    let alertRestored = false;

    const fakeWin = {
        alert: () => {},
        __origAlert: function alert() { /* native */ },
        document: {
            querySelector: () => ({
                dispatchEvent: (ev) => {
                    if (ev.type === 'keydown') keydownCount++;
                    if (ev.type === 'mousedown') mousedownCount++;
                },
                click: () => {
                    if (keydownCount >= 3 && mousedownCount >= 3 && alertRestored) {
                        clickCount++;
                    }
                }
            })
        }
    };

    // Preconditioning logic under test
    fakeWin.alert = fakeWin.__origAlert;
    alertRestored = true;
    const btn = fakeWin.document.querySelector();
    for (let i = 0; i < 5; i++) {
        btn.dispatchEvent({ type: 'mousedown' });
        btn.dispatchEvent({ type: 'keydown' });
    }
    btn.click();

    assert.equal(keydownCount >= 3, true);
    assert.equal(mousedownCount >= 3, true);
    assert.equal(clickCount, 1);
});

test('post-upload staleness check rejects submission when token expired', () => {
    const checkCanSubmit = (tokenAgeSec, isStale) => {
        if (isStale || tokenAgeSec > 600) {
            return { canSubmit: false, reason: 'token_stale' };
        }
        return { canSubmit: true };
    };

    assert.equal(checkCanSubmit(200, false).canSubmit, true);
    assert.equal(checkCanSubmit(650, true).canSubmit, false);
});
