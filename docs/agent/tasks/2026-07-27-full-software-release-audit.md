# Full Software Release Audit

Status: in progress
Date: 2026-07-27

## Goal

Audit and close the remaining release-level evidence for the PolyNexus workflow
across SAXS, DSC, WAXS, IR, NMR, and Joint without treating provider-only or
focused-test evidence as a complete module release.

## Scope

- Verify the shared analysis/evidence/figure/manifest/gallery/editor/export/
  history lifecycle for every declared mode.
- Verify the cross-technique AI-off, failed-run, and fallback safety contract.
- Re-run WAXS publication cutover evidence after the previously reported full
  verifier failure.
- Record the current canonical GUI visual state and distinguish automated
  evidence from restarted-GUI and scientific-review gates.
- Preserve diagnostic-only and assignment-limited outputs as non-promoted
  results.

## Non-goals

- No new physical thresholds, scientific interpretation, vendor semantics, or
  AI promotion rules.
- No modification of real regression datasets, generated outputs, secrets, or
  local runtime directories.
- No push, merge, deployment, branch deletion, or human scientific sign-off on
  behalf of a reviewer.

## Acceptance criteria

- [x] WAXS publication cutover and its focused provider/workbench matrix pass with
   a dedicated basetemp.
- [x] The cross-technique AI safety matrix records exact pass/fail evidence for
   DSC, IR, WAXS, SAXS, and NMR, with Joint explicitly report-level.
- [x] Each lifecycle mode has either fresh automated evidence or an explicit
   limitation naming the missing real fixture, timeout, or visual/scientific
   gate.
- [x] The canonical GUI is restarted from `D:\PolyNexus`, its default shell is
   captured, and visual checks are not represented as automated sign-off.
- [x] The full verifier is run with a dedicated basetemp when practical; any
   failure or timeout is recorded verbatim and never relabeled as pass.
- [x] The task card, implementation plan, acceptance note, and durable memory
   agree on the same status and next action.

## Affected boundaries

- Existing tests under `tests/` and real/synthetic fixtures under `tests/eval/`.
- Existing publication providers and shared figure lifecycle contracts, only
  for read-only verification in this task.
- `scripts/verify.py`, GUI launcher diagnostics, and temporary screenshot output.
- `docs/acceptance/`, `docs/agent/memory/`, and this task's plan/card.

## Implementation plan

1. Re-run the WAXS publication/provider/workbench matrix with an isolated
   basetemp and preserve the exact count.
2. Re-run the cross-technique AI-off/failure/fallback contract matrix and keep
   Joint explicitly outside single-technique preprocessing.
3. Run real-fixture and lifecycle files one at a time, classifying each mode as
   automated-pass, diagnostic-only, fixture-missing, bounded-timeout, or
   human-review.
4. Restart the canonical GUI from `D:\PolyNexus`, capture the default shell,
   and record the remaining route-level visual gates.
5. Run the full changed/type verifier with `--full --boundary` and reconcile
   this card, the plan, acceptance note, and durable memory.

