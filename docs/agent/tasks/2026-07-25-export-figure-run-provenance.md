# Export manifest declares figure-run provenance

## Goal

Make exported result bundles self-describing for manifest-backed figures by
declaring copied run documents/assets/provenance and preserving the active-run
pointer when available.

## Non-goals

- Do not change scientific results or legacy Gallery recovery.
- Do not silently make an export bundle the active GUI run; activation remains an
  explicit consumer action.

## Affected boundaries

- `polynexus/gui/export_context_service.py`
- export and context regression tests.

## Acceptance criteria

- [x] `copy_export_bundle_sections()` reports `figure_runs` when `runs/` is copied.
- [x] `active_run.json` is copied into the bundle's metadata when present.
- [x] `export_manifest.json` declares `metadata/runs` and the active pointer path.
- [x] focused export, GUI, quality, and type checks pass.

## Implementation plan

1. Extend export contract tests for figure-run directories and active pointer.
2. Run them red against the current implicit-only copy behavior.
3. Copy the pointer and declare both paths in the manifest/readme.
4. Run export and GUI regressions, then the structured verifier and allowlisted
   atomic checkpoint. (15 focused tests; verifier quality gate 282 and
   preprocessing gate 103 passed.)

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_export_figure_runs_verify'
python -m pytest tests/test_export_context_service.py tests/test_main_window_persistence.py::test_export_results_creates_structured_bundle_with_manifest -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-export-figure-run-provenance.md --changed --types
```
