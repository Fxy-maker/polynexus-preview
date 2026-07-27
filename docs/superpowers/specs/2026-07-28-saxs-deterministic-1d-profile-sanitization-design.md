# SAXS deterministic 1D profile sanitization design

## Context

The SAXS quality contract already counts defects in q/I and exposes four
evidence levels. The core analysis path still passes malformed 1D profiles to
multiple numerical methods before constructing that report. A recoverable
profile should be cleaned once at the analysis boundary, with the operation
auditable and the original input preserved by ownership semantics.

## Design

Add one pure helper beside the existing data-quality contract. It accepts any
q/I-like values, converts them to detached one-dimensional float arrays, aligns
only the existing prefix, removes pairs that cannot represent a positive finite
scattering observation, and stably sorts by q. It returns the analysis arrays,
raw and surviving counts, and ordered action codes. It does not average duplicate
q values: without uncertainties, retaining every observation is the least
assumptive behavior and keeps the transformation reversible at the point level.

`analyze_single()` calls the helper before smoothing. The returned arrays feed
all existing numerical methods, so clean input follows the same path and dirty
input no longer leaks NaN/non-positive values into algorithms that do not all
have their own guards. The `SAXSResult` continues to expose the analyzed q/I
arrays as before; the detached input arrays are never mutated by the helper.

The quality report is built from the original input plus the helper's actions.
Its existing defect counts and levels remain authoritative. The report's
`processed_data_ref` continues to identify `I_smooth`, while action codes make
the sanitization step explicit. If the sanitized profile is too short, the
existing quality level and evidence builders keep the result `Unusable` or
diagnostic as already defined; no new threshold is introduced.

## Action vocabulary

- `axis_length_aligned`: q and I had different lengths and only the aligned
  existing prefix was considered.
- `invalid_pairs_dropped`: at least one pair had non-finite or non-positive q/I
  and was excluded from the analysis copy.
- `q_sorted`: surviving q values were not already non-decreasing and were
  stably reordered.
- `duplicate_q_retained`: duplicate q values remained after sanitization; no
  aggregation was performed.

Actions are emitted only when their condition occurred and are ordered by the
sanitization pipeline. Existing caller-provided actions, if any, remain
detached and are appended without duplication.

## Failure and safety behavior

- Empty, scalar, or non-numeric inputs become empty analysis arrays and remain
  fail-closed through the existing quality/evidence contracts.
- No input array is modified in-place.
- No frame or point is fabricated, interpolated, copied from a neighbor, or
  silently promoted.
- JSON serialization remains limited to the existing report DTO values; the
  helper does not place NumPy arrays in evidence payloads.

## Testing strategy

RED tests cover detached arrays, length mismatch, invalid-pair removal,
stable-order duplicates, action ordering, and `analyze_single()` receiving a
clean profile while preserving clean legacy behavior. GREEN adds the helper and
one call at the analysis boundary. The focused matrix then checks quality and
Guinier contracts, followed by the exact SAXS matrix and structured verifier.
