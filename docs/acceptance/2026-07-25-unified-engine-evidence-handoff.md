# Unified engine evidence handoff

Date: 2026-07-25
Task: `docs/agent/tasks/2026-07-25-unified-engine-evidence-handoff.md`

The shared `AnalysisEvidence` boundary now covers ordinary DSC, WAXS, and IR
analysis results. Each affected engine attaches evidence after direct analysis
through one shared core helper. Existing richer payloads remain authoritative
because the helper is a no-op when evidence is already present.

Focused verification:

```text
44 passed in 86.49s
quality gate: 282 passed
preprocessing gate: 103 passed
changed-file Ruff, compile, and diff checks: passed
```

This closes a code-level evidence handoff gap. It does not by itself prove real
mode-by-mode Gallery/Editor/export restart behavior, AI-off/failure/fallback
scientific acceptance, IR mapping input semantics, or human release approval.
