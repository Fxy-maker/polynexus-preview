# SAXS long-period helper dirty-input guard design

**Date:** 2026-07-28
**Status:** approved working design for the SAXS quality goal

## Problem

The public low-level `bragg_long_period()`, `lorentz_fit_long_period()`, and
`correlation_function()` helpers still consume raw q/I arrays. A direct caller
with a string, non-finite, non-positive, or unsorted observation can raise
before the existing analysis gates run. Empty survivors can also reach `q[-1]`
in the Lorentz and correlation helpers.

## Goal

Make these three q/I helper boundaries reuse the existing deterministic
`sanitize_1d_profile()` policy and fail closed for an empty survivor profile,
without changing any analysis window, fit, extrapolation, or physical gate.

## Design

At each helper boundary, obtain detached finite-positive q/I survivors with
`sanitize_1d_profile()`. Apply the existing configured q bounds after
sanitization. For `bragg_long_period()`, the current mask naturally returns its
existing NaN/diagnostic tuple when no usable points remain. For
`lorentz_fit_long_period()` and `correlation_function()`, add an explicit empty
return before indexing q; the returned diagnostic dictionaries retain the
existing q-bound keys and empty-result shape.

The sanitizer stably sorts q and retains exact duplicates. It performs no
interpolation, aggregation, frame repair, or physical inference. Non-empty
profiles continue through the current numerical bodies unchanged.

## Non-goals

- No new point gate, q window, fit-quality threshold, or physical threshold.
- No changes to `analyze_single()` orchestration, result evidence, rescue/AI,
  publication roles, or 2D detector analysis.
- No changes to real datasets, generated outputs, GUI code, or parallel files.

## Acceptance criteria

- Dirty q/I input no longer raises in any of the three public helpers.
- Returned outputs are finite/ordered wherever the existing calculation can
  produce a result, and invalid pairs do not enter the numerical body.
- Empty/wholly invalid q/I input returns a stable existing-compatible
  diagnostic shape for all three helpers.
- Clean-input outputs remain numerically compatible.
- Focused RED/GREEN, exact SAXS matrix, structured verifier, diff check, and an
  explicit allowlist checkpoint are recorded.
