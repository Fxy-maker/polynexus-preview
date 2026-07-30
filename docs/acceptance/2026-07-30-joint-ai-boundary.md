# Joint AI boundary acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-joint-ai-boundary.md`

## Change

Every Joint report `ai_context` now declares the deterministic execution
boundary:

```json
{
  "mode": "off",
  "provider_status": "not_configured",
  "fallback": "rule_based_report",
  "failure_policy": "preserve_source_evidence_and_diagnostic_status"
}
```

The mapping is JSON-safe and is attached to both clean and conflicted report
paths. It is status/provenance only: Joint formulas, thresholds, evidence
weights, validation severities, source-run provenance, and review targets are
unchanged. No provider call or prompt construction was added.

## Evidence

- TDD RED: `2 failed`, both with `KeyError: 'ai_boundary'`.
- Focused Joint dataset and real lifecycle matrix with
  `POLYNEXUS_TEST_RETENTION=review`: `9 passed in 17.12s`, exit code `0`.
- The first post-change ephemeral run had `2 passed` in the test body but
  exited with `WinError 32` during pytest SQLite cleanup; it is recorded as a
  tool-level failure, not as a passing run.
- Structured verification passed with quality `290`, preprocessing `106`,
  Ruff, compile, type baseline, memory/task, and whitespace checks; exit code
  `0`. The broader Joint conflict/lifecycle/provenance matrix passed `27`
  tests in `28.92s`.
- The explicit allowlist checkpoint is the only commit action for this slice;
  no push or merge is performed.

## Remaining boundary

This closes the automated AI-off/fallback status contract only. It does not
approve IR/NMR physical-axis semantics, solid-C assignment/Xc promotion,
Joint conflict precedence, restarted-GUI visual behavior, or final release
approval.