## Verification

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_release_audit_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-27-full-software-release-audit.md --changed --types
```

The focused WAXS and AI matrices and the full/boundary command are listed
below. Any timeout, existing failure, or skipped boundary remains recorded as
limitation rather than pass.

## Current evidence and limitations

- WAXS publication cutover focused recheck: `30 passed` using an isolated
  basetemp on 2026-07-27.
- Cross-technique AI-off/failure/fallback matrix: `25 passed` using an isolated
  basetemp on 2026-07-27.
- Real published-run walkthrough shards: DSC `3 passed` (11 existing warnings),
  WAXS `3 passed`, SAXS `3 passed`, IR `2 passed`, NMR `4 passed`; all 15
  single-technique cases passed.
- Fresh IR walkthrough rerun: `2 passed, 13 deselected in 71.34s`, exit code
  `0`; fresh NMR walkthrough rerun: `4 passed, 11 deselected in 112.23s`,
  exit code `0`. Their real validation warnings remain recorded and do not
  promote IR 2D or solid-C NMR semantics.
- Lifecycle closure shards: DSC `3`, WAXS `3`, IR `3`, NMR `4`, and Joint `1`
  passed. IR's three modes include mapping; NMR's solid C assignment remains
  provisional.
- GUI shell/workbench/gallery/editor route contracts passed `58` focused tests;
  this does not replace the restarted-GUI pixel-level walkthrough.
- A temporary pytest visual capture passed `1` case and restored a real DSC
  run through Results, Gallery, History, and Editor, with four screenshots and
  one manifest gallery entry. Offscreen CJK glyphs render as square placeholders,
  so live-font and pixel-level review remains open.
- IR mapping/ROI and lifecycle matrix passed `11` tests; it rejects mismatched
  geometry/invalid pixels and preserves structural provenance without inferring
  vendor format or band meaning.
- NMR/Joint provenance and lifecycle matrix passed `4` tests; solid-state NMR C
  assignment and Joint scientific conflicts remain explicit human gates.
- A combined lifecycle/real-run command exceeded the short 180-second tool
  window without a test summary; this is not a pass or a failure claim.
- A fresh current-working-tree run completed with `2793 passed, 10 warnings`
  in `1607.00s`; compile, quality (`283`), preprocessing (`106`), Ruff/type
  baseline, whitespace, and boundary audit all passed. This supersedes the
  older `2af4baf` evidence of `2790 passed`.
- The responsive-shell GUI task was checkpointed as `83083bc`; a fresh
  `scripts/launch_gui.py --diagnose` resolved the canonical `D:\PolyNexus`
  source root and that commit. All-route live visual review remains open.
- Canonical GUI default-shell screenshot: `C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-gui-default.png`.
  It shows the SAXS empty state, workspace summary, mode navigation, and the
  Data/Config/Results/Plots shell. It is visual evidence only.
- Additional live-window capture at maximum size:
  `C:\Temp\polynexus-live-window-max.png`. It shows the canonical sidebar,
  Data/Config/Results/Plots/History tabs, and a fitting Data surface. The
  normal-size live capture is `C:\Temp\polynexus-live-window.png`; its
  narrow-width right edge remains a human visual-review item.
- Native Windows Qt capture with `QT_QPA_PLATFORM=windows` and external
  basetemp `C:\Temp\PolyNexus_native_gui_route` passed
  `tests/_tmp_phase3/test_visual_audit_capture.py`: `1 passed in 5.93s`.
  Native DSC Results/Gallery/History/Editor captures at 1600x1000 showed live
  CJK glyphs and constructible shared routes. This covers one DSC route only;
  export interaction and every other technique/mode remain open.
- A reusable native acceptance harness is now present at
  `tests/test_native_gui_real_route_capture.py`. It is skipped under the
  default offscreen test environment and parameterizes all real walkthrough
  modes when explicitly run with `QT_QPA_PLATFORM=windows`. The corrected
  harness now imports both `_real_cases()` and `_full_2d_real_cases()`.
- Native Windows Qt route shards passed all 15 cases with exit code `0`:
  DSC `3` (25.44s), SAXS `3` (49.93s), WAXS `3` (86.35s), IR `2` (66.72s),
  and NMR `4` (114.85s). Each case captured Results, Gallery, History, and
  Editor under external `C:\Temp\PolyNexus_native_gui_*_verified` folders.
  Representative images show the routes constructible and live CJK labels;
  body contrast/activity in inactive `grab()` captures remained a human visual
  gate.
- The native harness now triggers the real Chart Editor Export `QAction` for
  every mode using only the existing `PackageExporter` fallback. A second
  native matrix passed with exit code `0`: DSC `3` (24.25s), SAXS `3` (49.85s),
  WAXS `3` (87.35s), IR `2` (67.19s), and NMR `4` (117.75s). Each mode
  produced `Origin_Export/figure_document.json`, `metadata.json`, and
  `import.ogs` under its external run output. Installed OriginPro/COM behavior
  is intentionally not launched and remains an optional-runtime gate.
- The prior all-native command timed out at the 180-second tool boundary with
  no pytest summary and is classified as a tool-level timeout. The prior
  `-k waxs.strain` exit code `5` selected no tests because full-2D cases were
  not imported; it was a harness selection error, superseded by the WAXS/IR
  native shards above.
- Offscreen route capture after scientific-stack preload produced
  `C:\Temp\polynexus-route-0.png` through `polynexus-route-4.png` and
  `C:\Temp\polynexus-route-editor.png`; all five tabs and the Editor were
  constructed, and the active Gallery contained one manifest entry. This is
  structural evidence only because CJK glyphs render as squares offscreen.
- Documentation verifier rerun with external basetemp
  `C:\Temp\PolyNexus_release_gui_route_verify_20260727` passed task/memory
  checks, Ruff, compile/type baseline, quality `283`, preprocessing `106`,
  and whitespace. The first run against the pre-existing protected
  `D:\PolyNexus\.pytest_tmp` stopped with 54 setup errors (`WinError 5`) while
  pytest cleaned that directory; it was not a test assertion failure and was
  not used as final evidence.

## Verification commands

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_waxs_pub_matrix'
python -m pytest -q tests/test_waxs_publication_cutover.py tests/test_waxs_publication_temperature_provider.py tests/test_waxs_publication_strain_provider.py tests/test_waxs_publication_static_provider.py tests/test_waxs_workbench_figure_contracts.py tests/test_waxs_figure_provider.py tests/test_waxs_figure_document.py
```

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_release_ai2'
python -m pytest -q tests/test_preprocess_cross_technique_matrix.py tests/test_preprocess_ai_off_compat.py tests/test_preprocess_fault_injection.py
```

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\PolyNexus.pytest_tmp_release_full'
python scripts/verify.py --changed --types --full --boundary
```

## Next action

Automated release evidence is now complete. The remaining actions are the
restarted-GUI route walkthrough, IR vendor mapping/ROI semantics review,
assignment-limited NMR/Joint scientific review, and final human release
approval. Do not call the overall goal complete while those gates remain open.
