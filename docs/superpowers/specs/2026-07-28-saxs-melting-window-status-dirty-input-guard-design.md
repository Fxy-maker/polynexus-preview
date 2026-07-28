# SAXS melting-window status dirty-input guard design

## Context

`classify_melting_window_status()` is a public temperature evidence
classifier. Its scalar arguments are passed directly to `np.isfinite()` and
comparisons, while `_temperature_window_margin()` casts the complete supplied
temperature sequence with `dtype=float`. Malformed temperature/Tm values can
therefore abort an otherwise diagnostic status decision.

## Decision

At the boundary, coerce temperature, Tm onset/peak/end, and expected-melt hint
with the existing `_coerce_optional_float()` policy. In
`_temperature_window_margin()`, reuse `_as_1d_float_array()` and calculate the
existing finite sorted positive-difference median from detached values.

Keep every existing margin floor, status, reason code, sequence-window branch,
and expected-melt soft hint unchanged. Invalid inputs become NaN and follow
the existing unresolved/undetermined branches; no new status or threshold is
introduced.

## Scientific boundary

This is deterministic evidence hygiene only. It does not infer a melting
window, replace missing frames, interpolate temperatures, reorder caller
data, invoke AI/rescue, or alter publication roles. Clean inputs retain exact
status/reason behavior.

## Testing

Focused regressions cover numeric strings, malformed/non-finite scalar values,
dirty temperature sequences, margin equivalence, expected-melt hints, and
caller immutability. Existing temperature and exact SAXS matrices protect the
series caller.
