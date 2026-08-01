---
task_id: 2026-08-01-saxs-ai-candidate-reference-contract
kind: scientific-cross-module
status: completed
date: 2026-08-01
title: Add a fail-closed SAXS AI candidate reference contract
---

# SAXS AI candidate reference contract

## Goal

Let the Advisor identify an existing deterministic temperature sequence-rescue
candidate for diagnosis while guaranteeing that the reference cannot become an
executable rescue request.

## Non-goals

- no new rescue algorithm, threshold, quality level, physical/quality/sequence
  gate, interpolation, missing-frame fabrication, or automatic acceptance;
- no new execution, rerun, configuration mutation, GUI control, or change to
  the existing `PreprocessIntent` schema;
- no raw q/I, detector pixels, source paths, real datasets, Figure/Manifest/
  Export, memory, scratch, or storage changes;
- no `scripts/test_storage.py --apply`.

## Affected boundaries

- `rag/advisor.py`: derive the current candidate-ID allowlist and normalize
  the advisory reference field;
- `rag/prompt_builder.py`: describe the strict diagnostic-only response field;
- `tests/test_advisor.py` and `tests/test_saxs_prompt_builder.py`: RED/GREEN
  contract regressions;
- this task's spec, plan, task card, and final acceptance evidence.

## Acceptance criteria

- [x] Temperature SAXS context accepts only exact IDs already present in
      `series.sequence_rescue_candidates`, deduplicated in first-seen order.
- [x] Unknown, duplicate, non-string, malformed, static, strain, unsupported,
      missing-context, and non-SAXS references fail closed to an empty list.
- [x] Reference-only advice retains empty `changes`, no preprocess intent, and
      no executable candidate plan; existing orchestrator dispatch is unchanged.
- [x] Prompt explicitly requires exact current IDs and labels references as
      diagnostic-only, with no execute/rerun/config-mutation semantics.
- [x] Existing candidate-only, raw-field, physical-gate, quality-gate, and
      strict-JSON behavior remains green.
- [x] Focused tests, SAXS matrix, structured verifier, storage dry-run, diff
      audit, and an explicit allowlist checkpoint are recorded.

## Implementation plan

1. [x] Add Advisor and prompt RED tests for valid/invalid references and the
   diagnostic-only contract.
2. [x] Add the minimal context-derived ID allowlist normalizer and SAXS prompt
   language.
3. [x] Run focused GREEN, complete SAXS verification, structured verifier, and
   storage report/clean dry-run.
4. [x] Update evidence, audit the allowlist, and create one local checkpoint.

## Scientific boundary

The only new information crossing the AI output boundary is a reference to an
already-produced deterministic candidate ID. The reference does not assert
that the candidate is scientifically valid. Existing frame-level evidence,
SAXS physical/quality gates, sequence validation, and any later human
confirmation remain authoritative.

## TDD evidence

- RED: the initial three contract tests failed because Advisor omitted
  `saxs_candidate_references` and the prompt had no reference contract. The
  added non-SAXS boundary test also failed with the expected missing-field
  assertion before the final fail-closed normalization condition.
- GREEN: focused Advisor/prompt/summary/live/orchestrator matrix passed `42
  passed in 1.39s`; the final four explicit candidate-boundary assertions
  passed `4 passed in 0.18s`.
- Complete SAXS matrix: `725 passed, 6 warnings in 481.33s`, exit code `0`.
- Structured verifier exited `0`: task card and memory checks passed, Ruff,
  compile, type baseline, and whitespace passed; quality `297 passed` and
  preprocessing `106 passed`.
- Storage report and clean dry-run both used `mode=dry-run`: report found `155`
  artifacts and `34,468,506,754` bytes; clean found `eligible_bytes=0`,
  `eligible_count=19`, `removed_count=0`, and `failures=0`. No
  `test_storage.py --apply` was executed.
- `git diff --check` is required immediately before checkpointing.

## Verification

```powershell
python -m pytest -q tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_live_context.py tests/test_saxs_orchestrator_loop.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-candidate-reference-contract.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Storage commands are non-destructive dry-runs; no `--apply` is authorized by
this task.

## Explicit changed-file allowlist

- `rag/advisor.py`
- `rag/prompt_builder.py`
- `tests/test_advisor.py`
- `tests/test_saxs_prompt_builder.py`
- `docs/superpowers/specs/2026-08-01-saxs-ai-candidate-reference-contract-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-ai-candidate-reference-contract.md`
- `docs/agent/tasks/2026-08-01-saxs-ai-candidate-reference-contract.md`
- `docs/acceptance/2026-08-01-saxs-ai-candidate-reference-contract.md`

Parallel memory, GUI, real-data, generated-output, scratch, and test-storage
changes remain outside this checkpoint.
