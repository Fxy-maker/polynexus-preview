# NMR solid-C review provenance visibility

## Goal

Carry the existing solid-C assignment source, ppm-axis provenance, and
assignment-gated Xc decision into the shared Results review panel.

## Non-goals

- Do not assign ambiguous peaks or invent a vendor calibration.
- Do not promote Xc for `assignment_limited` or missing assignment evidence.
- Do not change NMR fitting thresholds, peak detection, figure roles, SAXS,
  IR, or Joint policy.

## Affected boundaries

- `polynexus/core/analysis_evidence_nmr.py`: preserve the existing
  `assignment_source` field in evidence.
- `polynexus/gui/results_review_service.py`: show source, axis, and Xc gate.
- `polynexus/gui/main_window_results_mixin.py` and `polynexus/gui/i18n.py`:
  render the review row.
- Focused evidence and native solid-C route tests.

## Implementation plan

1. Add failing evidence, formatter, and Results-panel tests for assignment
   source and the blocked Xc promotion state.
2. Preserve the existing source in NMR evidence and render the derived gate
   without changing scientific analysis.
3. Verify the real solid-C Windows route, update acceptance evidence, and make
   one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Real NMR evidence exposes `assignment_source` and axis metadata.
- [x] Results review shows assignment readiness, assignment source, axis
  calibration state, and the Xc promotion gate.
- [x] `assignment_limited` remains blocked and no Xc conclusion is promoted.
- [x] Focused tests, structured verification, diff check, and checkpoint pass.

## Verification

```powershell
python -m pytest -q tests/test_analysis_evidence.py tests/test_nmr_engine.py tests/test_results_review_service.py tests/test_nmr_lifecycle_closure.py
$env:QT_QPA_PLATFORM='windows'; $env:POLYNEXUS_TEST_RETENTION='evidence'; python -m pytest tests/test_native_gui_real_route_capture.py -k 'nmr.solid_c' -vv -s
python scripts/verify.py --task docs/agent/tasks/2026-07-30-nmr-solid-c-review-provenance.md --changed --types
git diff --check
```

Observed: the three new evidence/review regressions passed; the targeted NMR
engine source test passed in `0.39s`; solid-C lifecycle passed `1 passed, 4
deselected in 131.36s`; the native route passed `1 passed, 16 deselected`.
The structured verifier passed with quality `296 passed` and preprocessing
`106 passed`, plus Ruff, compile, type baseline, memory, task-check, and
whitespace.
