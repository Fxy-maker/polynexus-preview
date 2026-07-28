# NMR solid-C assignment column design

## Goal

Make dense solid-state NMR labels readable without changing the underlying
peak or assignment evidence.

## Design

The spectrum remains a single scientific plot panel. Every retained peak keeps
its vertical line and receives a short ppm-only text marker in the existing
`xdata_yaxes` coordinate mode. For every peak with an assignment, the provider
also emits one text object in an axes-relative side column at `x=1.02`, with a
deterministic descending row y coordinate. Its text is `ppm — assignment` and
contains the complete assignment string. The list is therefore visible in the
same FigureDefinition and follows the existing shared renderer, document,
Editor, Manifest, and Export paths; it is not a GUI-only overlay.

The spectrum canvas width increases from the compact single-plot width to
9.5 inches so the side column has a stable margin. The side text uses
`coordinate_space="axes"`, which is already supported by the shared renderer
and persisted as an object property. No new data source or scientific field is
introduced.

## Compatibility and boundaries

The existing peak limit and prominence ordering remain unchanged. Empty
assignments do not create a blank assignment row. Deconvolution continues to
use peak lines only, so its diagnostic plot does not acquire a duplicated list.
The existing V2 adapter treats the side text as a supported text object and
preserves its coordinate metadata.

## Testing

The provider regression will assert complete assignment text, ppm-only plot
markers, side-column coordinates, deterministic ordering, and widened layout.
Existing FigureDefinition validation, document persistence, shared renderer,
and V2 artifact tests will remain in the focused matrix. A fresh native
solid-C route will provide Results/Gallery/History/Editor/Export evidence.
