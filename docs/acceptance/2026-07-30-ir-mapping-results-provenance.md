# IR mapping Results provenance acceptance

## Scope

This slice verifies that the official Thermo/OMNIC Picta mapping rule already
stored in structured evidence is visible in the Results review panel. It does
not claim that the supplied project contains a vendor-native 2D mapping file,
ROI selection record, or calibration payload.

## Evidence

- Formatter regression: `1 passed` for the mapping coordinate provenance line.
- DTO regression: `1 passed` after the expected red test exposed the missing
  `ir_support_text` field.
- IR/results focused matrix: `64 passed in 32.39s`, exit code `0`.
- Windows-native synthetic mapping route: `1 passed`, including Results,
  Gallery, Editor, and Origin package export.
- Results capture visibly contains:
  `source=native-synthetic-map.json`, `map=2x2`,
  `x=column/microscope_stage_x (um)`,
  `y=row/microscope_stage_y (um)`, `origin=stage_home (0.0, 0.0)`,
  `roi=area_map_boundary_or_explicit_roi`,
  `order=unknown_without_vendor_map`, and
  `status=official_rule_sample_metadata_unverified`.

The structured verifier passed with quality `294 passed` and preprocessing
`106 passed`; Ruff, compile, type baseline, memory, task-check, and whitespace
also passed. `git diff --check` passed.

## Boundary

IR mapping remains `review_required` and diagnostic-only until a matching
vendor-native mapping/ROI/calibration record is supplied and scientifically
reviewed. Synthetic evidence is route evidence, not scientific approval.

## Commands to rerun

```powershell
python -m pytest tests/test_results_review_service.py -q
$env:QT_QPA_PLATFORM='windows'; $env:POLYNEXUS_TEST_RETENTION='evidence'; python -m pytest tests/test_native_gui_real_route_capture.py::test_native_windows_gui_synthetic_ir_mapping_route -vv -s
python scripts/verify.py --task docs/agent/tasks/2026-07-30-ir-mapping-results-provenance.md --changed --types
git diff --check
```
