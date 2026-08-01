---
task_id: 2026-08-01-saxs-ai-sequence-rescue-context
kind: scientific-cross-module
status: completed
date: 2026-08-01
title: Transport existing SAXS sequence rescue candidates to AI context
---

# SAXS AI sequence rescue context

## Goal

Make existing deterministic temperature sequence-rescue candidates visible to
the summary-only SAXS AI context while preserving candidate-only and
fail-closed semantics.

## Non-goals

- no new rescue algorithm, threshold, quality level, physical gate, or
  publication decision;
- no interpolation, missing-frame fabrication, candidate execution, rerun,
  configuration mutation, or automatic acceptance;
- no raw q/I, detector pixels, source paths, real data, generated outputs,
  memory, scratch, or storage changes.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`: strict detached projection
  and prompt sanitizer whitelist;
- `tests/test_saxs_ai_summary_context.py`: summary contract regression;
- `tests/test_advisor.py`: actual Advisor prompt regression;
- this task's spec, plan, task card, and acceptance record.

## Acceptance criteria

- [x] Temperature context exposes existing `sequence_rescue_candidates` under
      `series` with only the documented candidate and parameter fields.
- [x] Static and strain contexts do not gain fabricated sequence candidates.
- [x] Unknown fields and raw q/I, detector, and source-path fields are absent;
      output remains detached and strict-JSON-safe.
- [x] Candidate-only, preserve-missing-frames, and validation-required flags
      remain explicit; no candidate is executed or promoted.
- [x] Focused regression, SAXS matrix, structured verifier, storage dry-run,
      diff audit, and explicit checkpoint are recorded.

## Implementation plan

1. Add RED regressions for temperature candidate projection, prompt transport,
   raw-field exclusion, and static/strain absence.
2. Add the strict candidate and parameter whitelist to the existing SAXS
   summary builder and prompt sanitizer.
3. Run focused regressions, the complete SAXS matrix, and the task-scoped
   structured verifier.
4. Run storage report/clean dry-run, update acceptance evidence, audit the
   explicit allowlist, and create one local checkpoint.

## TDD evidence

- RED: the two initial projection/prompt tests failed as expected because the
  current builder did not expose `sequence_rescue_candidates`.
- GREEN: focused Advisor/prompt/summary/live/audit regression passed `33`.

## Verification evidence

- Complete SAXS matrix: `723 passed, 6 warnings in 476.46s`, exit code `0`.
- Structured verifier: exit code `0`; quality `297 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile, type baseline, and whitespace checks
  passed.
- Storage report and clean dry-run: `149` artifacts,
  `34,459,623,896` total bytes, `eligible_bytes=0`, `removed=0`, and
  `failures=0`. No `test_storage.py --apply` was executed.
- `git diff --check` is required immediately before checkpointing.

## Verification

```powershell
python -m pytest -q tests/test_saxs_ai_summary_context.py tests/test_advisor.py tests/test_saxs_prompt_builder.py -o addopts=
python -m pytest -q tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_live_context.py tests/test_saxs_prompt_builder.py tests/test_advisor.py tests/test_saxs_ai_acceptance_audit_context.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-sequence-rescue-context.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Pytest claims require a complete summary and exit code `0`. Storage commands
are dry-run only; `test_storage.py --apply` is not part of this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `tests/test_saxs_ai_summary_context.py`
- `tests/test_advisor.py`
- `docs/superpowers/specs/2026-08-01-saxs-ai-sequence-rescue-context-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-ai-sequence-rescue-context.md`
- `docs/agent/tasks/2026-08-01-saxs-ai-sequence-rescue-context.md`
- `docs/acceptance/2026-08-01-saxs-ai-sequence-rescue-context.md`

Parallel memory, GUI, real-data, generated-output, scratch, and test-storage
changes remain outside this checkpoint.
