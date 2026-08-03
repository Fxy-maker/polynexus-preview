---
task_id: 2026-08-03-saxs-orientation-ai-advisory
kind: scientific
status: planned
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

- [ ] Only existing source candidate IDs can be ranked.
- [ ] Numeric values are copied from deterministic evidence, not model output.
- [ ] Model output accepts no free-form numeric or scientific explanation text.
- [ ] Raw arrays, paths, and unknown fields are excluded.
- [ ] Missing/diagnostic evidence yields limitations-first output.
- [ ] No apply, candidate creation, rerun, or publication path exists.

## Verification

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_orientation_ai_advisory.py tests/test_saxs_2d_ai_context_bridge.py tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_confirmed_rerun_safety.py tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_orchestrator_handoff.py tests/test_saxs_ai_confirmation_gui_route.py tests/test_saxs_results_table_service.py tests/test_main_window_persistence.py tests/test_sample_db.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-orientation-ai-advisory.md --changed --types
git diff --check
```

## Pre-existing workspace changes

Inspect and preserve current parallel AI/GUI changes in overlapping files. Do
not mix them into this task checkpoint or modify real data and artifacts.
