#!/usr/bin/env node
/**
 * write-dc automated image & GIF uploader script
 *
 * Usage:
 *   node attach-images.mjs --session dcinside --draft <draft.txt> --images <img1> <img2> ...
 *
 * Automates uploading images (including large GIFs up to 10MB) directly into the active
 * DCInside browser writing session, replacing placeholders like [이미지 N: ...] with
 * the uploaded image tags and syncing to textarea[name="memo"].
 */

import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

function parseArgs() {
    const args = process.argv.slice(2);
    let session = 'dcinside';
    let draftPath = null;
    const images = [];

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--session' && args[i + 1]) {
            session = args[++i];
        } else if (args[i] === '--draft' && args[i + 1]) {
            draftPath = args[++i];
        } else if (args[i] === '--images') {
            while (i + 1 < args.length && !args[i + 1].startsWith('--')) {
                images.push(args[++i]);
            }
        }
    }

    return { session, draftPath, images };
}

const { session, draftPath, images } = parseArgs();

if (images.length === 0) {
    console.error('Error: No image files provided. Usage: node attach-images.mjs --images <file1> <file2> ...');
    process.exit(1);
}

function evalInBrowser(code) {
    const tmpFile = `/tmp/dc_eval_${Date.now()}_${Math.random().toString(36).slice(2, 6)}.js`;
    fs.writeFileSync(tmpFile, code);
    try {
        return execSync(`opencli browser ${session} eval "$(cat ${tmpFile})"`, {
            encoding: 'utf8',
            maxBuffer: 20 * 1024 * 1024
        });
    } finally {
        try { fs.unlinkSync(tmpFile); } catch {}
    }
}

console.log(`[write-dc] Starting automated upload for ${images.length} assets into session: "${session}"...`);

// 1. Prepare DOM helper
const setupJs = `
(() => {
  if (!window.attachments) window.attachments = [];
  window.__fileChunks = [];

  window.__uploadFileFromBase64 = function(base64, filename, mimeType, placeholderId) {
    return new Promise((resolve) => {
      try {
        const byteCharacters = atob(base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const file = new File([byteArray], filename, { type: mimeType });

        const originalAttach = window.attach;
        let done = false;

        window.attach = function(data) {
          window.attach = originalAttach;
          done = true;

          // Important: DCInside requires data-tempno on every uploaded img element!
          // Omitting data-tempno causes server rejection with NZK1NTG (비공식 확장 프로그램 오류).
          if (placeholderId) {
            const el = document.getElementById(placeholderId);
            if (el) {
              el.outerHTML = '<p style="text-align: center; margin: 18px 0;"><img src="' + data.imageurl + '" data-tempno="' + data.file_temp_no + '" class="tx-daum-image" style="max-width: 100%; border-radius: 4px;" alt="' + filename + '"></p>';
            }
          }

          if (!window.attachments) window.attachments = [];
          window.attachments.push(data);
          if (typeof $ !== 'undefined' && $('#upload_status').length) {
            $('#upload_status').val('Y');
          }
          resolve(JSON.stringify({ success: true, filename, url: data.imageurl, tempno: data.file_temp_no }));
        };

        window.imageUploader(file);

        setTimeout(() => {
          if (!done) {
            window.attach = originalAttach;
            resolve(JSON.stringify({ success: false, reason: "upload_timeout" }));
          }
        }, 30000);
      } catch (err) {
        resolve(JSON.stringify({ success: false, error: err.message }));
      }
    });
  };

  return "SETUP_OK";
})()
`;

evalInBrowser(setupJs);

// 2. Upload images one by one
for (let i = 0; i < images.length; i++) {
    const imgPath = path.resolve(images[i]);
    const filename = path.basename(imgPath);
    const ext = path.extname(imgPath).toLowerCase();
    const mime = ext === '.gif' ? 'image/gif' : (ext === '.jpg' || ext === '.jpeg' ? 'image/jpeg' : 'image/png');
    const placeholderId = `img-placeholder-${i + 1}`;

    const buffer = fs.readFileSync(imgPath);
    const base64 = buffer.toString('base64');
    const sizeMb = (buffer.length / 1024 / 1024).toFixed(2);

    console.log(`[write-dc] (${i + 1}/${images.length}) Uploading ${filename} (${sizeMb} MB)...`);

    if (base64.length < 700000) {
        // Small file: Single step
        const uploadJs = `window.__uploadFileFromBase64("${base64}", "${filename}", "${mime}", "${placeholderId}")`;
        const res = evalInBrowser(uploadJs);
        console.log(`  -> Result: ${res.trim()}`);
    } else {
        // Large file (>500KB up to 10MB): Chunked upload
        evalInBrowser('window.__fileChunks = []; "RESET"');
        const chunkSize = 400000;
        const totalChunks = Math.ceil(base64.length / chunkSize);

        for (let c = 0; c < totalChunks; c++) {
            const chunk = base64.slice(c * chunkSize, (c + 1) * chunkSize);
            evalInBrowser(`window.__fileChunks.push("${chunk}"); "CHUNK_${c + 1}/${totalChunks}"`);
            process.stdout.write(`\r  Sending chunks: ${c + 1}/${totalChunks}`);
        }
        console.log('\n  All chunks transmitted. Calling imageUploader...');

        const finishJs = `
        (() => {
          const fullBase64 = window.__fileChunks.join("");
          window.__fileChunks = [];
          return window.__uploadFileFromBase64(fullBase64, "${filename}", "${mime}", "${placeholderId}");
        })()
        `;
        const res = evalInBrowser(finishJs);
        console.log(`  -> Result: ${res.trim()}`);
    }
}

// 3. Sync to textarea[name="memo"] and summernote
evalInBrowser(`
(() => {
  const note = document.querySelector('.note-editable');
  const memo = document.querySelector('textarea[name="memo"], #memo');
  if (note && memo) {
    memo.value = note.innerHTML;
    if (typeof $ !== 'undefined' && $('#memo').length) {
      $('#memo').val(note.innerHTML);
    }
  }
  return "SYNC_OK";
})()
`);

// 4. Activate browser in foreground (macOS)
try {
    execSync("osascript -e 'tell application \"Google Chrome\" to activate'");
} catch {}

console.log(`[write-dc] Successfully uploaded and embedded all ${images.length} assets!`);
