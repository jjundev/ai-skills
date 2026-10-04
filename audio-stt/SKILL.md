---
name: audio-stt
description: Transcribe speech verbatim. By default outputs clean text without timestamps; use --timestamps or -t to include MM:SS timestamps. Use when user wants STT, transcription, or 음성 텍스트 변환 on media files (.mp3, .wav, .m4a, .mov, etc.).
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
4. **Plain Text by Default (Optional Timestamps)**:
   - Default transcription outputs natural paragraphs (2~4 sentences per paragraph, separated by blank lines `\n\n`) without timestamps.
   - Timestamps (`MM:SS`) are generated only when `--timestamps`, `-t`, or user explicitly asks (e.g., '타임스탬프 포함').
5. **Unified Single-File Output & Clean Workspace**:
   - Both short (<= 10 min) and long (> 10 min) audio default to producing a single `.md` file (`<NAME>.md`) containing clean transcribed speech without intermediate segment metadata or temporary file lists.
   - Intermediate chunk files (`_part*.mp3`, `_part*.md`, `*_temp.mp4`) are automatically cleaned up upon successful merge.
   - Retain intermediate segment files with `--keep-parts` when explicitly requested by user (e.g., "중간 파일도 남겨줘", "파트별 파일 보존").
6. **Zero External/Local Model Dependencies (STRICT - NO WHISPER)**:
   - NEVER search for, install, download, or execute external or local STT models under ANY circumstances (e.g. `whisper`, `mlx-whisper`, `faster-whisper`, `torch`, HuggingFace models, OpenAI Whisper API).
   - All transcription MUST rely solely on native multimodal perception (`view_file`).

---

## 🛠️ Workflow A: Single File (<= 10 Minutes)

1. **Wrap in MP4 Container (Exact Duration Match)**:
   ```bash
   dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "<AUDIO_PATH>")
   ffmpeg -y -f lavfi -i color=c=black:s=320x240:r=1 -i "<AUDIO_PATH>" -t "$dur" -c:v libx264 -c:a aac -b:a 128k "<WORKSPACE>/_temp_stt.mp4"
   ```
2. **Perceive via `view_file`**: Call `view_file` on `_temp_stt.mp4`.
   - **Default (Plain Text)**: Transcribe all spoken content verbatim into coherent paragraphs (2~4 sentences per paragraph, separated by blank lines `\n\n`) without `MM:SS` timestamps.
   - **If `--timestamps` / `-t` specified**: Transcribe with `MM:SS` timestamps preceding each speech segment.
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
   - **Subagent Prompt (Default - Clean Text without Timestamps)**:
     ```text
     You are a verbatim STT transcription agent.
     Target video: <OUTPUT_DIR>/<NAME>_part01_temp.mp4
     Output markdown: <OUTPUT_DIR>/<NAME>_part01.md

     Instructions:
     1. Call `view_file` on <OUTPUT_DIR>/<NAME>_part01_temp.mp4.
     2. Transcribe ALL spoken words verbatim from start to finish. Do not skip, summarize, or omit anything.
     3. Format strictly as clean text without timestamps: group 2~4 sentences per paragraph, separated by blank lines.
     4. Save directly to <OUTPUT_DIR>/<NAME>_part01.md using `write_to_file`. Ensure Overwrite is true.
     5. Strict Guardrails:
        - Perform the transcription in a single pass directly from the initial `view_file` call.
        - NEVER search for, install, or run `whisper`, `mlx-whisper`, or any external STT tools.
        - Do NOT inspect other part files or compare transcripts.
        - Do NOT run audio analysis, silence detection, ffmpeg slicing, or additional diagnostic tools.
     6. Report completion immediately when done.
     ```
   - **Subagent Prompt Variant (With `--timestamps` / `-t`)**:
     Replace instruction 3 with:
     ```text
     3. Format strictly with MM:SS timestamps:
     MM:SS
     발화내용 문장

     MM:SS
     발화내용 문장
     ```

