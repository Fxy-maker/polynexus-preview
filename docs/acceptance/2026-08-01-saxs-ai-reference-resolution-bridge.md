# SAXS AI Reference Resolution Bridge Acceptance

## Result

Accepted as a diagnostic-only bridge. An advisory SAXS candidate ID is
resolved only against the current full temperature result and only when the
existing deterministic source, validation marker, temperature axis, `lc_nm`
metric, candidate-only mode, and missing-frame preservation markers all match.
The orchestrator records the detached result in round advice.

## Safety boundary

Unknown, malformed, duplicate, incomplete, static, strain, and unsupported
references fail closed. The bridge does not call analysis, evaluate physical
or quality gates, mutate configuration, apply candidates, interpolate data,
or create a validation report. Existing AI normalization and execution
decisions remain unchanged.

## Evidence

- TDD RED: missing bridge API during collection.
- Focused bridge/orchestrator GREEN: `19 passed in 1.49s`.
- Expanded AI/Advisor/prompt/confirmed-rerun/orchestrator/resolver coverage:
  `102 passed in 1.79s`.
- Complete SAXS matrix: `740 passed, 6 warnings in 475.98s`, exit code `0`.
- Structured verifier: quality `297 passed`, preprocessing `106 passed`, with
  task/memory, Ruff, compile, type baseline, and whitespace checks passing.
- Storage report/clean: dry-run only, `158` artifacts, `eligible_bytes=0`,
  planned eligible count `19`, removed `0`, no failures.

## Files

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/orchestrator_run_round.py`
- `tests/test_saxs_ai_rescue_bridge.py`
- `tests/test_saxs_orchestrator_loop.py`
- linked spec, plan, task card, and this acceptance note

## Limitations

This bridge exposes identity/provenance evidence only. A later explicit user
review and existing physical, quality, and sequence gates are still required
before any candidate could be considered for a rerun.
