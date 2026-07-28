# SAXS melting-window status dirty-input guard acceptance

Date: 2026-07-28

## Delivered behavior

`classify_melting_window_status()` now applies the existing detached numeric
coercion policy to scalar temperature/Tm inputs and to the optional temperature
sequence used for the margin estimate. Malformed values degrade to the
existing unresolved/undetermined branches; finite values retain source order
and caller data is not mutated.

Existing margin floors, status names, reason codes, sequence branches, and the
expected-melt soft hint are unchanged. No interpolation, frame repair,
reordering, AI/rescue action, new threshold, or publication decision was
added.

## Evidence

- RED: `4 failed, 1 passed`.
- GREEN: `5 passed in 0.26s`.
- Temperature matrix: `53 passed in 14.83s`.
- Exact SAXS matrix retry: `529 passed, 6 warnings in 218.57s`, exit code `0`.
- Structured verifier: exit code `0`, quality `287`, preprocessing `106`;
  Ruff/compile/type-baseline/task/memory/whitespace checks passed.
- Targeted Ruff/compile and `git diff --check` passed; the latter reported
  only the existing CRLF normalization notice.

The first SAXS matrix invocation hit the 120-second tool timeout without a
pytest summary. Its process later exited naturally, but that run is not
counted as evidence; the independent retry above is authoritative. No fresh
full/boundary result is attributed to this atomic task.

## Test-data management

`python scripts/test_storage.py report --json` and
`python scripts/test_storage.py clean --older-than-hours 24` were run in
dry-run mode. The report contained `532` artifacts, `206` eligible, and
`removed=0`. No `--apply` was executed, and no test directory was deleted or
migrated.

## Scope and review

The seven-file checkpoint allowlist is the task source, focused regression,
task card, spec, plan, acceptance note, and `active-work.md`. Existing
parallel changes in `current-state.md`, `saxs_engine/io.py`, GUI/editor files,
`.superpowers/`, and test-output directories remain outside this checkpoint.
Scientific/publication review, push, merge, and deployment are not part of
this task.
