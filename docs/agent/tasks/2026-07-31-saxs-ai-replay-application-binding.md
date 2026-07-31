---
task_id: 2026-07-31-saxs-ai-replay-application-binding
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Bind SAXS AI replay audit to application outcome
---

# SAXS AI replay application binding

## Goal

Make `saxs_ai_rescue_replay` report the final shared preprocessing decision and
whether the selected candidate was actually committed.

## Non-goals

- No new SAXS physical or quality thresholds.
- No model call, intent generation, or raw-data transport.
- No change to shadow/confirmation/calibrated-auto policy rules.
- No edits to real data, generated outputs, scratch, storage, or parallel memory.

## Affected boundaries

- `polynexus/core/preprocess_optimization/replay.py`
- `polynexus/orchestrator_preprocess.py`
- `tests/test_preprocess_replay_contract.py`
- `tests/test_saxs_ai_orchestrator_handoff.py`

## Acceptance criteria

- [x] Calibrated auto-accept records `apply_performed=True` only for the selected
  replay row after a successful commit.
- [x] Commit failure records the final `keep_original` decision and leaves
  `apply_performed=False`.
- [x] Shadow, confirmation, failed trial, JSON-safe serialization, and existing
  SAXS hard gates remain unchanged.
- [x] The original config remains preserved in every replay row.

## Implementation plan

1. Extend the shared replay audit builder with an optional application-result
   flag that defaults to `False`.
2. Add RED tests for successful calibrated SAXS commit and failed commit audit
   synchronization.
3. Build SAXS replay rows after the existing commit branch from the final
   decision and application outcome.
4. Run focused tests, the SAXS matrix, structured verification, and storage
   dry-run before creating the explicit checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py -k replay_application
python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py tests/test_preprocess_replay_contract.py
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-replay-application-binding.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

The full/boundary release command is intentionally not part of this atomic
task; historical runs are recorded as incomplete when they end without a
pytest summary. Storage commands are dry-run only.

## Evidence

- Focused RED: `python -m pytest -q tests/test_preprocess_replay_contract.py
  -k application` failed with the expected unexpected-keyword `TypeError`.
- SAXS RED: `python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py
  -k replay_application` failed because successful commit was recorded as
  `apply_performed=False` and failed commit retained `auto_accept`.
- Focused GREEN: `12 passed in 0.31s`.
- Extended orchestrator/replay/bridge matrix: `28 passed in 0.54s`.
- SAXS matrix: `680 passed, 6 warnings in 539.16s`, exit code `0`.
- Structured verifier: exit code `0`; quality `297 passed`, preprocessing
  `106 passed`, Ruff, compile, type baseline, memory, task, and whitespace
  checks passed.
- Storage report: exit code `0`, `60` artifacts, `1,368,591,551` bytes,
  `10,911` eligible bytes at report time, `removed=false`.
- Storage clean dry-run: exit code `0`, `13` emergency-eligible artifacts,
  `18,784` bytes, `removed=false`.
- `git diff --check`: exit code `0`.

## Implementation status

- [x] Existing intent validation, candidate execution, and shared decision
  path inspected; no duplicate handoff is needed.
- [x] RED tests written and observed failing (`TypeError` and stale replay audit).
- [x] Minimal implementation written and GREEN (`12 passed` focused).
- [x] Structured verification and SAXS matrix completed.
- [x] Explicit allowlist checkpoint created with `auto_commit.py`; final hash
  is reported in the completion record.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py -k replay_application
python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py tests/test_preprocess_replay_contract.py
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-replay-application-binding.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Storage commands are dry-run only. No `test_storage.py --apply` is authorized
for this task.

## Changed-file allowlist

- `polynexus/core/preprocess_optimization/replay.py`
- `polynexus/orchestrator_preprocess.py`
- `tests/test_preprocess_replay_contract.py`
- `tests/test_saxs_ai_orchestrator_handoff.py`
- `docs/superpowers/specs/2026-07-31-saxs-ai-replay-application-binding-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-ai-replay-application-binding.md`
- `docs/agent/tasks/2026-07-31-saxs-ai-replay-application-binding.md`
