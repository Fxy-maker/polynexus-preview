---
task_id: 2026-07-26-qt-lifecycle-stability
kind: gui-reliability
status: completed
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
- [x] Full repository verification completes with no unrelated failures. The
  current HEAD full/boundary verifier passes `2671` tests with the known
  ten Qt/layout/scientific-font warnings and a passing boundary audit.
- [x] Allowlisted checkpoint commit is created (`fbf22b6`).

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

Focused Qt and persistence matrices remain green. The repository-wide
automation gate is closed for this slice; restarted-GUI visual review and
human scientific/publication review remain separate full-software release
gates.

## Checkpoint evidence

- Focused lifecycle/editor matrix: `274 passed` on the current HEAD.
- Structured verifier: quality gate `282 passed`; preprocessing gate `106
  passed`.
- Current-HEAD full/boundary verifier: `2671 passed, 10 warnings` in
  `1644.65s`; boundary audit passed.
