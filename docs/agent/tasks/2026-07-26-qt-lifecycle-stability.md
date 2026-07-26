---
task_id: 2026-07-26-qt-lifecycle-stability
kind: gui-reliability
status: in_progress
---

# Qt lifecycle stability

## Goal

Keep deferred Qt preview callbacks, MainWindow AI tuning context, and
ChartEditor test teardown safe across the full software suite.

## Non-goals

- Do not weaken production dirty-document close protection.
- Do not alter scientific calculations, figure roles, or export contracts.
- Do not delete user data, generated outputs, or pre-existing scratch.

## Affected boundaries

- `polynexus/gui/widgets/chart_viewer.py`
- `polynexus/gui/main_window.py`
- `polynexus/gui/main_window_workspace_mixin.py`
- `tests/conftest.py`
- Focused GUI lifecycle tests.

## Acceptance criteria

- [x] Preview deletion no longer calls a bound method after its scene is gone.
- [x] AI tuning workspace context calls the summary method successfully.
- [x] Existing lightweight workspace fakes retain their label behavior.
- [x] ChartEditor plus DSC lifecycle runs without Qt heap corruption.
- [ ] Full repository verification completes with no unrelated failures. The
  changed/type verifier is currently blocked before the quality gate by the
  pre-existing monolithic `main_window.py` Ruff baseline (150 errors on
  `HEAD`, 151 when the scoped rename is present); this task does not reformat
  that unrelated file-wide import surface.
- [ ] Allowlisted checkpoint commit is created.

## Implementation plan

1. Reproduce the deleted-scene callback and the MainWindow name collision.
2. Apply the parent-owned timer and label-name fixes, plus test-window cleanup.
3. Run focused and repository verification; repair only evidence-backed failures.
4. Update acceptance/memory and checkpoint the explicit file allowlist.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_qt_lifecycle'
python -m pytest tests/test_chart_viewer_lifecycle.py tests/test_chart_viewer.py -q
python -m pytest tests/test_chart_editor.py tests/test_dsc_lifecycle_closure.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-26-qt-lifecycle-stability.md --changed --types
```

## Known limitations

The focused Qt and persistence matrices complete, but the repository verifier
cannot reach its quality gate until the pre-existing `main_window.py` Ruff
baseline is separately addressed. Full/boundary release evidence remains open.
