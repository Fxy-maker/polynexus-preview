# SAXS invariant-conservation dirty-input guard acceptance

Date: 2026-07-28

## Delivered behavior

`check_invariant_conservation()` now coerces strain/Q* arrays through the
existing detached numeric policy, aligns their common prefix, retains finite
pairs in source order, and coerces the tolerance without raising. The existing
mean, standard deviation, CV, deviation, minimum-point, result-key, and finite
negative-Q behavior remain unchanged.

This is deterministic input hygiene only: no Q* positivity gate, interpolation,
padding, sorting, fabricated frame, AI/rescue action, or publication change
was added.

## Evidence

- RED: `6 failed`.
- GREEN: `6 passed in 0.13s`.
- Strain matrix: `11 passed in 0.35s`.
- Exact SAXS matrix: `524 passed, 6 warnings in 195.72s`.
- Task verifier without changed-file lint: exit code `0`; Pyright `0 errors`,
  quality `287`, preprocessing `106`, compile/whitespace/task/memory/diff
  checks passed.
- Targeted Ruff/compile for task files passed.
- Storage dry-run: `530` artifacts, `202` eligible, `328` protected, `0`
  removed.

## Verification limitation

The exact `--changed --types` verifier variant exited `1` on ten pre-existing
Ruff findings in parallel-modified `polynexus/core/saxs_engine/io.py`. That
file is outside this task's allowlist and was intentionally left untouched.
No fresh full/boundary result is attributed to this atomic task.
