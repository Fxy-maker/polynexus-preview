---
task_id: 2026-07-31-saxs-ai-summary-context
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Add summary-only SAXS AI context contract
---

# SAXS AI summary-only context

## Goal

Provide the future SAXS model adapter with a deterministic, strict-JSON
summary of already-computed quality and physical evidence, without exposing
raw q/I or detector data and without changing any decision authority.

## Non-goals

- No model call, model provider, RAG retrieval, or intent generation.
- No q/I or 2D detector processing, interpolation, imputation, frame repair,
  new threshold, or new physical gate.
- No candidate execution, automatic rescue, configuration mutation, quality
  level change, publication decision, Figure/Manifest/Export change.
- No changes to real data, generated outputs, scratch, storage, or parallel
  memory/worktree files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`: deterministic context DTO.
- `polynexus/core/saxs_engine/__init__.py`: public helper export.
- `rag/prompt_builder.py`: optional SAXS context rendering.
- Focused SAXS AI context and prompt regressions.

## Implementation plan

1. Add RED tests for strict-JSON summary projection, fail-closed missing or
   unsupported evidence, and optional prompt rendering.
2. Implement the context projection by reusing existing SAXS evidence/status
   helpers, then export it through the public SAXS engine module.
3. Bind the optional context to the SAXS prompt without changing the prompt
   when no context is supplied.
4. Run focused tests, the exact SAXS matrix, task-scoped verification, diff
   checks, and storage dry-runs before creating the explicit checkpoint.

## Acceptance criteria

- [x] Existing result evidence is projected into strict JSON with quality and
  physical status, candidate-only state, and explicit raw-data exclusion.
- [x] Missing/unsupported evidence fails closed as unavailable without
  fabricated values.
- [x] The SAXS prompt includes the optional context and tells the model to
  return only an intent; absent context preserves the current prompt.
- [x] Existing validator, candidate, decision, quality, physical, rescue,
  publication, Figure, Manifest, and Export behavior is unchanged.
- [x] TDD RED/GREEN, task verifier, SAXS matrix, diff check, storage dry-run,
  and explicit allowlist checkpoint are recorded.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_ai_summary_context.py tests/test_saxs_prompt_builder.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-summary-context.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

No `test_storage.py --apply` is part of this task.

## Verification

The task is complete only when the focused tests, exact SAXS matrix, structured
verifier, and diff check have complete summaries and exit code `0`. A timeout,
collection error, or process exit without a pytest summary is recorded as
incomplete rather than pass evidence.

The structured command is:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-summary-context.md --changed --types
```

## Evidence

- TDD RED: collection failed because `build_saxs_ai_summary_context` did not
  exist.
- Focused GREEN and existing AI/prompt regressions: `38 passed` in `0.41s`,
  exit code `0`.
- A second TDD RED exposed that an untrusted prompt context could carry raw
  fields; the sanitizer whitelist fixed it and the focused suite passed `6`.
- Exact SAXS matrix after the sanitizer: `678 passed, 6 warnings` in
  `486.95s`, exit code `0`.
- Structured verifier: exit code `0`; quality gate `297 passed`, preprocessing
  gate `106 passed`, Ruff, compile, type baseline, memory/task, and whitespace
  checks passed.
- Storage report and `clean --older-than-hours 24 --json` were dry-run only,
  both exit code `0`; final inventory was `57` artifacts,
  `1,368,589,871` bytes total, `7,873` eligible bytes, and `0` removed.
- `git diff --check`: exit code `0`.

The summary-only context is not a model call or an authorization path. It
contains only existing compact evidence and explicitly records that raw
profile/detector data is excluded. Existing SAXS validation and decision gates
remain authoritative.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `rag/prompt_builder.py`
- `tests/test_saxs_ai_summary_context.py`
- `tests/test_saxs_prompt_builder.py`
- `docs/superpowers/specs/2026-07-31-saxs-ai-summary-context-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-ai-summary-context.md`
- `docs/agent/tasks/2026-07-31-saxs-ai-summary-context.md`
- `docs/acceptance/2026-07-31-saxs-ai-summary-context.md`

Parallel memory edits, scratch directories, real data, and test-storage
artifacts remain outside this task.
