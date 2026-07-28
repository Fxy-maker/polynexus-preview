# SAXS invariant-conservation dirty-input guard design

## Context

`check_invariant_conservation()` is the public strain-series invariant
summary. It currently applies `np.isfinite()` and a boolean mask directly to
caller arrays. Malformed tokens and mismatched lengths can raise before the
existing insufficient-point result is returned; a non-finite strain can also
be carried into `max_dev_strain`.

## Decision

Coerce `strains` and `Q_star_array` with the existing detached
`_as_1d_float_array()` policy, align both to their common prefix, and retain
only pairs where both values are finite. Preserve source order. Coerce the
scalar `tolerance` with `_coerce_strain_value()` so a malformed tolerance
degrades to a non-conserving comparison rather than raising.

Run the existing mean, standard deviation, coefficient-of-variation,
deviation, and result-key logic unchanged. Finite negative Q* values remain
accepted exactly as before; this task does not add a positivity gate.

## Scientific boundary

This is deterministic input hygiene, not invariant repair. No interpolation,
padding, sorting, frame fabrication, new conservation threshold, AI/rescue,
or publication behavior is introduced. Clean inputs retain identical results.

## Testing

Focused regressions cover malformed/non-finite Q*/strain pairs, common-prefix
alignment, finite tolerance coercion, source order, insufficient input, clean
equivalence, and caller immutability. Existing strain and complete SAXS
matrices protect downstream behavior.
