# PolyNexus Full Software Release Audit

Date: 2026-07-27
Branch: `codex/origin-editor-usable-controls`
Status: automated evidence complete; release not approved

## Evidence ledger

| Boundary | Current evidence | Classification |
| --- | --- | --- |
| WAXS publication cutover and provider/workbench contracts | `30 passed` from the dedicated publication matrix with isolated basetemp | automated-pass |
| Cross-technique AI-off/failure/fallback | `25 passed` across DSC, IR, WAXS, SAXS, and NMR; Joint is explicitly report-level | automated-pass |
| DSC real published-run walkthrough | `3 passed` (`standard`, `isothermal`, `nonisothermal`), 11 existing warnings | automated-pass with warnings |
| WAXS real published-run walkthrough | `3 passed` (`static`, `temperature`, `strain/2D`) | automated-pass |
| SAXS real published-run walkthrough | `3 passed` (`static`, `temperature`, `strain`) | automated-pass; diagnostic roles preserved by test |
| IR real published-run walkthrough | `2 passed` (`standard`, `temperature-2D`) | automated-pass; mapping lifecycle separately covered |
| NMR real published-run walkthrough | `4 passed` (`liquid H/C`, `solid H/C`) | automated-pass; assignment-limited solid C remains provisional |
| Joint publish/editor/export/history lifecycle | `1 passed` with synthetic cross-technique rows | automated-pass for lifecycle; scientific conflict review open |
| Per-technique lifecycle closures | DSC `3`, WAXS `3`, IR `3` (including mapping), NMR `4`, Joint `1` passed | automated-pass |
| Canonical GUI default shell | Restarted canonical window screenshot shows SAXS empty state, workspace summary, mode navigation, and Data/Config/Results/Plots shell | human-review |
| Combined lifecycle/real-fixture attempt | 180-second tool window expired without a summary; replaced for evidence purposes by the successful per-technique shards below | historical bounded-timeout |
| Full repository verifier | Fresh dedicated run: `2767 passed, 10 warnings` in `24:13`; compile, quality, whitespace, and boundary audit passed | automated-pass with known warnings |

## Automated commands and results

### WAXS publication recheck

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_waxs_pub_matrix'
python -m pytest -q tests/test_waxs_publication_cutover.py tests/test_waxs_publication_temperature_provider.py tests/test_waxs_publication_strain_provider.py tests/test_waxs_publication_static_provider.py tests/test_waxs_workbench_figure_contracts.py tests/test_waxs_figure_provider.py tests/test_waxs_figure_document.py
```

Result: `30 passed in 3.49s`.

### AI safety matrix

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_release_ai2'
python -m pytest -q tests/test_preprocess_cross_technique_matrix.py tests/test_preprocess_ai_off_compat.py tests/test_preprocess_fault_injection.py -vv
```

Result: `25 passed in 0.68s`. This proves the contract boundary only; it does
not prove real model quality, candidate calibration, or human scientific
approval.

### Real published-run walkthrough shards

The 15 single-technique cases in `tests/test_real_published_run_walkthrough.py`
were run one technique at a time with dedicated basetemps:

- DSC: `3 passed, 11 warnings in 25.00s`.
- WAXS: `3 passed in 82.93s` (includes strain/2D).
- SAXS: `3 passed in 54.68s`.
- IR: `2 passed in 67.93s` (standard and temperature-2D).
- NMR: `4 passed in 97.25s` (liquid/solid H/C).

These runs verified the real engine -> manifest -> Gallery -> Editor revision
-> export bundle -> History restore route. They do not close human scientific
role review, and the solid-state NMR C assignment remains provisional.

The separate lifecycle closure shards also passed: DSC `3`, WAXS `3`, IR `3`
(standard/temperature-2D/mapping), NMR `4`, and Joint `1`.

### Combined lifecycle attempt

The combined command containing the real walkthrough, all five technique
lifecycle closures, IR mapping, NMR/Joint provenance, and WAXS publication
cutover exceeded the 180-second tool limit without a test summary. The running
pytest process was explicitly identified and terminated after the timeout.
This historical result is recorded as `bounded-timeout`, not as pass or failure;
the per-technique shards above are the authoritative replacement evidence.

### Full verifier and boundary audit

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_release_full'
python scripts/verify.py --changed --types --full --boundary
```

Result: `2767 passed, 10 warnings in 1453.05s (0:24:13)`. The selected
compile, quality, preprocessing, Ruff/type baseline, whitespace, and boundary
checks all passed. The warnings are the existing Matplotlib tight-layout,
DSC polynomial-conditioning, and Arial glyph warnings listed in stdout.

## GUI evidence

The canonical GUI was inspected from `D:\PolyNexus`. The temporary screenshot
is:

`C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-gui-default.png`

Observed: the main window opens on the SAXS empty state, shows `No project`,
workspace/run status, SAXS static/temperature/strain navigation, and the
Data/Config/Results/Plots shell. This is visual evidence for a reviewer. A
complete restarted-GUI walkthrough of all modes, Gallery, Editor, Export, and
History is still open.

## Open release gates

- Complete restarted-GUI visual review for all requested routes.
- Review IR vendor-native mapping/ROI semantics.
- Review assignment-limited solid-state NMR and Joint scientific conflicts.
- Complete the human scientific publication decision and final AI-off/
  failure/fallback release approval.

No code change in this audit promotes a diagnostic-only result or changes a
scientific threshold.
