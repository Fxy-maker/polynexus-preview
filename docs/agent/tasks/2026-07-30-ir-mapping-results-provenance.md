# IR mapping Results provenance visibility

## Goal

Make the existing structured IR mapping evidence visible in the Results review
panel, including its source, map shape, physical X/Y axes, origin, ROI rule,
flattened order, and scientific status.

## Non-goals

- Do not add a vendor reader or infer missing vendor-native metadata.
- Do not promote IR mapping from `review_required`.
- Do not change mapping arrays, ROI spectra, invalid-pixel validation, figure
  roles, export policy, NMR, Joint, or SAXS.

## Affected boundaries

- `polynexus/gui/results_review_service.py`: expose IR support text through the
  shared review DTO.
- `polynexus/gui/main_window_results_mixin.py`: render the DTO field in the
  Results review panel.
- `polynexus/gui/i18n.py`: add the provenance label.
- Focused service and native route tests verify the contract and the live GUI.

## Implementation plan

1. Add the IR provenance field to the shared Results review DTO and render it
   as a wrapped evidence row.
2. Exercise the canonical `IRMappingResult.to_evidence()` envelope in focused
   service and Windows-native route tests.
3. Run the structured verifier and create one explicit allowlist checkpoint;
   retain the diagnostic-only scientific boundary.

## Acceptance criteria

- [x] `analysis_evidence` retains the canonical
  `feature_evidence.mapping_evidence` nesting.
- [x] The Results review panel shows `source`, `map`, `x`, `y`, `origin`, `roi`,
  `order`, and `status` for an IR mapping result.
- [x] The native synthetic route still shows `review_required`/unverified status
  and completes Gallery, Editor, and package export.
- [x] Focused tests, compile, diff, and structured verification pass.

## Verification

```powershell
python -m pytest tests/test_results_review_service.py -q
$env:QT_QPA_PLATFORM='windows'; $env:POLYNEXUS_TEST_RETENTION='evidence'; python -m pytest tests/test_native_gui_real_route_capture.py::test_native_windows_gui_synthetic_ir_mapping_route -vv -s
python scripts/verify.py --task docs/agent/tasks/2026-07-30-ir-mapping-results-provenance.md --changed --types
git diff --check
```

Observed: IR/results matrix `64 passed in 32.39s`; structured verifier passed
with quality `294 passed` and preprocessing `106 passed`; Ruff, compile, type
baseline, memory, task-check, and whitespace all passed. The native Windows
route passed separately with `1 passed`.
