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
| GUI shell/workbench/gallery/editor route contracts | `58 passed` across MainWindow shell, Results Workbench profiles, Gallery management, figure window, and figure mixin tests | automated-pass; pixel-level visual review open |
| Real-result GUI route capture | Temporary pytest capture `1 passed`; restored DSC run produced Results, Gallery, History, and Editor screenshots with one manifest gallery entry | structural-pass; offscreen CJK font boxes require live visual review |
| IR mapping/ROI contract and lifecycle | `11 passed`; geometry mismatch and invalid pixels are rejected, provenance/roles/handoff are preserved | automated structural-pass; vendor semantics intentionally not inferred |
| NMR/Joint provenance and lifecycle | `4 passed`; NMR Main/diagnostic and Joint run provenance survive publication/history | automated provenance-pass; solid C assignment and Joint conflicts require scientific review |
| Canonical GUI default shell | Restarted canonical window screenshot shows SAXS empty state, workspace summary, mode navigation, and Data/Config/Results/Plots shell | human-review |
| Combined lifecycle/real-fixture attempt | 180-second tool window expired without a summary; replaced for evidence purposes by the successful per-technique shards below | historical bounded-timeout |
| Full repository verifier | Current-head retry at `2af4baf`: `2790 passed, 10 warnings` in `24:14`; compile, quality, whitespace, and boundary audit passed | automated-pass with known warnings |

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

Result at current HEAD `2af4baf`: `2790 passed, 10 warnings in 1454.97s
(0:24:14)`. The selected compile, quality (`283`), preprocessing (`106`),
Ruff/type baseline, whitespace, and boundary checks all passed. The warnings
are the existing Matplotlib tight-layout,
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

The canonical launcher was freshly revalidated after the GUI acceptance
checkpoint: `scripts/launch_gui.py --diagnose` resolved `D:\PolyNexus`, branch
`codex/origin-editor-usable-controls`, commit `83083bc`, and the local
`polynexus` package. The responsive-shell checkpoint covers content-width
clipping at default and maximized sizes; it does not replace the all-route live
visual review.

The temporary real-result capture also saved:

- `C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-real-results.png`
- `C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-real-gallery.png`
- `C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-real-history.png`
- `C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-real-editor.png`

The route structure and Editor canvas render, but the offscreen capture renders
Chinese glyphs as square placeholders. These screenshots are therefore
structural diagnostics only; they do not close live-font, spacing, or
publication-role visual approval.

Additional route evidence collected on 2026-07-27:

- A canonical live-window `PrintWindow` capture was taken from the existing
  `PolyNexus v2.0` process. The maximized capture
  `C:\Temp\polynexus-live-window-max.png` shows the restarted shell with the
  sidebar, Data/Config/Results/Plots/History tabs, and a fitting Data surface.
  The normal-size capture `C:\Temp\polynexus-live-window.png` still shows a
  narrow-width right-edge area that needs human visual review; maximizing the
  window is not a substitute for that review.
- An offscreen route capture, after preloading the scientific stack in the
  same order as `tests/conftest.py`, produced five tab captures
  (`C:\Temp\polynexus-route-0.png` through `polynexus-route-4.png`) and an
  Editor capture (`C:\Temp\polynexus-route-editor.png`). The run restored one
  real DSC figure and the active Gallery contained one manifest entry. These
  captures confirm route construction and rendering only; offscreen CJK glyphs
  render as square placeholders, so live-font and pixel-level approval remain
  open.
- The first documentation-verifier attempt inherited the protected
  `D:\PolyNexus\.pytest_tmp` basetemp and produced 54 pytest setup errors with
  `WinError 5` while removing that pre-existing directory. Rerunning with
  external basetemp `C:\Temp\PolyNexus_release_gui_route_verify_20260727`
  passed task/memory checks, Ruff, compile/type baseline, quality `283`,
  preprocessing `106`, and whitespace. This environment issue is recorded as
  a verifier limitation, not a product test failure.

## Open release gates

- Complete restarted-GUI visual review for all requested routes.
- Review IR vendor-native mapping/ROI semantics.
- Review assignment-limited solid-state NMR and Joint scientific conflicts.
- Complete the human scientific publication decision and final AI-off/
  failure/fallback release approval.

No code change in this audit promotes a diagnostic-only result or changes a
scientific threshold.
