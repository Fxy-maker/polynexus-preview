# SAXS Avrami dirty-input guard acceptance

Date: 2026-07-28

## Result

The public `avrami_kinetics()` boundary now coerces malformed numeric time and
relative-crystallinity arrays with the existing numeric policy, aligns their
common prefix, and lets the established finite/positive-time mask and Xc range
selection decide which observations enter the existing fit.

## Evidence

- TDD RED: `2 failed, 1 passed`; failures reproduced the raw `TypeError`.
- Focused GREEN: `3 passed in 0.12s`.
- Temperature SAXS matrix: `48 passed in 19.48s`.
- Exact SAXS matrix: `503 passed, 6 warnings in 265.09s`, exit code `0`.
- Structured verifier: exit code `0`; quality `287`, preprocessing `106`,
  Ruff, compile, type baseline, task/memory, and whitespace checks passed.
- `git diff --check`: exit code `0`.
- Test-storage report/cleanup dry-run: `522` artifacts, `26` eligible,
  `496` protected, and `0` removed.

## Scientific and scope limits

The Avrami equation, positive-time mask, Xc range selection, clipping,
minimum-point gates, R² rule, exponent validity bounds, and result keys are
unchanged. No sorting, interpolation, extrapolation, fabricated observation,
new threshold, AI/rescue behavior, or publication authorization was added.
`avrami_from_temp_series()` remains a separate follow-up boundary. No fresh
full/boundary result is attributed to this atomic task.

## Checkpoint

The explicit changed-file allowlist is the one in the task card. The local
checkpoint hash is reported in the task handoff; no push, merge, deployment,
or data deletion was performed.
