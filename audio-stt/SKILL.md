---
name: audio-stt
description: [Gemini Only] Transcribe speech verbatim via native multimodal perception (`view_file`). Strictly requires Gemini models; fails on Claude/GPT. Use when user wants STT, transcription, or 음성 텍스트 변환 on media files (.mp3, .wav, .m4a, .mov, etc.).
---

# Audio STT (Direct Multimodal Transcription)

Transcribe speech from audio/video files verbatim using native multimodal perception (`view_file`), bypassing external Whisper APIs.

> [!IMPORTANT]
> **Gemini 전용 스킬**: 본 스킬은 Gemini 모델의 네이티브 비디오/오디오 멀티모달(`view_file`) 인식 기능에 전적으로 의존합니다. 비디오/오디오 입력을 지원하지 않는 Claude, GPT 등의 비-Gemini 모델에서는 절대 실행하지 마십시오.

---

## 🧠 Core Principles

0. **Model Compatibility Gate (STRICT - GEMINI ONLY)**:
   - This skill strictly requires a Gemini multimodal model (e.g. Gemini 1.5, Gemini 2.0, Gemini 2.5, Gemini 3.x).
   - If the active model is NOT Gemini (e.g. Claude 3.5/3.7, GPT-4o, o1/o3, Llama, DeepSeek):
     - **STOP IMMEDIATELY BEFORE EXECUTING ANY COMMANDS.**
     - Do NOT run `ffmpeg`, `ffprobe`, create temp directories, or call `view_file`.
     - Output the following notice to the user and terminate the task immediately:
       > ⚠️ **audio-stt 스킬은 Gemini 모델 전용입니다.**  
       > 본 스킬은 Gemini의 네이티브 오디오 멀티모달 인식(`view_file`)을 사용하므로, 비디오/오디오 바이너리 입력을 처리할 수 없는 Claude 및 GPT 모델에서는 동작하지 않습니다.  
       > 모델 선택을 **Gemini(Gemini 2.5 / 3.0 등)**로 변경하신 후 다시 요청해 주세요.
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
7. **Speaker Diarization (화자 설명 필수)**:
   - **Trigger**: the user's prompt mentions speakers (e.g., "화자 구분", "화자 분리", "누가 말했는지", "대화자", `--speakers`, `-s`). If no such expression appears, transcribe as a single stream with NO speaker labels.
   - **Gate (BEFORE any ffmpeg/preprocessing)**: diarization requires a speaker description for every speaker, in the form `라벨: 특징` (특징 = 성별·연령대·역할·말투·음색 중 1개 이상). Example: `--speakers "진행자: 30대 남성, 낮은 목소리 / 게스트: 40대 여성, 교수"`.
     - Description missing, or names only (no 특징) → STOP, do not transcribe, and ask the user for `라벨: 특징` per speaker. NEVER invent labels such as "화자1/화자2".
     - Only one speaker described → skip diarization and transcribe normally.
   - **Labels**: use the roster's label spelling exactly. If a speaker cannot be matched to the roster, use the single label `화자?` (never guess the nearest speaker, never invent new labels).
   - **Format**: start a new paragraph on every speaker change and prefix with `**라벨:**`. With timestamps, keep `MM:SS` on its own line followed by the labeled line.

---

## 🛠️ Workflow A: Single File (<= 10 Minutes)

0. **Model Compatibility Check (Gate 0)**:
   - Verify active agent model is Gemini. If non-Gemini (Claude, GPT, etc.), emit Gate 0 notice and STOP immediately without running any commands.

1. **Wrap in MP4 Container (Exact Duration Match)**:
   ```bash
   dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "<AUDIO_PATH>")
   ffmpeg -y -f lavfi -i color=c=black:s=320x240:r=1 -i "<AUDIO_PATH>" -t "$dur" -c:v libx264 -c:a aac -b:a 128k "<WORKSPACE>/_temp_stt.mp4"
   ```
2. **Perceive via `view_file`**: Call `view_file` on `_temp_stt.mp4`.
   - **Default (Plain Text)**: Transcribe all spoken content verbatim into coherent paragraphs (2~4 sentences per paragraph, separated by blank lines `\n\n`) without `MM:SS` timestamps.
   - **If diarization is triggered** (Principle 7, gate passed): keep the speaker roster in view and label every utterance per the Speaker Diarization format.
   - **If `--timestamps` / `-t` specified**: Transcribe with `MM:SS` timestamps preceding each speech segment.
3. **Save Transcript**: Write verbatim markdown to `<AUDIO_DIR>/<NAME>.md`.
4. **Cleanup**: `rm -f "<WORKSPACE>/_temp_stt.mp4"`

---

## ⚡ Workflow B: Long Audio (> 10 Minutes) with Parallel Subagents

0. **Model Compatibility Check (Gate 0)**:
   - Verify active agent model is Gemini. If non-Gemini (Claude, GPT, etc.), emit Gate 0 notice and STOP immediately without running any commands.

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
   - **Diarization Variant (Principle 7, gate passed)**: inject the IDENTICAL speaker roster block into every subagent prompt and replace instruction 3 with:
     ```text
     Speakers (use these exact labels; unmatched voice -> `화자?`):
     - <라벨1>: <특징>
     - <라벨2>: <특징>

     3. Start a new paragraph on every speaker change, prefixed with `**라벨:**`. No timestamps unless instructed. Do not invent labels.
     ```
     With timestamps, put `MM:SS` on its own line, then the `**라벨:**` line below it.
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
   - **With Diarization (`--speakers`)**: pass the comma-separated labels only (not descriptions); the script warns on labels outside the roster (warning only, exit code 0):
     ```bash
     python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/scripts/merge_transcripts.py --dir "<OUTPUT_DIR>" --prefix "<NAME>" --speakers "진행자,게스트"
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

### With Diarization (`--speakers`)

```text
**진행자:** 오늘 주제는 채용 시장입니다.

**게스트:** 네, 변화가 빠릅니다.
```

With `-t`:

```text
00:12
**진행자:** 오늘 주제는 채용 시장입니다.
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

- [ ] Active model verified as Gemini before running any commands (or stopped immediately with Gate 0 notice if non-Gemini).
- [ ] Zero external or local STT models used (strictly no Whisper, mlx-whisper, faster-whisper, or external APIs).
- [ ] Audio preprocessed with 1-fps black MP4 wrapper matching exact audio duration (`-t "$dur"`).
- [ ] Verbatim transcription from start to finish without omission.
- [ ] Subagents operate in a single pass without tangent diagnostic loops or tool searches.
- [ ] Any safety filter triggers resolved exclusively via sub-slicing (2~3 min) and native `view_file`.
- [ ] Verbatim transcription without timestamps by default (or with `MM:SS` when `--timestamps` is requested).
- [ ] Saved as a single unified `.md` transcript (`<NAME>.md`) without intermediate segment metadata or temporary file lists.
- [ ] Diarization only when speakers are mentioned; never started without a `라벨: 특징` description per speaker (asked instead).
- [ ] Speaker labels identical across all parts; unmatched voices use `화자?` only.
- [ ] Intermediate chunk files cleaned up by default (or preserved only if `--keep-parts` was requested).
