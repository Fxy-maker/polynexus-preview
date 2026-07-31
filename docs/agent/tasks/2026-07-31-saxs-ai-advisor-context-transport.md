---
task_id: 2026-07-31-saxs-ai-advisor-context-transport
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Transport summary-only SAXS AI context through Advisor
---

# SAXS AI Advisor context transport

## Goal

Ensure the real Advisor path preserves the existing summary-only SAXS AI
context until `PromptBuilder`, where the established raw-data sanitizer applies.

## Non-goals

- No model provider or new model call.
- No intent generation, candidate execution, configuration mutation, or
  automatic rescue.
- No q/I calculation, detector processing, new threshold, quality/physical
  gate, publication role, Figure, Manifest, or Export change.
- No edits to real data, generated outputs, scratch, storage, or parallel memory.

## Affected boundaries

- `rag/advisor.py`: optional context transport in `_normalize_case()`.
- `tests/test_advisor.py`: real Advisor-to-prompt regression.

## Implementation plan

1. Add a fake retriever/LLM RED test through `Advisor.advise()`.
2. Preserve a mapping-valued `saxs_ai_context` in the normalized case.
3. Run focused and full SAXS verification, then record the exact results.
4. Create one explicit allowlist checkpoint without mixing parallel files.

## Acceptance criteria

- [x] A SAXS context reaches the actual Advisor prompt.
- [x] Non-mapping context is ignored safely and no-context behavior is
  unchanged.
- [x] Prompt-side sanitizer remains the raw-data boundary.
- [x] TDD RED/GREEN, task verifier, SAXS matrix, diff check, storage dry-run,
  and explicit allowlist checkpoint are recorded.

## Verification

```powershell
python -m pytest -q tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_summary_context.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-advisor-context-transport.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

The storage commands are dry-run only; no `test_storage.py --apply` is part of
this task.

## Evidence

- TDD RED: the Advisor prompt omitted the context and non-mapping input raised
  a missing-key assertion because `_normalize_case()` dropped the field.
- Focused Advisor/prompt/AI suite: `44 passed` in `0.60s`, exit code `0`.
- Exact SAXS matrix: `678 passed, 6 warnings` in `480.99s`, exit code `0`.
- Structured verifier: exit code `0`; quality gate `297 passed`, preprocessing
  gate `106 passed`, Ruff, compile, type baseline, memory/task, and whitespace
  checks passed.
- Storage report and clean were dry-run only, exit code `0`; final inventory
  was `58` artifacts, `1,368,590,431` bytes total, `7,873` eligible bytes,
  and `0` removed.
- `git diff --check`: exit code `0`.

The change transports only the optional field. Prompt-side
`sanitize_saxs_ai_summary_context()` remains responsible for excluding raw
data before prompt construction; no model or preprocessing authority was
added.

## Explicit changed-file allowlist

- `rag/advisor.py`
- `tests/test_advisor.py`
- `docs/superpowers/specs/2026-07-31-saxs-ai-advisor-context-transport-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-ai-advisor-context-transport.md`
- `docs/agent/tasks/2026-07-31-saxs-ai-advisor-context-transport.md`
- `docs/acceptance/2026-07-31-saxs-ai-advisor-context-transport.md`

The previous summary-context checkpoint, memory edits, scratch, real data, and
test-storage artifacts are outside this task.
