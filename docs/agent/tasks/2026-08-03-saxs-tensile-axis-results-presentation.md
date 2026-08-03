---
task_id: 2026-08-03-saxs-tensile-axis-results-presentation
kind: scientific
status: implemented_pending_parity_matrix
date: 2026-08-03
title: Capture the SAXS tensile axis and present orientation evidence
---

## Goal

Capture an explicit detector-plane tensile axis for strain runs and display
final, diagnostic, same-feature delta, q-band, stability, and reliability
evidence through existing config, table, figure, and workbench contracts.

## Scientific boundary

GUI code captures coordinates and consumes DTOs only. It cannot infer an axis,
select q features, apply thresholds, replace missing final values, or promote
evidence.

## Non-goals

- No automatic tensile-axis inference from scattering.
- No calibration correction, q-feature matching, AI authority, or publication
  promotion.
- No fallback from missing final Herman to principal-axis diagnostic Herman.

## Affected boundaries

- `polynexus/core/saxs.py`
- `polynexus/core/saxs_config_binding.py`
- `polynexus/core/saxs_engine/config.py`
- `polynexus/core/saxs_engine/saxs_2d_review_context.py`
- `polynexus/core/saxs_engine/figure_strain.py`
- `polynexus/gui/main_window_config_panel_mixin.py`
- `polynexus/gui/main_window_ai_tuning_mixin.py`
- `polynexus/gui/main_window_retranslate_mixin.py`
- `polynexus/gui/main_window_run_mixin.py`
- `polynexus/gui/widgets/saxs_tensile_axis_editor.py`
- `polynexus/gui/result_table_templates.py`
- `polynexus/gui/result_table_models.py`
- `polynexus/gui/results_table_service.py`
- `polynexus/gui/saxs_results_table_service.py`
- `polynexus/gui/i18n.py`
- `tests/test_saxs_config_binding.py`
- `tests/test_saxs_tensile_axis_editor.py`
- `tests/test_saxs_results_table_service.py`
- `tests/test_results_table_service.py`
- `tests/test_result_table_templates.py`
- `tests/test_saxs_strain_method_evidence.py`
- `tests/test_main_window_persistence.py`
- This task card.

## Implementation plan

1. Add failing coordinate, binding, and no-fallback tests.
2. Add strain-only axis config and detector-coordinate editor.
3. Bind and transport axis value plus convention provenance.
4. Present final/diagnostic/delta/q-band fields and evidence figures.
5. Run focused, SAXS, restarted-GUI, and structured verification.

## Acceptance criteria

- [x] Axis set/clear and screen-to-detector round-trip are deterministic.
- [ ] NumPy/pyFAI azimuth parity is proved before drag input is enabled; drag
  remains disabled until this gate has evidence.
- [x] Missing axis remains None and never becomes zero or an inferred axis.
- [x] Final and diagnostic values use distinct labels and no fallback.
- [x] Delta, q range, stability, and reliability are readable.
- [x] GUI contains no SAXS scientific branching.
- [x] Presets/retranslation preserve the axis; recent calibration excludes it.

## Verification

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_config_binding.py tests/test_saxs_tensile_axis_editor.py tests/test_saxs_results_table_service.py tests/test_result_table_templates.py tests/test_results_table_service.py tests/test_saxs_strain_method_evidence.py tests/test_main_window_persistence.py tests/test_saxs_figure_evidence_binding.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-tensile-axis-results-presentation.md --changed --types
git diff --check
```

## Pre-existing workspace changes

Review current GUI/AI staged changes before editing overlapping files. Preserve
them and keep the implementation checkpoint to this task's explicit allowlist.

## Current Evidence

- Core/config/binding/editor/table slice: `96 passed` in the agent's focused
  GREEN run.
- Additional binding/editor regression: `8 passed`; orientation table tests:
  `3 passed`; table template tests: `10 passed`; axis persistence/retranslation:
  `2 passed`.
- The prescribed seven-file GUI focused command exceeded 124 seconds without a
  pytest summary; it is not claimed as passed. Full SAXS matrix remains pending.
- No pyFAI parity evidence is available in this checkout, so the editor accepts
  direct normalized values but keeps drag input disabled with
  `preview_transform_unverified`.
