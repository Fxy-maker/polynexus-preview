# Flexible DSC qualification acceptance — 2026-08-28

## Result

The generic `thermal_program.v1` DSC path no longer requires a fixed 200 °C
preparation hold and no longer rejects an otherwise calculable hold solely for
temperature offset, span, noise, or drift. Those observations are retained as
canonical segment warnings and Avrami quality flags.

## Real-file replay

Using the shared `ComputeRunService` and the six-sample replay inputs:

- `PA11-DWJJ.txt`: `completed`; two isothermal holds at 163 and 164 °C.
- `PA12-50-DWJJ.txt`: `completed`; five isothermal holds at 80–84 °C.

No raw input was modified. The previous `provider_execution_failed` and
`artifact_format_mismatch:dsc_isothermal` statuses no longer occur for these
two files on the generic route.

## Verification

- `python -m pytest -q tests/test_dsc_canonical_isothermal_conversion.py tests/test_dsc_kinetics.py`
  -> `25 passed, 2 warnings`.
- `python scripts/verify.py --changed --types` -> selected checks passed
  (311 quality, 157 preprocessing).

Warnings do not automatically make a result suitable for Results; ARS and
human review still decide scientific use based on fit quality, provenance, and
the actual research question.
