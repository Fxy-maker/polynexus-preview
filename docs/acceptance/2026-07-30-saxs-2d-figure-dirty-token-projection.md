# SAXS 2D Figure dirty-token projection acceptance

## Result

Accepted for the local atomic checkpoint. The shared static/temperature
detector Figure projection and strain detector/azimuthal Figure projections
now coerce numeric tokens elementwise. Malformed tokens become explicit
non-finite projection entries and are removed only by the existing finite
pixel/pair filters.

## Evidence

- Focused TDD GREEN: `41 passed in 12.96s`.
- Structured task verification: exit `0`, quality `290 passed`, preprocessing
  `106 passed`, Ruff/compile/type/memory/whitespace checks passed.
- Fresh SAXS matrix: `593 passed, 6 warnings in 392.11s`, exit code `0`.
- Storage report/clean were both dry-run: `54` artifacts, `0` eligible bytes
  in the final report, `Eligible: 0 bytes`, `Cleanup failures: 0`, and no
  removals. `test_storage.py --apply` was not run.
- `git diff --check` passed.

## Scientific and release boundary

This is Figure-only projection recovery. It does not alter raw analysis
arrays, anisotropy/orientation calculations, quality levels, physical metrics,
detector geometry, publication roles, AI/rescue behavior, or release
authorization. Full/boundary evidence remains separate; the latest prior
full/boundary attempt ended after `1504.1s` without a final summary and is not
claimed as a pass for this task.
