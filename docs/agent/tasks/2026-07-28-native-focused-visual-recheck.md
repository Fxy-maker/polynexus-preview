---
kind: release-verification-audit
status: completed
date: 2026-07-28
title: Fresh native focused visual recheck for Joint, IR mapping, and NMR solid-C
---

# Fresh native focused visual recheck

## Goal

Re-run the three remaining high-signal native GUI routes from the current
checkout and inspect their fresh Results/Editor captures without promoting
visual evidence to scientific or release approval.

## Non-goals

- Do not infer IR vendor coordinate/ROI semantics.
- Do not approve NMR solid-C assignment correctness or label policy.
- Do not reinterpret Joint conflicts or change scientific thresholds.
- Do not modify production code, real datasets, generated repository outputs, or
  test-storage artifacts.

## Affected boundaries

- `tests/test_native_gui_real_route_capture.py` native Windows Qt route harness
- Results Workbench identity, mapping-risk, and NMR label presentation surfaces
- `docs/acceptance/`, `docs/agent/memory/`, and this verification task record

## Implementation plan

1. Run the focused Joint, IR mapping, and NMR solid-C native route shards with
   isolated D: basetemps and capture directories.
2. Inspect fresh Results/Editor images for identity consistency, explicit risk
   boundaries, and editable figure lifecycle.
3. Record exact summaries, paths, observations, and human-review limits in the
   acceptance note and durable memory.
4. Run the structured verifier and create one explicit documentation checkpoint.

## Acceptance criteria

- [x] Joint native route passes and fresh Results capture keeps the same
      `PA6-A` identity in the header, breadcrumb, Current task, and Review
      focus.
- [x] IR mapping native route passes and fresh Results capture keeps the
      structural mapping payload plus explicit `Not confirmed yet` boundary.
- [x] NMR solid-C native route passes and fresh Results/Editor captures remain
      editable and expose assignment labels without claiming scientific
      assignment acceptance.
- [x] Fresh capture paths, exact commands, and remaining human gates are
      recorded in the acceptance note.

## Verification

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_joint_recheck_20260730'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_native_joint_recheck_20260730_basetemp'
python -m pytest -q tests/test_native_gui_real_route_capture.py -k joint_synthetic
# 1 passed, 16 deselected in 8.16s
```

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_ir_mapping_recheck_20260730'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_native_ir_mapping_recheck_20260730_basetemp'
python -m pytest -q tests/test_native_gui_real_route_capture.py -k synthetic_ir_mapping
# 1 passed, 16 deselected in 7.07s
```

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_nmr_solid_c_recheck_20260730'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_native_nmr_solid_c_recheck_20260730_basetemp'
python -m pytest -q tests/test_native_gui_real_route_capture.py -k solid_c
# 1 passed, 16 deselected in 19.45s
```

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_native_visual_recheck_task_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-native-focused-visual-recheck.md --changed --types
git diff --check
```

## Fresh visual observations

- Joint: `joint_compare_results.png` shows `PA6-A` consistently in the top
  project label, breadcrumb, Current task source, and Review focus. The
  diagnostic table still exposes two errors and two warnings; interpretation
  remains a human scientific gate.
- IR mapping: `ir_mapping_results.png` shows the typed mapping route and an
  explicit structural-mapping risk note with `Not confirmed yet`; vendor file,
  coordinate convention, and ROI meaning remain open.
- NMR solid-C: `nmr_solid_c_results.png` shows the Solid 13C route and editable
  lifecycle; `nmr_solid_c_editor.png` shows peak labels including assigned and
  unassigned regions. Label density and assignment correctness remain open
  scientific review items.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-28-native-focused-visual-recheck.md`
- `docs/acceptance/2026-07-28-native-focused-visual-recheck.md`
- `docs/agent/memory/active-work.md`
