# PolyNexus Full Software Release Audit

Date: 2026-07-28
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
| Joint real-data transport lifecycle | `1 passed` (`tests/test_joint_real_data_lifecycle.py`); real DSC standard, SAXS static, and WAXS static engines persisted through SampleDB and published three Joint figures with source-run provenance | automated transport-pass; real-value interpretation, conflict review, and publication approval remain open |
| Native Windows Qt Joint route | `1 passed, 15 deselected in 5.94s`, exit code `0`; synthetic Joint report restored through Results, Gallery, History, Editor, and package Export | automated synthetic route-pass; real-data Joint and scientific conflict review remain open |
| Per-technique lifecycle closures | DSC `3`, WAXS `3`, IR `3` (including mapping), NMR `4`, Joint `1` passed | automated-pass |
| GUI shell/workbench/gallery/editor route contracts | `58 passed` across MainWindow shell, Results Workbench profiles, Gallery management, figure window, and figure mixin tests | automated-pass; pixel-level visual review open |
| Real-result GUI route capture | Temporary pytest capture `1 passed`; restored DSC run produced Results, Gallery, History, and Editor screenshots with one manifest gallery entry | structural-pass; offscreen CJK font boxes require live visual review |
| Native Windows Qt real-route harness | Fresh D:-isolated post-opacity-fix rerun: `15 passed, 1 deselected, 15 warnings in 398.02s`, exit code `0`; DSC `3`, SAXS `3`, WAXS `3`, IR `2`, NMR `4`. Each case restored actual `AnalysisResult` parameters/payload, asserted a non-empty Results table, captured Results/Gallery/History/Editor, and exercised package Export. Native synthetic Joint separately passed `1` in `8.92s`. | automated route/package-export pass; inactive-grab body contrast/activity, installed Origin/COM, and scientific gates remain human/optional-runtime gates |
| Fresh native all-mode route harness | Current-checkout Windows-native rerun: `17 passed, 15 warnings in 312.55s`, exit code `0`; 68 captures cover DSC `3`, SAXS `3`, WAXS `3`, IR `2`, NMR `4`, synthetic Joint `1`, and synthetic IR mapping `1` | automated route/capture/export pass; human visual review, IR vendor semantics, NMR solid-C label policy, Joint conflict interpretation, and release approval remain open |
| Fresh native all-mode post-Joint-identity rerun | Current-checkout Windows-native rerun: `17 passed, 15 warnings in 358.71s`, exit code `0`; 68 captures under `D:\PolyNexus_native_all_routes_capture_20260729_post_joint`; Joint project badge shows `PA6-A` while the synthetic route retains `No data loaded` context | automated route/capture/export pass; human visual review, IR vendor semantics, NMR solid-C label policy, Joint conflict interpretation, and release approval remain open |
| Results Workbench Light-theme contrast | TDD regression plus theme-switch test `2 passed`; Light muted text now has `4.72:1` contrast against the light background, and the complete 15-mode native route matrix passed after the fix | automated contrast/route pass; restarted-GUI visual review remains open |
| IR mapping/ROI contract and lifecycle | `11 passed`; geometry mismatch and invalid pixels are rejected, provenance/roles/handoff are preserved | automated structural-pass; vendor semantics intentionally not inferred |
| NMR/Joint provenance and lifecycle | `4 passed`; NMR Main/diagnostic and Joint run provenance survive publication/history | automated provenance-pass; solid C assignment and Joint conflicts require scientific review |
| Canonical GUI default shell | Restarted canonical window screenshot shows SAXS empty state, workspace summary, mode navigation, and Data/Config/Results/Plots shell | human-review |
| Combined lifecycle/real-fixture attempt | 180-second tool window expired without a summary; replaced for evidence purposes by the successful per-technique shards below | historical bounded-timeout |
| Full repository verifier | Fresh current-working-tree run: `2793 passed, 10 warnings` in `1607.00s`; compile, quality, whitespace, and boundary audit passed | automated-pass with known warnings |

### Joint real-data transport acceptance

The new acceptance test uses the existing public contract: real DSC, SAXS, and
WAXS engines write isolated outputs, `SampleDB` persists the completed runs,
and `JointCoordinator` consumes those persisted runs rather than reading raw
files. The fresh test returned `1 passed, 1 warning in 14.86s`, exit code `0`.

The focused Joint/NMR matrix returned `23 passed, 2 warnings in 14.83s`, exit
code `0`. The task-scoped verifier returned exit code `0`: task-card and memory
checks passed, Ruff/compile passed for changed project Python files, quality
gate passed (`283 passed, 2 warnings`), preprocessing gate passed (`106
passed, 2 warnings`), no changed type-baseline targets were selected, and
`git diff --check` passed. This is transport and publication-provenance
evidence only; it does not establish scientific agreement among the real
values or final Joint publication approval.

