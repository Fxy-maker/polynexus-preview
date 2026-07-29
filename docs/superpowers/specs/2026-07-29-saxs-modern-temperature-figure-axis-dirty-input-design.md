# SAXS modern temperature Figure axis dirty-input design

## Decision

The modern temperature Figure provider will coerce each temperature token
independently through the existing `_coerce_numeric_array()` helper. A token
that cannot be converted becomes `NaN` at its original frame position. The
provider continues to require aligned frame counts and keeps every frame
position; an invalid temperature is an unavailable condition value, not a
reason to delete, reorder, interpolate, or infer a frame.

The same projected temperature array must be reused by the per-frame,
waterfall, parameter-summary, and heatmap definitions. This prevents one
consumer from silently applying a different condition-axis policy.

## Scientific and product invariants

- q/I sanitization remains the existing finite-positive pair projection.
- Temperature coercion does not change `TempSeriesResult`, frame quality
  levels, physical thresholds, publication roles, evidence decisions, or
  rescue/AI behavior.
- Frame order and original positions are preserved, including an invalid
  temperature token.
- Existing frame-count mismatch behavior remains a `ValueError`.
- No interpolation, padding, frame copying, sorting, or automatic rescue is
  introduced.
- The output keeps the existing FigureDefinition contract and remains
  serializable through current Figure/Manifest routes; invalid condition
  values remain explicit missing numeric values rather than fabricated labels.

## Alternatives considered

1. **Fail closed on the whole series** — rejected because one malformed axis
   token currently erases otherwise usable frame Figures and prevents review
   of valid observations.
2. **Drop or reindex invalid-temperature frames** — rejected because it loses
   source-frame identity and conflicts with the existing position-preserving
   dirty-input policy.
3. **Elementwise `NaN` projection (selected)** — preserves valid observations,
   exposes the missing condition explicitly, and leaves scientific eligibility
   and publication decisions unchanged.

## Verification intent

The regression must demonstrate that a malformed temperature token no longer
raises, the frame count and valid frame order remain intact, all modern
temperature definitions are still emitted, and the projected condition value
is explicit missing data. Clean inputs and frame-count mismatch behavior must
remain unchanged.
