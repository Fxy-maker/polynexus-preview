---
task_id: 2026-08-01-saxs-sequence-rescue-reference-resolution
kind: scientific-cross-module
status: completed
date: 2026-08-01
title: Resolve advisory SAXS sequence-rescue references deterministically
---

# SAXS sequence-rescue reference resolution

## Goal

Turn an allowlisted AI candidate ID into one existing deterministic temperature
`RescueCandidate` only when its current full record proves the candidate
identity; never execute or accept the candidate in this step.

## Non-goals

- no new rescue algorithm, threshold, quality level, physical/quality/sequence
  gate, interpolation, missing-frame fabrication, rerun, or configuration
  mutation;
- no AI prompt/Advisor change, GUI selection control, Workbench, Figure,
  Manifest, or Export change;
- no automatic acceptance and no call to the analysis engine;
- no real datasets, memory, scratch, storage cleanup, or
  `scripts/test_storage.py --apply`.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_sequence_rescue.py`: pure resolver beside
  existing candidate construction and validation;
- `polynexus/core/saxs_engine/__init__.py`: public package export;
- `tests/test_saxs_sequence_rescue.py`: identity, detachment, and fail-closed
  regressions;
- this task's spec, plan, task card, and acceptance evidence.

## Acceptance criteria

- [x] A unique current temperature deterministic candidate with the existing
      source, axis, metric, candidate-only, preservation, and validation
      markers resolves to a fresh `RescueCandidate`.
- [x] Unknown, empty, malformed, duplicate, AI-kind, source-missing,
      candidate-only-mismatch, and non-temperature requests return `None`.
- [x] Resolution does not call analysis, modify source frames/configuration,
      or create an accepted validation report.
- [x] Existing `validate_sequence_rescue_candidate` gate semantics remain
      unchanged and existing AI candidate/gate tests remain green.
- [x] Focused tests, SAXS matrix, structured verifier, storage dry-run, diff
      audit, and an explicit allowlist checkpoint are recorded.

## Implementation plan

1. [x] Add resolver RED tests for a valid detached match and fail-closed identity
   boundaries.
2. [x] Implement and export the pure resolver with no new scientific threshold.
3. [x] Run focused GREEN, complete SAXS verification, structured verifier, and
   storage report/clean dry-run.
4. [x] Update acceptance evidence, audit the allowlist, and create one checkpoint.

## Scientific boundary

This task only restores the identity of an already-produced deterministic
candidate from the current result object. It does not assert that any existing
SAXS physical, quality, or sequence gate passed. A later validation caller must
still provide explicit gate results to `validate_sequence_rescue_candidate`.

## TDD evidence

- RED: resolver tests failed at collection with the expected missing public API
  error because `resolve_sequence_rescue_candidate` did not yet exist.
- GREEN: resolver tests passed `9 passed in 0.18s`; focused sequence/AI/
  confirmed-rerun/orchestrator matrix passed `80 passed in 1.79s`.
- The shared AI live-context test contract was minimally corrected without
  production changes: temperature asserts
  `series.guinier_sequence_evidence`, while strain asserts
  `metric_evidence.guinier`. Fresh live-context coverage passed `6 passed in
  1.04s`; the combined Advisor/prompt/sequence/orchestrator focused matrix
  passed `86 passed in 1.64s`.
- Complete SAXS matrix: `734 passed, 6 warnings in 485.43s`, exit code `0`.
- Structured verifier exited `0`: task card and memory checks passed, Ruff,
  compile, type baseline, and whitespace passed; quality `297 passed` and
  preprocessing `106 passed`.
- Storage report and clean dry-run both used `mode=dry-run`: report found `156`
  artifacts and `34,472,130,143` bytes; clean found `eligible_bytes=0`,
  `eligible_count=19`, `removed_count=0`, and `failures=0`. No
  `test_storage.py --apply` was executed.
- `git diff --check` is required immediately before checkpointing.

## Verification

```powershell
python -m pytest -q tests/test_saxs_sequence_rescue.py tests/test_saxs_ai_summary_context.py tests/test_advisor.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_orchestrator_loop.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-sequence-rescue-reference-resolution.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Storage commands are non-destructive dry-runs; no `--apply` is authorized.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_sequence_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_sequence_rescue.py`
- `docs/superpowers/specs/2026-08-01-saxs-sequence-rescue-reference-resolution-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-sequence-rescue-reference-resolution.md`
- `docs/agent/tasks/2026-08-01-saxs-sequence-rescue-reference-resolution.md`
- `docs/acceptance/2026-08-01-saxs-sequence-rescue-reference-resolution.md`

Parallel memory, AI prompt, GUI, real-data, generated-output, scratch, and
test-storage changes remain outside this checkpoint.
