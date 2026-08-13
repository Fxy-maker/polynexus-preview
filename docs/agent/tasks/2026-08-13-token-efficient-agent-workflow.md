---
task_id: 2026-08-13-token-efficient-agent-workflow
kind: architecture
status: implementation_complete_review_required
date: 2026-08-13
title: Add token-efficient agent workflow rules
---

# Token-Efficient Agent Workflow

## Goal

Reduce routine agent context and output consumption without weakening evidence,
scientific boundaries, or verification quality.

## Non-goals

- Do not set a mechanical token limit that can truncate a safety investigation.
- Do not skip required source inspection, regression tests, or verification.
- Do not replace structured project memory with undocumented conversation state.

## Affected boundaries

- Agent contract, development workflow, definition of done, and testing matrix.
- Durable project memory and task templates.

## Acceptance criteria

- [x] Agents read memory and source in layers, starting from concise indexes and
  targeted sections instead of entire historical files by default.
- [x] Searches, diffs, and logs are scoped; failed commands expand only the
  relevant tail or named files.
- [x] Completion reports provide evidence and limitations concisely, without
  replaying command output or unrelated history.
- [x] Scientific, security, architecture, and repeated-failure work may expand
  context when the narrower evidence is insufficient.

## Implementation plan

1. Add an explicit token-efficiency section to the agent contract and workflow.
2. Make task planning and completion evidence name the narrowest source, test,
   and report scope needed to prove the task.
3. Add test/log output rules to the focused testing matrix and record the
   durable policy in project memory.
4. Run the structured task verifier and whitespace check, then create an
   allowlisted local checkpoint without pushing or merging.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-13-token-efficient-agent-workflow.md --changed --types
git diff --check
```
