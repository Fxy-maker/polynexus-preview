---
task_id: 2026-07-30-joint-ai-context-fallback-provenance
kind: cross-module-contract
status: complete
date: 2026-07-30
title: Preserve the Joint AI boundary in GUI/history fallback contexts
---

# Joint AI context fallback provenance

## Goal

Keep the deterministic Joint AI-off/fallback boundary present when the GUI
compatibility adapter builds `joint_ai_context` from legacy `rows` and
`validations` instead of receiving the current report-level context.

## Non-goals

- No provider call, prompt construction, or AI model behavior.
- No change to Joint formulas, conflict thresholds, evidence weights, or
  scientific promotion decisions.
- No change to report issue families, counts, labels, or existing fallback
  summaries beyond adding JSON-safe status provenance.

## Affected boundaries

- `polynexus/gui/analysis_history_service.py`: legacy report fallback context.
- `tests/test_analysis_history_service.py`: clean and conflicted fallback
  contract assertions.
- Durable task/design/plan/acceptance/memory records.

## Implementation plan

1. Add clean and conflicted legacy fallback assertions for the explicit
   `ai_boundary` payload and verify the expected RED failures.
2. Add the static boundary to both existing fallback dictionaries without
   changing diagnostic calculations or report priority behavior.
3. Run the focused consumer matrix and structured verifier, then create one
   explicit allowlist checkpoint.

## Acceptance criteria

- [x] Clean legacy fallback context declares the same `ai_boundary` as the
  current Joint report.
- [x] Conflicted legacy fallback context declares the same `ai_boundary` while
  preserving issue counts and families.
- [x] Existing report, tuning-context, history-context, and export consumers
  remain compatible.
- [x] Focused tests, task-scoped verifier, and one explicit allowlist
  checkpoint pass.

## Verification

```powershell
python -m pytest -q tests/test_analysis_history_service.py -k "joint_ai_context"
python scripts/verify.py --task docs/agent/tasks/2026-07-30-joint-ai-context-fallback-provenance.md --changed --types
git diff --check
```

Focused fallback tests: `4 passed`, exit code `0`. The History/Export/Joint
consumer and lifecycle matrix passed `143 passed in 20.97s`, exit code `0`.
Task-scoped verifier passed with quality `290`, preprocessing `106`, task/
memory, Ruff, compile, type baseline, and whitespace checks; exit code `0`.
The explicit allowlist checkpoint is the only remaining commit action for
this atomic task.

Checkpoint: `c179c25` (local only; no push).

## Explicit changed-file allowlist

- `polynexus/gui/analysis_history_service.py`
- `tests/test_analysis_history_service.py`
- `docs/agent/tasks/2026-07-30-joint-ai-context-fallback-provenance.md`
- `docs/superpowers/specs/2026-07-30-joint-ai-context-fallback-provenance-design.md`
- `docs/superpowers/plans/2026-07-30-joint-ai-context-fallback-provenance.md`
- `docs/acceptance/2026-07-30-joint-ai-context-fallback-provenance.md`
- `docs/agent/memory/active-work.md`
