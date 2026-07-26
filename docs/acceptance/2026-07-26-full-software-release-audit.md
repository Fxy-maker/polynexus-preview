# PolyNexus full-software release audit — 2026-07-26

## Current result

The automated shared platform and technique slices are closed through the
repository's release verifier: Results Workbench profiles,
FigureDefinition/Manifest/Gallery/Editor/export contracts, History restore,
SAXS/DSC/WAXS/IR/NMR/Joint lifecycle regressions, AI-off/failure/fallback
safety matrices, and MainWindow persistence are covered by focused and full
evidence. This is not yet a release approval because visual and human
scientific gates remain open.

## Fresh evidence

```text
python scripts/verify.py --changed --types
selected checks passed; quality gate 282 passed; preprocessing gate 103 passed

python -m pytest --basetemp=C:\Temp\PolyNexus_main_window_persistence_lint_final2 tests/test_main_window_persistence.py -q
197 passed in 185.80s (0:03:05)

python -m pytest --basetemp=C:\Temp\PolyNexus_qt_editor_after_conftest tests/test_chart_editor.py tests/test_dsc_lifecycle_closure.py -q
251 passed in 53.48s

python -m pytest --basetemp=C:\Temp\PolyNexus_joint_lifecycle_checkpoint tests/test_joint_lifecycle_closure.py -q
1 passed in 4.92s

python -m pytest --basetemp=C:\Temp\PolyNexus_nmr_plot_cutover tests/test_engine_figure_production_cutover.py -q
5 passed in 1.77s

python scripts/verify.py --task docs/agent/tasks/2026-07-26-full-suite-runtime-investigation.md --changed --types
quality gate: 282 passed; preprocessing gate: 103 passed

python scripts/verify.py --task docs/agent/tasks/2026-07-26-full-suite-runtime-investigation.md --changed --types --full --boundary
all-tests: 2587 passed, 8 warnings in 1042.86s (0:17:22)
boundary audit: passed; verify exit code 0
```

The earlier 15-minute run was incomplete because the single-process suite
needs about 17 minutes, dominated by real NMR lifecycle tests; the complete
run above passed with a 30-minute allowance.

## Open release gates

- Real published-run inspection for every mode: active Gallery selection,
  Editor revision, export bundle, and History restore.
- Restarted canonical GUI visual walkthrough and publication-role review.
- Human scientific confirmation of IR mapping/ROI vendor semantics and
  assignment-limited NMR/Joint conclusions.
- Final release decision after the visual and scientific gates above.
