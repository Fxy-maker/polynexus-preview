# SAXS strain-helper dirty-input guard design

## Context

The strain-series route already sanitizes profiles before its post-processing,
but `detect_strain_phase()` and `detect_voids()` remain public helper
boundaries. Direct callers can pass object tokens, non-finite values, invalid
intensities, or mismatched lengths. The current helpers then compare or mask
the raw arrays and can raise before their existing physical calculations run.

## Options considered

1. Sanitize only at each helper boundary (recommended): fixes direct callers
   and keeps the helpers safe wherever they are reused, with one existing
   policy and no caller-specific assumptions.
2. Sanitize only in `analyze_strain_series()`: smaller local diff, but direct
   public helper callers remain unsafe and future callers can reintroduce the
   same defect.
3. Add a new strain-specific validator: duplicates the established policy and
   risks semantic drift in thresholds and provenance.

## Decision

Use option 1. At entry, call `sanitize_1d_profile(q, I)` and replace only the
local calculation arrays with its detached `q` and intensity survivors. The
sanitizer's current policy is the contract: align to the common prefix,
coerce numeric values, drop non-finite or non-positive pairs, stable-sort by q,
and retain duplicates.

## Compatibility and scientific boundary

`detect_strain_phase()` keeps its scalar Q-star normalization, low-q window,
power-law fit, phase thresholds, and enum return unchanged. `detect_voids()`
keeps the Porod call, low-q Guinier calculation, invariant integration, result
keys, and physical interpretation unchanged. Empty survivors continue through
the existing no-fit paths; no value is fabricated. Caller arrays are never
mutated and no quality report or evidence level is added by these helpers.

## Testing

The regression suite uses a real object-array dirty profile with a malformed q
token, non-finite q, non-positive intensity, and reversed order. It compares
both helpers with the explicit sanitized survivor reference, verifies
mismatched lengths use the aligned prefix, checks empty result compatibility,
and asserts caller-owned arrays are unchanged. Existing strain and exact SAXS
matrices protect surrounding contracts.
