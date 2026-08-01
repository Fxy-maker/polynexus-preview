---
task_id: 2026-08-01-saxs-ai-reference-resolution-bridge
kind: scientific-cross-module
status: completed
date: 2026-08-01
title: Attach deterministic SAXS AI candidate reference resolution
---

# SAXS AI reference resolution bridge

## Goal

Make an AI-returned SAXS sequence-candidate ID reviewable against the current
full temperature result without turning the advisory response into execution.

## Non-goals

- no new SAXS threshold, rescue algorithm, quality level, or physical gate;
- no analysis rerun, interpolation, missing-frame fabrication, or config change;
- no AI prompt redesign or Advisor normalization change;
- no automatic candidate acceptance or validation report;
- no GUI, Workbench, Figure, Manifest, Export, real dataset, memory, scratch,
  or test-storage cleanup change;
- no `scripts/test_storage.py --apply`.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`: pure diagnostic resolver
  adapter using the existing sequence-candidate resolver;
- `polynexus/orchestrator_run_round.py`: attach detached diagnostic evidence
  after the advisory call;
- `tests/test_saxs_ai_rescue_bridge.py` and `tests/test_saxs_orchestrator_loop.py`;
- this task's spec, plan, and acceptance note.

## Acceptance criteria

- [x] One exact temperature AI reference resolves only against one current,
      fully-provenanced deterministic candidate.
- [x] Unknown, malformed, duplicate, incomplete, static, strain, and
      unsupported inputs fail closed with explicit reason codes.
- [x] The returned record is detached and JSON-safe; source result, advice,
      engine configuration, and analysis state remain unchanged.
- [x] Orchestrator history receives the diagnostic field without changing
      existing AI response fields or execution decisions.
- [x] Focused tests, complete SAXS matrix, structured verifier, dry-run storage
      audit, diff audit, and explicit allowlist checkpoint are recorded.

## Scientific boundary

Resolution proves identity/provenance only. Existing physical, quality, and
sequence gates remain authoritative and must be evaluated by a later explicit
review/validation action.

## Implementation plan

1. [x] Add RED coverage for pure reference resolution and orchestrator
   diagnostic attachment.
2. [x] Implement the fail-closed core bridge and export it through the SAXS
   engine package.
3. [x] Attach the detached resolution record after the SAXS Advisor call
   without changing execution decisions.
4. [x] Run structured verification, storage dry-run, diff audit, and create
   the explicit allowlist checkpoint.

## Verification

### TDD and verification evidence

- RED: collection failed because the new
  `resolve_saxs_ai_candidate_references` API was missing.
- GREEN: bridge/orchestrator focused tests passed `19 passed in 1.49s`.
- Follow-up live-context contract check initially exposed a test projection
  mismatch only: the temperature assertion must read
  `series.guinier_sequence_evidence`, while the strain assertion must read
  `series.metric_evidence.guinier`. The test contract was corrected without
  changing production logic; the fresh Advisor/prompt/live-context/orchestrator
  regression passed `48 passed in 2.58s`.
- Expanded AI/Advisor/prompt/confirmed-rerun/orchestrator/resolver focused
  tests passed `102 passed in 1.79s`.
- Complete SAXS matrix passed `740 passed, 6 warnings in 475.98s`, exit code
  `0`.
- Fresh current-HEAD SAXS matrix rerun passed `740 passed, 6 warnings in
  671.86s`, exit code `0`; this is the matrix used for the current handoff.
- Structured verifier passed task/memory checks, Ruff, compile, type baseline,
  whitespace, quality `297 passed`, and preprocessing `106 passed`.
- Storage report and clean were both dry-run: `158` artifacts,
  `eligible_bytes=0`, planned eligible count `19`, removed `0`, and no
  failures. No `test_storage.py --apply` was run.
- `git diff --check` is required immediately before checkpointing.

The focused and complete SAXS verification commands are listed below.

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-reference-resolution-bridge.md --changed --types
```

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_ai_rescue_bridge.py tests/test_saxs_ai_summary_context.py tests/test_advisor.py tests/test_saxs_orchestrator_loop.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-reference-resolution-bridge.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/orchestrator_run_round.py`
- `tests/test_saxs_ai_rescue_bridge.py`
- `tests/test_saxs_orchestrator_loop.py`
- `docs/superpowers/specs/2026-08-01-saxs-ai-reference-resolution-bridge-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-ai-reference-resolution-bridge.md`
- `docs/agent/tasks/2026-08-01-saxs-ai-reference-resolution-bridge.md`
- `docs/acceptance/2026-08-01-saxs-ai-reference-resolution-bridge.md`

Parallel memory, GUI, real-data, generated-output, scratch, and test-storage
changes remain outside this checkpoint.
