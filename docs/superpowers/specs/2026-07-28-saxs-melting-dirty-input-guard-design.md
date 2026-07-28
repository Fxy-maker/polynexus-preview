# SAXS melting-range dirty-input guard design

## Context

`detect_melting_from_saxs()` is a public temperature-series helper that still
applies `np.isfinite()` and boolean indexing directly to caller-provided
temperature and peak-intensity arrays. A malformed token raises before the
existing insufficient-data and initial-intensity gates can degrade the result;
mismatched lengths can also fail during masking.

## Decision

Reuse `_as_1d_float_array()` for the two arrays consumed by this helper and
align detached local arrays to their common prefix. Keep only finite
temperature/peak-intensity pairs in original order, then run the existing
initial-intensity median, normalization, sustained-threshold crossings, and
result construction unchanged.

The legacy `q_star_array` parameter is not consumed by the current algorithm;
it remains outside the new selection policy so this task does not silently
change the method's physical semantics or discard observations based on an
unused input.

## Scientific boundary

This is deterministic hygiene only. It does not filter finite negative
intensities, add thresholds, sort temperatures, interpolate missing points,
infer a melting point, call AI, or alter publication roles. Clean equal-length
inputs follow the same numerical path, while too few finite pairs retain the
existing invalid result dictionary.

## Testing

Focused regressions cover malformed numeric tokens, non-finite pairs,
common-prefix mismatch, source-order preservation, insufficient/empty input,
clean-output equivalence, and caller immutability. Existing temperature and
exact SAXS matrices protect downstream series behavior.
