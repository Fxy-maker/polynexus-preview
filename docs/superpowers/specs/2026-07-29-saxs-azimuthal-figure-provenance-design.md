# SAXS azimuthal Figure projection provenance design

## Decision

Record deterministic pair counts for the existing azimuthal chi/I Figure
projection. The recipe will identify input pairs, retained finite pairs,
non-finite pairs, and `complete` or `partial_nonfinite` status per frame.

This is a read-only Figure projection audit. It does not alter the existing
azimuthal values, orientation calculations, detector quality report, or
publication role. Invalid or empty traces remain omitted as before.

## Invariants

- Counts are based on the aligned prefix already selected by the provider.
- No chi/I value is interpolated, replaced, or inferred.
- The recipe is detached and strict JSON-safe.
- The orientation analysis boundary remains independently fail-closed for
  non-finite required inputs.

## Verification boundary

TDD RED/GREEN, focused azimuthal/2D Figure tests, structured verification,
fresh SAXS matrix, diff audit, and storage report/clean dry-runs are required.
`test_storage.py --apply` is prohibited.

## Recorded evidence

- The RED regressions first failed on the missing
  `azimuthal_projection_quality` recipe field.
- The focused Figure/orientation matrix passed `59` tests.
- The structured verifier passed quality `287` and preprocessing `106`, plus
  Ruff, compile, task/memory, and whitespace checks.
- The fresh SAXS matrix passed `545` tests with `6` warnings in `289.88s`.
- Storage remained dry-run only: `350` artifacts, `57` eligible, `9` process
  referenced, `284` younger than retention, and no removals.
