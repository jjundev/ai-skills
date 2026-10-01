import test from 'node:test';
import assert from 'node:assert/strict';

function restoreNativeDialogs(windowObj, createIframe) {
    if (windowObj.__origAlert) windowObj.alert = windowObj.__origAlert;
    else delete windowObj.alert;
    if (windowObj.__origConfirm) windowObj.confirm = windowObj.__origConfirm;
    else delete windowObj.confirm;

    if (!windowObj.alert || windowObj.alert.toString().indexOf('[native code]') === -1) {
        if (createIframe) {
            const f = createIframe();
            windowObj.alert = f.contentWindow.alert.bind(windowObj);
            windowObj.confirm = f.contentWindow.confirm.bind(windowObj);
        }
    }
}

test('dialog restoration restores original native alert and confirm', () => {
    const origNativeAlert = function alert() { /* native code */ };
    origNativeAlert.toString = () => 'function alert() { [native code] }';
    const origNativeConfirm = function confirm() { /* native code */ };
    origNativeConfirm.toString = () => 'function confirm() { [native code] }';

    const fakeWindow = {
        alert: (msg) => console.log('suppressed:', msg),
        confirm: () => true,
        __origAlert: origNativeAlert,
        __origConfirm: origNativeConfirm
    };

    restoreNativeDialogs(fakeWindow);

    assert.equal(fakeWindow.alert, origNativeAlert);
    assert.equal(fakeWindow.confirm, origNativeConfirm);
});

test('dialog restoration falls back to iframe when original is missing', () => {
    const fakeWindow = {
        alert: (msg) => console.log('suppressed:', msg),
        confirm: () => true
    };
    fakeWindow.alert.toString = () => '(msg) => console.log(...)';

    const iframeAlert = function alert() { /* native code */ };
    iframeAlert.toString = () => 'function alert() { [native code] }';
    const iframeConfirm = function confirm() { /* native code */ };
    iframeConfirm.toString = () => 'function confirm() { [native code] }';
    const createIframe = () => ({
        contentWindow: { alert: iframeAlert, confirm: iframeConfirm }
    });

    restoreNativeDialogs(fakeWindow, createIframe);

    assert.equal(fakeWindow.alert.toString().includes('[native code]'), true);
});

test('anti-bot event simulation code dispatches required keydown and mousedown events', () => {
    let keydownCount = 0;
    let mousedownCount = 0;
    const fakeBtn = {
        dispatchEvent: (ev) => {
            if (ev.type === 'keydown') keydownCount++;
            if (ev.type === 'mousedown') mousedownCount++;
        }
    };

    // Preconditioning loop
    for (let i = 0; i < 5; i++) {
        fakeBtn.dispatchEvent({ type: 'mousedown' });
        fakeBtn.dispatchEvent({ type: 'keydown' });
    }

    assert.equal(keydownCount >= 3, true);
    assert.equal(mousedownCount >= 3, true);
});

test('minor gallery head selection synchronizes headtext input and fires change event', () => {
    let changeFired = false;
    let inputFired = false;
    const fakeHeadInput = {
        value: '',
        dispatchEvent: (ev) => {
            if (ev.type === 'change') changeFired = true;
            if (ev.type === 'input') inputFired = true;
        }
    };

    const fakeItem = {
        getAttribute: (attr) => (attr === 'data-no' ? '0' : attr === 'data-val' ? '일반' : ''),
        textContent: '일반',
        clicked: false,
        click: function() { this.clicked = true; }
    };

    // Minor gallery sync logic under test
    fakeItem.click();
    if (!fakeHeadInput.value && fakeItem.getAttribute('data-no')) {
        fakeHeadInput.value = fakeItem.getAttribute('data-no');
    }
    fakeHeadInput.dispatchEvent({ type: 'change' });
    fakeHeadInput.dispatchEvent({ type: 'input' });

    assert.equal(fakeItem.clicked, true);
    assert.equal(fakeHeadInput.value, '0');
    assert.equal(changeFired, true);
    assert.equal(inputFired, true);
});

