# Legend Object Geometry Design

## Goal

Make generated legends behave as one Origin-like editable object: the visible
legend, selection frame, handles, hit testing, drag preview, resize preview,
undo/redo, and export must all use the same geometry.

## Problem statement

The current editor still has several runtime interpretations of a legend's
placement. Matplotlib renders from `loc` and `bbox_to_anchor`, while editor
selection and resize logic can use `box_size` and a separately resolved axes
rectangle. These interpretations can diverge: the legend content can appear in
one place while the selection frame and handles appear elsewhere. Resizing the
frame can also change the box without continuously scaling the content.

The problem is architectural rather than a missing conditional in one drag
handler. The editor needs one object geometry contract and one render/measure
boundary.

## Non-goals

- Replace Matplotlib as the publication/export plotting backend.
- Change static-image annotation behavior.
- Add new legend styling controls beyond geometry, font size, and existing
  column presentation.
- Change scientific data, axis scales, or multi-panel figure semantics.

## Design principles

1. **One runtime geometry.** The editor owns one `LegendGeometry` per legend.
   No interaction path reads `loc`, `bbox_to_anchor`, or `box_size` directly.
2. **Display space for interaction.** Selection, handles, hit testing, and
   drag transactions use the measured display-space rectangle of the live
   legend artist.
3. **Axes space for persistence.** Persisted geometry is normalized to the
   owning panel's axes so it survives canvas and DPI changes.
4. **Compatibility at one boundary.** Existing fields are parsed only by a
   centralized importer. They are not an active runtime contract.
5. **One transaction.** A resize or move commits one command containing the
   complete before/after legend state.

## Runtime model

The core model is a small, renderer-neutral value object:

```text
LegendGeometry
├─ panel_id
├─ rect_display: (x, y, width, height)
├─ rect_axes: (x, y, width, height)
├─ font_size
└─ ncol
```

`rect_display` is authoritative while a figure is live. It is measured from
the actual Matplotlib legend after the figure has been drawn. `rect_axes` is the
normalized equivalent used for persistence and re-rendering. The two are
related through the current panel's `transAxes` transform; no other coordinate
conversion is allowed in editor event handlers.

The geometry service exposes these operations:

- `import_style(style, axes, legend_artist) -> LegendGeometry`
- `measure(legend_artist, renderer) -> rect_display`
- `move(geometry, dx_display, dy_display) -> LegendGeometry`
- `resize(geometry, handle, target_display_point) -> LegendGeometry`
- `serialize(geometry, original_style) -> style`

The service owns minimum sizes, finite-value validation, corner anchoring, and
font-size clamping. It does not know about Qt widgets or undo sessions.

## Persisted schema

Newly saved generated legend styles use one explicit geometry object:

```json
{
  "type": "legend",
  "panel_id": "main",
  "style": {
    "legend_geometry": {
      "space": "axes",
      "x": 0.62,
      "y": 0.78,
      "width": 0.24,
      "height": 0.12
    },
    "font_size": 9.0,
    "ncol": 2
  }
}
```

`space="axes"` is explicit to prevent display pixels from being mistaken for
persisted coordinates. The importer accepts the current `loc`,
`bbox_to_anchor`, and `box_size` combinations and produces this geometry once.
New runtime code reads `legend_geometry`; it never reinterprets the legacy
fields. During migration, existing documents remain readable and are rewritten
to the new schema on the next successful save.

## Rendering boundary

The shared renderer and legacy editor renderer use one legend-render helper.
The helper consumes `LegendGeometry`, applies the normalized anchor and current
font/column presentation to Matplotlib, draws the figure, and measures the
resulting artist. The measured display rectangle is then registered with the
`FigureRenderAdapter` as the only interaction rectangle.

If Matplotlib's padding or column layout changes the measured extent, the
geometry service updates the live display rectangle; selection and handles use
that result rather than guessing from the input anchor. The renderer remains
responsible for line/text appearance and export; the editor remains responsible
for object geometry.

## Interaction flow

### Selection and hit testing

- Selection frame and four handles are generated from the measured display
  rectangle.
- Legend hit testing checks the same rectangle, with the existing pick slop.
- Selecting from the object list redraws the figure before creating overlays,
  so overlays bind to the current artist and transform.

### Body move

- Press captures the pointer offset from `rect_display`.
- Motion creates a preview geometry through the service.
- The shared legend renderer applies the preview, measures the new artist, and
  updates the frame and handles.
- Release commits one complete style/object command.

### Corner resize

- Press captures the opposite corner, starting display rectangle, font size,
  and column presentation.
- Motion computes a target rectangle with minimum dimensions and derives a
  continuous content scale from the target/start dimensions.
- The preview renderer applies font size and geometry in one pass, then
  remeasures the live legend. Handles are refreshed from the measured result.
- Release commits geometry, font size, and presentation together. Body drags do
  not alter font size.

### Undo, redo, and cancel

- A drag session produces at most one history command.
- Escape restores the complete captured state and redraws once.
- Undo and redo restore the serialized geometry and visual typography together.

## Migration and error handling

- Invalid or non-finite legacy fields produce a concise diagnostic and fall back
  to automatic placement without crashing the editor.
- Documents with `legend_geometry` take precedence over legacy fields.
- A successful save writes the new geometry schema. Legacy keys are not used by
  runtime rendering after import.
- If the current legend artist cannot be measured, selection is disabled for
  that legend and the status service reports the reason instead of creating a
  guessed frame.

## Testing strategy

### Core geometry tests

- Import two-value upper anchors and four-value rectangles into the same
  normalized geometry.
- Reject non-finite and non-positive dimensions with diagnostics.
- Verify move and four-corner resize preserve the opposite corner.
- Verify font scaling is monotonic, clamped, and independent of body moves.
- Verify serialization emits only `legend_geometry`, `font_size`, and existing
  presentation fields.

### Renderer/editor tests

- Assert the selection frame bounds equal the live legend window extent within
  renderer tolerance after selection.
- Assert handles equal the four frame corners.
- Exercise move and resize preview before release, then verify the live legend
  and frame move together.
- Verify one undo/redo restores position, size, font, and columns.
- Cover multi-series, single-series suppression, log axes, legacy documents,
  and static fallback.
- Verify generated exports contain no selection frame or handles.

### Verification commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_object'
python -m pytest tests/test_legend_layout.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py tests/test_chart_editor_status_service.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-24-legend-object-geometry.md --changed --types
python scripts/verify.py --changed --types
```

## Acceptance criteria

- The visible legend and selection frame never diverge after opening, selecting,
  moving, resizing, undoing, or redoing.
- Corner resize visibly scales legend content during pointer movement.
- New saves use `legend_geometry`; legacy fields are confined to the importer.
- Existing generated, multi-series, log-axis, static fallback, and export tests
  remain green.
- The task has a focused regression test for the original screenshot failure,
  not only for persisted style values.
