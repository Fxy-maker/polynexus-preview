---
task_id: 2026-07-30-full-native-visual-reacceptance
kind: release-verification
status: completed
date: 2026-07-30
title: Reaccept all-mode native GUI routes
---

# Full native visual reacceptance

## Goal

Re-run the current checkout's native Windows Qt route for every automated
single-technique mode plus the synthetic Joint and IR mapping routes, and
record route construction, capture evidence, and remaining human visual and
scientific gates without relabeling them as approved.

## Non-goals

- Do not change production code, scientific thresholds, publication roles, or
  reviewer-owned IR/NMR/Joint semantics.
- Do not infer scientific correctness from screenshot or route construction.
- Do not modify real datasets, generated outputs, or repository test-storage
  directories; use external D: capture and basetemp roots.

## Affected boundaries

- `tests/test_native_gui_real_route_capture.py` native Windows Qt harness.
- Results Workbench, Gallery, History, Editor, and PackageExporter fallback.
- Release evidence under `docs/acceptance/` and durable active-work memory.

## Acceptance criteria

- [x] The full current-checkout selector returns a complete pytest summary and
  exit code `0`.
- [x] Every selected mode reaches Results, Gallery, History, Editor, and the
  no-Origin PackageExporter fallback.
- [x] Representative captures are inspected for route usability and defects;
  screenshots remain evidence only.
- [x] IR vendor mapping semantics, NMR solid-C assignment/Xc policy, Joint
  conflict precedence, and final release authorization remain explicitly
  separate human gates.

## Implementation plan

1. Run the current-checkout native Windows Qt selector with D:-isolated
   capture and pytest temporary roots, preserving the complete stdout/stderr
   summary and exit code.
2. Inspect representative Results, Gallery, History, Editor, and no-Origin
   fallback captures, recording route usability and visible diagnostic states
   without inferring scientific meaning.
3. Record the evidence and open human gates in the task, acceptance, and
   active-work documents, then run focused tests, the task verifier, and diff
   checks before creating one explicit-allowlist checkpoint.

## Recorded result

- Fresh current-checkout native Windows Qt run:
  `17 passed, 15 warnings in 443.92s (0:07:23)`, exit code `0`.
- Coverage: DSC standard/isothermal/non-isothermal; SAXS static/temperature/
  strain; WAXS static/temperature/strain; IR standard/temperature-2D; NMR
  liquid-H/liquid-C/solid-H/solid-C; synthetic Joint; and synthetic IR mapping.
- Every selected route reached Results, Gallery, History, Editor, and the
  no-Origin PackageExporter fallback. Capture root:
  `D:\PolyNexus_full_native_visual_reacceptance_20260730_rerun`.
- Representative captures were inspected. SAXS strain remains usable after
  skipping the assetless `generation_failed` entry for initial Editor
  selection; the diagnostic card remains visible as a diagnostic-only card.
  IR mapping visibly reports `Review required | reason=review_missing` while
  retaining its heatmap and Editor route. NMR solid-C peak labels are dense.
  Synthetic Joint shows two errors and two warnings; its fixture review state
  is provenance for the fixture only, not scientific approval.
- The native run is route/display evidence only. It does not establish IR
  vendor coordinate/origin/ROI/invalid-pixel semantics, NMR solid-C assignment
  provenance or Xc promotion rules, Joint conflict precedence or minimum
  evidence level, or the final `approve`/`conditional`/`reject` release
  decision.

## Verification

```powershell
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_full_native_visual_reacceptance_20260730_rerun'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_full_native_visual_basetemp_20260730'
python -m pytest -q tests/test_native_gui_real_route_capture.py -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-30-full-native-visual-reacceptance.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/gui/plot_gallery_service.py` (already checkpointed in `941917e`)
- `tests/test_plot_gallery_service.py` (already checkpointed in `941917e`)
- `docs/agent/tasks/2026-07-30-full-native-visual-reacceptance.md`
- `docs/acceptance/2026-07-30-full-native-visual-reacceptance.md`
- `docs/agent/memory/active-work.md`
