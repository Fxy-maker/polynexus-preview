# NMR solid-C review provenance acceptance

## Scope

This slice makes the existing NMR solid-C evidence visible in Results. It
does not assign peaks, calibrate the JEOL axis, or approve a crystalline Xc
conclusion.

## Evidence

- New core/formatter/panel regressions: `3 passed` after expected red tests.
- Targeted NMR engine source regression: `1 passed in 0.39s`.
- Real solid-C lifecycle: `1 passed, 4 deselected in 131.36s`.
- Real Windows Qt route: `1 passed, 16 deselected`; Results, Gallery, Editor,
  History, and Origin package export completed.
- Results capture shows:
  `Assignment readiness | assignment_limited`,
  `Assignment source | generic_region`,
  `Axis | source=default_range | units=ppm | calibrated=false`, and
  `Xc promotion | blocked | reason=phase_assignment_limited`.

The structured verifier passed with quality `296 passed` and preprocessing
`106 passed`; Ruff, compile, type baseline, memory, task-check, and whitespace
also passed. `git diff --check` passed.

## Boundary

The supplied solid-C data remains assignment-limited. The display confirms the
software's fail-closed rule; it is not a scientific assignment or release
approval.

## Commands to rerun

```powershell
python -m pytest -q tests/test_analysis_evidence.py tests/test_nmr_engine.py tests/test_results_review_service.py tests/test_nmr_lifecycle_closure.py
$env:QT_QPA_PLATFORM='windows'; $env:POLYNEXUS_TEST_RETENTION='evidence'; python -m pytest tests/test_native_gui_real_route_capture.py -k 'nmr.solid_c' -vv -s
python scripts/verify.py --task docs/agent/tasks/2026-07-30-nmr-solid-c-review-provenance.md --changed --types
git diff --check
```
