# Preprocessing fallback safety matrix checkpoint

Date: 2026-07-25
Task: `docs/agent/tasks/2026-07-25-preprocess-fallback-safety-matrix.md`

## Change

`PreprocessEvidence` now carries backward-compatible `fallback_active` and
`fallback_reason` fields. The shared adapter normalizes known fallback markers
from candidate output/evidence, including calibrated and temperature
calibration markers. The shared decision function treats active fallback as a
hard guard: the candidate remains `keep_original`, confidence is `low`, and
`fallback_active` is retained in reason codes.

The matrix covers DSC, IR, WAXS, SAXS, and NMR. Joint is explicitly outside
single-technique preprocessing; its AI surface remains the existing
review-only cross-technique context.

## Evidence

Focused command:

```powershell
$base = Join-Path $env:TEMP 'polynexus-preprocess-fallback-safety-green'
$env:PYTEST_ADDOPTS = "--basetemp=$base"
python -m pytest tests/test_preprocess_cross_technique_matrix.py tests/test_preprocess_optimization_contracts.py tests/test_preprocess_optimization_decision.py tests/test_preprocess_ai_off_compat.py -q
```

Result: `42 passed`.

Task-scoped verifier passed with Ruff, compile, memory check, quality gate
(`282 passed`), and preprocessing gate (`103 passed`).

## Still open

Technique-specific real/Golden fixtures, GUI restart review, and scientific
review of fallback reasons remain release gates. This guard does not claim the
full software goal is complete.
