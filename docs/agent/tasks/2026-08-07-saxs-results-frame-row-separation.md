# SAXS Results Frame Row Separation

## Goal

Ensure SAXS strain result tables show one primary row per analyzed frame and do
not present detached orientation-track observations as additional frame rows.

## Non-goals

- No SAXS analysis, feature-tracking, orientation, or reliability changes.
- No fixed five-row limit; row counts follow the actual sequence length.
- No new orientation-track table or scientific aggregation.
- No push, merge, deployment, or source-data mutation.

## Affected boundaries

- SAXS GUI presentation projection.
- Focused SAXS result-table regression coverage.
- Durable task and acceptance records.

## Implementation plan

1. Replace the old test that requires flattened orientation tracks in the
   detail table with a failing regression for dynamic frame-only rows.
2. Stop appending `_orientation_tracking_rows` to the shared frame view while
   preserving detached `orientation_tracking_evidence` diagnostics.
3. Run focused and structured verification, record evidence, and create an
   explicit-file checkpoint.

## Acceptance criteria

- [x] N `_batch_data` frame mappings produce exactly N primary rows.
- [x] Detail and diagnostic sections contain only the N frame rows and the
      existing optional batch-summary row.
- [x] Orientation-track observations do not repeat strain values as frames.
- [x] Detached orientation-tracking evidence remains serializable and the
      source payload is not mutated.
- [x] Focused and structured verification pass.

## Focused evidence

- TDD regression failed before the repair with `11 == 6`, proving five
  detached track observations were appended to five frame rows plus one
  summary row; it passed after the presentation-only change.
- Complete SAXS result-table module: `59 passed in 0.17s`.
- Workbench series-evidence and orientation-transport matrix: `29 passed in
  0.26s`.
- Read-only EDF 8 replay: `primary=5`, `detail=6`, `diagnostics=6`.
- Structured verifier passed task/memory checks, Ruff, compile, quality `297
  passed`, preprocessing `107 passed`, and whitespace checks.
- A broader GUI integration run returned `11 passed, 1 failed`; the unrelated
  history-restore language test expected `Parameter` but received `歌方`. It
  does not exercise the changed SAXS presentation path and remains out of
  scope.

Supplemental commands:

```powershell
python -m pytest -p no:cacheprovider -q tests/test_saxs_workbench_series_evidence.py tests/test_saxs_orientation_tracking_transport.py
# Read-only inline replay used Path.home() / "Desktop" / "edf" / "8" and
# asserted 5 _batch_data/primary rows plus 6 detail/diagnostic rows.
python -m pytest -p no:cacheprovider -q tests/test_unified_tables_gui_integration.py tests/test_saxs_orientation_tracking_transport.py
```

The last command's unrelated failing node was
`test_history_restore_without_submodule_clears_stale_structured_context`.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_saxs_results_table_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-07-saxs-results-frame-row-separation.md --changed --types
git diff --check
```

## Review gate

This is a presentation-only correction. Scientific semantics remain unchanged;
human review is still required before any later merge because the surrounding
SAXS strain feature remains under scientific review.
