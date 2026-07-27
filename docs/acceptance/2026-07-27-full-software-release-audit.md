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
| Native Windows Qt Joint route | `1 passed, 15 deselected in 5.94s`, exit code `0`; synthetic Joint report restored through Results, Gallery, History, Editor, and package Export | automated synthetic route-pass; real-data Joint and scientific conflict review remain open |
| Per-technique lifecycle closures | DSC `3`, WAXS `3`, IR `3` (including mapping), NMR `4`, Joint `1` passed | automated-pass |
| GUI shell/workbench/gallery/editor route contracts | `58 passed` across MainWindow shell, Results Workbench profiles, Gallery management, figure window, and figure mixin tests | automated-pass; pixel-level visual review open |
| Real-result GUI route capture | Temporary pytest capture `1 passed`; restored DSC run produced Results, Gallery, History, and Editor screenshots with one manifest gallery entry | structural-pass; offscreen CJK font boxes require live visual review |
| Native Windows Qt real-route harness | Fresh post-fix shards: `DSC 3`, `SAXS 3`, `WAXS 3`, `IR 2`, `NMR 4` passed, all exit code `0`; each case restored actual `AnalysisResult` parameters/payload, asserted a non-empty Results table, and captured Results, Gallery, History, Editor, and package Export artifacts | automated route/package-export pass; inactive-grab body contrast/activity and installed Origin/COM remain human/optional-runtime gates |
| Results Workbench Light-theme contrast | TDD regression plus theme-switch test `2 passed`; Light muted text now has `4.72:1` contrast against the light background, and the complete 15-mode native route matrix passed after the fix | automated contrast/route pass; restarted-GUI visual review remains open |
| IR mapping/ROI contract and lifecycle | `11 passed`; geometry mismatch and invalid pixels are rejected, provenance/roles/handoff are preserved | automated structural-pass; vendor semantics intentionally not inferred |
| NMR/Joint provenance and lifecycle | `4 passed`; NMR Main/diagnostic and Joint run provenance survive publication/history | automated provenance-pass; solid C assignment and Joint conflicts require scientific review |
| Canonical GUI default shell | Restarted canonical window screenshot shows SAXS empty state, workspace summary, mode navigation, and Data/Config/Results/Plots shell | human-review |
| Combined lifecycle/real-fixture attempt | 180-second tool window expired without a summary; replaced for evidence purposes by the successful per-technique shards below | historical bounded-timeout |
| Full repository verifier | Fresh current-working-tree run: `2793 passed, 10 warnings` in `1607.00s`; compile, quality, whitespace, and boundary audit passed | automated-pass with known warnings |

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
- IR: fresh rerun `2 passed, 13 deselected in 71.34s`, exit code `0`
  (standard and temperature-2D); `temperature_2d/neg_fraction = WARN` remains
  in the real output.
- NMR: fresh rerun `4 passed, 11 deselected in 112.23s`, exit code `0`
  (liquid/solid H/C); liquid C, solid H, and solid C validation warnings remain
  in the real output, including `Xc_NMR_assignment = WARN` for solid C.

These runs verified the real engine -> manifest -> Gallery -> Editor revision
-> export bundle -> History restore route. They do not close human scientific
role review, and the solid-state NMR C assignment remains provisional.

The fresh IR and NMR commands were run independently after the native harness
Results check was added: IR `2 passed, 13 deselected in 70.19s`, exit code `0`;
NMR `4 passed, 11 deselected in 105.59s`, exit code `0`. The native harness
previously restored only `data_file` with empty parameters, which made the
Results table empty despite a valid Gallery. It now restores the existing
`AnalysisResult.parameters` and `AnalysisResult.to_dict()` payload and asserts
that the shared Results model and table contain rows. This is a test-harness
acceptance correction; no production GUI or scientific behavior changed.

The separate lifecycle closure shards also passed: DSC `3`, WAXS `3`, IR `3`
(standard/temperature-2D/mapping), NMR `4`, and Joint `1`.

The native Windows Qt route harness was then run in bounded technique shards
with `QT_QPA_PLATFORM=windows`, external basetemps, and exit codes printed by
the PowerShell wrapper:

- DSC: `3 passed, 12 deselected, 15 warnings in 25.44s`, exit code `0`.
- SAXS: `3 passed, 12 deselected in 49.93s`, exit code `0`; the temperature
  route retained its expected validation error state while the shared GUI route
  itself passed.
- WAXS: `3 passed, 12 deselected in 86.35s`, exit code `0` (static,
  temperature, strain).
- IR: `2 passed, 13 deselected in 66.72s`, exit code `0`; the temperature-2D
  route retained `neg_fraction = WARN`.
- NMR: `4 passed, 11 deselected in 114.85s`, exit code `0`; solid C retained
  `NMR_fit_R2 = WARN` and `Xc_NMR_assignment = WARN`.

