---
task_id: 2026-07-30-current-head-native-nonsaxs-walkthrough
kind: verification-audit
status: completed
date: 2026-07-30
title: Walk through current non-SAXS native GUI routes
---

# Current HEAD Native Non-SAXS Walkthrough

## Goal

Verify the current native Windows Qt Results, Gallery, History, Editor, and
Export routes for every selected non-SAXS mode, and record visual boundaries
without converting fixture review records into scientific approval.

## Non-goals

- Do not run or modify SAXS routes.
- Do not change production code, real datasets, review records, or publication
  roles.
- Do not treat a synthetic accepted record as a reviewer decision for real
  Joint data.

## Affected boundaries

- Native Qt GUI route harness and current non-SAXS mode selection.
- Results Workbench, manifest-only Gallery, History, Editor, and Export
  fallback surfaces.
- Visual evidence and durable acceptance records only.

## Implementation plan

1. Run the native route harness under `QT_QPA_PLATFORM=windows`, excluding
   SAXS and writing captures outside the repository.
2. Confirm complete pytest output and count route captures.
3. Inspect representative DSC, IR mapping, IR temperature-2D, NMR solid-C,
   and Joint surfaces for blank or misleading state.
4. Record boundaries, verify this task, and create one documentation-only
   checkpoint.

## Acceptance criteria

- [x] Native non-SAXS route selection passes with a complete pytest summary.
- [x] Four expected surfaces are captured for every selected route.
- [x] Representative boundary states are documented without scientific
      approval claims.
- [x] SAXS and real data remain untouched.
- [x] Task verifier, boundary audit, diff check, and explicit allowlist
      checkpoint are recorded below.

## Verification

```powershell
$env:POLYNEXUS_TEST_ROOT='D:\PolyNexus-test-runs-current-native-all'
$env:POLYNEXUS_TEST_RETENTION='review'
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_all_routes_current_nonsaxs_20260730'
python -m pytest -p no:cacheprovider tests/test_native_gui_real_route_capture.py -k 'not saxs' -vv -rs
python scripts/verify.py --task docs/agent/tasks/2026-07-30-current-head-native-nonsaxs-walkthrough.md --changed --types
python scripts/boundary_audit.py --root D:\PolyNexus --json
git diff --check
```

## Evidence

- Native route: `14 passed, 3 deselected, 15 warnings in 353.49s`, exit `0`.
- Capture root: `D:\PolyNexus_native_all_routes_current_nonsaxs_20260730`.
- Capture count: `56` PNGs, four per selected route.
- Representative captures show IR mapping `Review required`, NMR solid-C
  `review_missing`, and Joint fixture `Accepted` with 2 errors/2 warnings.
  The last state is synthetic fixture provenance only.
- Task verifier exited `0`; quality `292`, preprocessing `106`, Ruff,
  compile, memory/task, type baseline, and whitespace passed. Boundary audit
  and diff check also exited `0` before this final documentation update.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-30-current-head-native-nonsaxs-walkthrough.md`
- `docs/acceptance/2026-07-30-current-head-native-nonsaxs-walkthrough.md`
- `docs/superpowers/specs/2026-07-30-current-head-native-nonsaxs-walkthrough-design.md`
- `docs/superpowers/plans/2026-07-30-current-head-native-nonsaxs-walkthrough.md`
- `docs/agent/memory/active-work.md`
