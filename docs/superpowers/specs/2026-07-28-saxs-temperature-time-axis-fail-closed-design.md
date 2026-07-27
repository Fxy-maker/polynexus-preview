# SAXS mismatched temperature time axis fail-closed design

## Context

The temperature series accepts an optional time axis for Avrami kinetics. A
length mismatch is currently allowed through the input boundary and then
causes a sort-index `IndexError`. The q/I frame evidence does not require the
time axis and should not be discarded because of this auxiliary metadata
defect.

## Design

Compute `time_axis_length_mismatch` after the existing temperature/q/I length
validation. When a non-None `times` list has the wrong length, create an
all-NaN internal array of length `n_points` before sorting. After the normal
result object is initialized, attach the JSON-safe Avrami status:

```python
{"valid": False, "reason": "temperature_time_axis_length_mismatch"}
```

The branch prevents indexing failure without treating frame indices as time.
Correctly-sized and absent time axes continue through the existing path.

## Evidence and safety

The record makes the time-dependent limitation visible, while `get_parameters`
already exports only valid Avrami values. No temperature, Guinier, metric,
physical, rescue, AI, or publication evidence is promoted by this change.

## Verification evidence (2026-07-28)

- RED reproduced the sort-index `IndexError`; focused GREEN passed `24` tests.
- The exact SAXS matrix passed `417` tests with `6` existing warnings.
- Structured verification and the explicit allowlist checkpoint are recorded
  by the task card after the final documentation update. Invalid time elements
  and full/boundary verification remain outside this slice.
