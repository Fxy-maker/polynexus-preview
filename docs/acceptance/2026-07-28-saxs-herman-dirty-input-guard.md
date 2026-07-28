# SAXS Herman dirty-input guard acceptance

Date: 2026-07-28
Task: `docs/agent/tasks/2026-07-28-saxs-herman-dirty-input-guard.md`
Status: automated acceptance complete; checkpoint hash reported in handoff

## Change

`herman_orientation_factor()` now prepares detached angle/intensity pairs with
the existing elementwise numeric coercion policy, finite-pair filtering, and
stable angle sorting. It preserves finite negative intensities and leaves the
Herman formula, angular windows, integration weighting, and NaN return shape
unchanged.

## Evidence

- RED: `2 failed, 1 passed in 0.49s`; failures were the expected malformed
  angle/object-array arithmetic errors.
- GREEN: `3 passed in 0.18s`.
- Related strain/orientation matrix: `36 passed in 0.82s`.
- Exact SAXS matrix: `494 passed, 6 warnings in 259.20s`, exit code `0`, using
  `D:\PolyNexus_saxs_herman_dirty_matrix`.
- Structured verifier exited `0`: quality `287 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile/type baseline, and whitespace passed.
- `git diff --check` passed.

## Scientific boundary

This is input hygiene only. No positive-intensity gate, orientation inference,
detector geometry/mask interpretation, evidence promotion, rescue, AI,
publication, or Figure/Manifest/Export behavior changed. No new full/boundary
result is attributed to this atomic task.

The explicit allowlist checkpoint is created from the paths listed in the task
card; its final hash is reported in the handoff.
