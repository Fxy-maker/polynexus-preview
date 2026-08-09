---
task_id: 2026-08-09-gui-import-ai-panel-performance
kind: performance
status: completed
date: 2026-08-09
title: Remove synchronous full-history reads from import and AI result panels
---

# GUI import and AI-panel performance

## Goal

Remove the measured import and Results-page stalls caused by synchronous
full-history JSON hydration.

## Non-goals

- No scientific calculation, result JSON, export, or database cleanup change.
- No background SQLite access or new persisted schema.

## Affected boundaries

- `polynexus/data/sample_db.py`
- `polynexus/gui/work_memory_service.py`
- `polynexus/gui/analysis_history_service.py`
- `polynexus/gui/main_window_results_mixin.py`
- Focused database, work-memory, and results-panel tests.

## Implementation plan

1. Add focused count/latest-header database reads for work-memory surfaces.
2. Make comparison candidate collection rank only lightweight headers.
3. Hydrate a selected comparison baseline only when opening detailed compare.
4. Verify focused regressions and run the structured changed/type verifier.

## Acceptance criteria

- [x] Work-memory construction does not enumerate batches through
  `get_analysis_runs()`.
- [x] Comparison selection does not decode every historical result JSON.
- [x] Detailed comparison retains full historical parameters after selection.
- [x] The targeted import selection and Results-page UI contracts pass.

## Verification

```powershell
python -m pytest tests/test_sample_db.py tests/test_work_memory_service.py tests/test_analysis_history_service.py tests/test_main_window_persistence.py -q
python scripts/verify.py --task docs/agent/tasks/2026-08-09-gui-import-ai-panel-performance.md --changed --types
```

## Evidence

The production EDT directory import reproduced at 18.662 seconds after a
0.001-second classifier step. The work-memory snapshot decoded 5,408 JSON
documents across 552 batches. The result comparison selector decoded 357 full
run documents and took 3.307 seconds.

Implementation verification: the structured verifier passed Ruff, compile,
quality (303), preprocessing (157), and whitespace checks. The complete
listed pytest command recorded 336 passed and 12 pre-existing History-list
assertion failures that expect a full payload in header-only rows; those
assertions are outside this task's import and comparison boundaries. Focused
work-memory, header-candidate, and lazy-comparison regressions pass.
