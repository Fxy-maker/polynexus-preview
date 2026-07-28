# SAXS melting-range dirty-input guard acceptance

Date: 2026-07-28

## Delivered behavior

`detect_melting_from_saxs()` now coerces its consumed temperature and peak-
intensity arrays through the existing detached numeric policy, aligns their
common prefix, and retains finite pairs in source order before running the
unchanged initial-median and sustained-threshold logic.

The unused `q_star_array` parameter is unchanged. Finite negative intensities,
melting thresholds, result keys, publication roles, and physical semantics are
unchanged. No interpolation, padding, sorting, inference, AI, or rescue was
added.

## Evidence

- RED: `4 failed, 1 passed`.
- GREEN: `5 passed in 0.10s`.
- Temperature matrix: `48 passed in 16.31s`.
- Exact SAXS matrix: `513 passed, 6 warnings in 238.42s`.
- Structured verifier: exit code `0`; quality `287`, preprocessing `106`,
  Ruff/compile/type-baseline/task/memory/whitespace checks passed.
- `git diff --check`: exit code `0` with only the CRLF normalization notice.
- Storage dry-run: `522` artifacts, `24` eligible, `498` protected, `0`
  removed.

## Limitation

No fresh full/boundary verification is attributed to this atomic task; the
exact SAXS matrix and structured verifier are the recorded automated gates.
Real-data scientific interpretation and final release review remain open.
