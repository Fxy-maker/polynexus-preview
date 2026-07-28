---
task_id: 2026-07-29-nmr-assignment-column
kind: cross-module-display-regression
status: completed
---

# NMR solid-C assignment column

## Goal

Keep dense solid-C spectra readable by separating peak-position labels from a
complete, inspectable assignment list in the same portable figure document.

## Non-goals

- Do not change peak detection, ranking, fitting, assignment, or Xc semantics.
- Do not truncate, hide, or rewrite assignment text.
- Do not introduce a GUI-only or export-only NMR rendering path.

## Affected boundaries

- `polynexus/core/nmr_engine/figure_provider.py`: emit the assignment column
  and widen the spectrum canvas while retaining ppm peak markers.
- `tests/test_nmr_figure_provider.py`: regression for the complete list and
  plot/list separation.
- Existing shared renderer/document/Editor/Manifest/Export consumers.

## Implementation plan

1. Add a failing provider regression for a complete assignment list, ppm-only
   plot labels, and the widened spectrum canvas.
2. Implement the smallest FigureDefinition-only provider change using existing
   axes-coordinate text support.
3. Run the provider/document/renderer matrix and a current native solid-C route.
4. Record visual evidence, run the task verifier, and create an allowlisted
   checkpoint without mixing pre-existing workspace scratch.

## Acceptance criteria

- [x] The plot retains one ppm label and line for every retained peak.
- [x] Every non-empty assignment appears in a right-side axes-coordinate row
      containing its ppm and complete assignment text.
- [x] The spectrum canvas is wide enough for the assignment column in the
      shared Matplotlib, Editor, and export paths.
- [x] FigureDefinition validation, document persistence, and V2 adaptation
      remain valid.
- [x] Focused tests, native solid-C route, task verifier, and diff checks pass.
- [x] Scientific assignment and final release approval remain separate gates.

## Verification

```powershell
python -m pytest -q tests/test_nmr_figure_provider.py tests/test_nmr_figure_document.py tests/test_figure_render_plan_core.py
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='D:\PolyNexus_native_nmr_assignment_column_20260729'
python -m pytest -q tests/test_native_gui_real_route_capture.py -k nmr.solid_c -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-29-nmr-assignment-column.md --changed --types
```

## Known limitations

The assignment column improves display readability but does not validate the
scientific correctness of vendor assignments or close human release review.
