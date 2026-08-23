---
task_id: 2026-08-24-core-foundation-direct-run
kind: architecture
status: active
date: 2026-08-24
title: Define the direct-run core migration boundary
---

# Define the direct-run core migration boundary

## Goal

Establish the protected architecture boundary for a shared direct-run façade
before source migration begins.

## Non-goals

- Change DSC, IR, SAXS, WAXS, or NMR numerical algorithms.
- Delete legacy workflow, evidence, writing, manuscript, Joint, RAG, or
  persistence code.
- Change the database schema or migrate historical persisted results.

## Affected boundaries

- Analysis engine: adds a façade only; DSC, IR, SAXS, WAXS, and NMR numerical
  algorithms remain unchanged.
- Result/schema contract: creates compute contracts while legacy `AnalysisResult`
  remains a compatibility projection.
- CLI/AI: existing single-technique CLI commands return direct-run JSON via
  `--json`.
- GUI: `AnalysisWorker` invokes the same service and retains the received
  `ComputeRun` in memory.
- Persistence/export: the database schema remains unchanged; old legacy-result
  persistence is a temporary adapter.

## Acceptance criteria

- [ ] A missing path produces `needs_input`, not a review state.
- [ ] A legacy engine validation warning produces a `completed` run with
  warnings.
- [ ] CLI and GUI both call `ComputeRunService.run_direct`.
- [ ] Public compute JSON contains no `analysis_evidence`, writing eligibility,
  or manuscript fields.
- [ ] The façade preserves the legacy `AnalysisResult` only as an in-memory
  compatibility projection while consumer migrations are completed.

## Implementation plan

1. Record the protected direct-run contract and exclusions in this task card.
2. Inventory current import and entry-point consumers from scoped source search
   evidence before future deletion work.
3. Add the temporary-bridge status to durable active-work memory without
   removing legacy code.
4. Validate the task card and whitespace, then checkpoint only these records.

## Verification

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-08-24-core-foundation-direct-run.md
python scripts/verify.py --task docs/agent/tasks/2026-08-24-core-foundation-direct-run.md --changed --types
git diff --check
```

For this documentation-only checkpoint, the focused task-card validation and
whitespace check are required before committing. Structured verification is
reserved for the implementation and acceptance tasks in this migration slice.

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(core): define direct-run migration boundary" `
  --files docs/agent/tasks/2026-08-24-core-foundation-direct-run.md docs/agent/inventories/2026-08-24-core-simplification-import-inventory.md docs/agent/memory/active-work.md
```
