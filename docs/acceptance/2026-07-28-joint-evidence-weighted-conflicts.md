# Joint evidence-weighted conflict severity

Date: 2026-07-28
Task: `docs/agent/tasks/2026-07-28-joint-evidence-weighted-conflicts.md`

## Change

The Joint dataset boundary now carries the minimum DSC/SAXS evidence weight
into the existing Tm/Gibson-Thompson validation result. A failed Tm conflict
with effective weight below `0.5` remains visible and numerically unchanged,
but is classified as `WARN`, matching the existing phi-c policy. Fully
evidenced conflicts remain `ERROR`; no formula or tolerance changed.

This prevents a diagnostic-only SAXS thickness from turning a review item into
a hard Joint error while preserving the source-run provenance and `passed=False`
signal.

## TDD and verification evidence

- RED with an external basetemp: the new regression failed because the result
  was `ERROR` instead of the expected `WARN`.
- GREEN focused regression: `1 passed`.
- Joint component/lifecycle/provenance matrix: `23 passed in 13.11s`.
- Changed-file Ruff and compile checks for the Joint dataset/test boundary:
  passed.
- Task-scoped verifier: passed with quality `283`, preprocessing `106`, memory,
  task, type baseline, and whitespace checks; exit code `0`.

## Remaining boundary

This is a conservative evidence-severity fix, not a scientific release
decision. IR/NMR calibration semantics, real Joint inputs, restarted-GUI
visual review, and human scientific approval remain open.
