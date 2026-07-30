# Joint AI context fallback provenance acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-joint-ai-context-fallback-provenance.md`

## Scope

The compatibility adapter that reconstructs Joint context from legacy
`rows`/`validations` must preserve the report-level deterministic AI boundary.
This keeps Workbench, History, and Export consumers from losing the explicit
AI-off/fallback status when loading an older report shape.

## Boundary

Only status/provenance is added. Existing Joint issue counts, severities,
families, highlights, and review targets remain unchanged. No provider or
prompt is introduced, and no scientific conflict is promoted.

## Evidence

- TDD RED: `2 failed, 2 passed, 114 deselected`; both failures were missing
  `ai_boundary` keys in the two legacy fallback branches.
- GREEN fallback tests: `4 passed`, exit code `0`.
- History/Export/Joint consumer and lifecycle matrix: `143 passed in 20.97s`,
  exit code `0`.
- Task-scoped verification passed with quality `290`, preprocessing `106`,
  task/memory, Ruff, compile, type baseline, and whitespace checks; exit code
  `0`.
- The explicit seven-file allowlist checkpoint is the only commit action for
  this slice; no push or merge is performed.

## Remaining boundary

This does not satisfy human confirmation of IR coordinate/ROI semantics, NMR
solid-C assignment/Xc policy, Joint conflict precedence, restarted-GUI visual
review, or final release authorization.
