# SAXS invalid temperature-axis fail-closed design

## Context

Temperature-series evidence already represents missing conditions with NaN and
keeps the corresponding frame/source position visible. The series entry point
currently converts the whole input list at once, so one malformed condition
aborts the complete analysis before the existing evidence layer can report the
problem.

## Design

At the temperature-axis boundary, convert each supplied condition with the
existing `_coerce_optional_float()` helper:

```python
temps_arr = np.asarray(
    [_coerce_optional_float(value) for value in temperatures],
    dtype=float,
)
```

This accepts numeric strings, maps invalid/non-finite values to NaN, and leaves
the existing stable sort, source-index mapping, frame analysis, and evidence
builders unchanged. A malformed condition is therefore an unresolved axis
value, not a reason to discard its q/I frame or invent a replacement value.

## Evidence and gates

`build_guinier_sequence_evidence()` remains the authority for axis validity. It
will emit the existing invalid-axis reason and keep the sequence at its current
conservative level. No new threshold, applicability rule, physical gate, or
rescue behavior is introduced. Existing length mismatch checks remain before
axis conversion and continue to raise `ValueError`.

## Verification evidence (2026-07-28)

- RED reproduced the bulk-cast `ValueError`; focused GREEN passed `23` tests.
- The exact SAXS matrix passed `416` tests with `6` existing warnings.
- Structured verification and the explicit allowlist checkpoint are recorded
  by the task card after the final documentation update. The separate
  mismatched-`times` boundary and full/boundary repository verification remain
  outside this slice.
