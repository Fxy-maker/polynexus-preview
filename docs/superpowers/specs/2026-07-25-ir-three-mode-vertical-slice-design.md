# IR Three-Mode Vertical Slice Design

## Goal

Converge IR standard, temperature-2D, and mapping/ROI figure definitions on a
single explicit publication-role contract without changing scientific input
semantics.

## Design

The existing IR provider remains the only place that assigns figure roles.
Standard spectra use Main only for the first emitted frame and SI for later
frames; peak-fit figures are SI; computed-vs-experimental comparisons are
diagnostic; the crystallinity series is Main. Temperature-2D heatmap is Main,
band tracking and band indices are SI, and synchronous/asynchronous 2D-COS
figures are diagnostic. Mapping keeps its established Main map, SI ROI spectra,
and diagnostic invalid-pixel map.

This role assignment is conservative: a diagnostic or assignment-limited view
cannot become a publication conclusion merely because it rendered. Existing
`FigurePipeline` behavior already converts per-definition exceptions into
`generation_failed` entries while preserving sibling entries, so the slice
locks that behavior with a regression rather than adding a second error path.

## Data flow

```text
IR analysis result
  -> IR figure provider (role + provenance)
  -> FigurePipeline (document/data/assets/Manifest)
  -> manifest-backed Gallery -> Editor/export -> History
```

The mapping branch accepts only `IRMappingResult`; it validates geometry,
mask, ROI spectra, and `provenance.source_id` before emitting definitions.

## Testing

Tests assert role matrices, definition validity, mask/provenance preservation,
and sibling-safe generation failure. Synthetic tests prove contract behavior;
real readers, external fixtures, and restarted-GUI review remain explicit
follow-up acceptance items.

## Scope review

No new public cross-layer interface is introduced. No reader format or band
interpretation is guessed. All behavior changes are covered by focused tests.
