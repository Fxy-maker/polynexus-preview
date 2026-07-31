# SAXS Herman confidence gate acceptance

Date: 2026-07-31
Task: `docs/agent/tasks/2026-07-31-saxs-herman-confidence-gate.md`

## Result

The implementation separates diagnostic raw Herman values from effective
values. Weak or incomplete azimuthal evidence and hard aligned 1D quality
defects leave the effective strain value unavailable while preserving raw
evidence and explicit reason codes.

## Verification evidence

- Focused orientation and strain matrix: `57 passed in 0.43s`, exit `0`.
- Complete `tests/test_saxs_*.py` matrix: `689 passed, 6 warnings in
  503.60s`, exit `0`.
- Structured verifier: exit `0`; task/memory checks, Ruff, compile, type
  baseline, quality `297 passed`, preprocessing `106 passed`, whitespace, and
  `git diff --check` all passed. The first verifier attempt was rejected by
  `task_check.py` because the task card used noncanonical section headings; the
  corrected card passed on the immediate rerun.

## Scientific boundary

The gate is a conservative evidence usability rule. It does not infer a
three-dimensional tensile orientation, force zero strain to zero, change the
Herman convention, or replace human review of raw detector data.

## Changed-file boundary

The checkpoint allowlist is limited to the four production files, two focused
test files, the task/spec/plan documents, and this acceptance note. Parallel
Advisor, memory, SAXS scratch, real-data, and test-storage changes remain
outside the checkpoint.
