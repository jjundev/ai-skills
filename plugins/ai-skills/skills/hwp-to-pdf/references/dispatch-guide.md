# Parallel Agent Dispatch Guide for HWP to PDF

This guide provides instructions and templates for dispatching parallel subagents to convert HWP documents across multiple directories or large file sets using the `/dispatching-parallel-agents` pattern.

## When to Dispatch Parallel Agents

- **Trigger Condition:** 2 or more independent directories containing HWP files, OR 15+ HWP files spread across subfolders.
- **Why Parallel Dispatch:** Isolates context per domain, allows independent recovery/retries, and speeds up batch processing across large sets without context bloat in the coordinator.

## Chrome Debugging Port Allocation Rule

Each agent must be assigned an isolated base port range (`9222 + i * 10`) to prevent Chrome DevTools Protocol socket collisions:
- **Agent 0 (Worker Group 0):** `--base-port 9222 --workers 2` (Uses ports 9222, 9223)
- **Agent 1 (Worker Group 1):** `--base-port 9232 --workers 2` (Uses ports 9232, 9233)
- **Agent 2 (Worker Group 2):** `--base-port 9242 --workers 2` (Uses ports 9242, 9243)
- **Agent 3 (Worker Group 3):** `--base-port 9252 --workers 2` (Uses ports 9252, 9253)

## Subagent Dispatch Pattern

In the coordinator session, call `invoke_subagent` in a single turn for all target domains:

```python
invoke_subagent(
    Subagents=[
        {
            "TypeName": "self",
            "Role": "HWP Converter - Domain A",
            "Prompt": prompt_for_domain_a,
        },
        {
            "TypeName": "self",
            "Role": "HWP Converter - Domain B",
            "Prompt": prompt_for_domain_b,
        }
    ]
)
```

## Subagent Prompt Template

```markdown
Convert all HWP/HWPX documents in the assigned directory to PDF.

**Assigned Directory:** <ABSOLUTE_DIRECTORY_PATH>
**Pre-flight Check:**
Check file sizes beforehand. If any file exceeds 50MB, do NOT pass it directly to `hwp_to_pdf.py`. Instead, split it beforehand:
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/split_hwp.py "<FILE_PATH>"
and convert the resulting part files (`_part1.hwp`, `_part2.hwp`).

**Execution Command:**
python3 /Users/hyunjun_macbook_pro/.gemini/config/skills/hwp-to-pdf/scripts/hwp_to_pdf.py "<ABSOLUTE_DIRECTORY_PATH>" --base-port <ASSIGNED_BASE_PORT> -w 2

**Constraints:**
1. Do NOT modify or inspect files outside the assigned directory.
2. Verify each output PDF has `%PDF-` header and size >= 100 bytes.

**Return:**
A structured markdown summary containing:
- Total HWP files discovered in directory
- Successfully converted files list
- Failed or skipped files list
- Any split part files generated
```

## Integration Step for Coordinator

Upon receiving subagent completion messages:
1. Aggregate reports from all subagents.
2. Spot-check that all expected PDFs exist in their destination folders and pass `header.lstrip().startswith(b"%PDF-")`.
3. Output a unified batch conversion summary table to the user.
