# SAXS 2D Parent Review Transport Design

## Decision

When a temperature or strain SAXS engine owns 2D detector/orientation evidence
on its mode-specific series result but stores the existing reviewer-owned
`scientific_review_record` on the outer result parameters, the AI summary
builder will pass that record explicitly to the existing 2D context projector.
The projector continues to read detector and orientation evidence from the
mode-specific result.

This is a provenance transport fix only. It does not create a review, infer a
scope, recalculate a metric, change a threshold, promote a diagnostic result,
or authorize an AI candidate.

## Boundaries

- The outer result is read only for `scientific_review_record` and the existing
  `scientific_review` compatibility field.
- The mode-specific result remains the only source for 2D detector, geometry,
  mask, beam-center, orientation, and acceptance-audit evidence.
- Existing `review_record_from_payload`, scope validation, source matching, and
  fail-closed reasons remain authoritative.
- Missing, malformed, wrong-scope, or stale review records remain
  `review_missing`, `review_invalid`, or the existing mismatch reason.
- The AI envelope remains detached, strict JSON-safe, candidate-only, and
  physically validated before any downstream action.

## Acceptance

1. Temperature and strain summary contexts expose the existing accepted 2D
   review when it is present only on outer `result.parameters`.
2. The same contexts retain child-series detector/orientation evidence.
3. Missing and wrong-scope outer review records remain fail-closed.
4. Static projection and prompt sanitization remain unchanged.
5. No engine result is mutated and no rescue/rerun/apply/publication behavior
   changes.

## Verification

- TDD RED and GREEN for the temperature/strain parent-review matrix.
- Existing SAXS AI/2D/Advisor/prompt focused regression.
- Complete `test_saxs_*.py` matrix.
- Structured task verifier, storage report/clean dry-run, `git diff --check`,
  and explicit allowlist checkpoint.

## Initial evidence

The regression first failed with `3 failed, 7 passed in 0.65s` because outer
temperature/strain review records were projected as `review_missing`. After
the minimal read-only transport, the bridge test passed `10` tests and the
broader AI/Advisor/prompt/live regression passed `35` tests. Complete SAXS and
repository verification then passed: the SAXS matrix returned `710 passed, 6
warnings in 485.73s`, task-scoped quality/preprocessing returned `297`/`106`,
and storage remained dry-run-only with `removed=0`. The explicit checkpoint is
created only from the task allowlist.
