# SAXS 2D reviewer consumer propagation acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-29-saxs-2d-review-consumer-propagation.md`

## Result

The configured accepted `saxs.2d` reviewer snapshot now reaches the SAXS
result contract and authoritative `quality_evidence.json`. The Figure document
and `reactive_figure_v2.json` retain the same detached snapshot. Existing
manifest readiness and publication roles are unchanged.

The adapter reuses source matching and the shared fail-closed review contract.
Malformed, wrong-scope, partial-source, and source-mismatched configured
records remain disallowed. Empty optional review configuration remains absent
from generic non-gated SAXS result consumers, while Figure evidence continues
to record `review_missing` where a Figure review projection is attached.

## Verification evidence

- TDD RED: `4 failed` in the new consumer module, covering missing result,
  bundle, V2 sidecar, and partial-source snapshots.
- Focused GREEN: `4 passed in 2.07s`, exit code `0`.
- Adjacent matrix: `70 passed in 3.17s`, exit code `0`.
- Independent broader adjacent consumer recheck: `160 passed in 10.00s`,
  exit code `0`.
- Exact PowerShell-expanded `tests/test_saxs_*.py` matrix:
  this session `588 passed, 6 warnings in 591.42s (0:09:51)`, exit code `0`;
  independent shared recheck `588 passed, 6 warnings in 594.35s`, exit code
  `0`.
- Task verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-2d-review-consumer-propagation.md --changed --types`
  passed with quality `290`, preprocessing `106`, Ruff, compile, memory,
  type-baseline, and whitespace checks green.
- Storage report and non-apply clean were run: `46` artifacts,
  `eligible_bytes=0`, `removed=0`; no storage deletion was part of this task.

## Final evidence reconciliation

The independent shared recheck is the canonical final numeric record for this
task: the exact `tests/test_saxs_*.py` matrix completed with `588 passed, 6
warnings in 594.35s`, exit code `0`. The task verifier recorded quality `290`
and preprocessing `106`; storage remained non-destructive at `46` artifacts,
`eligible_bytes=0`, and `removed=0`. This documentation update is captured in
the follow-up explicit-allowlist checkpoint; it does not change scientific
semantics or release authorization.

## Boundary

No SAXS numerical analysis, quality level, physical gate, AI/rescue behavior,
publication role, 1D review behavior, real dataset, or scientific release
decision changed. An explicit allowlist checkpoint is recorded in Git history.
