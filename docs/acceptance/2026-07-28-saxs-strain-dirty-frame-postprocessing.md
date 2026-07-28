# SAXS strain dirty-frame post-processing acceptance

Date: 2026-07-30

The SAXS strain-series 1D post-processing slice is checkpointed in the current
mainline at `777eaef`.

Evidence recorded by the implementation task:

- TDD RED: `1 failed, 2 warnings`; the failing assertion showed raw NaN q
  reaching the reference invariant helper.
- TDD GREEN: `3 passed, 1 warning`; strain/method cross-matrix: `9 passed, 1
  warning`.
- Exact SAXS matrix: `428 passed, 8 warnings` in `29.83s`.
- Task-scoped verifier: exit code `0`; quality `283`, preprocessing `106`,
  Ruff, compile, type baseline, memory/task, and whitespace checks passed.
- Fresh full/boundary verification: `2869 passed, 17 skipped, 12 warnings` in
  `1686.81s`, exit code `0`; boundary audit passed.

Scope remains limited to deterministic sanitized survivors for strain-series 1D
invariant/phase/void consumers. Original q/I and raw quality provenance remain
authoritative; 2D sector/Herman interpretation and scientific publication
authorization remain separate human review gates.

No test data was deleted or migrated. The current uncommitted
`docs/agent/memory/current-state.md` and concurrent `saxs_temperature.py` work
are intentionally outside this documentation reconciliation.
