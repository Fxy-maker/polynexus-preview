# SAXS Gibbs-Thomson dirty-input guard design

## Context

`gibbs_thomson_analysis()` receives temperature and lamellar-thickness arrays
from temperature-series analysis and is also publicly exported. The current
implementation applies `np.isfinite()` directly to caller arrays, so a
malformed token raises before its existing finite/positive filter can mark the
fit unavailable.

## Options considered

1. Coerce and align at this helper boundary (recommended): direct callers and
   series callers share one established numeric-coercion policy.
2. Require every caller to coerce first: leaves the public helper unsafe and
   duplicates boundary logic.
3. Convert malformed input to zeros: avoids exceptions but invents physical
   observations and changes the fit.

## Decision

Use option 1. Apply `_as_1d_float_array()` to each input, slice both to the
   common prefix, and then run the existing mask and fit unchanged. Numeric
   conversion failures become NaN and are removed by the existing finite mask;
   non-positive `lc` remains excluded by the existing condition. The local
   arrays are detached and caller-owned arrays are not mutated.

## Compatibility and scientific boundary

Clean inputs follow the same numerical path. The existing minimum four-point
gate, linear fit, R2 calculation, `Tm_inf`/surface-energy calculations, valid
flag, and result keys are preserved. Original observation order is retained;
missing observations are not synthesized or sorted into a new temperature
axis.

## Testing

Regression tests compare dirty input to an explicit finite-positive survivor
reference, cover common-prefix mismatch and empty input, and assert caller
arrays are unchanged. Existing temperature and exact SAXS matrices protect
the series and downstream consumer contracts.
