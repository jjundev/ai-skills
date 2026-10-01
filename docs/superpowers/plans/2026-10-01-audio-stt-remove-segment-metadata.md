# audio-stt 산출물 세그먼트 메타데이터 제거 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/audio-stt` 스킬로 생성되는 최종 마크다운 전사본에서 중간 세그먼트 정보(`- **총 세그먼트**: ...`, `- **파트 목록**: ...`) 및 불필요한 구분선을 제거하여 본문 중심의 깔끔한 전사본을 생성하도록 개선합니다.

**Architecture:** 
- `audio-stt/scripts/merge_transcripts.py`에서 마스터 전사본 생성 시 추가되던 세그먼트 요약 메타데이터(총 세그먼트 수, 파트 파일 목록, 구분선)를 제거하고 타이틀 및 파트별 본문만 직결되도록 수정합니다.
- `audio-stt/tests/test_merge_transcripts.py`에 세그먼트 메타데이터가 결과물에 포함되지 않음을 검증하는 단위 테스트를 추가(TDD)합니다.
- `audio-stt/SKILL.md` 문서를 점검하여 산출물 명세에 부합하도록 갱신하고, 변경 사항을 `plugins/ai-skills/skills/audio-stt/` 및 글로벌 링크 환경에 동기화합니다.

**Tech Stack:** Python 3 (unittest, argparse, re), Markdown, Bash

**Spec:** 사용자 피드백 스크린샷(`총 세그먼트: N개 파트`, `파트 목록: ..._part*.md`) 기반 요구사항 — 산출물 마크다운에서 해당 메타데이터를 전면 제외.

## Global Constraints

- Python 표준 라이브러리(`re`, `argparse`, `os`, `sys`, `unittest`)만 사용하며 외부 패키지 추가 의존성 금지.
- `audio-stt`의 기존 축어 전사(Verbatim fidelity), 타임스탬프 옵션(`--timestamps`), 자동 중간 파일 정리(`keep_parts=False`) 기능에 회귀가 없어야 함.
- 저장소 내 `audio-stt/`, `plugins/ai-skills/skills/audio-stt/`, 그리고 글로벌 `~/.gemini/config/skills/audio-stt/` 간 완전한 파일 일치 유지.

## Review Focus

1. **메타데이터 완전 제거**: `총 세그먼트` 및 `파트 목록` 텍스트가 최종 마크다운 본문에 일체 나타나지 않는지 확인.
2. **불필요한 구분선(`---`) 및 다중 개행 제거**: 메타데이터 제거 후 제목(`# ...`)과 첫 파트(`## Part 01`) 사이가 깔끔하게 1개 빈 줄(`\n\n`)로 연결되는지 확인.
3. **타임스탬프 모드 호환성**: `--timestamps` (`-t`) 사용 시에도 파트 헤더(`## Part 01 (00:00 ~ )`)와 타임스탬프 계산이 정상 동작하는지 확인.
4. **중간 파일 보존 모드 호환성**: `--keep-parts` 플래그 사용 시에도 마크다운 본문에는 파트 파일 목록이 노출되지 않고 실제 파일만 보존되는지 확인.
5. **동기화 무결성**: canonical 저장소(`audio-stt/`)와 배포본(`plugins/ai-skills/skills/audio-stt/`) 간 diff가 0인지 확인.

---

### Task 1: Update `merge_transcripts.py` to remove segment metadata (TDD)

**Files:**
- Modify: `audio-stt/tests/test_merge_transcripts.py`
- Modify: `audio-stt/scripts/merge_transcripts.py`

**Interfaces:**
- Consumes: `merge_transcripts(target_dir, prefix, segment_seconds, keep_parts, output_file, timestamps)`
- Produces: Clean markdown output starting with `# {Title} 전체 오디오 전사본\n\n## Part 01` without bullet metadata.

- [ ] **Step 1: Write failing tests asserting absence of segment metadata**

In `audio-stt/tests/test_merge_transcripts.py`:
Add assertions to `test_merge_transcripts_default_cleans_parts` and a dedicated test `test_merge_transcripts_no_segment_metadata`:

```python
    def test_merge_transcripts_no_segment_metadata(self):
        """
        Verify that merged transcript does not contain segment metadata bullets
        (- **총 세그먼트**: ..., - **파트 목록**: ...) or redundant horizontal rule.
        """
        part1_path = os.path.join(self.test_dir, "sample_part01.md")
        part2_path = os.path.join(self.test_dir, "sample_part02.md")

        with open(part1_path, "w", encoding="utf-8") as f:
            f.write("첫 번째 파트 발화 내용입니다.\n")
        with open(part2_path, "w", encoding="utf-8") as f:
            f.write("두 번째 파트 발화 내용입니다.\n")

        result = merge_transcripts(self.test_dir, prefix="sample", keep_parts=True)
        self.assertTrue(os.path.isfile(result))

        with open(result, "r", encoding="utf-8") as f:
            content = f.read()

        # Metadata bullets must NOT be present
        self.assertNotIn("총 세그먼트", content)
        self.assertNotIn("파트 목록", content)
        self.assertNotIn("---", content)

        # Title and parts should be cleanly formatted
        self.assertTrue(content.startswith("# sample 전체 오디오 전사본\n\n## Part 01\n"))
        self.assertIn("첫 번째 파트 발화 내용입니다.", content)
        self.assertIn("두 번째 파트 발화 내용입니다.", content)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest audio-stt/tests/test_merge_transcripts.py -k test_merge_transcripts_no_segment_metadata -v`
