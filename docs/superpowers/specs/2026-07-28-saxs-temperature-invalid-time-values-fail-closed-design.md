# SAXS invalid temperature-time values fail-closed design

## Context

The optional time axis feeds only time-dependent Avrami analysis, but a single
malformed value currently aborts the entire temperature series during bulk
conversion. A NaN time is accepted by NumPy yet its reason is not visible in
the result.

## Design

For a correctly-sized supplied time list, create an aligned input array with
the existing `_coerce_optional_float()` helper, detect non-finite elements, and
then apply the existing temperature sort index:

```python
time_values = np.asarray(
    [_coerce_optional_float(value) for value in times],
    dtype=float,
)
time_axis_invalid_values = bool(np.any(~np.isfinite(time_values)))
times_arr = time_values[sort_idx]
```

When `time_axis_invalid_values` is true, attach the strict JSON-safe Avrami
failure record and skip fitting. Numeric strings remain valid; no missing time
is inferred from frame order. The existing length-mismatch branch takes
precedence and keeps its existing reason.

## Verification evidence

- RED: `1 failed` with the expected `ValueError` from the old bulk cast.
- Focused GREEN: `25 passed`.
- Exact SAXS matrix: `418 passed, 6 warnings`.
- Structured verifier passed with quality gate `283`, preprocessing gate `106`,
  Ruff, compile, memory/task, and whitespace checks. Explicit allowlist
  checkpoint: `c07d49a`.
- Full/boundary verification is a separate release gate and is not claimed.
