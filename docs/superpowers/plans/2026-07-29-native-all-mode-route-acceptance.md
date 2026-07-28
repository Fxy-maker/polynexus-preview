# Native All-Mode Route Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-run the current native Windows Qt route harness against every real mode and the synthetic Joint/IR mapping routes, then record exactly what the captures prove and what remains human review.

**Architecture:** Reuse `tests/test_native_gui_real_route_capture.py` and its existing public GUI/PackageExporter routes. This is an acceptance-only slice: no production behavior, scientific thresholds, publication roles, or fixture data change. Native captures are evidence of route construction and visual structure, not scientific approval.

**Tech Stack:** Python 3.14 bundled runtime, pytest, PySide6 native Windows Qt, existing real fixtures, PackageExporter fallback, Markdown acceptance/memory records.

---

### Task 1: Execute the current native route matrix

**Files:**
- Read: `tests/test_native_gui_real_route_capture.py`
- Read: `tests/test_real_published_run_walkthrough.py`
- Write: external diagnostics under `D:\PolyNexus_native_all_routes_capture_20260729` and `D:\PolyNexus_native_all_routes_basetemp_20260729`

- [x] Run with `QT_QPA_PLATFORM=windows` and isolated D: basetemp.
- [x] Capture Results, Gallery, History, and Editor for every case.
- [x] Exercise the real Editor Export action with the PackageExporter fallback.

Exact command:

```powershell
$py='D:\PolyNexus\Python\pythoncore-3.14-64\python.exe'
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_all_routes_capture_20260729'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_native_all_routes_basetemp_20260729'
& $py -m pytest -q tests/test_native_gui_real_route_capture.py -vv
```

Expected acceptance result: 17 selected cases, 4 captures per case, and exit
code 0; warnings remain visible and are recorded rather than suppressed.

### Task 2: Inspect representative captures and classify limits

**Files:**
- Read: `D:\PolyNexus_native_all_routes_capture_20260729\dsc_standard_results.png`
- Read: `D:\PolyNexus_native_all_routes_capture_20260729\saxs_temperature_results.png`
- Read: `D:\PolyNexus_native_all_routes_capture_20260729\nmr_solid_c_editor.png`
- Read: `D:\PolyNexus_native_all_routes_capture_20260729\ir_mapping_editor.png`
- Read: `D:\PolyNexus_native_all_routes_capture_20260729\joint_compare_results.png`
- Read: `D:\PolyNexus_native_all_routes_capture_20260729\saxs_static_gallery.png`

- [x] Confirm native shell, live labels, Results, Gallery, History, and Editor
  surfaces are constructible in the fresh process.
- [x] Confirm the NMR solid-C dense labels, synthetic IR mapping boundary, and
  Joint `PA6-A` identity with synthetic `No data loaded` context remain
  explicit review limitations.
- [x] Keep SAXS diagnostic/validation states visible in the evidence rather
  than treating them as scientific conclusions.

### Task 3: Record evidence and checkpoint

**Files:**
- Modify: `docs/acceptance/2026-07-27-full-software-release-audit.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`
- Create: `docs/agent/tasks/2026-07-29-native-all-mode-route-acceptance.md`

- [x] Record the exact 17-case pytest summary, 68-capture count, warnings, and
  representative visual observations.
- [x] Run the task-scoped verifier and `git diff --check`.
- [x] Create one allowlisted local checkpoint with `scripts/auto_commit.py`.

## Scope audit

- No production source, raw fixture, scientific formula, threshold, evidence
  severity, publication role, or AI policy changes.
- The task does not close human scientific review, IR vendor mapping semantics,
  NMR solid-C assignment policy, Joint conflict interpretation, or final release
  approval.
