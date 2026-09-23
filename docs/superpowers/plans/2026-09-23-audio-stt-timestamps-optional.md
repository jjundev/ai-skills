# audio-stt 기본 타임스탬프 비활성화 및 옵션화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/audio-stt` 스킬의 기본 전사 출력을 타임스탬프 없는 깔끔한 줄글/단락으로 전환하고, `--timestamps` (`-t`) 인수를 통해 선택적으로 `MM:SS` 타임스탬프를 출력할 수 있도록 스킬 정의, 머지 스크립트, 단위 테스트를 개선합니다.

**Architecture:** 
- `scripts/merge_transcripts.py`에 `--timestamps` / `-t` boolean 플래그(기본값 `False`)를 추가하고, `False`일 때 타임스탬프 행 정제 및 파트 헤더 시간 표기 생략(`## Part 01`)을 수행합니다.
- `SKILL.md`의 단일 파일(Workflow A) 및 분할 파일(Workflow B) 서브에이전트 프롬프트에 기본 텍스트 모드와 타임스탬프 모드를 분기 정의합니다.
- 변경된 동작을 단위 테스트(`tests/test_merge_transcripts.py`)로 TDD 검증하고, `plugins/` 및 글로벌 `~/.gemini/config/skills/audio-stt/`에 동기화합니다.

**Tech Stack:** Python 3 (unittest, argparse, re), Bash, Markdown