Expected: FAIL because `merge_transcripts.py` still inserts `총 세그먼트`, `파트 목록`, and `---`.

- [ ] **Step 3: Remove segment metadata header from `merge_transcripts.py`**

In `audio-stt/scripts/merge_transcripts.py`:
Replace lines 50-54:
```python
    full_content = [
        f"# {prefix or os.path.basename(target_dir)} 전체 오디오 전사본\n\n",
    ]
```

- [ ] **Step 4: Run all unit tests to verify they pass**

Run: `python3 -m unittest discover -s audio-stt/tests -v`
Expected: PASS (all 9 tests pass).

- [ ] **Step 5: Commit**

```bash
git add audio-stt/scripts/merge_transcripts.py audio-stt/tests/test_merge_transcripts.py
git commit -m "fix(audio-stt): remove segment metadata and file list from merged transcript markdown"
```

---

### Task 2: Update `audio-stt/SKILL.md` specification

**Files:**
- Modify: `audio-stt/SKILL.md`

**Interfaces:**
- Documentation of output structure and completion criteria.

- [ ] **Step 1: Update Core Principles and Completion Criteria in `audio-stt/SKILL.md`**

In `audio-stt/SKILL.md`:
Under `Core Principles` point 5 ("Unified Single-File Output & Clean Workspace"):
Clarify that the merged output contains only the title and verbatim speech content, without intermediate chunk metadata or segment file lists.

Under `Completion Criteria`:
Ensure:
- [ ] Saved as a single unified `.md` transcript (`<NAME>.md`) without intermediate segment file lists or segment metadata.

- [ ] **Step 2: Review markdown rendering and accuracy**

Review `audio-stt/SKILL.md` to ensure formatting consistency.

- [ ] **Step 3: Commit**

```bash
git add audio-stt/SKILL.md
git commit -m "docs(audio-stt): reflect removal of segment metadata in output specification"
```

---

### Task 3: Sync to plugin distribution and verify repository suite

**Files:**
- Modify: `plugins/ai-skills/skills/audio-stt/scripts/merge_transcripts.py`
- Modify: `plugins/ai-skills/skills/audio-stt/tests/test_merge_transcripts.py`
- Modify: `plugins/ai-skills/skills/audio-stt/SKILL.md`

**Interfaces:**
- Syncing canonical `audio-stt/` to `plugins/ai-skills/skills/audio-stt/`.

- [ ] **Step 1: Copy modified files to plugin distribution**

```bash
cp audio-stt/scripts/merge_transcripts.py plugins/ai-skills/skills/audio-stt/scripts/merge_transcripts.py
cp audio-stt/tests/test_merge_transcripts.py plugins/ai-skills/skills/audio-stt/tests/test_merge_transcripts.py
cp audio-stt/SKILL.md plugins/ai-skills/skills/audio-stt/SKILL.md
```

- [ ] **Step 2: Run test suite across the repository**

Run: `python3 script/manage.py test`
Expected: PASS (all tests pass across the entire AI Skills repo).

- [ ] **Step 3: Verify diff between canonical and plugin copy**

Run: `diff -u audio-stt/scripts/merge_transcripts.py plugins/ai-skills/skills/audio-stt/scripts/merge_transcripts.py`
Expected: No difference.

- [ ] **Step 4: Commit**

```bash
git add plugins/ai-skills/skills/audio-stt/
git commit -m "chore(audio-stt): sync clean transcript changes to plugin distribution"
```

---

### Task 4: Clean up existing `1001 생명.md` transcript

**Files:**
- Modify: `/Users/hyunjun_macbook_pro/Downloads/1001 생명.md`

**Interfaces:**
- User's working deliverable from the previous run.

- [ ] **Step 1: Remove metadata lines 3-6 from `/Users/hyunjun_macbook_pro/Downloads/1001 생명.md`**

Remove:
```markdown
- **총 세그먼트**: 5개 파트 (각 약 10분)
- **파트 목록**: 1001 생명_part01.md, 1001 생명_part02.md, 1001 생명_part03.md, 1001 생명_part04.md, 1001 생명_part05.md

---
```

Verify that the file starts with:
```markdown
# 1001 생명 전체 오디오 전사본

## Part 01

어디까지 한 건가?
```

- [ ] **Step 2: Verify cleaned file**

Check `head -n 15 "/Users/hyunjun_macbook_pro/Downloads/1001 생명.md"` to confirm clean appearance matching user's intent.