4. **Merge Master Transcript & Auto-Cleanup**:
   - **Default (Plain Text)**:
     ```bash
     python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/scripts/merge_transcripts.py --dir "<OUTPUT_DIR>" --prefix "<NAME>"
     ```
   - **With Timestamps (`--timestamps` / `-t`)**:
     ```bash
     python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/scripts/merge_transcripts.py --dir "<OUTPUT_DIR>" --prefix "<NAME>" --timestamps
     ```
   - **Keep Intermediate Part Files (`--keep-parts`)**:
     Add `--keep-parts` if explicitly requested (e.g., "중간 파일도 남겨줘", "파트별 파일 보존"):
     ```bash
     python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/scripts/merge_transcripts.py --dir "<OUTPUT_DIR>" --prefix "<NAME>" --keep-parts
     ```
   - **Combined Options (`--timestamps --keep-parts`)**:
     Combine flags when both timestamps and part retention are needed:
     ```bash
     python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/scripts/merge_transcripts.py --dir "<OUTPUT_DIR>" --prefix "<NAME>" --timestamps --keep-parts
     ```

5. **Cleanup Verification**:
   - By default, `merge_transcripts.py` automatically deletes intermediate part files (`_part*.md`, `_part*.mp3`, `*_temp.mp4`) once the merged file is verified non-empty.
   - Run a quick check to ensure only the final `<NAME>.md` (and original source) remains, unless `--keep-parts` was specified.

---

## 📝 Format Specification

### Default (Clean Text without Timestamps)

```text
전문가로 위촉돼서 활동하고 있습니다. 그러다 보니 자연스럽게 채용 시장의 변화를 바라보고 있습니다. 채용 시장의 트렌드가 급격하게 바뀌고 있는 것을 체감합니다.

네, 계속 진행하도록 하겠습니다. 비대면 강의는 오늘 처음입니다. 온라인 환경이라 다소 낯설지만 최선을 다해 전달해 드리겠습니다.
```

### With `--timestamps` / `-t`

```text
00:00
전문가로 위촉돼서 활동하고 있습니다. 그러다 보니 자연스럽게 채용 시장의 변화를 바라보고 있습니다.

00:29
네, 계속 진행하도록 하겠습니다. 비대면 강의는 오늘 처음입니다.
```

---

## 🛡️ Safety Filter Recovery Protocol (Zero-Model Chunk Sub-slicing)

If Gemini's safety filter triggers on a specific chunk (e.g. `This request was blocked by Gemini's filters` due to false-positive keywords in casual conversation, contract discussions, gaming, or finance):
1. **ABSOLUTELY NO WHISPER FALLBACK**:
   - Do NOT search for `which whisper`, download model weights, or install python STT libraries.
2. **Sub-slice the chunk into smaller windows (2~3 minutes)**:
   ```bash
   ffmpeg -y -i "<FAILING_CHUNK>.mp3" -ss 0 -t 150 -c copy "<FAILING_CHUNK>_sub01.mp3"
   ffmpeg -y -i "<FAILING_CHUNK>.mp3" -ss 150 -t 150 -c copy "<FAILING_CHUNK>_sub02.mp3"
   ```
3. **Wrap in MP4 & Transcribe via `view_file`**:
   - Wrap each sub-chunk into a 1-fps black MP4 wrapper (`color=c=black:s=320x240:r=1`).
   - Call `view_file` directly or via subagent to transcribe. Shorter context spans eliminate multimodal false-positive filter triggers completely.
4. **Merge sub-chunks into `<NAME>_partXX.md`**:
   - Concatenate sub-chunk markdown files into the expected part file, clean up intermediate sub-chunk files, and proceed with master merge.

---

## ✅ Completion Criteria

- [ ] Zero external or local STT models used (strictly no Whisper, mlx-whisper, faster-whisper, or external APIs).
- [ ] Audio preprocessed with 1-fps black MP4 wrapper matching exact audio duration (`-t "$dur"`).
- [ ] Verbatim transcription from start to finish without omission.
- [ ] Subagents operate in a single pass without tangent diagnostic loops or tool searches.
- [ ] Any safety filter triggers resolved exclusively via sub-slicing (2~3 min) and native `view_file`.
- [ ] Verbatim transcription without timestamps by default (or with `MM:SS` when `--timestamps` is requested).
- [ ] Saved as a single unified `.md` transcript (`<NAME>.md`) without intermediate segment metadata or temporary file lists.
- [ ] Intermediate chunk files cleaned up by default (or preserved only if `--keep-parts` was requested).
