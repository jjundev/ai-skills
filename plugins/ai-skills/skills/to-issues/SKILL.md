---
name: to-issues
description: Break a plan, spec, or PRD into independently-grabbable tracer-bullet vertical slices — publish to a configured issue tracker when available, otherwise return and save local issue drafts.
---

# To Issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

Before publishing or fetching remote references, determine whether this project has a configured issue tracker with usable read/write integrations. Do not infer a tracker or vendor from an issue-like reference. The tracker and its triage-label vocabulary may be provided by project configuration; if they are absent or unavailable, use the local-draft fallback below.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a local path, read it. If they pass a remote issue reference and a configured tracker is available, fetch its full body and comments. Otherwise, ask for the issue content rather than assuming a tracker.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Issue titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Any prefactoring should be done first

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?

Iterate until the user approves the breakdown.

### 5. Publish the issues or save local drafts

For each approved slice, create an issue using the body template below. These issues are considered ready for AFK agents.

- **Configured tracker available:** publish issues in dependency order (blockers first) so the `Blocked by` field can reference real issue identifiers. Apply the configured ready-for-agent triage label unless instructed otherwise.
- **No configured tracker available:** return every finalized issue draft in chat and save each one to `docs/issues/<order>-<slug>.md`, creating the directory if necessary. In each local draft, make `Blocked by` reference the blocking draft's filename. State all saved paths in the response. Do not attempt to publish or assume a tracker vendor.

## Issue Body Template

## Parent

A reference to the parent issue on the issue tracker (if the source was an existing issue, otherwise omit this section).

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

Avoid specific file paths or code snippets — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it here and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Acceptance criteria

- Criterion 1
- Criterion 2
- Criterion 3

## Blocked by

- A reference to the blocking ticket (if any)

Or "None - can start immediately" if no blockers.

Do NOT close or modify any parent issue.
