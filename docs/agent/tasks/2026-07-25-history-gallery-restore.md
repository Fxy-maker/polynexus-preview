# History restore rehydrates the active figure Gallery

## Goal

History restore must restore the selected run's output directory and reload its
active manifest-backed Gallery so Editor and export routes remain usable.

## Non-goals

- Do not change manifest-only discovery or enable legacy recursive discovery.
- Do not re-run scientific analysis or infer missing vendor mapping semantics.

## Affected boundaries

- `polynexus/gui/main_window_history_mixin.py`
- `tests/test_main_window_persistence.py`

## Acceptance criteria

- [x] Restoring a record with a valid output directory calls the existing Gallery
  population path.
- [x] A real active manifest entry is visible after restore with its run ID and
  figure ID intact.
- [x] Existing history, GUI, quality, and type checks pass.

## Implementation plan

1. Add a Qt regression that publishes one IR manifest and restores a history
   record pointing to its output root.
2. Run the regression to confirm Gallery remains empty before the fix.
3. Call the existing `_populate_plots` boundary after restoring `output_dir`.
4. Run the focused history/persistence matrix and the structured verifier, then
   create an allowlisted atomic checkpoint. (32 focused tests; verifier quality
   gate 282 and preprocessing gate 103 passed.)

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_history_gallery_verify'
python -m pytest tests/test_main_window_persistence.py::test_history_restore_rehydrates_active_manifest_gallery -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-history-gallery-restore.md --changed --types
```
