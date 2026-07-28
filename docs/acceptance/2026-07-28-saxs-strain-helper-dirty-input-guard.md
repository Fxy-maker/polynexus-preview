# SAXS strain-helper dirty-input guard acceptance

Date: 2026-07-28

## Result

The public `detect_strain_phase()` and `detect_voids()` helpers now reuse the
existing deterministic `sanitize_1d_profile()` boundary. Malformed object q/I,
non-finite values, non-positive intensities, reversed q order, and mismatched
lengths no longer raise or enter the existing phase/void calculations as
invalid observations.

## Evidence

- TDD RED: `2 failed, 1 passed`; the failures reproduced the raw-input
  `TypeError`/`IndexError`.
- Focused GREEN: `3 passed in 0.12s`.
- Strain matrix: `11 passed in 0.33s`.
- Exact SAXS matrix: `497 passed, 6 warnings in 193.07s`, exit code `0`.
- Structured verifier: exit code `0`; quality `287`, preprocessing `106`,
  Ruff, compile, type baseline, task/memory, and whitespace checks passed.
- `git diff --check`: exit code `0`.
- Test-storage report/cleanup dry-run: `505` artifacts, `175` eligible,
  `330` protected, and `0` removed.

## Scientific and scope limits

The existing sanitizer policy, phase thresholds, Porod/void windows,
point-count gates, return keys, and scalar Q-star semantics are unchanged.
No interpolation, extrapolation, duplicate aggregation, fabricated frames,
new quality levels, AI/rescue behavior, or publication authorization was added.
No fresh full/boundary result is attributed to this atomic task; human
scientific review remains separate.

## Checkpoint

The explicit changed-file allowlist is the one in the task card. The local
checkpoint hash is reported in the task handoff; no push, merge, deployment,
or data deletion was performed.