The same five native shards were rerun with the Editor Export action enabled
and the external-runtime-free `PackageExporter` selected explicitly:

- DSC: `3 passed, 12 deselected, 15 warnings in 24.25s`, exit code `0`.
- SAXS: `3 passed, 12 deselected in 49.85s`, exit code `0`.
- WAXS: `3 passed, 12 deselected in 87.35s`, exit code `0`.
- IR: `2 passed, 13 deselected in 67.19s`, exit code `0`.
- NMR: `4 passed, 11 deselected in 117.75s`, exit code `0`.

Every mode triggered the real Chart Editor Export `QAction` and produced an
`Origin_Export` package containing `figure_document.json`, `metadata.json`,
and `import.ogs`. The test deliberately injects only the existing
`PackageExporter` adapter so it cannot launch an installed Origin process or
COM server. Installed OriginPro/COM behavior remains an optional-runtime
manual gate, while the no-Origin fallback is now automated across all modes.

After correcting the history fixture to carry the actual engine result, the
native Results assertion was rerun in fresh technique shards: DSC `3 passed,
13 deselected in 23.13s`, SAXS `3 passed, 13 deselected in 48.91s`, WAXS `3
passed, 13 deselected in 85.25s`, IR `2 passed, 14 deselected in 65.91s`, and
NMR `4 passed, 12 deselected in 111.49s`; every command exited `0`. A
representative native Results capture now corresponds to a non-empty table,
but its inactive `grab()` body text remains visually pale and therefore stays
an explicit human contrast/activity gate.

The native visual review then exposed a real Light-theme issue: Results labels
were retaining old dark-only inline colors while the active background was
light. `MainWindowResultsMixin` now reapplies the active `ThemeTokens` on
construction and live theme switches, and Light `text_muted` is `#667085`
(`4.72:1` against `#f7f9fc`). The focused Results/theme matrix passed `24`
tests; the complete non-Joint native route matrix passed `15` tests after the
change. This closes the code-level contrast defect, but does not substitute
for a reviewer inspecting an activated/restarted GUI window.

The separate native Joint probe passed `1 passed, 15 deselected in 5.94s`,
exit code `0`. It uses the existing synthetic `JointCoordinator` report-level
fixture, restores `joint.compare`, captures the shared Results/Gallery/History/
Editor surfaces, and creates the same package artifacts. It is software-route
evidence only; it does not establish real-data Joint behavior or resolve
cross-technique scientific conflicts.

The earlier combined native invocation exceeded the 180-second tool window
without a pytest summary and is therefore a tool-level timeout, not a pass or
failure. Its follow-up `-k nmr.solid_c` command did have a real summary:
`1 passed, 12 deselected in 16.66s`, exit code `0`. The earlier `-k
waxs.strain` command had `13 deselected, 0 selected`, exit code `5` because
the harness had not yet imported the full-2D case list; this was a harness
selection error, not a WAXS test failure. The harness now includes both
`waxs.strain` and `ir.temperature_2d`, and the fresh shards above are the
authoritative native results.

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

Fresh current-working-tree result: `2793 passed, 10 warnings in 1607.00s
(0:26:46)`. The selected compile, quality (`283`), preprocessing (`106`),
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
- A native Windows Qt route capture was run against the current worktree with
  `QT_QPA_PLATFORM=windows` and external basetemp
  `C:\Temp\PolyNexus_native_gui_route`:
  `tests/_tmp_phase3/test_visual_audit_capture.py` returned `1 passed in
  5.93s`. At the test's 1600x1000 window size, the real DSC Results, Gallery,
  History, and Editor captures were inspected. CJK labels rendered normally;
  the main shell, sidebar, tabs, Gallery entry, History table, and Editor
  inspector were constructible. This is native live-font evidence for one DSC
  route, not all-mode visual approval; export was exposed but not clicked.
- The reusable harness for extending this evidence is
  `tests/test_native_gui_real_route_capture.py`; it is explicitly skipped in
  offscreen CI and parameterizes all real walkthrough modes for native Qt
  capture.
- The completed native harness saved captures under
  `C:\Temp\PolyNexus_native_gui_dsc_verified`,
  `C:\Temp\PolyNexus_native_gui_saxs_verified`,
  `C:\Temp\PolyNexus_native_gui_waxs_verified`,
  `C:\Temp\PolyNexus_native_gui_ir_verified`, and
  `C:\Temp\PolyNexus_native_gui_nmr_verified`. Representative Results,
  Gallery, and Editor images show the native shell, tabs, plots, and CJK labels
  constructible; Results/Gallery body text is visually pale in these inactive
  `grab()` captures, so contrast/activity remains a human review item. The
  package Export action is automated across all modes; installed Origin/COM
  interaction is intentionally not launched by the acceptance harness.
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
