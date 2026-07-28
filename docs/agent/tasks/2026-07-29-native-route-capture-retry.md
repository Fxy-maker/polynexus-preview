---
task_id: 2026-07-29-native-route-capture-retry
kind: release-verification-audit
status: completed
---

# Windows-native all-route capture retry

## Goal

Re-run the complete Windows-native Qt route harness from the current checkout,
capture all requested Results/Gallery/History/Editor surfaces, and inspect the
high-signal scientific boundary states without promoting them to approval.

## Non-goals

- Do not change production code or scientific thresholds.
- Do not infer IR vendor/ROI, NMR assignment, or Joint conflict meaning.
- Do not treat in-process Qt captures as a substitute for unlocked interactive
  human release review.
- Do not delete or migrate test data.

## Affected boundaries

- `tests/test_native_gui_real_route_capture.py`
- Native Results Workbench, Gallery, History, Editor, and no-Origin fallback
  Export routes.
- Fresh D: capture and pytest basetemp directories.

## Implementation plan

1. Run the complete 17-case native route matrix with Windows Qt and D: paths.
2. Capture and count the four surfaces per case.
3. Inspect representative SAXS, IR mapping, NMR solid-C, and Joint images.
4. Record explicit scientific/release limitations.

## Acceptance criteria

- [x] The complete native matrix has a pytest summary and exit code.
- [x] All four surfaces and fallback Export are exercised for each route.
- [x] Fresh captures are present and representative boundary states are
      inspected.
- [x] Automated evidence is not promoted to scientific approval.

## Verification

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_all_routes_capture_20260729_retry'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_native_all_routes_retry_basetemp'
python -m pytest -q tests/test_native_gui_real_route_capture.py
# 17 passed, 15 warnings in 370.95s (0:06:10)
# NATIVE_GUI_EXIT_CODE=0

python scripts/verify.py --task docs/agent/tasks/2026-07-29-native-route-capture-retry.md --changed --types
git diff --check
```

Fresh capture directory: `D:\PolyNexus_native_all_routes_capture_20260729_retry`
with `68` PNG files. Representative inspected files include
`saxs_temperature_results.png`, `ir_mapping_results.png`,
`nmr_solid_c_editor.png`, and `joint_compare_results.png`.

## Observations and limitations

- SAXS temperature keeps diagnostic-only validation and next-step warnings
  visible instead of promoting the series.
- IR mapping shows the structural mapping payload and `Not confirmed yet`.
- NMR solid-C is editable and shows assignment labels, but label density and
  assignment correctness remain scientific review items.
- Joint preserves `PA6-A` identity and displays two errors/two warnings; their
  scientific meaning remains open.

These are native application-window capture observations, not final human
scientific/release approval. No test data was deleted or migrated.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-native-route-capture-retry.md`
- `docs/acceptance/2026-07-29-native-route-capture-retry.md`
- `docs/agent/memory/active-work.md`
