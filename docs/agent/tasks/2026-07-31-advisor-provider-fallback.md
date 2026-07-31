---
task_id: 2026-07-31-advisor-provider-fallback
kind: cross-module-safety
status: completed
date: 2026-07-31
title: Close Advisor provider failure fallback boundary
---

# Advisor provider failure fallback

## Goal

Ensure malformed provider responses follow the existing deterministic Advisor
fallback while explicit user cancellation remains distinguishable and is
re-raised.

## Non-goals

- No model provider or prompt protocol changes.
- No retry, candidate execution, configuration mutation, persistence, or
  scientific interpretation changes.
- No changes to SAXS, IR, NMR, DSC, WAXS, Joint, real datasets, generated
  outputs, memory, or test-storage directories.

## Affected boundaries

- `rag/advisor.py`: keep parsing and normalization inside the provider failure
  boundary while preserving cancellation propagation.
- `tests/test_advisor.py`: malformed-response and cancellation regressions.
- Task design, plan, acceptance, and checkpoint records.

## Acceptance criteria

- [x] A provider response that parses but fails normalization returns the
      existing mock/failure advice with `llm_used=False`.
- [x] `LLMCancelledError` escapes unchanged and is not converted to fallback.
- [x] Existing Advisor, prompt, summary, and live-context tests remain green.
- [x] Task verifier, diff check, and explicit allowlist checkpoint have exact
      recorded outcomes.
- [x] No parallel memory, real data, scratch, or test-storage path enters the
      checkpoint.

## Implementation plan

1. Preserve the inherited regression tests and current production diff.
2. Run the focused Advisor test and the combined shared AI/context matrix.
3. Run task-scoped verification and `git diff --check`.
4. Record exact results and checkpoint only the explicit allowlist.

## Verification

```powershell
$env:POLYNEXUS_TEST_ROOT='D:\PolyNexus-test-runs-advisor-fallback'
$env:POLYNEXUS_TEST_RETENTION='ephemeral'
python -m pytest -q tests/test_advisor.py -o addopts=
python -m pytest -q tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_live_context.py -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-advisor-provider-fallback.md --changed --types
git diff --check
```

All test claims require a complete pytest summary and exit code `0`.

## Explicit changed-file allowlist

- `rag/advisor.py`
- `tests/test_advisor.py`
- `docs/superpowers/specs/2026-07-31-advisor-provider-fallback-design.md`
- `docs/superpowers/plans/2026-07-31-advisor-provider-fallback.md`
- `docs/agent/tasks/2026-07-31-advisor-provider-fallback.md`
- `docs/acceptance/2026-07-31-advisor-provider-fallback.md`

Parallel memory edits, real datasets, generated outputs, scratch directories,
and test-storage paths are intentionally excluded.

## Evidence

- Advisor regression: `8 passed in 0.37s`, exit code `0`.
- Combined Advisor/Prompt/summary/live-context suite: `19 passed in
  1.90s`, exit code `0`.
- Task-scoped verifier: exit code `0`; quality `297 passed`, preprocessing
  `106 passed`, with task/memory, Ruff, compile, type baseline, and whitespace
  checks passing.
- `git diff --check`: exit code `0` through the verifier.
