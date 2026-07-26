---
task_id: 2026-07-26-nmr-plot-sentinel-compatibility
kind: scientific-export-compatibility
status: completed
---

# NMR plot sentinel compatibility

## Goal

Keep the shared figure-publication cutover safe when an NMR engine is marked
as analyzed by a non-`NMRResult` sentinel, while preserving parameter and peak
CSV export for real NMR results.

## Non-goals

- Do not change NMR peak fitting, assignment gates, or scientific metrics.
- Do not broaden the legacy writer to accept untyped objects.
- Do not modify fixtures or generated outputs.

## Affected boundaries

- `polynexus/core/nmr.py` compatibility export boundary.
- Shared figure-publication cutover and NMR regression tests.
- Task and acceptance evidence under `docs/agent/` and `docs/acceptance/`.

## Acceptance criteria

- [x] Non-standard sentinel results skip only the compatibility CSV writers.
- [x] Real `NMRResult` collections still emit the existing CSV outputs.
- [x] Shared production cutover and NMR regression matrices pass.
- [x] The boundary and its limitation are recorded for future provider removal.

## Implementation plan

1. Reproduce the shared cutover with the existing non-typed NMR sentinel.
2. Guard only the legacy CSV writers by the typed result capabilities.
3. Re-run the NMR and shared cutover matrices, then record the compatibility
   boundary and checkpoint the allowlisted files.

## Verification

```powershell
python -m pytest --basetemp=C:\Temp\PolyNexus_nmr_plot_cutover tests/test_engine_figure_production_cutover.py -q
python -m pytest --basetemp=C:\Temp\PolyNexus_nmr_matrix_final tests/test_nmr_engine.py tests/test_nmr_figure_document.py tests/test_nmr_figure_provider.py tests/test_nmr_joint_provenance_matrix.py tests/test_nmr_lifecycle_closure.py tests/test_preprocess_nmr_adapter.py tests/test_ir_nmr_joint_workbench_profiles.py -q
ruff check polynexus/core/nmr.py
python -m py_compile polynexus/core/nmr.py
python scripts/verify.py --task docs/agent/tasks/2026-07-26-nmr-plot-sentinel-compatibility.md --changed --types
```

## Known limitation

The compatibility CSV path remains until all callers consume the shared typed
figure/export contracts directly; this task does not remove that legacy API.