**Spec:** Chat design spec from `/grill-yourself` session (Decision #6: Option A - `## Part 01` 헤더 유지 & 시간 생략; Decision #7: Option A - 2~4개 문장 단위 `\n\n` 단락 구분).

## Global Constraints

- Python 표준 라이브러리(`re`, `argparse`, `os`, `sys`, `unittest`)만 사용하며 외부 패키지 추가 의존성 금지.
- `audio-stt`의 기존 축어 전사(Verbatim fidelity) 및 자동 정리(`keep_parts=False`) 기능에 회귀가 없어야 함.
- 저장소 내 `audio-stt/`, `plugins/ai-skills/skills/audio-stt/`, 그리고 글로벌 `~/.gemini/config/skills/audio-stt/` 간 완전한 파일 일치 유지.

---

### Task 1: Update `merge_transcripts.py` with `--timestamps` flag (TDD)

**Files:**
- Modify: `audio-stt/scripts/merge_transcripts.py`
- Modify: `audio-stt/tests/test_merge_transcripts.py`

**Interfaces:**
- Consumes: `merge_transcripts(target_dir, prefix, segment_seconds, keep_parts, output_file, timestamps=False)`
- Produces: `merge_transcripts()` with `timestamps: bool = False`, supporting CLI `--timestamps` / `-t`.

- [ ] **Step 1: Write failing tests for timestamps=False and timestamps=True**

In `audio-stt/tests/test_merge_transcripts.py`:
- Update `test_merge_transcripts_timestamp_offset` to explicitly test with `timestamps=True`.
- Add `test_merge_transcripts_default_strips_timestamps`:
  - When `timestamps=False` (default), lines matching `^\d{1,2}:\d{2}$` are removed.
  - Part headers are formatted as `## Part 01\n\n` without `(00:00 ~ )`.
  - Spoken text content is preserved without excessive blank lines.
- Add `test_merge_transcripts_cli_timestamps_flag`:
  - Verify CLI accepts `--timestamps` and `-t` flags.

```python
    def test_merge_transcripts_default_strips_timestamps(self):
        """
        Verify that default timestamps=False strips MM:SS timestamp lines
        and outputs clean headers without time intervals.
        """
        part1_path = os.path.join(self.test_dir, "meeting_part01.md")
        part2_path = os.path.join(self.test_dir, "meeting_part02.md")

        with open(part1_path, "w", encoding="utf-8") as f:
            f.write("00:05\n안녕하세요 반갑습니다.\n\n00:20\n오늘 회의를 시작하겠습니다.\n")
        with open(part2_path, "w", encoding="utf-8") as f:
            f.write("01:10\n이어서 두 번째 안건입니다.\n")

        result = merge_transcripts(self.test_dir, prefix="meeting", keep_parts=True)
        self.assertTrue(os.path.isfile(result))

        with open(result, "r", encoding="utf-8") as f:
            content = f.read()

        # Headers should not contain (XX:00 ~ )
        self.assertIn("## Part 01\n", content)
        self.assertNotIn("## Part 01 (00:00 ~ )", content)
        self.assertIn("## Part 02\n", content)
        self.assertNotIn("## Part 02 (10:00 ~ )", content)

        # Timestamps should be stripped
        self.assertNotIn("00:05", content)
        self.assertNotIn("00:20", content)
        self.assertNotIn("11:10", content)

        # Content must be preserved
        self.assertIn("안녕하세요 반갑습니다.", content)
        self.assertIn("오늘 회의를 시작하겠습니다.", content)
        self.assertIn("이어서 두 번째 안건입니다.", content)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest audio-stt/tests/test_merge_transcripts.py -v`
Expected: FAIL because `merge_transcripts()` still outputs `## Part 01 (00:00 ~ )` and keeps/offsets timestamps by default.

- [ ] **Step 3: Implement timestamps parameter and filtering in `merge_transcripts.py`**

In `audio-stt/scripts/merge_transcripts.py`:
- Update `merge_transcripts()` signature:
  ```python
  def merge_transcripts(
      target_dir: str,
      prefix: str = "",
      segment_seconds: int = 600,
      keep_parts: bool = False,
      output_file: str = "",
      timestamps: bool = False,
  ) -> str:
  ```
- Adjust header generation:
  ```python
  if timestamps:
      start_min = (part_num - 1) * (segment_seconds // 60)
      full_content.append(f"## Part {part_num:02d} ({start_min:02d}:00 ~ )\n\n")
  else:
      full_content.append(f"## Part {part_num:02d}\n\n")
  ```
- Adjust line processing:
  ```python
  with open(part_path, "r", encoding="utf-8") as f:
      for line in f:
          line_clean = line.strip()
          match = timestamp_pattern.match(line_clean)
          if match:
              if timestamps:
                  mm, ss = int(match.group(1)), int(match.group(2))
                  total_sec = offset_seconds + mm * 60 + ss
                  new_mm = total_sec // 60
                  new_ss = total_sec % 60
                  full_content.append(f"{new_mm:02d}:{new_ss:02d}\n")
              else:
                  # Strip timestamp line when timestamps is False
                  continue
          else:
              full_content.append(line)
  ```
- Clean up excessive blank lines before writing `output_path`:
  ```python
  raw_text = "".join(full_content)
  cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text)
  with open(output_path, "w", encoding="utf-8") as f:
      f.write(cleaned_text)
  ```
- In `main()` add CLI argument:
  ```python
  parser.add_argument(
      "--timestamps",
      "-t",
      action="store_true",
      default=False,
      help="Include continuous MM:SS timestamps in merged transcript (default: False)",
  )
  ```
  And pass `timestamps=args.timestamps` to `merge_transcripts(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest audio-stt/tests/test_merge_transcripts.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add audio-stt/scripts/merge_transcripts.py audio-stt/tests/test_merge_transcripts.py
git commit -m "feat(audio-stt): make timestamps optional in merge_transcripts.py defaulting to False"
```

---

### Task 2: Update `SKILL.md` with optional timestamps documentation and prompt templates

**Files:**
- Modify: `audio-stt/SKILL.md`

**Interfaces:**
- Consumes: updated `merge_transcripts.py` interface.
- Produces: comprehensive instructions in `SKILL.md` for both default plain text mode and `--timestamps` mode.

- [ ] **Step 1: Update Frontmatter & Principles in `audio-stt/SKILL.md`**
  - Update description to state: "Transcribe speech verbatim. By default outputs clean text without timestamps; use --timestamps or -t to include MM:SS timestamps."
  - Update Core Principle 4 / add note on timestamps:
    "Plain Text by Default: Default transcription outputs natural paragraphs without timestamps. Timestamps (`MM:SS`) are generated only when `--timestamps`, `-t`, or user explicitly asks (e.g., '타임스탬프 포함')."

- [ ] **Step 2: Update Workflow A (<= 10 min) in `audio-stt/SKILL.md`**
  - Step 2: Perceive via `view_file`.
    - Default: Transcribe all spoken content verbatim into coherent paragraphs (2~4 sentences per paragraph, separated by blank lines `\n\n`) without `MM:SS` timestamps.
    - If `--timestamps` / `-t` specified: Transcribe with `MM:SS` timestamps preceding each speech segment.

- [ ] **Step 3: Update Workflow B (> 10 min) Subagent Prompt & Merge command**
  - Update subagent instructions to show the conditional prompt:
    - Default prompt:
      ```text
      Instructions:
      1. Call `view_file` on <OUTPUT_DIR>/<NAME>_part01_temp.mp4.
      2. Transcribe ALL spoken words verbatim from start to finish. Do not skip, summarize, or omit anything.
      3. Format strictly as clean text without timestamps: group 2~4 sentences per paragraph, separated by blank lines.
      4. Save directly to <OUTPUT_DIR>/<NAME>_part01.md using `write_to_file`. Ensure Overwrite is true.
      ```
    - With `--timestamps` prompt:
      ```text
      3. Format strictly with MM:SS timestamps:
      MM:SS
      발화내용 문장

      MM:SS
      발화내용 문장
      ```
  - Step 4 (Merge):
    - Default: `python3 .../merge_transcripts.py --dir "<OUTPUT_DIR>" --prefix "<NAME>"`
    - With timestamps: `python3 .../merge_transcripts.py --dir "<OUTPUT_DIR>" --prefix "<NAME>" --timestamps`

- [ ] **Step 4: Update Format Specification & Completion Criteria**
  - Format Specification: Display both Default format (clean text) and Timestamped format (`MM:SS`).
  - Completion Criteria:
    - Update checklist: "Verbatim transcription without timestamps by default (or with `MM:SS` when `--timestamps` is requested)."

- [ ] **Step 5: Verify formatting and commit**

Run: `git diff audio-stt/SKILL.md`
Verify markdown syntax and consistency.
```bash
git add audio-stt/SKILL.md
git commit -m "docs(audio-stt): document optional timestamps in SKILL.md"
```

---

### Task 3: Mirror changes to `plugins/` and global config, and run full acceptance test suite

**Files:**
- Modify: `plugins/ai-skills/skills/audio-stt/SKILL.md`
- Modify: `plugins/ai-skills/skills/audio-stt/scripts/merge_transcripts.py`
- Modify: `plugins/ai-skills/skills/audio-stt/tests/test_merge_transcripts.py`
- Sync: `/Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/`

**Interfaces:**
- Consumes: Task 1 and Task 2 artifacts.
- Produces: Byte-identical plugin copy and synced global skill config.

- [ ] **Step 1: Copy modified files to plugin distribution**

```bash
cp audio-stt/SKILL.md plugins/ai-skills/skills/audio-stt/SKILL.md
cp audio-stt/scripts/merge_transcripts.py plugins/ai-skills/skills/audio-stt/scripts/merge_transcripts.py
cp audio-stt/tests/test_merge_transcripts.py plugins/ai-skills/skills/audio-stt/tests/test_merge_transcripts.py
```

- [ ] **Step 2: Sync to user global skills directory**

```bash
cp audio-stt/SKILL.md /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/SKILL.md
cp audio-stt/scripts/merge_transcripts.py /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/scripts/merge_transcripts.py
cp audio-stt/tests/test_merge_transcripts.py /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/tests/test_merge_transcripts.py
```

- [ ] **Step 3: Run unit tests across all copies**

Run:
```bash
python3 -m unittest discover -s audio-stt/tests -v
python3 -m unittest discover -s plugins/ai-skills/skills/audio-stt/tests -v
python3 -m unittest discover -s /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt/tests -v
```
Expected: All tests pass across all three locations.

- [ ] **Step 4: Verify zero diff between directories**

Run:
```bash
diff -ru --exclude='__pycache__' --exclude='.DS_Store' audio-stt plugins/ai-skills/skills/audio-stt
diff -ru --exclude='__pycache__' --exclude='.DS_Store' audio-stt /Users/hyunjun_macbook_pro/.gemini/config/skills/audio-stt
```
Expected: Zero output (identical).

- [ ] **Step 5: Commit**

```bash
git add plugins/ai-skills/skills/audio-stt/
git commit -m "feat(audio-stt): sync optional timestamps to plugin distribution"
```

---

## Self-Review

### Spec coverage
- Default no timestamps: Task 1 (script filter), Task 2 (skill docs & prompts).
- Args to enable timestamps (`--timestamps` / `-t`): Task 1 (CLI & function args), Task 2 (workflow invocation).
- Decision #6 (Keep `## Part 01` without time range): Implemented in Task 1 line formatting.
- Decision #7 (2~4 sentences per paragraph): Documented in Task 2 prompt templates.
- Full repo & global config parity: Task 3.

### Placeholder scan
No "TODO", "TBD", or unwritten code blocks exist in any task. All test cases, implementation code, and CLI commands are concrete and runnable.

### Type consistency
`timestamps: bool = False` is consistently typed and used across `merge_transcripts()`, CLI `--timestamps` / `-t` argument, and test suites.
