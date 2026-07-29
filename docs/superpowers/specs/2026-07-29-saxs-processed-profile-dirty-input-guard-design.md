# SAXS ProcessedProfile dirty-input guard design

## Decision

Make the read-only `ProcessedProfile` projection tolerant of malformed numeric
tokens without changing the SAXS analysis path. Each supplied array-like layer
is converted element by element with `float()`. A failed conversion becomes
`numpy.nan` at the same position, and the resulting array keeps its original
shape and length.

The canonical projection records invalid counts in the existing `diagnostics`
mapping under `invalid_numeric_values`, keyed by layer name. Any such count
sets `quality_status` to `WARN`. The SAXS payload adapter uses the same
conversion behavior for q/raw and lets `ProcessedProfile` apply it to all
optional layers.

## Invariants

- Caller-owned arrays and sequences are never modified.
- No values are deleted, sorted, interpolated, padded, copied from neighbors,
  or otherwise fabricated.
- Layer positions and lengths remain aligned for display and transport.
- Existing length-mismatch diagnostics are preserved.
- Clean input retains the current `OK` status and numeric values.
- The analysis engine, physical thresholds, quality levels, rescue behavior,
  AI behavior, and publication roles are unchanged.

## Out of scope

This task does not sanitize analysis inputs, alter Guinier/Porod/Kratky or
temperature-series calculations, add scientific thresholds, infer missing
frames, invoke AI, or change Figure/Manifest/Export semantics.

## Acceptance

1. Every `ProcessedProfile` numeric layer tolerates a malformed token.
2. Failed conversions are `NaN` at the original position.
3. Diagnostics identify each affected layer and its invalid count.
4. Dirty projections are `WARN`; clean projections remain `OK`.
5. The SAXS payload projection does not raise for dirty q/raw or optional
   layers, and caller-owned inputs remain unchanged.
