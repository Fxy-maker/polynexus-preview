# Full native visual reacceptance

Status: automated route acceptance complete; scientific and release approval
remain open.

## Evidence

- Command: `python -m pytest -q tests/test_native_gui_real_route_capture.py -vv`
- Environment: native Windows Qt, D:-isolated capture and pytest temporary
  roots.
- Result: `17 passed, 15 warnings in 443.92s (0:07:23)`, exit code `0`.
- Capture root: `D:\PolyNexus_full_native_visual_reacceptance_20260730_rerun`.

The run covered DSC standard/isothermal/non-isothermal, SAXS
static/temperature/strain, WAXS static/temperature/strain, IR
standard/temperature-2D, NMR liquid-H/liquid-C/solid-H/solid-C, synthetic
Joint, and synthetic IR mapping. Each route reached Results, Gallery, History,
Editor, and the no-Origin PackageExporter fallback.

## Inspected observations

- SAXS strain Results, Gallery, and Editor are usable. The preserved
  `generation_failed` diagnostic entry has no figure asset, so Gallery initial
  selection skips it while the diagnostic card remains visible.
- IR mapping retains its heatmap and Editor route and visibly reports
  `Review required | reason=review_missing`.
- NMR solid-C Editor peak labels are visually dense.
- Synthetic Joint displays two errors and two warnings. Its accepted fixture
  review state is fixture provenance only and is not scientific approval.

## Open human gates

This evidence does not confirm IR vendor coordinate direction/origin/ROI or
invalid-pixel semantics; NMR solid-C assignment provenance, ambiguity labels,
or Xc promotion conditions; Joint conflict precedence, minimum evidence level,
or unresolved-conflict policy; nor a final `approve`, `conditional`, or
`reject` release decision. A restarted-GUI walkthrough and final scientific
review/publication authorization remain required.
