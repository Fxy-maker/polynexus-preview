---
task_id: 2026-08-03-saxs-orientation-ai-advisory
kind: scientific
status: completed
date: 2026-08-03
title: Add read-only AI advisory for SAXS orientation evidence
---

## Goal

Project sanitized q-band and tracking evidence into a strict AI advisory that
can rank existing candidate IDs and explain limitations without mutation or
rerun authority.

## Scientific boundary

AI cannot create q bands, numbers, axes, masks, corrections, physical labels,
gates, candidates, reruns, or publication decisions.

## Non-goals

- No AI parameter tuning, preprocess candidate, confirmation, apply, or rerun.
- No model-authored numbers, physical labels, free-form scientific claims,
  axes, masks, corrections, or gates.
- No reuse of temperature sequence-rescue candidate references.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_2d_review_context.py`
- `polynexus/core/saxs_engine/saxs_orientation_advisory.py`
- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/core/saxs_batch_helpers.py`
- `rag/advisor.py`
- `rag/prompt_builder.py`
- `polynexus/gui/saxs_orientation_advisory_service.py`
- `polynexus/gui/main_window_workers.py`
- `polynexus/gui/main_window_results_mixin.py`
- `polynexus/gui/saxs_results_table_service.py`
- `polynexus/gui/analysis_history_service.py`
- `polynexus/gui/i18n.py`
- `polynexus/data/sample_db.py`
- `tests/test_saxs_orientation_ai_advisory.py`
- `tests/test_saxs_2d_ai_context_bridge.py`
- `tests/test_saxs_ai_summary_context.py`
- `tests/test_saxs_ai_confirmed_rerun_safety.py`
- `tests/test_advisor.py`
- `tests/test_saxs_prompt_builder.py`
- `tests/test_saxs_ai_orchestrator_handoff.py`
- `tests/test_saxs_ai_confirmation_gui_route.py`
- `tests/test_saxs_results_table_service.py`
- `tests/test_main_window_persistence.py`
- `tests/test_sample_db.py`
- This task card.

## Implementation plan

1. Add failing context-sanitization and no-authority tests.
2. Add compact q-band/track/correction evidence projection.
3. Implement a separate response namespace containing only existing IDs and
   allowlisted rationale/action codes; hydrate numbers and text locally.
4. Present advisory text without an apply or rerun action.
5. Run AI safety, SAXS, and structured verification.

## Acceptance criteria

- [x] Only existing source candidate IDs can be ranked.
- [x] Numeric values are copied from deterministic evidence, not model output.
- [x] Model output accepts no free-form numeric or scientific explanation text.
- [x] Raw arrays, paths, and unknown fields are excluded.
- [x] Missing/diagnostic evidence yields limitations-first output.
- [x] No apply, candidate creation, rerun, or publication path exists.

## Verification

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_orientation_ai_advisory.py tests/test_saxs_2d_ai_context_bridge.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_ai_confirmation_gui_route.py tests/test_saxs_results_table_service.py tests/test_main_window_persistence.py tests/test_sample_db.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-orientation-ai-advisory.md --changed --types
git diff --check
```

## Completion Evidence

- Core context, strict response parsing, deterministic hydration, fallback,
  prompt isolation, rescue rejection, and read-only worker tests are covered by
  `tests/test_saxs_orientation_ai_advisory.py` and the related SAXS AI safety
  matrix.
- SAXS parameters now transport a deep-copied detached advisory report, and
  `SampleDB.update_analysis_parameters()` updates only an existing run's JSON
  parameters column without changing confirmation or publication state.
- Results exposes a review-only action for `saxs.strain`; it is hidden without
  eligible q-band evidence and has no apply, rerun, engine, config, or source
  path authority.
- Advisory regression matrix: `26 passed` in 0.93s; q-resolved/feature-tracking
  bridge matrix: `24 passed, 2 skipped`; GUI/DB/batch/result-table matrix:
  `97 passed`.
- Full SAXS matrix after the transport hardening: `862 passed, 2 skipped,
  6 warnings` in 496.29s. Warnings are the existing missing-font and EDF
  geometry-default warnings.
- Structured verifier passed: quality gate `297 passed`, preprocess gate
  `106 passed`, Ruff, compile, and whitespace checks all passed. The known
  parallel GUI translation expectation remains outside this task:
  `tests/test_main_window_persistence.py::test_workflow_task_card_shows_controlled_optimization_state`.

## Scientific Limits

The advisory is read-only and cannot establish physical orientation validity,
repair detector calibration, infer tensile axis, or authorize publication. Real
detector correction remains disabled until reviewed formulas, compatible EDF
calibration inputs, ownership policy, and real-data replay are available.

## Pre-existing workspace changes

Inspect and preserve current parallel AI/GUI changes in overlapping files. Do
not mix them into this task checkpoint or modify real data and artifacts.
