# SAXS dirty numeric coercion design

## Decision

Convert q/I elements independently to finite-or-nonfinite floats before the
existing deterministic 1D sanitization. Values that cannot be converted are
represented as `NaN` at their original position. The existing paired validity
mask then drops the malformed observation and emits the same quality actions
and reason codes already used for non-finite numeric input.

## Why

The current whole-array conversion fails closed too early: one malformed token
causes `np.asarray(values, dtype=float)` to fail and returns an empty axis,
discarding otherwise usable measurements. Elementwise conversion rescues the
valid observations without inventing any values or changing the scientific
gates.

## Invariants

- Original q/I objects are never mutated.
- Original order and positions are preserved until the existing stable sort.
- Length mismatch remains truncation/alignment, never padding.
- Invalid, non-finite, non-positive, duplicate, and non-monotonic values retain
  their existing semantics.
- Entirely malformed or empty input remains empty and reaches the existing
  `Unusable` contract.
- The output remains strict JSON-safe through the existing report serializer.

## Out of scope

No string parsing heuristics, locale-dependent decimal handling, interpolation,
neighbor borrowing, duplicate aggregation, threshold changes, AI, rescue
acceptance, or publication-role changes.

## Evidence plan

1. Add a RED regression with one malformed q token and one malformed intensity
   token surrounded by valid values.
2. Implement the smallest elementwise coercion helper change.
3. Run the focused test, all SAXS tests, the task verifier, and diff checks.
4. Record exact outcomes and create one explicit allowlist checkpoint.
