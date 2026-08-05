# SAXS Scientific Correctness Repair Acceptance

Date: 2026-08-05
Task card: `docs/agent/tasks/2026-08-04-saxs-scientific-correctness-repair.md`

## Evidence

- Focused repair and closure suites: `30 passed, 6 warnings`.
- Changed-contract compatibility matrix: `177 passed, 6 warnings`.
- Full SAXS matrix:
  `python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs*.py' | ForEach-Object { $_.FullName })`
  -> `916 passed, 2 skipped, 15 warnings` in `575.81s`, exit `0`.
- `git diff --check`: passed.
- `python scripts/verify.py --changed --types`: passed, including task-check,
  memory, Ruff, compile, type baseline, quality `297 passed`, preprocessing
  `106 passed`, and whitespace checks.
- `python scripts/verify.py --changed --types --full --boundary`: reached the
  full pytest stage but timed out after `3600s` with exit `124` and no summary;
  this command is not claimed as passed.
- Warnings are existing EDF geometry-default warnings and missing Arial glyphs;
  no warning was promoted to a scientific result.

## Delivered contracts

- Transmission background scaling uses `T_sample/T_background`; Guinier q=0
  extension is finite or remains unavailable; Porod invariant and `Sv` use the
  documented two-phase convention.
- Cooling/isothermal crystallinity uses complete-sequence endpoints; Avrami
  requires explicit seconds; Gibbs-Thomson requires melting-window evidence and
  `delta_Hf_Jm3`.
- q units and provenance are explicit, Angstrom profiles normalize to nm, and
  unitless 1D inputs remain inspectable but cannot produce absolute metrics.
- Frame geometry is copied per input; HDF5/Nexus routes precede Fabio and reject
  equally eligible datasets; correlation raw views retain q-bound provenance.
- Nonuniform q is resampled only in the Fourier analysis view; signed source
  profiles remain observable while derived positive-domain fits exclude residuals.
- Sector masks are pi-periodic and detector-plane orientation is labeled as a
  projected 2D diagnostic metric; Ruland and Vonk remain unsupported.

## Human review limits

Absolute contrast, detector calibration, lamellar two-phase interpretation,
and publication promotion remain scientific review gates. Historical generated
figures and real beamline datasets were intentionally not rewritten.

## Workspace note

Pre-existing pytest artifact directories with Windows permission warnings remain
untouched. No push, merge, deployment, or user-data deletion was performed.
