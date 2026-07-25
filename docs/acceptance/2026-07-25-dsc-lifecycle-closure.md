# DSC figure lifecycle closure acceptance

## Delivered

The three DSC modes now have one shared lifecycle regression over the existing
contracts, without adding technique-specific GUI or scientific branches:

- `dsc.standard` uses the repository's standard DSC fixture and completed
  engine path.
- `dsc.isothermal` uses a qualified Avrami DTO.
- `dsc.nonisothermal` uses conversion curves and a qualified Kissinger DTO.

For each mode the regression publishes a manifest-backed run, verifies active
Gallery entries and publication roles, saves a working editor revision,
publishes complete assets, copies the run into an export bundle with figure-run
provenance, and restores a history record through `MainWindow` before checking
the active Gallery again.

## Verification evidence

```text
python -m pytest tests/test_dsc_lifecycle_closure.py -q
3 passed in 13.96s

python -m pytest <DSC/provider/Workbench/project/export/history matrix> -q
78 passed in 21.72s

python -m pytest tests/test_dsc_lifecycle_closure.py tests/test_main_window_persistence.py -k "history_restore or restore_history or active_manifest_gallery or populate_plots" -q
10 passed, 190 deselected in 16.11s

python scripts/verify.py --task docs/agent/tasks/2026-07-25-dsc-lifecycle-closure.md --changed --types
selected checks passed; quality gate 282 passed; preprocessing gate 103 passed
```

The verifier required an external pytest basetemp because a first invocation
hit a Windows permission error while cleaning the pre-existing repository-root
`.pytest_tmp`; the rerun with `C:\Temp\PolyNexus_dsc_verifier` passed.

## Remaining acceptance boundary

This closes the DSC automated lifecycle evidence boundary only. Restarted-GUI
visual review, real instrument-data scientific sign-off, and the shared
AI-off/failure/fallback release matrix remain open. A broader mixed command
including the entire `tests/test_main_window_persistence.py` file also exposed
18 unrelated pre-existing GUI baseline failures (`254 passed`); those failures
were outside the DSC lifecycle files and were not changed here.
