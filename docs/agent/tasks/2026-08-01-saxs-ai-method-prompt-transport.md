---
task_id: 2026-08-01-saxs-ai-method-prompt-transport
kind: scientific-cross-module
status: completed
date: 2026-08-01
title: Verify SAXS 1D method evidence in the Advisor prompt
---

# SAXS AI 1D method prompt transport

## Goal

Verify that the real Advisor prompt retains existing Guinier, Porod, Kratky,
invariant, and lamellar evidence after SAXS summary sanitization.

## Non-goals

- no production code, model-provider, RAG, prompt instruction, threshold,
  physical gate, candidate, rescue, or publication behavior change;
- no raw q/I, detector pixels, source paths, interpolation, or frame repair;
- no real data, Figure/Manifest/Export, memory, scratch, or storage changes.

## Affected boundaries

- `tests/test_advisor.py`: actual Advisor-to-`last_prompt` method evidence
  regression;
- existing `rag/advisor.py`, `rag/prompt_builder.py`, and SAXS sanitizer are
  read-only boundaries under test;
- this task's spec, plan, acceptance, and task card.

## Acceptance criteria

- [x] All five existing 1D method evidence keys appear in the actual Advisor
      prompt after normalization and sanitization.
- [x] The prompt retains `candidate_only` and
      `physical_validation_required` safeguards.
- [x] Existing Advisor/prompt behavior and raw-field exclusion remain green.
- [x] Focused regression, complete SAXS matrix, structured verifier, storage
      dry-run, diff, and explicit checkpoint are recorded.

## Implementation plan

1. [x] Add the Advisor prompt regression with detached summary evidence.
2. [x] Run the focused Advisor/prompt/summary suite and inspect the actual
   prompt assertions.
3. [x] Run the complete SAXS matrix and task-scoped structured verifier.
4. [x] Run storage report/clean dry-run and diff audit.
5. [x] Record exact outcomes and create a test-plus-documentation checkpoint.

## Evidence

- Fresh Advisor/prompt/summary/live regression: `25 passed in 2.61s`, exit code
  `0`. The captured `Advisor.last_prompt` retained Guinier, Porod, Kratky,
  invariant, and lamellar keys plus candidate-only and physical-validation
  safeguards.
- Fresh complete SAXS matrix: `713 passed, 6 warnings in 482.99s`, exit code
  `0`.
- Structured verifier exited `0`: quality `297 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile, type-baseline, and whitespace checks
  passed.
- Storage report and dry-run clean both exited `0`: `145` artifacts,
  `34,459,621,656` total bytes, `eligible_bytes=0`, `failures=[]`, and
  `removed=0`. No `test_storage.py --apply` was executed.
- `git diff --check` passed. No production code changed.

## Verification

```powershell
python -m pytest -q tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_live_context.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-method-prompt-transport.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Pytest requires a complete summary and exit code `0`; storage commands are
dry-run only and `--apply` is not authorized.

## Explicit changed-file allowlist

- `tests/test_advisor.py`
- `docs/superpowers/specs/2026-08-01-saxs-ai-method-prompt-transport-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-ai-method-prompt-transport.md`
- `docs/agent/tasks/2026-08-01-saxs-ai-method-prompt-transport.md`
- `docs/acceptance/2026-08-01-saxs-ai-method-prompt-transport.md`

Parallel production, memory, GUI, real-data, generated-output, scratch, and
test-storage changes remain outside this checkpoint.
