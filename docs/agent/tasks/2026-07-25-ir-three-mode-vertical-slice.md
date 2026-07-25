---
task_id: 2026-07-25-ir-three-mode-vertical-slice
kind: scientific-cross-module
status: completed
---

# IR three-mode vertical slice

## Goal

Make the existing IR standard, temperature-2D, and mapping/ROI providers use
an explicit Main/SI/diagnostic publication contract while preserving the
typed mapping handoff and manifest failure visibility.

## Non-goals

- Infer a vendor-specific mapping reader, coordinate convention, or band
  meaning.
- Promote low-confidence assignment or invalid-pixel diagnostics into Main.
- Replace the shared Gallery, Editor, export, or History contracts.
- Claim real-data or restarted-GUI acceptance from synthetic tests.

## Affected boundaries

- `polynexus/core/ir_engine/figure_provider.py`: explicit roles for standard
  and temperature-2D definitions.
- `polynexus/core/ir_engine/ir_mapping.py`: existing typed mapping roles and
  provenance remain the source of truth.
- `tests/test_ir_complete_figure_provider.py` and
  `tests/test_ir_figure_provider.py`: role and manifest regression matrix.
- `docs/acceptance/2026-07-25-ir-three-mode-vertical-slice.md`: evidence and
  remaining external acceptance.

## Acceptance criteria

- [x] Every emitted IR definition has an explicit publication role verified by
   `validate_figure_definition`.
- [x] Standard spectrum/crystallinity and temperature heatmap are Main; fitting,
   tracking, indices, and ROI spectra are SI; computed comparison, 2D-COS,
   and invalid-pixel views are diagnostic.
- [x] Mapping provenance and invalid-pixel evidence remain in the recipe and
   diagnostic figure, including non-fatal masked cells.
- [x] A generation failure remains a `generation_failed` Manifest entry and does
   not hide successful siblings.
- [x] Focused tests, task verifier, changed/type verifier, and diff checks pass.

## Implementation plan

1. [x] Add failing role and sibling-failure regressions to the existing IR provider
   and Manifest test modules.
2. [x] Assign explicit standard IR publication roles in the provider while keeping
   the existing temperature-2D and mapping contracts unchanged.
3. [x] Run focused tests and the repository task verifier with an external pytest
   base temp, then record the evidence and checkpoint the allowlisted files.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\polynexus-ir-three-mode'
python -m pytest tests/test_ir_complete_figure_provider.py tests/test_ir_figure_provider.py tests/test_ir_mapping.py tests/test_run_figure_manifest.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-ir-three-mode-vertical-slice.md --changed --types
git diff --check
```

## Known external acceptance

Vendor reader/input semantics, real/Golden mapping fixtures, AI-off/failure/
fallback scientific review, export-bundle inspection, and restarted-GUI visual
review remain separate release gates.
