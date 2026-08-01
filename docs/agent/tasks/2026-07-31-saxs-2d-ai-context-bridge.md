---
task_id: 2026-07-31-saxs-2d-ai-context-bridge
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Bridge SAXS 2D reviewer context into summary-only AI context
---

# SAXS 2D AI context bridge

## Goal

Carry the existing 2D reviewer DTO through the SAXS AI summary and prompt
sanitizer while preserving candidate-only and physical-validation boundaries.

## Non-goals

- no model/provider/RAG change, intent generation, candidate execution, rescue,
  rerun, apply, or configuration mutation;
- no q/I, detector-pixel, geometry, mask, beam-center, or orientation
  calculation and no new threshold or publication decision;
- no Figure/Manifest/Export/Workbench/History behavior change;
- no real data, generated output, storage, scratch, or parallel memory edits.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_2d_review_context.py`: trusted and prompt
  sanitizer entry points;
- `polynexus/core/saxs_engine/saxs_ai_rescue.py`: optional summary projection;
- `polynexus/core/saxs_engine/__init__.py`: public sanitizer export;
- `tests/test_saxs_2d_ai_context_bridge.py`: bridge/security regressions.

## Acceptance criteria

- [x] Existing static/temperature/strain 2D summaries reach the optional SAXS
  AI context only when 2D evidence exists.
- [x] Prompt-side sanitization retains only the fixed DTO and drops q/I,
  pixels, paths, unknown fields, and prompt instructions.
- [x] Missing 2D evidence leaves existing summary and prompt behavior unchanged.
- [x] Context remains strict JSON-safe, detached, candidate-only, and requires
  existing physical validation.
- [x] No Advisor execution, candidate, rescue, rerun, or publication authority
  changes.
- [x] TDD RED/GREEN, SAXS matrix, structured verifier, storage dry-run, diff,
  and explicit allowlist checkpoint are recorded.

## Implementation plan

1. [x] Add RED tests for trusted 2D projection, prompt sanitization, raw-data
   exclusion, strict JSON, immutability, and absent-context compatibility.
2. [x] Add the fixed 2D DTO sanitizer and attach the existing mode-specific DTO to
   the summary-only SAXS context.
3. [x] Run focused AI/Advisor/prompt regressions and the complete SAXS matrix.
4. [x] Run the task verifier and storage dry-runs, review disjoint diff, and create
   the explicit allowlist checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_2d_ai_context_bridge.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_acceptance_audit_context.py tests/test_saxs_prompt_builder.py tests/test_advisor.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-2d-ai-context-bridge.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Only complete pytest summaries with exit code `0` count as pass evidence.
Storage commands are dry-run only; `test_storage.py --apply` is forbidden.

## Evidence

- TDD RED: `python -m pytest -q tests/test_saxs_2d_ai_context_bridge.py -o addopts=`
  returned `4 failed, 2 passed in 0.87s`; failures were the missing summary
  field and sanitizer bridge.
- Initial GREEN returned `6 passed in 0.25s`.
- Advisor/summary/audit/prompt regression returned `25 passed in 0.47s`;
  live-context regression returned `6 passed in 1.43s`.
- Final focused bridge/Advisor/prompt/live regression returned `32 passed in
  1.67s`, including malformed nested DTO fail-closed coverage. The existing
  temperature assertion remains `series.guinier_sequence_evidence`; the
  strain assertion remains `series.metric_evidence.guinier`.
- Latest fresh SAXS matrix returned `707 passed, 6 warnings in 486.94s` with
  exit code `0`.
- Latest task-card focused bridge/AI/Advisor/prompt regression returned
  `26 passed in 0.41s` with exit code `0`.
- Final structured verifier exited `0`: quality `297 passed`, preprocessing
  `106 passed`, Ruff/compile/type-baseline/whitespace passed.
- Storage `report --json` and `clean --older-than-hours 24 --json` were both
  dry-runs: `142` artifacts, `28,835,126,572` total bytes,
  `15,743,185,346` eligible bytes, `removed=0`, failures `0`. No
  `test_storage.py --apply` was executed.
- Final `git diff --check` passed.

## Completion

The bridge is complete within the explicit allowlist. The 2D reviewer DTO is
optional summary evidence only; Advisor/model execution, candidate generation,
physical validation, rescue/rerun/apply, and publication authority remain
unchanged. Parallel memory, GUI, scratch, generated output, and test-storage
changes were intentionally left untouched.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_2d_review_context.py`
- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_2d_ai_context_bridge.py`
- `docs/superpowers/specs/2026-07-31-saxs-2d-ai-context-bridge-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-2d-ai-context-bridge.md`
- `docs/agent/tasks/2026-07-31-saxs-2d-ai-context-bridge.md`

Parallel memory, `pytest.ini`, GUI, scratch, test-storage, real-data, and
generated-output changes remain outside this checkpoint.
