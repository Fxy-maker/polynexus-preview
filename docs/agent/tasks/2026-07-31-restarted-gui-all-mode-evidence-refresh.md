---
task_id: 2026-07-31-restarted-gui-all-mode-evidence-refresh
kind: release-readiness
status: completed
date: 2026-07-31
title: Refresh restarted GUI all-mode evidence
---

# Restarted GUI all-mode evidence refresh

## Goal

Refresh current-checkout native Windows evidence for every real technique mode,
plus synthetic Joint and IR mapping routes, and preserve the distinction
between route evidence and scientific/owner approval.

## Non-goals

- No production, test, real-data, or generated-output changes.
- No scientific promotion, vendor calibration, assignment, or conflict
  precedence decision.
- No push, merge, deployment, or storage cleanup.

## Affected boundaries

- `tests/test_native_gui_real_route_capture.py`: read-only native route
  harness.
- External D-drive capture and pytest roots only; no repository source or real
  dataset files.
- Results, Manifest/Gallery, Editor, History, and PackageExporter evidence
  surfaces.

## Implementation plan

1. Run the native route harness with a fresh Windows Qt process and external
   evidence roots.
2. Count the PNG captures and inspect representative populated/conservative
   states.
3. Run boundary and structured verification, then record exact outcomes.
4. Create one allowlist checkpoint containing only the four documentation
   files.

## Acceptance criteria

- [x] Native route matrix has a complete pytest summary and exit code `0`.
- [x] Every captured mode has Results, Gallery, History, and Editor images.
- [x] PackageExporter fallback artifacts are created by the real Editor action.
- [x] Representative images are nonblank and show populated route state.
- [x] IR mapping, NMR solid-C, and Joint conservative limitations remain
      visible rather than being represented as scientific approval.
- [x] Warnings and known visual limitations are recorded exactly.
- [x] Boundary audit, task verifier, diff check, and explicit allowlist
      checkpoint are recorded.

## Verification

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_TEST_ROOT='D:\PolyNexus-test-runs-native-restarted-20260731'
$env:POLYNEXUS_TEST_RETENTION='evidence'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_restarted_gui_audit_20260731'
python -m pytest -q tests/test_native_gui_real_route_capture.py -o addopts=
python scripts/boundary_audit.py --root D:\PolyNexus --json
python scripts/verify.py --task docs/agent/tasks/2026-07-31-restarted-gui-all-mode-evidence-refresh.md --changed --types
git diff --check
```

Only a complete pytest summary with exit code `0` is counted as a route pass.

## Evidence

- Native matrix: `17 passed, 15 warnings in 521.92s`, exit code `0`.
- Captures: `68` PNGs, `14,567,314` bytes, four per each of 17 modes.
- Representative Results images show populated metrics/evidence for DSC,
  explicit `review_missing` IR mapping, `assignment_limited` NMR solid-C, and
  Joint diagnostics with errors/warnings and a blocked conclusion.
- Editor capture shows a nonblank editable multi-plot canvas, object tree,
  and export controls. PackageExporter fallback artifacts were asserted for
  each route.
- Warnings include DSC polynomial-fit/font glyph/constrained-layout warnings;
  these remain visual review signals and are not suppressed.

## Explicit changed-file allowlist

- `docs/superpowers/specs/2026-07-31-restarted-gui-all-mode-evidence-refresh-design.md`
- `docs/superpowers/plans/2026-07-31-restarted-gui-all-mode-evidence-refresh.md`
- `docs/agent/tasks/2026-07-31-restarted-gui-all-mode-evidence-refresh.md`
- `docs/acceptance/2026-07-31-restarted-gui-all-mode-evidence-refresh.md`

The external capture and pytest directories are evidence/runtime paths, not
checkpoint files. Scientific reviewer and final owner approval remain open.
