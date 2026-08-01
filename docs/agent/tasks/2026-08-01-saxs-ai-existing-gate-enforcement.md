---
task_id: 2026-08-01-saxs-ai-existing-gate-enforcement
kind: scientific-cross-module
status: completed
date: 2026-08-01
title: Enforce existing SAXS gates for AI preprocessing candidates
---

# SAXS AI existing-gate enforcement

## Goal

Prevent a SAXS AI preprocessing candidate from being confirmed or automatically
applied unless the existing SAXS physical and quality gates pass on the trial
result.

## Non-goals

- no new physical threshold, quality level, rescue algorithm, interpolation,
  frame repair, or raw q/I handling;
- no model/provider/RAG change and no change to manual confirmed-rerun
  transaction semantics;
- no Figure, Manifest, Export, publication-role, or real-dataset change;
- no `scripts/test_storage.py --apply`.

## Affected boundaries

- `polynexus/orchestrator_preprocess.py`: compose the existing SAXS assessment
  with the generic AI candidate decision;
- `polynexus/core/saxs_engine/saxs_ai_rescue.py`: read-only authority via
  `assess_saxs_confirmed_rerun()`;
- `tests/test_saxs_ai_orchestrator_handoff.py`: regression for failed and
  passing static/temperature/strain candidate trials;
- this task's spec, plan, task card, and acceptance record.

## Acceptance criteria

- [x] A generic-metric-positive candidate with failed or missing existing SAXS
      quality/physical evidence is `keep_original` and `apply_allowed=False`.
- [x] Existing passing evidence keeps the calibrated tiered-auto behavior for
      static, temperature, and strain modes.
- [x] Decision/replay evidence exposes the two existing-gate hard guards and
      remains strict-JSON; original config/result are preserved on rejection.
- [x] Non-SAXS preprocessing and the manual confirmed-rerun transaction remain
      unchanged.
- [x] Focused regression, SAXS matrix, structured verifier, storage dry-run,
      diff audit, and an explicit allowlist checkpoint are recorded.

## Implementation plan

1. [x] Add a failing orchestration regression where generic preprocessing
   evidence passes but the candidate's existing SAXS quality level is
   `Diagnostic`; verify it currently reaches `auto_accept`.
2. [x] Add the minimal SAXS-only gate composition after trial evidence is built,
   using `assess_saxs_confirmed_rerun()` and no new threshold.
3. [x] Update the fake SAXS trial to carry explicit passing existing evidence
   and verify static, temperature, and strain passing/rejection behavior.
4. [x] Run focused tests, the complete SAXS matrix, task-scoped verifier,
   storage report/clean dry-run, and `git diff --check`.
5. [x] Update acceptance evidence and create the explicit allowlist checkpoint.

## Scientific boundary

The change only prevents AI candidate application when current deterministic
SAXS evidence is unavailable or fails. It does not make detector geometry,
orientation, temperature, strain, or publication meaning scientifically
approved.

## Evidence so far

- TDD RED: the new Diagnostic-quality candidate test failed with
  `expected keep_original, got auto_accept`.
- Focused GREEN and adjacent safety matrix: `46 passed in 0.42s`, exit code
  `0`, covering static, temperature, strain, confirmed reruns, rescue bridge,
  and preprocessing automation.
- Complete SAXS matrix: `720 passed, 6 warnings in 443.79s`, exit code `0`.
- Task-scoped verifier exited `0`: quality `297 passed` and preprocessing
  `106 passed`; task/memory, Ruff, compile, type baseline, and whitespace
  checks passed.
- Storage report remained non-destructive with `147` artifacts and
  `34,459,622,776` bytes; the clean dry-run saw `148` artifacts. Both reported
  `eligible_bytes=0` and `failures=0`, with `removed=0`. No
  `test_storage.py --apply` ran.
- `git diff --check` exited `0`.

## Verification

```powershell
python -m pytest -q tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_saxs_ai_rescue_bridge.py tests/test_orchestrator_preprocess_automation.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-existing-gate-enforcement.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Pytest commands require complete summaries and exit code `0`. Storage commands
are non-destructive dry-runs; no `--apply` is authorized by this task.

## Explicit changed-file allowlist

- `polynexus/orchestrator_preprocess.py`
- `tests/test_saxs_ai_orchestrator_handoff.py`
- `docs/superpowers/specs/2026-08-01-saxs-ai-existing-gate-enforcement-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-ai-existing-gate-enforcement.md`
- `docs/agent/tasks/2026-08-01-saxs-ai-existing-gate-enforcement.md`
- `docs/acceptance/2026-08-01-saxs-ai-existing-gate-enforcement.md`

Parallel memory, real-boundary, scratch, generated-output, and test-storage
changes remain outside this checkpoint.
