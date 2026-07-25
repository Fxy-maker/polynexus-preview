---
task_id: 2026-07-25-waxs-lifecycle-closure
kind: cross-module
status: completed
---

# WAXS figure lifecycle closure

## Goal

Prove the shared figure lifecycle for WAXS static, temperature, and strain
modes, including the strain 2D image-grid editor path.

## Non-goals

- Do not change WAXS scientific calculations or evidence gates.
- Do not change provider figure IDs, publication roles, or fallback policy.
- Do not replace manifest-only Gallery discovery.
- Do not claim restarted-GUI visual review or scientific release sign-off.

## Affected boundaries

- `polynexus/core/waxs_engine/figure_provider.py`
- `polynexus/core/figures/project_service.py`
- `polynexus/core/figures/reactive_project_service.py`
- `polynexus/gui/plot_gallery_service.py`
- `polynexus/gui/main_window_history_mixin.py`
- `polynexus/gui/export_context_service.py`
- `tests/test_waxs_lifecycle_closure.py`

## Acceptance criteria

- [x] Static, temperature, and strain each run through one lifecycle regression.
- [x] Strain 2D image-grid remains on the reactive editor route.
- [x] Active Gallery preserves run root, IDs, roles, and editor context.
- [x] Export includes manifest-backed figure runs and active pointer.
- [x] History restore repopulates the active WAXS Gallery for all three modes.
- [x] Focused matrix and task-scoped verifier pass.
- [x] An allowlisted checkpoint commit is created.

## Implementation plan

1. Add and run the parameterized lifecycle regression before production edits.
2. Implement only a connection proven missing by that regression.
3. Run focused verification, update acceptance/memory, and create one checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_waxs_lifecycle_focus'
python -m pytest tests/test_waxs_lifecycle_closure.py tests/eval/test_waxs_publication_real_data.py tests/test_waxs_figure_provider.py tests/test_waxs_workbench_figure_contracts.py tests/test_reactive_figure_project_service.py tests/test_figure_project_service.py tests/test_main_window_history_mixin.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-waxs-lifecycle-closure.md --changed --types
```
