# NMR solid-C peak label lanes design

## Goal

Improve dense solid-state NMR peak-label readability through the existing
portable figure contract, without changing scientific interpretation.

## Design

`_peak_objects()` continues to rank and retain at most the existing sixteen
most prominent peaks. For each retained peak it emits the same vertical peak
line and a text object containing the complete formatted ppm value and
assignment. The text object uses `coordinate_space="xdata_yaxes"`; its x value
is the ppm data coordinate and its y value is one of five deterministic axes
lanes (`0.96`, `0.84`, `0.72`, `0.60`, `0.48`) selected cyclically in ranked
order. The existing 90-degree rotation and styling remain unchanged.

The shared Matplotlib renderer recognizes this coordinate mode with
`axis.get_xaxis_transform()`, which is the blended transform for data-space x
and axes-space y. Existing `coordinate_space="axes"` text and unannotated text
continue to use their current paths. Figure documents, V2 graph properties,
Editor identity, Manifest persistence, and Export therefore keep consuming the
same object without a second NMR-only rendering path.

## Boundaries and error handling

The coordinate mode is a display contract only. It is preserved as an opaque
object field by the existing document normalization and V2 adapter. Invalid or
missing coordinates retain the renderer's existing numeric fallback behavior;
no peak data is fabricated. Assignment text is never truncated by this change.

## Testing

1. Provider regression proves full assignment preservation and deterministic
   lane coordinates for more than one lane cycle.
2. Renderer regression proves the mixed transform is used and the x/y values
   remain the intended data/axes coordinates.
3. Existing NMR provider validation and shared renderer regressions prove that
   legacy text and all existing FigureDefinition consumers remain compatible.
