# LegendLayout Refactor Design

## Goal

Make generated legends a single, predictable editable object. The legend that
the user sees, selects, drags, resizes, inspects, saves, and exports must use
one resolved geometry instead of separate `loc`, `bbox_to_anchor`, `box_size`,
and renderer-specific interpretations.

## Scope and non-goals

This refactor covers generated Matplotlib legends in ChartEditor, the shared
formal/legacy figure render paths, selection overlays, hit testing, geometry
controls, drag transactions, persistence, and export overlay exclusion.

It does not change static-image annotation semantics, curve data, axis
algorithms, publication profiles, or introduce a second Qt-owned legend
renderer.

## Chosen architecture

Add a pure core resolver, `polynexus/core/figures/legend_layout.py`, that
converts a legend document plus axes/renderer measurements into a
`LegendLayout` value object. The object contains:

- `mode`: `auto` or `fixed`;
- `anchor_axes`: the normalized lower-left anchor of the interaction box;
- `size_axes`: a positive normalized width/height for fixed mode, otherwise
  `None`;
- `content_bbox_display`: the measured legend content rectangle;
- `interaction_bbox_display`: the editable rectangle used for selection,
  hit-testing, and handles;
- a diagnostics/normalization flag so callers can explain compatibility
  fallbacks without mutating the document implicitly.

The resolver is the only module allowed to interpret legacy placement fields.
All consumers receive the resolved object through a small adapter/service and
must not independently recompute legend bounds.

### Coordinate and anchor rules

The canonical interaction rectangle is expressed in axes-fraction coordinates
for persistence and display coordinates for interaction. Its `anchor_axes` is
the lower-left corner. Internally the resolver converts Matplotlib's
`bbox_to_anchor` according to `loc` exactly once:

- a two-value anchor keeps the legacy point-anchor meaning;
- a four-value anchor is treated as the legacy rectangle and its lower-left
  plus width/height are used when available;
- `loc` remains honored for old automatic legends, while fixed mode normalizes
  to `loc="lower left"` with the resolved lower-left anchor.

For old documents without `box_size`, `mode="auto"` preserves the current
rendered content geometry. For documents with `box_size`, the values are
validated as positive axes fractions and become `mode="fixed"`; the current
visual position is preserved when converting old upper-left anchors.

### Compatibility and normalization

Old documents are read without rewriting. A normalized style is produced only
when the user changes geometry, explicitly saves, or the document is migrated
through an existing persistence path. Unknown style keys are retained. Invalid
or partial dimensions fall back to `auto` and expose a diagnostic rather than
silently moving the legend.

The normalized document may continue to write `loc` and `bbox_to_anchor` for
compatibility, but those fields are derived from `LegendLayout`; callers never
edit them independently. `box_size` is written only for fixed mode.

## Data flow

1. Figure document and current axes are passed to the resolver.
2. The resolver measures the actual legend content once after rendering and
   derives the interaction rectangle.
3. Formal and legacy renderers apply the same resolved anchor, dimensions,
   columns, and explicit typography.
4. `FigureRenderAdapter` receives `interaction_bbox_display` for selection,
   hover, hit testing, and transient frame/handle drawing.
5. Body/corner gestures create one style transaction. The transaction updates
   the layout through the resolver's serialization helper, then redraws and
   persists through the existing undo/save path.
6. Inspector X/Y/W/H fields read and write the same layout. Export renders the
   figure without transient interaction artists.

## Error handling

Resolver failures are non-fatal for preview: the editor keeps the measured
content box, marks the layout as compatibility-fallback, and exposes a concise
status message. Geometry edits reject non-finite or non-positive dimensions,
clamp to a documented minimum, and leave the document unchanged on failure.
No broad `except: pass` is added around user-visible operations.

## Testing and acceptance

The implementation is accepted only when focused tests prove:

1. legacy two-value and four-value anchors resolve to the same visible result
   in formal and legacy render paths;
2. auto legends preserve position, columns, and font size when selected;
3. fixed legends keep content and interaction boxes aligned;
4. body and corner drags update one undoable style transaction and survive
   save/reload;
5. inspector values round-trip through the same model;
6. log axes, multiple series, missing/invalid legacy fields, and static-image
   fallback remain safe;
7. selection frames and handles are absent from exported images.

The visual companion could not run because the local Chromium executable is
not installed; the acceptance matrix therefore relies on deterministic Qt and
renderer tests plus manual review when the GUI is available.
