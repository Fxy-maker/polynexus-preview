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
- A fresh dedicated full verifier completed with `2767 passed, 10 warnings` in
  `1453.05s`; compile, quality, preprocessing, Ruff/type baseline, whitespace,
  and boundary audit all passed. The earlier `2763 passed, 1 failed` result is
  retained as historical evidence only; the WAXS focused recheck and fresh
  full run now pass.
- Canonical GUI default-shell screenshot: `C:\Users\Fan Xuyi\AppData\Local\Temp\polynexus-gui-default.png`.
  It shows the SAXS empty state, workspace summary, mode navigation, and the
  Data/Config/Results/Plots shell. It is visual evidence only.

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
