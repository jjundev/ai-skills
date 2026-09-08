---
name: hwp-to-pdf
description: MUST USE when the user wants to convert HWP/HWPX documents to PDF — e.g. "HWP PDF로 변환해줘", "hwp to pdf", "한글 파일 변환", "/hwp-to-pdf", or batch converting HWP files across directories. Supports single-file conversion, high-speed multi-worker batch conversion, large file splitting (>50MB), and parallel subagent orchestration for multi-directory tasks.
---

# HWP to PDF Skill (`hwp-to-pdf`)

Converts Hancom Word Processor (HWP / HWPX) files into high-integrity PDF documents using headless Chrome automation with Chrome DevTools Protocol (CDP) and Allinpdf.

## Quick Start

### 1. Single File or Small Batch (<= 14 files, single directory)
Run the unified Python converter directly in the current session:

```bash
# Convert a single file (PDF saved alongside HWP)
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py "path/to/document.hwp"

# Convert all files in a folder with 3 workers
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py "path/to/folder" -w 3

# Specify output directory
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py "path/to/folder" -o "path/to/output_pdf"
```

---

### 2. Large Batch or Multi-Directory (>= 2 independent folders OR >= 15 files)
Follow the `/dispatching-parallel-agents` pattern to isolate tasks and avoid session context bloat:

1. **Scan:** Identify target directories containing HWP files.
2. **Assign Ports:** Give each subagent an isolated base port (`9222 + i*10`):
   - Subagent 0: `--base-port 9222 -w 2`
   - Subagent 1: `--base-port 9232 -w 2`
   - Subagent 2: `--base-port 9242 -w 2`
3. **Dispatch in Parallel:** In a single response, invoke one subagent per domain using `invoke_subagent`. See [dispatch-guide.md](references/dispatch-guide.md) for full prompt templates.
4. **Aggregate & Verify:** Inspect subagent completion summaries and ensure all PDFs start with `%PDF-` and >= 100 bytes.

---

## Large Files Handling (> 50MB)
Online conversion services (Allinpdf) reject files exceeding 50MB. If a file exceeds 50MB:
```bash
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/split_hwp.py "path/to/large_file.hwp"
```
This produces `large_file_part1.hwp`, `large_file_part2.hwp`, etc. Convert the parts into corresponding PDFs.

---

## Security & Privacy Notice
All conversions are routed through external SaaS (Allinpdf) via Headless Chrome. Before running, notify the user if files contain strictly confidential data.
