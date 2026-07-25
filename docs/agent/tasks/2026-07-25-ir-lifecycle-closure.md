---
task_id: 2026-07-25-ir-lifecycle-closure
kind: cross-module
status: completed
---

# IR figure lifecycle closure

## Goal

Prove the shared lifecycle for IR standard, temperature-2D, and mapping/ROI
modes using explicit completed-analysis DTOs.

## Non-goals

- Do not add a vendor-native mapping reader or infer coordinate semantics.
- Do not choose band meaning or recalculate IR science in GUI code.
- Do not change provider IDs, publication roles, or legacy fallback policy.
- Do not claim restarted-GUI visual review or scientific release sign-off.

## Affected boundaries

- `polynexus/core/ir_engine/figure_provider.py`
- `polynexus/core/ir_engine/ir_mapping.py`
- `polynexus/core/figures/project_service.py`
- `polynexus/gui/plot_gallery_service.py`
- `polynexus/gui/main_window_history_mixin.py`
- `polynexus/gui/export_context_service.py`
- `tests/test_ir_lifecycle_closure.py`

## Acceptance criteria

- [x] Standard, temperature-2D, and mapping/ROI each run through one lifecycle regression.
- [x] Mapping provenance and invalid-pixel diagnostics remain explicit.
- [x] Active Gallery preserves run root, IDs, roles, and editor context.
- [x] Export includes manifest-backed figure runs and active pointer.
- [x] History restore repopulates the active IR Gallery for all three modes.
- [x] Focused matrix and task-scoped verifier pass.
- [x] An allowlisted checkpoint commit is created.

## Implementation plan

1. Add and run the parameterized lifecycle regression before production edits.
2. Implement only a shared connection proven missing by that regression.
3. Verify, update acceptance/memory, and create one checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_ir_lifecycle_focus'
python -m pytest tests/test_ir_lifecycle_closure.py tests/test_ir_complete_figure_provider.py tests/test_ir_figure_provider.py tests/test_ir_temperature.py tests/test_ir_mapping.py tests/test_ir_nmr_joint_workbench_profiles.py tests/test_figure_project_service.py tests/test_export_context_service.py tests/test_main_window_history_mixin.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-ir-lifecycle-closure.md --changed --types
```
