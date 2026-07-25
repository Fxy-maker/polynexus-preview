---
task_id: 2026-07-25-nmr-lifecycle-closure
kind: scientific
status: completed
---

# NMR real-data lifecycle closure

## Goal

Run liquid/solid 1H/13C NMR fixtures through input, preprocessing, analysis,
evidence, Workbench/provider, Gallery/Editor, export, and History restore.

## Non-goals

- Do not modify real fixtures or existing generated outputs.
- Do not change peak fitting, assignment gates, or solid-state Xc semantics.
- Do not promote assignment-limited evidence to a strong conclusion.
- Do not claim restarted-GUI visual review or scientific release sign-off.

## Affected boundaries

- `polynexus/core/nmr.py`
- `polynexus/core/nmr_engine/figure_provider.py`
- `polynexus/core/figures/project_service.py`
- `polynexus/gui/plot_gallery_service.py`
- `polynexus/gui/main_window_history_mixin.py`
- `polynexus/gui/export_context_service.py`
- `tests/test_nmr_lifecycle_closure.py`

## Acceptance criteria

- [x] All four NMR partitions run from repository fixtures through the shared lifecycle.
- [x] Each run carries evidence and active Manifest/Gallery run context.
- [x] Main editor working and published revisions are persisted.
- [x] Export contains manifest-backed figure runs and active pointer.
- [x] History restore repopulates the matching Gallery and submodule.
- [x] Assignment-limited solid 13C remains provisional.
- [x] Focused matrix and task-scoped verifier pass.
- [x] An allowlisted checkpoint commit is created.

## Implementation plan

1. Add and run the real four-partition lifecycle regression before production edits.
2. Implement only a shared connection proven missing by the regression.
3. Verify, update acceptance/memory, and create one checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_nmr_lifecycle_focus'
python -m pytest tests/test_nmr_lifecycle_closure.py tests/test_nmr_engine.py tests/test_nmr_figure_provider.py tests/test_nmr_joint_provenance_matrix.py tests/eval/test_runner_real_nmr.py tests/test_figure_project_service.py tests/test_export_context_service.py tests/test_main_window_history_mixin.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-25-nmr-lifecycle-closure.md --changed --types
```
