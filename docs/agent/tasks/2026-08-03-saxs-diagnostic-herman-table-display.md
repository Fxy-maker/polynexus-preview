---
task_id: 2026-08-03-saxs-diagnostic-herman-table-display
kind: scientific
status: verified
date: 2026-08-03
title: Show diagnostic Herman values in the in-situ SAXS table
---

## Goal

Make measured raw Herman orientation evidence visible in the in-situ strain
table when the final tensile-axis-referenced value is unavailable.

## Scientific Boundary

`f_Herman` remains the final table value and is finite only with an explicit
tensile axis and valid quality gates. `f_Herman_raw` is an image-derived
diagnostic value referenced to the observed principal scattering axis; it is
shown under an explicit diagnostic label and must not be promoted to the final
Herman value.

## Non-goals

- Do not infer or silently configure a tensile axis.
- Do not promote `f_Herman_raw` to the final tensile-axis Herman value.
- Do not alter detector geometry, EDF data, or unrelated GUI/memory changes.

## Affected boundaries

- `polynexus/core/saxs.py`: transport raw orientation evidence into strain
  frame and summary payloads.
- `polynexus/gui/result_table_templates.py` and `polynexus/gui/i18n.py`: show
  the diagnostic field with an explicit label.
- Focused SAXS and results-table regression tests.

## Implementation plan

1. Add raw Herman transport alongside the existing final Herman field.
2. Add explicit diagnostic columns to the strain table and summary.
3. Verify the 610 EDF replay and focused/full changed-file test boundaries.

## Files

- `polynexus/core/saxs.py`
- `polynexus/gui/result_table_templates.py`
- `polynexus/gui/i18n.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_results_table_service.py`
- `tests/test_result_table_templates.py`
- `tests/test_results_table_service.py`

## Acceptance criteria

- [x] 610 EDF raw Herman values are transported into `_batch_data`.
- [x] The results table shows a diagnostic Herman column while final Herman
  remains unavailable without tensile-axis metadata.
- [x] Existing final Herman behavior and unrelated GUI changes remain intact.
- [x] Focused tests and the changed-file verifier pass.

## Verification

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_batch_parameters.py tests/test_saxs_preprocess.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_results_table_service.py tests/test_result_table_templates.py -q
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-diagnostic-herman-table-display.md --changed --types
git diff --check
```

## Verification Results

- SAXS orientation/table matrix: `230 passed`.
- Structured verifier: quality gate `297 passed`, preprocessing gate `106
  passed`, Ruff, compile, memory, task-card, type-baseline, and whitespace
  checks all passed.
- Read-only 610 EDF replay: raw diagnostic values transported for all four
  frames; final `f_Herman` remains unavailable because no explicit tensile axis
  is supplied.
- The complete SAXS matrix excluding the known missing-fixture collector was
  attempted but exceeded the five-minute command limit without a reported
  failing test; the focused matrix and structured verifier are the acceptance
  evidence for this narrow display change.
