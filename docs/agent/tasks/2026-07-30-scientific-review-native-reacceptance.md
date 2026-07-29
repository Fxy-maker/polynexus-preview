---
task_id: 2026-07-30-scientific-review-native-reacceptance
kind: gui-acceptance-recheck
status: completed
---

# Scientific Review native reacceptance

## Goal

Re-run the current native Windows Qt route for synthetic IR mapping, NMR
solid-C, and Joint after checkpoint `e7209ee`, verifying that Results/Gallery/
History/Editor remain constructible and the new Scientific Review display does
not break the routes.

## Non-goals

- Do not infer IR vendor coordinate/ROI semantics, NMR assignment/Xc policy, or
  Joint conflict precedence.
- Do not promote diagnostic/assignment-limited figures or authorize release.
- Do not modify production code, real datasets, generated outputs, or test
  storage directories.

## Affected boundaries

- `tests/test_native_gui_real_route_capture.py` native route harness.
- Scientific Review display visibility in Results/History/Export context.
- Existing PackageExporter fallback and route provenance.

## Acceptance criteria

- [x] The three current native route tests pass with complete output and exit 0.
- [x] Results, Gallery, History, Editor, and fallback Export remain reachable.
- [x] No scientific/release gate is relabeled as approved by this recheck.
- [x] Exact output, warnings, capture root, and limitations are recorded.

## Implementation plan

1. Run the three selected native route tests using an external D: basetemp and
   capture root.
2. Inspect the current IR mapping Editor, NMR solid-C Editor, and Joint Results
   captures for route construction and explicit limitation visibility.
3. Record exact pytest output and run the task verifier without changing source.
4. Create an explicit documentation-only checkpoint while preserving existing
   untracked test/storage directories and `current-state.md`.

## Verification

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_scientific_review_native_reacceptance_20260730'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_scientific_review_native_basetemp_20260730'
python -m pytest -q tests/test_native_gui_real_route_capture.py -k "solid_c or native_windows_gui_joint_synthetic_route or native_windows_gui_synthetic_ir_mapping_route" -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-30-scientific-review-native-reacceptance.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-30-scientific-review-native-reacceptance.md`
- `docs/acceptance/2026-07-30-scientific-review-native-reacceptance.md`
- `docs/agent/memory/active-work.md`
