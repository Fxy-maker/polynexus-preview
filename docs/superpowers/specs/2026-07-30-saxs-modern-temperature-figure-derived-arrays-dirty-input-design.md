# SAXS modern temperature Figure derived-array dirty-input design

## Decision

The existing modern temperature Figure provider will project each derived
temperature-series array elementwise through `_coerce_numeric_array()` before
the current count and fallback logic. A malformed or non-finite token becomes
`NaN` at the same frame position. The existing length-mismatch `ValueError`
and `missing_ok` behavior remain unchanged.

The affected arrays are `L_array`, `lc_array`, `lc_effective_array`,
`Q_star_array`, and `Xc_array`. `lc_effective_array` continues to fall back to
the raw `lc_array` value elementwise through the existing `np.where` policy;
this task does not invent a fallback for any other missing metric.

## Invariants

- Frame count and source positions are preserved.
- No interpolation, padding, frame copying, sorting, duplicate aggregation,
  inference, or automatic rescue is introduced.
- Existing parameter semantics, quality levels, physical thresholds, evidence
  roles, publication roles, AI behavior, and Manifest/Export contracts remain
  unchanged.
- Clean arrays produce the same values.
- Missing required arrays and length mismatch retain their current errors;
  only individual malformed elements are degraded.
- Invalid values remain explicit missing numeric evidence and do not gain a
  scientific interpretation.

## Alternatives considered

1. **Keep whole-array fail-closed conversion** — rejected because one malformed
   derived metric currently removes the complete parameter Figure even when
   neighboring frames remain usable.
2. **Drop the affected frame** — rejected because it breaks frame identity and
   conflicts with the position-preserving dirty-input contract.
3. **Elementwise `NaN` projection (selected)** — retains valid neighboring
   metrics while preserving existing downstream finite-value and publication
   gates.

## Verification intent

The regression will put malformed tokens in representative required and
optional derived arrays, assert that all modern temperature definitions are
still constructed, verify valid neighbors and the existing effective/raw
fallback, and retain clean-input and length-mismatch behavior.
