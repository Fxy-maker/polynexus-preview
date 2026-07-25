---
 task_id: 2026-07-25-dsc-lifecycle-closure
 kind: cross-module
 status: completed
---

# DSC figure lifecycle closure

## Goal

 Prove the complete shared figure lifecycle for DSC standard, isothermal, and
 non-isothermal modes: provider, active Manifest/Gallery, editor working save
 and publish, export provenance, and history restore.

## Non-goals

 - Do not change DSC scientific calculations or evidence thresholds.
 - Do not change provider figure IDs, publication roles, or diagnostic gates.
 - Do not replace manifest-only Gallery discovery with recursive discovery.
 - Do not claim restarted-GUI visual review or scientific release sign-off.

## Affected boundaries

 - `polynexus/core/dsc_engine/figure_provider.py`
 - `polynexus/core/figures/production.py`
 - `polynexus/core/figures/project_service.py`
 - `polynexus/gui/plot_gallery_service.py`
 - `polynexus/gui/main_window_history_mixin.py`
 - `polynexus/gui/export_context_service.py`
 - `tests/test_dsc_lifecycle_closure.py`
 - `docs/acceptance/2026-07-25-dsc-lifecycle-closure.md`

## Acceptance criteria

 - [x] All three DSC modes have one lifecycle regression using their real
   provider definitions and completed-analysis DTO shape.
 - [x] Active Gallery entries preserve run root, figure ID, publication role,
   and editor context.
 - [x] A working revision and complete publication can be saved without
   mutating the original published assets unexpectedly.
 - [x] Export metadata includes manifest-backed figure runs and active pointer.
 - [x] History restore repopulates the DSC active Gallery for each mode.
 - [x] Focused matrix and task-scoped verifier pass.
 - [x] An allowlisted checkpoint commit is created.

## Current evidence and known gap

 Existing DSC provider/Workbench checks pass, but they do not combine all
 lifecycle boundaries in one regression. The prior DSC checkpoint explicitly
 leaves history restore, export provenance, AI-off/failure/fallback, restarted
 GUI visual review, and scientific sign-off open.

## Verification

 ```powershell
 $env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_dsc_lifecycle_focus'
 python -m pytest tests/test_dsc_lifecycle_closure.py tests/test_dsc_engine.py tests/test_dsc_figure_provider.py tests/test_dsc_publication_standard_provider.py tests/test_dsc_publication_isothermal_provider.py tests/test_dsc_publication_nonisothermal_provider.py tests/test_dsc_publication_cutover.py tests/test_dsc_workbench_figure_contracts.py tests/test_results_workbench_profiles.py tests/test_results_export_contracts.py tests/test_figure_project_service.py tests/test_chart_editor_save_mixin.py tests/test_export_context_service.py tests/test_main_window_persistence.py -q
 python scripts/verify.py --task docs/agent/tasks/2026-07-25-dsc-lifecycle-closure.md --changed --types
 ```

## Implementation plan

1. Add and run the parameterized lifecycle regression before any production change.
2. Reuse existing manifest, gallery, project, export, and history contracts; implement only a failing-case product connection if the regression identifies one.
3. Run the focused matrix and structured verifier, then record acceptance evidence and create an allowlisted checkpoint.

Detailed plan: `docs/superpowers/plans/2026-07-25-dsc-lifecycle-closure.md`.