### Fresh native all-mode route acceptance

The current checkout was exercised in a fresh Windows-native Qt process with
the existing route harness and D:-isolated diagnostics. The command returned
`17 passed, 15 warnings in 312.55s`, exit code `0`. The selected cases were DSC
`3`, SAXS `3`, WAXS `3`, IR `2`, NMR `4`, synthetic Joint `1`, and synthetic IR
mapping `1`. The capture directory
`D:\PolyNexus_native_all_routes_capture_20260729` contains 68 images: Results,
Gallery, History, and Editor for each case. Every case also exercised the
existing no-Origin `PackageExporter` fallback and created its package files.

Representative fresh images show a constructible native Results surface with
live labels, a five-figure SAXS Gallery, an editable NMR solid-C spectrum, an
editable IR mapping heatmap, and visible Joint diagnostic rows. The images also
retain the review signals: solid-C peak labels are crowded, the synthetic Joint
restore header says `No project` / `No data loaded`, IR mapping is synthetic,
and SAXS temperature retains diagnostic/validation evidence. This closes
automated native route evidence only; it does not close human visual or
scientific release gates.

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

The earlier command-level recheck of the two delegated shards also completed
with real pytest summaries: IR published-run walkthrough `2 passed, 13
deselected in 84.78s`, exit code `0`; NMR solid-C lifecycle `1 passed, 3
deselected in 126.89s`, exit code `0`. A later independent recheck captured
complete stdout/stderr and exit codes: IR walkthrough `2 passed, 13
deselected in 88.67s`, exit code `0`; NMR walkthrough `4 passed, 11
deselected in 132.02s`, exit code `0`; and the exact NMR solid-C lifecycle
command `1 passed, 3 deselected in 138.00s`, exit code `0`. These are fresh
automated rechecks and do not change the scientific/release boundaries above.

A fresh four-partition NMR published-run walkthrough then returned `4 passed,
11 deselected in 108.37s`, exit code `0` (`liquid_h`, `liquid_c`, `solid_h`,
`solid_c`).

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

The native harness also calls `raise_()` and `activateWindow()` before Results,
Gallery, History, and Editor captures. A fresh DSC probe with that activation
path passed `1 passed, 15 deselected in 6.90s`, exit code `0`, without the
deprecated `setActiveWindow` warning. Gallery body text remained visually pale
in the capture, so it remains a human visual-review item rather than evidence
for an additional production color change.

The separate native Joint probe passed `1 passed, 15 deselected in 5.94s`,
exit code `0`. It uses the existing synthetic `JointCoordinator` report-level
fixture, restores `joint.compare`, captures the shared Results/Gallery/History/
Editor surfaces, and creates the same package artifacts. It is software-route
evidence only; it does not establish real-data Joint behavior or resolve
cross-technique scientific conflicts.

After the shared Main Tab opacity correction, the complete native route harness
was rerun with `TEMP`, `TMP`, pytest basetemp, and capture output on D: to avoid
the exhausted C: temporary volume. The authoritative result was `15 passed, 1
deselected, 15 warnings in 398.02s`, exit code `0`; all five technique groups
passed and produced the four route captures plus the package-export artifacts.
The synthetic Joint route then passed `1 passed, 15 deselected in 8.92s`, exit
code `0`. Representative captures are retained under
`D:\PolyNexus_native_all_routes_capture_20260728` and were visually inspected
for live CJK labels, opaque Results text, constructible Gallery cards, and an
editable Editor surface. This is stronger native route evidence, not human
scientific/release approval.

The preceding C:-based attempt is recorded as an environment failure rather
than a test failure: it ended with `4 passed, 11 failed` after `database or disk
is full`/`No space left on device`. It was superseded by the D:-isolated run.

The earlier combined native invocation exceeded the 180-second tool window
without a pytest summary and is therefore a tool-level timeout, not a pass or
failure. Its follow-up `-k nmr.solid_c` command did have a real summary:
`1 passed, 12 deselected in 16.66s`, exit code `0`. The earlier `-k
waxs.strain` command had `13 deselected, 0 selected`, exit code `5` because
the harness had not yet imported the full-2D case list; this was a harness
selection error, not a WAXS test failure. The harness now includes both
`waxs.strain` and `ir.temperature_2d`, and the fresh shards above are the
authoritative native results.

