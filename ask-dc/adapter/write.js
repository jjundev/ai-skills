import { cli, Strategy } from '@jackwener/opencli/registry';
import { CommandExecutionError, ArgumentError } from '@jackwener/opencli/errors';
import { mainGalleryWriteUrl, navigateToDcinside, requireBoundedInteger, requireGalleryId } from './common.js';

cli({
    site: 'dcinside',
    name: 'write',
    access: 'write',
    description: 'Compose and submit a new post to a DCInside gallery',
    domain: 'gall.dcinside.com',
    strategy: Strategy.UI,
    browser: true,
    navigateBefore: false,
    args: [
        { name: 'galleryId', type: 'string', required: true, positional: true, help: 'Gallery ID to post in' },
        { name: 'title', type: 'string', required: true, help: 'Post title' },
        { name: 'content', type: 'string', required: true, help: 'Post body text or HTML' },
        { name: 'name', type: 'string', default: 'ㅇㅇ', help: 'Nickname for anonymous post (if not logged in)' },
        { name: 'password', type: 'string', default: '1234', help: 'Password for anonymous post (if not logged in)' },
        { name: 'head', type: 'string', help: 'Head category code or name (e.g. 10 or 일반)' },
        { name: 'mgallery', type: 'bool', default: false, help: 'Target minor gallery' },
        { name: 'no-submit', type: 'bool', default: false, help: 'Fill form only without clicking submit (useful for manual review or CAPTCHA resolution)' },
        { name: 'wait-timeout', type: 'int', default: 30, help: 'Seconds to wait for redirect or manual CAPTCHA completion (1-300s)' },
    ],
    columns: ['success', 'galleryId', 'title', 'url', 'message'],
    func: async (page, args) => {
        const galleryId = requireGalleryId(args.galleryId);
        const title = String(args.title ?? '').trim();
        const content = String(args.content ?? '').trim();
        const nickname = String(args.name || 'ㅇㅇ').trim();
        const password = String(args.password || '1234').trim();
        const head = args.head ? String(args.head).trim() : null;
        const isMinor = Boolean(args.mgallery);
        const noSubmit = Boolean(args['no-submit'] ?? (args.submit === false));
        const waitTimeoutSec = requireBoundedInteger(args['wait-timeout'], 30, 1, 300, 'wait-timeout');

        if (!title) throw new ArgumentError('title must not be empty');
        if (!content) throw new ArgumentError('content must not be empty');

        const writeUrl = mainGalleryWriteUrl(galleryId, { isMinor });
        // Disable checkAuth because write form contains anonymous password input and sidebar login form
        await navigateToDcinside(page, writeUrl, 'DCInside post compose', { checkAuth: false });

        // Suppress browser modal dialogs (alert, confirm) during fill to avoid CDP hang/crash
        await page.evaluate(() => {
            window.__origAlert = window.alert;
            window.__origConfirm = window.confirm;
            window.alert = (msg) => console.warn('[DCInside OpenCLI] Suppressed alert dialog:', msg);
            window.confirm = () => true;
        });

        // Form filling inside the browser page with retry loop for editor attachment
        let fillResult = null;
        for (let attempt = 0; attempt < 3; attempt++) {
            fillResult = await page.evaluate(async ({ title, content, nickname, password, head }) => {
                // 1. Check title input
                const subjectInput = document.querySelector('input[name="subject"], #subject');
                if (!subjectInput) return { success: false, reason: 'Subject input not found on page' };

                subjectInput.value = title;
                subjectInput.dispatchEvent(new Event('input', { bubbles: true }));
                subjectInput.dispatchEvent(new Event('change', { bubbles: true }));

                // 2. Anonymous author name and password inputs
                const nameInput = document.querySelector('input[name="name"], #name');
                if (nameInput && !nameInput.disabled && nameInput.type !== 'hidden') {
                    nameInput.value = nickname;
                    nameInput.dispatchEvent(new Event('input', { bubbles: true }));
                    nameInput.dispatchEvent(new Event('change', { bubbles: true }));
                }

                const pwInput = document.querySelector('input[name="password"], #password');
                if (pwInput && !pwInput.disabled && pwInput.type !== 'hidden') {
                    pwInput.value = password;
                    pwInput.dispatchEvent(new Event('input', { bubbles: true }));
                    pwInput.dispatchEvent(new Event('change', { bubbles: true }));
                }

                // 3. Head category selection (by value or visible text match)
                if (head) {
                    const headSelect = document.querySelector('select[name="headtext"], select#headtext');
                    if (headSelect && headSelect.tagName === 'SELECT') {
                        let matched = false;
                        for (const opt of headSelect.options) {
                            if (opt.value === head || opt.textContent.trim() === head) {
                                headSelect.value = opt.value;
                                matched = true;
                                break;
                            }
                        }
                        if (matched) {
                            headSelect.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    } else {
                        // Minor gallery list-based head category (e.g. ul.subject_list li)
                        const headItems = document.querySelectorAll('ul.subject_list li, .subject_option li');
                        for (const item of headItems) {
                            const val = item.getAttribute('data-val') || '';
                            const no = item.getAttribute('data-no') || '';
                            const text = item.textContent.trim();
                            if (no === head || val === head || val.includes(head) || text.includes(head)) {
                                item.click();
                                const headInput = document.querySelector('input[name="headtext"], #headtext');
                                if (headInput) {
                                    if (!headInput.value && no) headInput.value = no;
                                    headInput.dispatchEvent(new Event('change', { bubbles: true }));
                                    headInput.dispatchEvent(new Event('input', { bubbles: true }));
                                }
                                break;
                            }
                        }
                    }
                }

                // 4. Content injection (WYSIWYG iframe, textarea, or Summernote)
                let contentSet = false;
                const iframe = document.querySelector('iframe[name="tx_canvas_wysiwyg"], #tx_canvas_wysiwyg, iframe.tx_canvas_wysiwyg');
                if (iframe && iframe.contentDocument && iframe.contentDocument.body) {
                    iframe.contentDocument.body.innerHTML = content.replace(/\n/g, '<br>');
                    contentSet = true;
                }

                const memoTextarea = document.querySelector('textarea[name="memo"], #memo');
                if (memoTextarea) {
                    memoTextarea.value = content;
                    memoTextarea.dispatchEvent(new Event('input', { bubbles: true }));
                    memoTextarea.dispatchEvent(new Event('change', { bubbles: true }));
                    contentSet = true;
                }

                const noteEditable = document.querySelector('.note-editable');
                if (noteEditable) {
                    noteEditable.innerHTML = content.replace(/\n/g, '<br>');
                    noteEditable.dispatchEvent(new Event('input', { bubbles: true }));
                    if (typeof $ !== 'undefined' && $('#memo').length && typeof $('#memo').summernote === 'function') {
                        try { $('#memo').summernote('code', content.replace(/\n/g, '<br>')); } catch {}
                    }
                    contentSet = true;
                }

                // 5. CAPTCHA detection
                const hasCaptcha = Boolean(document.querySelector('.kcaptcha, #kcaptcha, #captcha_box, input[name="code"]'));

                return { success: contentSet, hasCaptcha };
            }, { title, content, nickname, password, head });

            if (fillResult?.success) break;
            await page.wait(1);
        }

        if (!fillResult?.success) {
            throw new CommandExecutionError(`Failed to populate post content: ${fillResult?.reason ?? 'Editor DOM not ready'}`);
        }

        // If no-submit requested, restore native dialogs and pre-condition anti-bot counters, then return
        if (noSubmit) {
            await page.evaluate(() => {
                // 1. Restore native alert and confirm
                if (window.__origAlert) window.alert = window.__origAlert;
                else delete window.alert;
                if (window.__origConfirm) window.confirm = window.__origConfirm;
                else delete window.confirm;

                // Fallback to iframe native prototype if still tainted
                if (!window.alert || window.alert.toString().indexOf('[native code]') === -1) {
                    try {
                        const f = document.createElement('iframe');
                        f.style.display = 'none';
                        document.body.appendChild(f);
                        window.alert = f.contentWindow.alert.bind(window);
                        window.confirm = f.contentWindow.confirm.bind(window);
                    } catch {}
                }

                // 2. Pre-condition anti-bot interaction counters on submit button
                const submitBtn = document.querySelector(
                    '.btn_blue.btn_svc.write, .btn_blue.btn_svc.write_btn, .btn_apply, button[class*="write"]'
                );
                if (submitBtn) {
                    for (let i = 0; i < 5; i++) {
                        submitBtn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                        submitBtn.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
                    }
                }
            });

            return [{
                success: true,
                galleryId,
                title,
                url: writeUrl,
                message: 'Form filled successfully in browser. Submit manually after review.',
            }];
        }

        // If CAPTCHA is present, do NOT submit immediately to avoid triggering client validation alert
        if (fillResult.hasCaptcha) {
            console.warn('[DCInside OpenCLI] CAPTCHA detected. Please complete CAPTCHA in Chrome browser.');
        } else {
            // Attempt submission if no CAPTCHA is actively displayed
            await page.evaluate(() => {
                const submitBtn = document.querySelector(
                    '.btn_blue.btn_svc.write, .btn_blue.btn_svc.write_btn, .btn_apply, button[class*="write"], a[class*="write"], form#write input[type="submit"]'
                );
                if (submitBtn) {
                    submitBtn.click();
                } else {
                    const form = document.querySelector('form#write, form[name="write"]');
                    if (form) form.submit();
                }
            });
        }

        // Wait for redirect to view page or user manual CAPTCHA resolution
        const startTime = Date.now();
        let finalUrl = '';
        let redirected = false;

        while (Date.now() - startTime < waitTimeoutSec * 1000) {
            await page.wait(2);
            finalUrl = await page.evaluate('window.location.href').catch(() => '');
            if (finalUrl.includes('/board/view/') || finalUrl.includes('/mgallery/board/view/')) {
                redirected = true;
                break;
            }
        }

        if (!redirected) {
            return [{
                success: false,
                galleryId,
                title,
                url: finalUrl,
                message: fillResult.hasCaptcha
                    ? 'CAPTCHA required. Please resolve CAPTCHA and submit in the Chrome browser window.'
                    : 'Submitted, but did not redirect to post view within timeout. Check Chrome window.',
            }];
        }

        return [{
            success: true,
            galleryId,
            title,
            url: finalUrl,
            message: 'Post submitted and published successfully.',
        }];
    },
});
