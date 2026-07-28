# SAXS temperature-phase dirty-input guard design

## Context

`detect_temperature_phase()` is a public single-frame classifier. It compares
raw Q* and lamellar-length values and calls `np.isfinite()` on L values
without a numeric boundary policy. Malformed scalar tokens can therefore
abort one frame's phase classification even though the existing enum and
threshold logic can safely degrade to a declared branch.

## Decision

Coerce `Q_star`, `Q_star_solid`, `L`, and `L_solid` with the existing
`_coerce_optional_float()` helper at the function boundary. Keep `exp_type`
unchanged and run the existing Q*/L thresholds and fallback branches on the
detached local floats.

Invalid/non-finite values become `NaN`, matching the existing internal numeric
convention. This prevents exceptions without inventing a phase, changing a
threshold, copying a neighboring frame, or adding a new scientific rule.

## Compatibility

Clean numeric inputs follow the same comparisons and return the same
`TempPhase` members. The existing `Q_star_solid <= 0` fallback to a normalized
value of `1.0`, the heating/cooling/isothermal branches, and cold-
crystallization check remain unchanged.

## Testing

Focused regressions cover numeric-string coercion, malformed/non-finite Q*/L
values, clean branch equivalence, and the unchanged experiment-type fallback.
Temperature and exact SAXS matrices protect the series caller.
