---
task_id: 2026-08-28-gui-batch-compute-run-persistence
kind: structured
status: implementation_complete_review_required
date: 2026-08-28
title: Persist one shared ComputeRun per GUI batch row
---

# Persist one shared ComputeRun per GUI batch row

## Goal

Keep each successful GUI batch row's source path, output directory, and shared
`ComputeRun` when persisting history, instead of retaining the canonical run
only in transient memory.

## Non-goals

- Do not change provider algorithms or batch scientific grouping.
- Do not persist failed rows that have no completed ComputeRun.

## Affected boundaries

- `polynexus/gui/main_window_workers.py`: include source/output locators.
- `polynexus/gui/analysis_run_service.py`: batch persistence helper.
- `polynexus/gui/main_window_run_mixin.py`: invoke persistence on completion.
- `polynexus/gui/main_window_history_mixin.py`: build shared context.
- `polynexus/gui/main_window.py`: expose helper alias.
- Focused GUI/persistence tests.

## Acceptance criteria

- [x] Every successful batch row carries its source path and `ComputeRun`.
- [x] Persistence writes one history record per row with its own shared run projection.
- [x] Legacy rows without `compute_run` remain display-only and are not fabricated.

## Implementation plan

1. Add failing tests for per-row persistence and worker locators.
2. Implement the pure persistence helper and wire GUI completion to it.
3. Run focused GUI/persistence tests, structured verification, and checkpoint.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_analysis_run_service.py tests/test_main_window_workers.py tests/test_main_window_run_mixin.py
python scripts/verify.py --task docs/agent/tasks/2026-08-28-gui-batch-compute-run-persistence.md --changed --types
git diff --check
```

## Completion evidence

- Focused GUI/persistence matrix: **20 passed**.
