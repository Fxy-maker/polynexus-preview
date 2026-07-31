---
task_id: 2026-07-31-advisor-provider-fallback
status: accepted-automated
date: 2026-07-31
---

# Advisor Provider Failure Fallback Acceptance

## Delivered boundary

`Advisor.advise()` now keeps response normalization inside the ordinary
provider failure boundary. A provider payload that parses as JSON but fails
the existing normalization contract returns the existing deterministic mock
advice with `llm_used=False`. `LLMCancelledError` remains a control-flow
signal and is re-raised instead of being converted to fallback advice.

No prompt protocol, retry policy, candidate execution, configuration mutation,
scientific interpretation, persistence, or technique-specific behavior was
changed.

## Verification evidence

- `python -m pytest -q tests/test_advisor.py -o addopts=` -> `8 passed in
  0.37s`, exit code `0`.
- Combined Advisor/Prompt/summary/live-context suite -> `19 passed in
  1.90s`, exit code `0`.
- `python scripts/verify.py --task
  docs/agent/tasks/2026-07-31-advisor-provider-fallback.md --changed --types`
  -> exit code `0`; quality `297 passed`, preprocessing `106 passed`, with
  task/memory, Ruff, compile, type baseline, and whitespace checks passing.
- `git diff --check` -> exit code `0`.

## Explicit changed-file allowlist

- `rag/advisor.py`
- `tests/test_advisor.py`
- `docs/superpowers/specs/2026-07-31-advisor-provider-fallback-design.md`
- `docs/superpowers/plans/2026-07-31-advisor-provider-fallback.md`
- `docs/agent/tasks/2026-07-31-advisor-provider-fallback.md`
- `docs/acceptance/2026-07-31-advisor-provider-fallback.md`

Parallel memory edits, real datasets, generated outputs, scratch directories,
and test-storage paths are excluded from this checkpoint.
