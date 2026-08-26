---
task_id: 2026-08-27-gui-persistence-compute-run-migration
kind: architecture
status: complete
date: 2026-08-27
title: Persist shared ComputeRun fields in GUI history
---

# Persist shared ComputeRun fields in GUI history

## Goal

Store the shared `ComputeRun` canonical template and capability items in the
existing GUI history projection without breaking legacy result display or old
database rows.

## Non-goals

- No database schema migration.
- No GUI redesign or result-table rewrite.
- No Batch, Agent/Codex, or DSC migration in this phase.

## Affected boundaries

- `polynexus/gui/analysis_run_service.py`
- `polynexus/gui/main_window_history_mixin.py`
- `tests/test_analysis_run_service.py`, `tests/test_main_window_persistence.py`

## Implementation plan

1. Add a persistence context field for the in-memory shared `ComputeRun`.
2. Include a JSON-safe `compute_run` projection in `results_summary` while
   retaining legacy `result` and `parameters` fields.
3. Populate that field from the current GUI run map and add round-trip tests.
4. Run focused GUI/persistence and structured verification.

## Acceptance criteria

- [x] A GUI-persisted generic run contains canonical template and capability
  item fields in its history summary.
- [x] Existing legacy result fields remain unchanged.
- [x] Old rows without `compute_run` remain readable.
- [x] GUI persistence tests and quality gates remain green.

## Completion evidence

- New shared projections are written under `results_summary.compute_run`;
  legacy `result`, `parameters`, and old rows remain compatible.
- History restore retains JSON-safe projections in the GUI cache without
  fabricating a provider `legacy_result`.
- Focused migration tests: `13 passed, 199 deselected`.
- Structured verification passed task checks, Ruff/compile, quality `310`,
  preprocessing `157`, and whitespace checks.
- The broader historical GUI persistence file still contains unrelated
  pre-existing failures; they are outside this task and are not claimed green.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_analysis_run_service.py tests/test_main_window_persistence.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-gui-persistence-compute-run-migration.md --changed --types
git diff --check
```
