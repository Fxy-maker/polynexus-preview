# SAXS Temperature Dirty-Frame Post-Processing Design

Date: 2026-07-28
Status: approved working design

## Problem

`analyze_single()` already sanitizes each q/I profile and records the
original defects in `data_quality_report`. `analyze_temperature_series()`
still sends the original arrays to reference invariant/Bragg calculations,
per-frame invariant calculation, and peak-intensity tracking. A frame with a
recoverable NaN, non-positive value, or unsorted pair can therefore have a
successful cleaned frame analysis while its temperature-series evidence is
made unavailable by the raw arrays.

The reproducible diagnostic used q/I containing NaN, a negative intensity, and
an out-of-order pair. Both frame reports recorded
`invalid_pairs_dropped`/`q_sorted`, but `Q_star` was NaN for every frame and
the Guinier sequence became `Unusable` with an `All-NaN slice` warning.

## Decision

Reuse the existing `sanitize_1d_profile()` contract at the temperature
post-processing boundary. For each sorted frame, create a detached sanitized
auxiliary profile and use it only for:

- the solid/reference invariant and Bragg long-period calculations;
- per-frame invariant calculation; and
- Bragg peak-intensity tracking.

Keep passing the original q/I arrays to `analyze_single()` so its existing
quality report retains the original point counts, invalid-pair counts, and
repair actions. The auxiliary profile is not a replacement dataset and is not
exported as a new provenance layer.

## Safety and scientific boundary

- No interpolation, neighbor copy, duplicate-q aggregation, frame deletion,
  or new physical threshold is introduced.
- Empty sanitized profiles remain empty and continue through existing
  fail-closed warnings/results.
- Existing temperature sorting, source indices, Guinier evidence, LC path,
  publication roles, and AI/rescue behavior remain unchanged.
- Clean profiles must follow the same code path and produce the same values.

## Data flow

```text
original frame q/I
  -> analyze_single(original q/I)
       -> existing frame quality report + cleaned frame analysis
  -> sanitize_1d_profile(original q/I)
       -> temperature reference/invariant/peak tracking only
  -> existing TempSeriesResult evidence aggregation
```

## Verification

Focused regression tests assert that post-processing receives finite, positive,
sorted surviving observations while the frame quality report still records the
original dirty input. The task-scoped verifier and exact SAXS matrix pass with
isolated basetemps. Fresh full/boundary verification passes
`2869 passed, 17 skipped, 12 warnings` in `1686.81s`, including a passing
boundary audit.
