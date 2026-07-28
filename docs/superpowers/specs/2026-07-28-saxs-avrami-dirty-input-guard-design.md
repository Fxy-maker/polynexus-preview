# SAXS Avrami dirty-input guard design

## Context

`avrami_kinetics()` is publicly exported and can be called directly with
time/Xc arrays. Its current finite mask assumes numeric, equally sized arrays;
malformed tokens raise before the existing invalid-point handling can return
an unavailable result.

## Options considered

1. Coerce and align at the helper boundary (recommended): direct and series
   callers share one established numeric policy.
2. Require callers to coerce first: leaves the public helper unsafe and
   duplicates boundary logic.
3. Substitute invalid values with a time or Xc default: avoids exceptions but
   invents kinetics observations and can change the fitted exponent.

## Decision

Use option 1. Apply `_as_1d_float_array()` to time and relative-crystallinity
inputs, slice both to the common prefix, then run the existing finite,
positive-time mask and Avrami fit unchanged. Numeric conversion failures become
NaN and are excluded by the existing mask; Xc range semantics remain those of
the current `auto_range` branch.

## Compatibility and scientific boundary

Clean inputs follow the same numerical path. The existing range selection,
clipping, minimum-point gates, fit, R² calculation, exponent bounds, valid
flag, and result keys are unchanged. Order is preserved; missing observations
are not synthesized or reordered.

## Testing

Regression tests compare dirty input with an explicit valid-survivor reference,
cover common-prefix mismatch and empty input, and assert caller arrays remain
unchanged. Existing temperature and exact SAXS matrices protect downstream
series behavior.
