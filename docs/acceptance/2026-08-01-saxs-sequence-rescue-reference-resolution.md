# SAXS Sequence Rescue Reference Resolution Acceptance

## Result

Accepted as a pure identity handoff. A candidate ID resolves only against the
current full temperature result records, and only when exactly one candidate
retains the existing deterministic source, temperature axis, `lc_nm` metric,
candidate-only, missing-frame preservation, and validation markers. The
resolver returns a newly materialized `RescueCandidate` or `None`.

## Scientific and Safety Boundary

The resolver does not calculate, rerun, interpolate, create frames, mutate
configuration, invoke an engine, evaluate gates, or create an accepted
validation report. Existing `validate_sequence_rescue_candidate` remains the
only gate-report constructor and still requires explicit hard, physical,
preservation, and sequence results. Summary-only prompt dictionaries without
source provenance cannot be promoted into validation candidates.

## Evidence

- TDD RED: new resolver tests failed at collection with the expected missing
  public API error before implementation.
- Resolver GREEN: `9 passed in 0.18s`.
- Focused sequence/AI/confirmed-rerun/orchestrator matrix: `80 passed in
  1.79s`.
- Complete SAXS matrix: `734 passed, 6 warnings in 473.91s`, exit code `0`.
- Structured verifier: exit code `0`; quality `297 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile, type baseline, and whitespace checks
  passed.
- Storage report: `156` artifacts, `34,472,130,143` bytes,
  `eligible_bytes=0`, failures `0`.
- Storage clean dry-run: `eligible_count=19`, `removed_count=0`, failures `0`.
  No `test_storage.py --apply` was executed.
- `git diff --check` passed before checkpointing.

## Changed Files

- `polynexus/core/saxs_engine/saxs_sequence_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_sequence_rescue.py`
- the linked spec, plan, and task card

## Limitations

This task does not yet connect an AI reference to a user confirmation control
or execute deterministic gate validation. It provides the safe core resolver
that those later routes must use.
