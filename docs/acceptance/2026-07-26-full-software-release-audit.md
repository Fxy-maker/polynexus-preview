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

python scripts/verify.py --changed --types --full --boundary
all-tests: 2647 passed, 10 warnings in 1389.67s (0:23:09)
boundary audit: passed; verify exit code 0
```

The single-process suite is dominated by real NMR and Qt lifecycle tests; the
fresh run above completed with a 35-minute allowance. The warnings are existing
Qt tight-layout, DSC polyfit-conditioning, and CJK glyph warnings; no warning
was a test failure.

## Real-fixture follow-up

The real-fixture audit is recorded in
`docs/acceptance/2026-07-26-real-published-run-audit.md`. DSC standard, WAXS
static/temperature, IR standard, and SAXS temperature produced fresh output
under `C:\Temp\PolyNexus_release_walkthrough_20260726`. The SAXS temperature
run preserves a scientific validation failure (`Q*` contamination and
diagnostic-only lamellar rows) while still exposing ready Figure Manifest
siblings; it is not a scientific release pass. WAXS strain and IR
temperature-2D exceeded the bounded 244-second diagnostic run and remain open.

The same run exposed and fixed a shared figure-audit defect: Matplotlib
colorbar axes were incorrectly checked as data axes. The focused correction is
tracked by `docs/agent/tasks/2026-07-26-colorbar-audit-regression.md`.

The real walkthrough matrix now covers fifteen cases (SAXS
static/temperature/strain, DSC standard/isothermal/non-isothermal, WAXS
static/temperature/strain/2D, IR standard/temperature-2D, and NMR liquid/solid
H/C) through active Gallery selection, Editor working/published revisions, export provenance, and
History restore. Evidence and limitations are recorded in
`docs/acceptance/2026-07-26-real-published-run-audit.md`.

## Open release gates

- Real published-run inspection for every mode: active Gallery selection,
  Editor revision, export bundle, and History restore.
- Restarted canonical GUI visual walkthrough and publication-role review.
- Human scientific confirmation of IR mapping/ROI vendor semantics and
  assignment-limited NMR/Joint conclusions.
- Final release decision after the visual and scientific gates above.
