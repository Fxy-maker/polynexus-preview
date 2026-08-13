---
task_id: 2026-08-13-dual-entry-workbench-contract
kind: architecture
status: implementation_complete_review_required
date: 2026-08-13
title: Establish the dual-entry PolyNexus workbench contract
---

# Dual-Entry Workbench Contract

## Goal

Establish PolyNexus as one polymer research workbench with two equal entry
points: Codex/AI and the user interface. Both must operate on the same project,
run, chart, evidence, and export objects.

## Non-goals

- Do not replace the GUI with an AI-only interface.
- Do not make the GUI a separate persistence or analysis path.
- Do not change scientific algorithms, raw data, or existing package formats.
- Do not create a continuous autonomous coding runner.

## Affected boundaries

- Repository product statement and agent contract.
- Task definition of done and verification selection.
- Agent workflow templates and durable project memory.

## Acceptance criteria

- [x] Repository documentation names the dual-entry workbench as the product.
- [x] AI and GUI are required to share domain objects and deterministic analysis
  boundaries; neither may recreate a private result representation.
- [x] Non-trivial tasks declare affected entry points and require focused
  cross-entry verification whenever a shared object changes.
- [x] Default verification remains focused and storage-conscious; full/boundary
  verification is reserved for release, integration, or explicit scope.

## Implementation plan

1. Add the dual-entry product statement to `AGENTS.md` and `README.md`.
2. Add the workflow, definition-of-done, task-template, and focused testing
   matrix assets under `docs/agent/`.
3. Record the shared-object rule and verification policy in durable project
   memory without rewriting historical entries.
4. Run the task verifier and whitespace check, then create an allowlisted local
   checkpoint without pushing or merging.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-13-dual-entry-workbench-contract.md --changed --types
git diff --check
```

## Required evidence

- The task is checkpointed with an explicit allowlist through
  `scripts/auto_commit.py`; no push, merge, deployment, or deletion occurs.
