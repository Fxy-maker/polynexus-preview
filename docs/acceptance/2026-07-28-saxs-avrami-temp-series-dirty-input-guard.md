# SAXS Avrami temperature-series dirty-input guard acceptance

Date: 2026-07-28

## Delivered behavior

`avrami_from_temp_series()` now uses the existing detached numeric coercion
policy, aligns time/temperature/Xc to their common prefix, keeps finite points
inside the existing temperature tolerance in source order, and delegates the
relative-time fit to the unchanged `avrami_kinetics()` implementation.

No interpolation, padding, sorting, fabricated observation, new physical
threshold, AI action, or publication decision was added. Clean inputs retain
the prior contract; insufficient survivors remain invalid.

## Evidence

- RED: `4 failed, 1 passed`.
- GREEN: `5 passed in 0.10s`.
- Temperature matrix: `48 passed in 15.20s`.
- Exact SAXS matrix: `508 passed, 6 warnings in 194.16s`.
- Structured verifier: exit code `0`, quality `287`, preprocessing `106`,
  Ruff/compile/type-baseline/task/memory/whitespace checks passed.
- `git diff --check`: exit code `0` with only the CRLF normalization notice.

## Test-storage apply record

The pre-apply dry-run found `524` artifacts: `29` eligible and `495`
protected. The requested command
`python scripts/test_storage.py clean --older-than-hours 24 --apply` removed
five eligible legacy directories, then stopped with exit code `1` because
`D:\PolyNexus\PolyNexusPolyNexus.pytest_tmp_metric_position_full` returned
Windows `WinError 5` (access denied). The follow-up dry-run found `518`
artifacts and `24` eligible remaining. Protected and inaccessible paths were
left untouched; no manual deletion or permission change was attempted.

## Open limitation

The code task is verified and ready for its explicit checkpoint. Test-storage
cleanup is only partially applied because one legacy directory is inaccessible
to the current Windows identity; the remaining eligible artifacts are not
claimed as removed.
