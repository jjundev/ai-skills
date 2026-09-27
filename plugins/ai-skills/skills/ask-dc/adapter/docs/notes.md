## 2026-08-15

- Strategy is `UI`: OpenCLI browser analysis on a public general-gallery post found no stable JSON XHR candidate.
- General gallery list rows: `.gall_list tbody tr.ub-content`; post rows expose `data-no` and a `/board/view/?id=...&no=...` link.
- Post header/body: `.gallview_head`, `.gall_writer`, `.writing_view_box .write_div`.
- Comments: `li[id^="comment_li_"]`; replies: `li[id^="reply_li_"]` nested in `ul.reply_list[p-no]`; `.dory` is an advertisement row and is skipped.
- Authentication is manual through the connected Chrome profile. No cookies, tokens, or user-specific data are recorded here.

## 2026-09-07

- Strategy is `UI`: DCInside write functionality uses browser automation (`Strategy.UI`) to navigate to `/board/write/` or `/mgallery/board/write/` via the connected Chrome session.
- Editor & Form Injection:
  - Title is filled into `input[name="subject"], #subject`.
  - Anonymous post author nickname and password are set in `input[name="name"]` and `input[name="password"]` (defaulting to "ㅇㅇ" and "1234" if not specified and fields are editable).
  - Category head selection is handled via `select[name="headtext"]` matching code or option label.
  - Body content is injected into the Daum/SmartEditor WYSIWYG iframe (`iframe[name="tx_canvas_wysiwyg"]` body innerHTML with `<br>` conversion) and mirrored to `textarea[name="memo"]`.
- Modal Alert Suppression:
  - `window.alert` and `window.confirm` are overridden in the browser page context (`window.alert = (msg) => console.warn(...)`, `window.confirm = () => true`) to prevent CDP hangs or crashes caused by DCInside's native confirmation/validation dialogs.
- CAPTCHA Handling:
  - Form checks for `.kcaptcha, #kcaptcha, #captcha_box, input[name="code"]`.
  - When CAPTCHA is present, automated submission is deferred to avoid trigger failures and allow the user to resolve the CAPTCHA in the open Chrome window.
  - `--no-submit` flag allows dry-run form filling for manual review prior to submission.
  - `--wait-timeout` (default: 30s) polls for navigation to the submitted post view URL (`/board/view/` or `/mgallery/board/view/`).


## 2026-09-27

- Strategy for `list`/`read` is now `PUBLIC` (`browser: false`): both are plain HTTPS requests handled by `adapter/http.js`, shared with the standalone CLI `scripts/dc.mjs`. `write` stays `UI`.
- List and post pages are server-rendered; comments come from `POST /board/comment/` (JSON) using the `e_s_n_o` and `_GALLTYPE_` hidden inputs from the post page. See `endpoints.json`.
- Gallery type detection: minor galleries JS-redirect (`location.replace`, query dropped) from the general path; mini galleries 404 there, so the core retries `/mini/` once on 404.
- Requests are sequential with a 300 ms gap and one retry on 429/5xx/network errors. 40 requests at 8-way concurrency all returned 200 during probing.
