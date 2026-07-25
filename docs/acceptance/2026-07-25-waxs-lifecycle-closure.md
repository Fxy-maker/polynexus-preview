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

## Remaining acceptance boundary

Restarted-GUI visual inspection of the 2D image-grid, real instrument-data
scientific sign-off, and the shared AI-off/failure/fallback release matrix
remain open. The existing 1D strain fallback policy remains covered by the
provider matrix and was not changed here.
