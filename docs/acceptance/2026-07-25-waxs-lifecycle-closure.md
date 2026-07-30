# WAXS figure lifecycle closure acceptance

## Delivered

The static, temperature, and strain WAXS modes now share one automated
lifecycle regression over the existing services. Static and temperature use
`FigureProjectService` for working save and complete publication; strain keeps
its `image_grid` on `ReactiveFigureProjectService` and performs a real V2
worksheet edit before publish.

Each mode also verifies active Manifest/Gallery role and run context, export
bundle `metadata/runs` plus `metadata/active_run.json`, and MainWindow History
restore back to the same active Gallery.

## Verification evidence

```text
python -m pytest tests/test_waxs_lifecycle_closure.py -q
3 passed in 17.35s

python -m pytest <WAXS lifecycle/publication/provider/Workbench/document/V2/history matrix> -q
29 passed in 38.25s

python scripts/task_check.py --task docs/agent/tasks/2026-07-25-waxs-lifecycle-closure.md
valid task card
```

The structured verifier is the remaining checkpoint command for this atomic
task; it will use an external pytest basetemp to avoid repository-root scratch
directory locks.

## Current checkout recheck (2026-07-30)

The current checkout was re-run against the repository WAXS fixtures after the
earlier lifecycle checkpoint:

```text
python -m pytest tests/test_real_published_run_walkthrough.py -k waxs -q
3 passed, 12 deselected in 128.22s, exit code 0

python -m pytest tests/test_waxs_lifecycle_closure.py tests/eval/test_waxs_publication_real_data.py tests/test_waxs_figure_provider.py tests/test_waxs_workbench_figure_contracts.py tests/test_reactive_figure_project_service.py tests/test_figure_project_service.py tests/test_main_window_history_mixin.py -q
20 passed in 50.85s, exit code 0

QT_QPA_PLATFORM=windows python -m pytest tests/test_native_gui_real_route_capture.py -k waxs -q
3 passed, 14 deselected in 125.09s, exit code 0
```

The native capture set is isolated at
`D:\PolyNexus_native_waxs_capture_20260730`. It contains Results, Gallery,
History, and Editor captures for static, temperature, and strain. Visual
inspection confirmed that the strain Editor exposes editable curves, axes,
legend, and `Image Grid`; Gallery shows the Main and SI figure entries; and
the temperature Editor exposes the 2theta (degree) and intensity axes with
temperature series labels. The Results surface retains the explicit warning
that WAXS physical support is limited, so this is route and artifact evidence,
not scientific publication approval.

## Remaining acceptance boundary

Restarted-GUI visual inspection of the 2D image-grid, real instrument-data
scientific sign-off, and the shared AI-off/failure/fallback release matrix
remain open. The existing 1D strain fallback policy remains covered by the
provider matrix and was not changed here.
