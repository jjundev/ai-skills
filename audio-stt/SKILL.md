---
name: audio-stt
description: Transcribe speech from audio/video files verbatim using direct multimodal perception without external Whisper. Use when user wants STT, transcription, or 음성 텍스트 변환 on media files (.mp3, .wav, .m4a, .mov, etc.).
---

# Audio STT (Direct Multimodal Transcription)

Transcribe speech from audio/video files verbatim using native multimodal perception (`view_file`), bypassing external Whisper APIs.

---

## 🧠 Core Principles

1. **Verbatim Fidelity**: Transcribe every spoken utterance word-for-word without skipping, summarizing, or rephrasing.
2. **Deterministic Preprocessing (MP4 Wrapper)**:
   - `view_file` ingests video/image/PDF binaries directly into the model's multimodal context. Raw audio formats (`.mp3`, `.wav`, `.m4a`) can hit MIME-type delivery limits.
   - Wrapping audio with a minimal 1-fps black canvas video (`color=c=black:s=320x240:r=1`) in an `.mp4` container allows direct audio listening with zero visual overhead and zero external API fees.
3. **10-Minute Segmentation for Long Media**:
   - For audio longer than 10 minutes, slice into 10-minute (600s) chunks to prevent context truncation and enable **Parallel Subagent** execution.
4. **Unified Single-File Output & Clean Workspace**:
   - Both short (<= 10 min) and long (> 10 min) audio default to producing a single `.md` file (`<NAME>.md`).
   - Intermediate chunk files (`_part*.mp3`, `_part*.md`, `*_temp.mp4`) are automatically cleaned up upon successful merge.
   - Retain intermediate segment files with `--keep-parts` when explicitly requested by user (e.g., "중간 파일도 남겨줘", "파트별 파일 보존").

---

## 🛠️ Workflow A: Single File (<= 10 Minutes)

1. **Wrap in MP4 Container (Exact Duration Match)**:
   ```bash
   dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "<AUDIO_PATH>")
   ffmpeg -y -f lavfi -i color=c=black:s=320x240:r=1 -i "<AUDIO_PATH>" -t "$dur" -c:v libx264 -c:a aac -b:a 128k "<WORKSPACE>/_temp_stt.mp4"
   ```
2. **Perceive via `view_file`**: Call `view_file` on `_temp_stt.mp4` and transcribe all spoken content with `MM:SS` timestamps.
3. **Save Transcript**: Write verbatim markdown to `<AUDIO_DIR>/<NAME>.md`.
4. **Cleanup**: `rm -f "<WORKSPACE>/_temp_stt.mp4"`

---

## ⚡ Workflow B: Long Audio (> 10 Minutes) with Parallel Subagents

1. **Split into 10-Minute Chunks**:
   ```bash
   mkdir -p "<OUTPUT_DIR>"
   ffmpeg -y -i "<SOURCE_PATH>" -vn -c:a libmp3lame -b:a 192k \
     -f segment -segment_time 600 -segment_start_number 1 -reset_timestamps 1 \
     "<OUTPUT_DIR>/<NAME>_part%02d.mp3"
   ```

2. **Batch Wrap into MP4s (Parallel & Exact Duration)**:
   ```bash
   for f in "<OUTPUT_DIR>"/*_part*.mp3; do
     (
       dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
       ffmpeg -y -f lavfi -i color=c=black:s=320x240:r=1 \
         -i "$f" -t "$dur" -c:v libx264 -c:a aac -b:a 128k "${f%.mp3}_temp.mp4" -loglevel error
     ) &
   done
   wait
   ```

3. **Dispatch Parallel Subagents**: Concurrently spawn one `self` subagent per part.
   - **Subagent Prompt**:
     ```text
     You are a verbatim STT transcription agent.
     Target video: <OUTPUT_DIR>/<NAME>_part01_temp.mp4
     Output markdown: <OUTPUT_DIR>/<NAME>_part01.md

     Instructions:
     1. Call `view_file` on `<OUTPUT_DIR>/<NAME>_part01_temp.mp4`.
     2. Transcribe ALL spoken words verbatim from 00:00 to the end. Do not skip, summarize, or omit anything.
     3. Format strictly as:
     MM:SS
     발화내용 문장

     MM:SS
     발화내용 문장

     4. Save directly to `<OUTPUT_DIR>/<NAME>_part01.md` using `write_to_file`. Ensure Overwrite is true.
     5. Strict Guardrails:
        - Perform the transcription in a single pass directly from the initial `view_file` call.
        - Do NOT inspect other part files or compare transcripts.
        - Do NOT run audio analysis, silence detection, ffmpeg slicing, or additional diagnostic tools.
     6. Report completion immediately when done.
     ```

4. **Merge Master Transcript & Auto-Cleanup**:
   - Default (Single unified `<NAME>.md` output, cleans up chunk files):
     ```bash
     python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/scripts/merge_transcripts.py --dir "<OUTPUT_DIR>" --prefix "<NAME>"
     ```
   - If the user explicitly asks to keep intermediate part files (e.g. "중간 파일도 남겨줘", "파트별 파일 보존"):
     ```bash
     python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/scripts/merge_transcripts.py --dir "<OUTPUT_DIR>" --prefix "<NAME>" --keep-parts
     ```

5. **Cleanup Verification**:
   - By default, `merge_transcripts.py` automatically deletes intermediate part files (`_part*.md`, `_part*.mp3`, `*_temp.mp4`) once the merged file is verified non-empty.
   - Run a quick check to ensure only the final `<NAME>.md` (and original source) remains, unless `--keep-parts` was specified.

---

## 📝 Format Specification

```text
00:00
전문가로 위촉돼서 활동하고 있습니다. 그러다 보니 자연스럽게 채용 시장의 변화를 바라보고 있습니다.

00:29
네, 계속 진행하도록 하겠습니다. 비대면 강의는 오늘 처음입니다.
```

---

## ✅ Completion Criteria

- [ ] Audio preprocessed with 1-fps black MP4 wrapper matching exact audio duration (`-t "$dur"`).
- [ ] Verbatim transcription from 00:00 to finish without omission.
- [ ] Subagents operate in a single pass without tangent diagnostic loops.
- [ ] Formatted strictly with `MM:SS\n발화내용\n\n`.
- [ ] Saved as a single unified `.md` transcript (`<NAME>.md`) for both short and long audio.
- [ ] Intermediate chunk files cleaned up by default (or preserved only if `--keep-parts` was requested).
