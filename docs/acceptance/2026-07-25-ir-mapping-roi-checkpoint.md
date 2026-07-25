# IR mapping/ROI contract checkpoint — 2026-07-25

## Scope

This checkpoint establishes the safe lifecycle boundary for IR mapping/ROI. It
does not claim a vendor instrument reader or scientific band-selection policy.

## Implemented

- `IRMappingResult` requires an explicit scalar map, row/column coordinates,
  boolean invalid-pixel mask, metric label, ROI spectra, and provenance source id.
- Structural validation rejects shape mismatches, unmarked non-finite pixels,
  non-finite ROI spectra, duplicate ROI ids, and missing provenance.
- `IRMappingResult.to_evidence()` exposes map shape, invalid-pixel ratio, ROI and
  assignment coverage as review evidence; it performs no composition inference.
- Main `ir.mapping.roi`, SI `ir.mapping.spectra`, and diagnostic
  `ir.mapping.invalid-pixels` FigureDefinitions publish through FigurePipeline.
- `IREngine.set_mapping_result()` hands the contract to `AnalysisResult`, and
  the mapping Workbench profile points at all three logical figure IDs.
- Shared heatmap rendering accepts a complete grid containing masked NaN cells
  while still rejecting genuinely missing or duplicate grid cells.

## Evidence

- Focused mapping/provider/profile/engine and heatmap matrix: 15 passed.
- Full `tests/test_ir_*.py` matrix: 38 passed.
- Masked heatmap renderer regression and existing regular-grid renderer: passed.
- Task-scoped verifier passed with an external basetemp:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-25-ir-mapping-roi-contract.md --changed --types`
  (Ruff/compile/type baseline, quality gate 282, preprocessing gate 103).

## Open review items

- Confirm whether production input is an instrument-native 2D map or a pixel
  matrix plus explicit ROI configuration; implement that adapter only after the
  data contract is confirmed.
- Add real/Golden map fixtures, restarted-GUI Gallery → Editor → export review,
  and AI-off/failure/fallback acceptance.
