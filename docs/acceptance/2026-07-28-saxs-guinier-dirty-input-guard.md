# SAXS Guinier dirty-input guard acceptance

Date: 2026-07-28
Task: `docs/agent/tasks/2026-07-28-saxs-guinier-dirty-input-guard.md`
Status: automated acceptance complete; checkpoint `c4c78a7`

## Change

The public low-level Guinier helper now reuses the existing detached
`sanitize_1d_profile()` survivors before its unchanged low-q fit. It accepts
recoverable string, non-finite, non-positive, and unsorted observations without
mutating caller data. No new scientific threshold or rescue behavior was
introduced.

## Evidence

- RED: `2 failed, 1 passed in 0.66s`; failures were the expected raw
  `np.isfinite()` `TypeError` on dirty input.
- GREEN: `3 passed in 0.22s`.
- Exact SAXS matrix: `487 passed, 6 warnings in 260.77s`, exit code `0`, using
  `D:\PolyNexus_saxs_guinier_dirty_matrix`.
- Structured verification rerun: exit code `0`; quality `287 passed`,
  preprocessing `106 passed`, task/memory, Ruff, compile, type baseline, and
  whitespace checks passed.
- `git diff --check`: exit code `0`.
- Explicit allowlist checkpoint: `c4c78a7`; no push or merge was performed.

The six warnings are the existing SAXS font-glyph and EDF geometry-header
warnings. No full/boundary result is attributed to this task because the
separate long-running process did not provide a final summary and exit code.

## Boundary

The helper still returns the existing NaN/empty tuple for fewer than ten usable
points. This task does not decide whether a Guinier fit is scientifically
applicable, alter `qRg < 1.3`, infer missing observations, interpolate, rescue,
invoke AI, or change Figure/Manifest/Export publication roles.
