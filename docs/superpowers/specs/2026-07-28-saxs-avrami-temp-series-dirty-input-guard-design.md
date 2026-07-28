# SAXS Avrami temperature-series dirty-input guard design

## Context

`avrami_from_temp_series()` is a public wrapper around the already guarded
`avrami_kinetics()` helper. It currently performs arithmetic and boolean
indexing on caller-owned arrays before numeric coercion. A malformed
temperature token therefore raises, and mismatched lengths can fail during
masking instead of degrading to the valid observations.

## Decision

At the wrapper boundary, coerce `time_array`, `temp_array`, and `Xc_array`
with the existing `_as_1d_float_array()` policy and align them to their common
prefix. Preserve observation order. Build the existing temperature tolerance
mask from finite temperatures, then remove observations with non-finite time
or relative crystallinity before establishing relative time. Pass the detached
survivors to `avrami_kinetics()`.

This is deterministic data hygiene, not an inferred rescue: no interpolation,
padding, sorting, fabricated frame, new threshold, or AI candidate is added.
The `Tc_target`, `tolerance`, minimum selected-point gate, Avrami fit, and
physical validity rules remain unchanged.

## Compatibility and failure behavior

Clean equal-length inputs follow the same selection and relative-time path.
Dirty or mismatched input either fits the finite survivors or returns the
existing invalid result when fewer than the existing minimum observations are
available. Caller arrays are never mutated. Temperature values outside the
existing tolerance remain excluded.

## Testing

The focused regression covers malformed temperature tokens, non-finite time
and Xc values, common-prefix alignment, order preservation, insufficient
survivors, clean-input equivalence, and caller immutability. Temperature and
exact SAXS matrices protect downstream callers; the structured verifier and
test-storage audit provide repository-level evidence.