A fresh current-checkout native Windows Qt run was then executed in a new
pytest process with all temporary state and captures isolated on D:. The
authoritative command was:

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_all_routes_capture_20260728_with_ir_mapping'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_native_all_routes_with_ir_mapping_basetemp_20260728'
python -m pytest -q tests/test_native_gui_real_route_capture.py
```

It returned `17 passed, 15 warnings in 363.16s`, exit code `0`. The 15
real-fixture cases cover DSC (3), SAXS (3), WAXS (3, including the full-2D
strain fixture), IR (2), and NMR (4); the other two cases are synthetic Joint
and synthetic IR mapping. Each case captured Results, Gallery, History, and
Editor and exercised the existing PackageExporter fallback, producing 68
captures under
`D:\PolyNexus_native_all_routes_capture_20260728_with_ir_mapping`. There is
still no vendor-native IR mapping fixture, so mapping coordinate/ROI semantics
remain open.

Visual inspection of the fresh captures confirmed live CJK rendering, opaque
Results text, constructible Gallery/History surfaces, and an editable Editor
surface. The synthetic IR mapping capture shows the explicit map heatmap and
ROI/editor route with its structural provenance; it does not validate an
instrument vendor reader. The NMR solid-C Editor still shows crowded peak
labels and requires scientific/visual judgment about label policy. The
synthetic Joint capture shows diagnostic rows while its synthetic restore
header says `No project` / `No data loaded`; this is recorded as a fixture/route
review signal, not silently changed in production. These observations do not
constitute final scientific or publication approval.

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

The latest D:-isolated current-working-tree result is green: the verifier
exited `0`, and its all-tests quality phase returned `2845 passed, 16 skipped,
12 warnings` in `1574.30s`. Compile, quality (`283`), preprocessing (`106`),
Ruff/type baseline, whitespace, and boundary audit all passed. The earlier
`2836 passed / 2 failed` condition-recovery result was not reproducible in the
current checkout; the focused condition-recovery rerun and this full run both
pass. It remains historical diagnostic evidence, not a current release
failure. The warnings are the existing tight-layout, DSC polynomial
conditioning, Arial glyph, and EDF geometry fallback warnings.

### Current-checkout full/boundary recheck (2026-07-29)

The verifier was rerun with an isolated D: basetemp after the current Results
Review and SAXS 2D checkpoints:

```text
2883 passed, 17 skipped, 12 warnings in 1405.74s (23:25), exit code 0
```

The quality gate passed `287`, preprocessing passed `106`, and compile, Ruff,
type baseline, whitespace, and boundary audit all passed. This confirms the
current automated contract only; restarted-GUI visual review, IR mapping
vendor semantics, NMR solid-C assignment semantics, Joint conflict meaning,
and final human release approval remain open.

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

### Native capture review update (2026-07-28 continuation)

The 68-capture D:-isolated native matrix was re-inspected for the remaining
route signals. `ir_mapping_results.png` shows the typed mapping payload and
non-empty Results review, while `ir_mapping_editor.png` shows the map heatmap,
color scale, editable figure surface, and Editor Inspector. These confirm the
synthetic mapping route only; they do not establish vendor file, coordinate, or
ROI conventions. `nmr_solid_c_editor.png` is editable and renders the real
spectrum, but its dense peak labels remain a scientific/visual label-policy
decision. `joint_compare_results.png` shows the diagnostic rows and conflicts,
while the synthetic restore header still says `No project` / `No data loaded`;
this remains a fixture/route review signal rather than a production change.

The direct OS capture attempt against the currently running GUI handle produced
the desktop wallpaper instead of the window content, so it is explicitly not
counted as restarted-GUI evidence. The existing valid live-window captures
(`C:\Temp\polynexus-live-window-max.png` and
`C:\Temp\polynexus-live-window.png`) remain shell/default-state evidence only;
the all-route restarted-GUI gate is still open.

On 2026-07-29 a new `python -m polynexus --gui` process was started from the
current worktree (`PID 39700`) and closed gracefully after capture. Qt-native
window grabs are valid for the fresh process: `C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-restarted-shell-20260729.png`
shows the default shell, and
`C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-restarted-temperature-saxs-post2-20260729.png`
shows a fresh SAXS temperature route after a real window-message click. The
same fresh process also reached SAXS static before the temperature route.
These captures close only the restarted shell/mode-switch evidence; the
all-mode real-data route, Gallery/Editor/export walkthrough and human release
decision remain open.

### Joint history identity follow-up (2026-07-29)

History restore now projects a Joint report's persisted/sample identity into
the display-only project badge: an explicit non-default label wins, one report
sample supplies its name, multiple samples use the translated Joint workspace
label, and empty reports retain `No project`. The Joint identity/lifecycle
slice passed `5` tests and the complete MainWindow persistence slice passed
`197` tests; together they confirmed existing Joint values, provenance,
manifests, and run identity remain unchanged. This is a UI persistence fix
only; it does not close scientific conflict review or restarted-GUI release
approval.

## Open release gates

- Complete restarted-GUI visual review for all requested routes.
- Review IR vendor-native mapping/ROI semantics.
- Review assignment-limited solid-state NMR and Joint scientific conflicts.
- Complete the human scientific publication decision and final AI-off/
  failure/fallback release approval.

No code change in this audit promotes a diagnostic-only result or changes a
scientific threshold.
