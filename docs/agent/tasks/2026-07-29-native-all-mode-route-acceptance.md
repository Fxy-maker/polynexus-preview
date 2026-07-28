---
task_id: 2026-07-29-native-all-mode-route-acceptance
kind: gui-acceptance
status: completed
---

# Native all-mode route acceptance

## Goal

Capture fresh native Windows Qt evidence for every real technique mode plus the
synthetic Joint and IR mapping boundaries, covering Results, Gallery, History,
Editor, and the no-Origin PackageExporter route.

## Non-goals

- Do not change production GUI behavior, scientific algorithms, thresholds,
  evidence severity, publication roles, or raw fixtures.
- Do not infer IR vendor coordinate/ROI semantics from a synthetic payload.
- Do not treat NMR solid-C labels or Joint conflicts as scientifically approved.
- Do not close human visual/scientific review or final release approval.

## Affected boundaries

- Existing harness: `tests/test_native_gui_real_route_capture.py`.
- Existing real-case source: `tests/test_real_published_run_walkthrough.py`.
- External capture/basetemp directories on D: only.
- Acceptance and durable memory records; no production code.

## Implementation plan

1. Run the native Windows Qt harness on the current checkout with an isolated D:
   basetemp and capture directory.
2. Verify that all 17 selected cases produce Results, Gallery, History, and
   Editor captures and trigger the existing PackageExporter fallback.
3. Inspect representative fresh images and classify structural evidence versus
   human scientific/visual limitations.
4. Record exact output, run the task-scoped verifier, and create one allowlisted
   local checkpoint without push or merge.

## Acceptance criteria

- [x] The fresh matrix covers DSC 3, SAXS 3, WAXS 3, IR 2, NMR 4, synthetic
  Joint 1, and synthetic IR mapping 1.
- [x] Pytest returns 17 passed with exit code 0 and warnings recorded.
- [x] The capture directory contains 68 images: four route surfaces per case.
- [x] The harness exercises the real Editor Export action and creates the
  PackageExporter fallback bundle for every case.
- [x] Representative captures show constructible native Results/Gallery/
  History/Editor surfaces and live labels.
- [x] Known limitations remain explicit: synthetic IR mapping, Joint's
  `PA6-A` identity with `No data loaded` synthetic context, crowded NMR
  solid-C labels, and open scientific/release gates.
- [x] Task-scoped verifier passes; the automated route evidence is checkpointed
  while human visual/scientific/release gates remain open.

## Verification

```powershell
$py='D:\PolyNexus\Python\pythoncore-3.14-64\python.exe'
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_all_routes_capture_20260729'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_native_all_routes_basetemp_20260729'
& $py -m pytest -q tests/test_native_gui_real_route_capture.py -vv
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_native_all_routes_verify_20260729'
python scripts/verify.py --task docs/agent/tasks/2026-07-29-native-all-mode-route-acceptance.md --changed --types
git diff --check
```

## Known limitations

This is automated native route and capture evidence. It is not a human
publication decision. The fresh images retain crowded solid-C peak labels,
the Joint route displays the restored `PA6-A` identity but retains synthetic
`No data loaded` context, and IR mapping uses an explicit synthetic payload
rather than a vendor-native file. The SAXS temperature route retains
diagnostic/validation signals that require scientific interpretation.

## Evidence before checkpoint

- Fresh current-checkout native matrix: `17 passed, 15 warnings in 358.71s`,
  exit code `0`.
- Capture directory: 68 PNGs under
  `D:\PolyNexus_native_all_routes_capture_20260729_post_joint`, exactly four surfaces
  (Results/Gallery/History/Editor) for each of 17 cases.
- Representative images were inspected for DSC Results, SAXS temperature
  Results, SAXS static Gallery, NMR solid-C Editor, IR mapping Editor, and Joint
  Results/History. Joint now shows `PA6-A` in the project badge while its
  synthetic route still has `No data loaded` context.
- Task-scoped verifier: exit code `0`; task/memory checks, Ruff, compile,
  quality (`283 passed, 2 warnings`), preprocessing (`106 passed, 2 warnings`),
  no changed type-baseline targets, and whitespace all passed.

## Post-prefix rerun evidence (2026-07-29)

- The current checkout reran the same native matrix after the shared Results
  Review prefix fix: `17 passed, 15 warnings in 320.08s`, exit code `0`.
- Fresh captures are under
  `D:\PolyNexus_native_all_routes_capture_20260729_post_prefix` and contain
  68 PNGs. Results/Gallery/History/Editor were produced for all 17 routes and
  the no-Origin PackageExporter fallback was exercised.
- Representative Results captures show one shared `Risk note`/`Next step`
  wrapper per panel. SAXS's multiple labeled lines are separate evidence
  sections, not duplicate formatting. IR mapping remains synthetic, NMR
  solid-C assignment remains provisional, and Joint retains the explicit
  `PA6-A` badge plus synthetic `No data loaded` route context.

## Follow-up checkpoint boundary

This evidence update changes only the task/plan/memory records. The existing
uncommitted `docs/agent/memory/current-state.md` legacy-storage edit is
intentionally excluded from this follow-up checkpoint.

## Explicit changed-file allowlist

- `docs/superpowers/plans/2026-07-29-native-all-mode-route-acceptance.md`
- `docs/agent/tasks/2026-07-29-native-all-mode-route-acceptance.md`
- `docs/acceptance/2026-07-27-full-software-release-audit.md`
- `docs/agent/memory/current-state.md`
- `docs/agent/memory/active-work.md`
