---
task_id: 2026-08-27-gui-batch-compute-run-migration
kind: architecture
status: implementation_complete_review_required
date: 2026-08-27
title: Route GUI folder batch through ComputeRun
---

# Route GUI folder batch through ComputeRun

## Goal

Make the GUI folder-batch entry point use the same `ComputeRunService` as the
CLI batch and single-file routes, while keeping the existing result table
compatible with its `params` projection.

## Non-goals

- No removal of the user-facing folder batch feature.
- No provider algorithm or raw-data changes.
- No database schema migration in this slice.

## Shared objects and entry points

- Producer: `polynexus/gui/main_window_workers.py` via `ComputeRunService`.
- Consumers: `MainWindowRunMixin` and the batch result-table DTO.

## Affected boundaries

- `BatchWorker` now emits rows containing `file`, compatibility `params`, and
  shared `compute_run`.
- The GUI keeps complete batch rows in `_batch_results`; the table ignores the
  extra shared field and renders the same columns.

## Implementation plan

1. Add a failing worker test requiring a completed shared run on a GUI batch
   result row.
2. Replace the direct `engine.run_pipeline` call with `ComputeRunService`,
   preserving lifecycle signals and legacy parameter rendering.
3. Retain complete rows in the main-window batch context and run focused GUI,
   compute, and batch consumer verification.

## Acceptance criteria

- [x] Every successful GUI batch item carries a completed `ComputeRun`.
- [x] Existing `file_done(filename, params)` and result-table behavior remain
  compatible.
- [x] Provider failures remain isolated to the affected file.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_main_window_workers.py tests/test_main_window_run_mixin.py tests/test_results_table_service.py tests/test_compute_service.py tests/test_cli_batch_run_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-gui-batch-compute-run-migration.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(gui): route folder batch through ComputeRun" `
  --files docs/agent/tasks/2026-08-27-gui-batch-compute-run-migration.md polynexus/gui/main_window_workers.py polynexus/gui/main_window_run_mixin.py tests/test_main_window_workers.py docs/agent/tasks/2026-08-27-shared-object-migration.md docs/acceptance/2026-08-27-shared-compute-run-migration.md
```
