---
task_id: 2026-07-31-saxs-live-advisor-summary-context
status: accepted-automated-with-timeout
date: 2026-07-31
---

# SAXS Live Advisor Summary Context Acceptance

## Delivered boundary

The live `ParameterOrchestrator` state now projects the existing SAXS
summary-only evidence into `saxs_ai_context` for static, temperature, and
strain results. The projection remains candidate-only, requires physical
validation, excludes raw q/I, detector pixels, and source paths, and fails
closed to an empty context. Non-SAXS state is unchanged.

## Verification evidence

- Focused live-state regression: `5 passed in 1.00s`, exit code `0`.
- Combined live-state/Advisor/prompt/summary suite: `17 passed in 1.49s`,
  exit code `0`.
- Structured task verifier: exit code `0`; quality `297 passed`,
  preprocessing `106 passed`, with Ruff, compile, type baseline, memory/task,
  and whitespace checks passing.
- The latest exact `tests/test_saxs_*.py` matrix timed out at the tool limit
  after approximately `604` seconds with no pytest summary and exit code
  `124`. This is a tool-level timeout, not evidence that the matrix passed.
- `git diff --check`: exit code `0`.
- Storage `report` and dry-run `clean`: `63` artifacts,
  `1,368,593,231` total bytes, `18,784` eligible bytes, and `0` removed.
- The explicitly authorized `clean --older-than-hours 24 --apply` then removed
  one managed ephemeral run (`10,911` bytes) but exited `1`: ten legacy
  D-drive directories returned Windows `PermissionError`, and the C-drive
  legacy path was protected by an active-process reference. No ACL or ownership
  bypass was attempted.

## Explicit changed-file allowlist

- `polynexus/orchestrator_state.py`
- `tests/test_saxs_ai_live_context.py`
- `docs/superpowers/specs/2026-07-31-saxs-live-advisor-summary-context-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-live-advisor-summary-context.md`
- `docs/agent/tasks/2026-07-31-saxs-live-advisor-summary-context.md`
- `docs/acceptance/2026-07-31-saxs-live-advisor-summary-context.md`

## Remaining gate

The implementation checkpoint is `37f83db` and the evidence checkpoint is
`69ca458`. The exact SAXS matrix needs a
separate bounded rerun or approved timeout policy before it can be called
green. Broader non-SAXS scientific review, restarted-GUI review, and final
release approval remain open.
