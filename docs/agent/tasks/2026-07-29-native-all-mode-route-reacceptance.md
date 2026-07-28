---
task_id: 2026-07-29-native-all-mode-route-reacceptance
kind: gui-acceptance-recheck
status: completed
---

# Native all-mode route reacceptance

## Goal

Refresh current-checkout native Windows Qt evidence for every real technique
mode after the NMR solid-C assignment-column change.

## Non-goals

- Do not change production GUI behavior, scientific algorithms, thresholds,
  evidence severity, publication roles, or real fixtures.
- Do not infer IR vendor coordinate/ROI semantics or Joint scientific meaning.
- Do not treat automated native captures as human publication approval.
- Do not delete or migrate C-drive test data.

## Affected boundaries

- Existing harness: `tests/test_native_gui_real_route_capture.py`.
- External D: basetemp/capture roots only.
- Acceptance/task/memory evidence; no production code.

## Implementation plan

1. Run all 17 native cases on the current checkout with isolated D: roots.
2. Confirm four surfaces and PackageExporter fallback for every route.
3. Inspect representative current screenshots, especially NMR solid-C and
   Joint, and classify automated versus human/scientific evidence.
4. Run the task-scoped verifier and create an explicit documentation-only
   checkpoint without mixing existing worktree changes.

## Acceptance criteria

- [x] Native matrix covers DSC 3, SAXS 3, WAXS 3, IR 2, NMR 4, Joint 1, and
      synthetic IR mapping 1.
- [x] Pytest returns 17 passed with exit code 0 and warnings recorded.
- [x] Current capture root contains 68 images and export fallback artifacts.
- [x] NMR solid-C current Editor capture shows the complete assignment column.
- [x] Remaining IR vendor, Joint scientific, visual, and release gates stay
      explicitly open.
- [x] Task verifier, whitespace, and allowlist checkpoint pass.

## Verification

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_all_routes_reacceptance_20260729'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_native_all_routes_reacceptance_basetemp_20260729'
python -m pytest -q tests/test_native_gui_real_route_capture.py -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-29-native-all-mode-route-reacceptance.md --changed --types
git diff --check
```

## Known limitations

Native route evidence proves construction and automated interactions. It does
not prove vendor-native IR mapping semantics, Joint conflict interpretation,
solid-C assignment correctness, or final human release approval.
