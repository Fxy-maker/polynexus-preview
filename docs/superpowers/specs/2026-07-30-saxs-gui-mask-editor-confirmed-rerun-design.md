# SAXS GUI Mask Editor Confirmed Rerun Design

## Goal

Expose a small, fail-closed static SAXS 2D detector-mask editor that turns
explicit pixel edits into the existing confirmed mask candidate and starts one
normal engine rerun only after the user confirms the candidate.

## Scope

The core preprocessing contract will expose a detached boolean
`mask_edit_base_mask` alongside the existing raw image. The GUI will use that
base mask and image to render a review dialog with left-click mask and
right-click unmask behavior, reset/cancel controls, a changed-pixel count, and
an explicit confirm-and-rerun action. The confirmed candidate is passed through
the existing `AnalysisWorker` keyword and `SAXSEngine` static-image boundary.

The action is available only when the current result is SAXS static, the input
is a single 2D image, and image/base-mask shapes agree. The dialog emits a
detached confirmed candidate; it never mutates the result image, engine state,
or configured mask.

## Safety contract

- The base mask is produced by the core preprocessing path, not reconstructed
  in a GUI event handler.
- Cancel, close, invalid shapes, and zero-change edits produce no candidate and
  no rerun.
- Candidate confirmation reuses `confirm_mask_edit_candidate()` and therefore
  preserves shape/digest/coordinate validation.
- Only the existing static 2D rerun route is used. Directory, temperature,
  strain, 1D, plot-only, AI, interpolation, morphology, and automatic rescue
  are outside this slice.
- Existing detector quality, data-quality, physical, and publication gates
  remain final authority after the rerun.

## Data flow

```text
SAXS preprocess
  -> raw_data[img, mask_edit_base_mask]
  -> Workbench action availability check
  -> editor preview (detached edited mask)
  -> explicit confirm
  -> validated confirmed candidate
  -> AnalysisWorker(mask_edit_candidate=...)
  -> SAXSEngine static 2D rerun
  -> existing quality/physical/publication gates
```

## Verification

Focused tests cover base-mask transport, editor availability and no-op routes,
mouse edits/reset/confirm, and MainWindow-to-Worker candidate forwarding. The
task verifier and complete current SAXS matrix are required before an explicit
allowlist checkpoint. Test storage remains report/dry-run only.
