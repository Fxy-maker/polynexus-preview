---
task_id: 2026-07-25-preprocess-fallback-safety-matrix
kind: scientific-cross-module
status: completed
---

# Preprocessing fallback safety matrix

## Goal

Make fallback-derived evidence a shared hard guard for AI-assisted preprocessing
across DSC, IR, WAXS, SAXS, and NMR, and add an explicit cross-technique
AI-off/failure/fallback regression matrix.

## Non-goals

- Change deterministic preprocessing output when AI is off.
- Change any technique-specific fallback calculation or scientific tolerance.
- Add single-technique preprocessing to Joint; Joint uses report-level AI
  context and review targets instead.
- Automatically replace fallback values or silently discard their provenance.

## Affected boundaries

- `polynexus/core/preprocess_optimization/contracts.py`: versioned evidence
  fields for fallback state/reason.
- `polynexus/core/preprocess_optimization/adapters/base.py`: normalize known
  fallback signals from output/evidence into the contract.
- `polynexus/core/preprocess_optimization/decision.py`: fail closed when the
  candidate remains fallback-derived.
- `tests/test_preprocess_cross_technique_matrix.py`: policy/adapter matrix.
- Existing preprocessing contract/decision tests: focused regressions.

## Acceptance criteria

- [x] All five single-technique policies and adapters are covered by AI-off,
  engine-failure, and fallback-derived evidence cases.
- [x] Fallback-active evidence always yields `keep_original`, low confidence,
  and a `fallback_active` reason regardless of apparent improvement.
- [x] Fallback reason survives `PreprocessEvidence.to_dict()` and orchestrator
  reports; no deterministic AI-off payload changes.
- [x] Joint is explicitly documented/tested as preprocessing N/A, with its
  report-level AI context remaining review-only.
- [x] Focused tests, task verifier, changed/type verifier, and diff checks pass.

## Implementation plan

1. [x] Add the parametrized red matrix and fallback contract assertions.
2. [x] Add normalized fallback fields and a fail-closed decision guard.
3. [x] Run focused preprocessing and AI-off tests, then repository verification
   and an allowlist checkpoint.

## Verification

```powershell
$base = Join-Path $env:TEMP 'polynexus-preprocess-fallback-safety'
$env:PYTEST_ADDOPTS = "--basetemp=$base"
python -m pytest tests/test_preprocess_cross_technique_matrix.py tests/test_preprocess_optimization_contracts.py tests/test_preprocess_optimization_decision.py tests/test_preprocess_ai_off_compat.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-preprocess-fallback-safety-matrix.md --changed --types
python scripts/verify.py --changed --types
git diff --check
```

## Known limitations

Real instrument fixtures, GUI restart review, and scientific review of each
technique's fallback reason remain release gates.
