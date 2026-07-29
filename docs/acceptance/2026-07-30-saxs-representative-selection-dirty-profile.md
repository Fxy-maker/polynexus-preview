# SAXS representative selection dirty profile acceptance

## Result

Accepted for the local atomic checkpoint. Representative-frame selection now
retains finite q/I evidence for its area and maximum-intensity features when
individual profile tokens are malformed.

## Evidence

- TDD RED: `1 failed`; GREEN: `9 passed in 0.16s`.
- Structured task verification: exit `0`, quality `290 passed`, preprocessing
  `106 passed`, with Ruff/compile/type/memory/whitespace checks passing.
- Fresh SAXS matrix: `594 passed, 6 warnings in 400.98s`, exit code `0`.
- Storage report/clean were dry-run only: `54` artifacts, `0` eligible bytes,
  `Eligible: 0 bytes`, `Cleanup failures: 0`, and no removals. The explicit
  `--apply` command was not run.
- `git diff --check` passed.

## Scientific and release boundary

This change affects only representative Figure selection features. It does not
change raw analysis, q/I source arrays, transition policy, condition ordering,
quality levels, physical metrics, publication roles, AI/rescue behavior, or
release authorization. The prior full/boundary timeout remains separately
recorded and is not claimed as evidence for this task.
