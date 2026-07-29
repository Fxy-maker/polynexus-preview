# SAXS partial detector V2 binding design

## Decision

Static and temperature detector Figures are diagnostic-only outputs whose
finite detector pixels are already materialized as sparse heatmap rows.  Bind
only these two Figure recipes to the existing V2 adapters: `saxs_static` for
static and `temperature_saxs` for temperature series.

## Data and safety boundary

`figure_detector._downsample_detector()` retains only finite source pixels and
records sampled, retained, and non-finite counts in Figure provenance.  The
V2 adapter consumes the same retained x/y/log-intensity rows.  The V2 layout
creates rectangles only for those rows, so absent source pixels remain absent
in the reactive scene and publication asset.  This task must not synthesize
coordinates, intensities, frames, quality labels, or scientific conclusions.

## Runtime flow

```text
detector Figure definition (explicit V2 adapter)
  -> FigurePipeline capability/sidecar
  -> ReactiveFigureProjectService.load
  -> LayoutResolver sparse heatmap rectangles
  -> ReactiveFigureProjectService.publish
```

If an adapter or scene cannot be built, the existing capability layer remains
fail-closed and returns a static fallback.  The recipe binding itself is the
only implementation change.

## Verification

One parametrized regression builds a mixed finite/non-finite 2x2 detector
image in both modes.  It proves the Manifest is V2-ready, the sidecar exists,
the loaded scene has three finite rectangles, reactive publication emits a
non-empty asset, and original diagnostic/provenance fields are preserved.
