# Origin-style generated text labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make generated chart text compact Origin-style labels whose selected bounds follow their rendered glyphs and whose corner drags resize the font rather than a persisted box.

**Architecture:** Keep the existing document fields and Axes-relative coordinate contract, but make rendered `Text` extents the sole source for text selection overlays.  A text-corner transaction records its initial display-space extent, previews an adjusted `Text` font/position without mutating the document, then commits exactly one `UpdateStyleCommand` containing `font_size`.  All other generated-object geometry paths retain their current contracts.

**Tech Stack:** Python 3, PySide6, Matplotlib, pytest, existing `EditSession` command history.

---

## File structure

- Modify `polynexus/core/figures/renderer.py`: render Axes-relative generated text as unwrapped labels while preserving legacy text-box compatibility.
- Modify `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`: give the in-editor generated renderer the same label rendering rule as export.
- Modify `polynexus/gui/figure_render_adapter.py`: derive text selection frames and handle offsets from padded rendered display extents.
- Modify `polynexus/gui/widgets/chart_editor_generated_hit_testing_mixin.py`: hit display-space text handle offsets correctly while preserving the rendered-glyph body hit path.
- Modify `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`: calculate and preview display-space font-size scaling for text handles.
- Modify `polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py` and `polynexus/gui/widgets/chart_editor_generated_drag_mixin.py`: pass pixel pointer positions into text scaling and commit one style command.
- Modify `polynexus/gui/widgets/chart_editor_generated_preview_mixin.py`: preview font-size changes and refresh rendered text overlays without geometry resizing.
- Modify `polynexus/gui/widgets/chart_editor_inline_text_mixin.py`: use a fixed single-line editor height and a width based on the rendered label/input content.
- Modify `tests/test_chart_editor_workflow.py` and `tests/test_chart_editor_curve.py`: cover tight extents, movement, font scaling, undo/redo, one-line editing, and overlay-free export.
- Modify `docs/agent/tasks/2026-07-22-origin-label-text.md` and `docs/agent/memory/active-work.md`: record scope, evidence, and the completed checkpoint.

### Task 1: Write selection and rendering regression tests

**Files:**
- Modify: `tests/test_chart_editor_curve.py:86-174`
- Modify: `tests/test_chart_editor_workflow.py:693-1053,1143-1185`

- [ ] **Step 1: Add a failing test proving Axes-relative text ignores legacy box area**

```python
def test_generated_axes_text_label_is_not_wrapped_or_clipped_by_legacy_box():
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "label-with-legacy-box",
        "type": "text",
        "coordinate_space": "axes",
        "bounds": {"x": 0.2, "y": 0.3, "width": 0.04, "height": 0.02},
        "text": "A label that exceeds its former box",
        "style": {"font_size": 14.0},
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    assert artist.get_wrap() is False
    assert artist.get_clip_on() is False
```

- [ ] **Step 2: Add a failing test for a tight rendered selection frame and handles**

```python
def test_generated_text_selection_overlays_follow_rendered_extent_not_saved_box(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {
        "id": "tight-label",
        "type": "text",
        "coordinate_space": "axes",
        "bounds": {"x": 0.2, "y": 0.3, "width": 0.7, "height": 0.5},
        "text": "Peak",
        "style": {"font_size": 12.0},
    }
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")
    editor._canvas.draw()
    artist = editor._figure_render_adapter.artists_for_object_id(payload["id"])[0]
    text_bbox = artist.get_window_extent(editor._canvas.get_renderer())
    frame = next(patch for patch in editor._figure.axes[0].patches
                 if patch.get_gid() == "pn-selection-frame:tight-label")
    frame_bbox = frame.get_window_extent(editor._canvas.get_renderer())
    assert frame_bbox.width < 100.0
    assert frame_bbox.width == pytest.approx(text_bbox.width, abs=12.0)
    assert frame_bbox.height == pytest.approx(text_bbox.height, abs=12.0)
```

- [ ] **Step 3: Add a failing end-to-end corner-drag test that expects a style-only transaction**

```python
def test_generated_text_corner_drag_scales_font_and_undo_redo(tmp_path, app):
    editor = make_generated_editor(tmp_path)
    payload = {"id": "scalable-label", "type": "text", "coordinate_space": "axes",
               "bounds": {"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.2},
               "text": "Peak", "style": {"font_size": 12.0}}
    editor._execute_edit(AddObjectCommand(payload))
    editor._show_generated_figure_document()
    editor._select_generated_object(payload["id"], "list")
    editor._canvas.draw()
    handle = editor._generated_selection_handle_artist(payload["id"])
    corner = handle.get_offsets()[2]
    press = MouseEvent("button_press_event", editor._canvas, *corner, button=1)
    press.inaxes = editor._figure.axes[0]
    editor._on_generated_button_press(press)
    editor._on_generated_mouse_move(MouseEvent("motion_notify_event", editor._canvas,
                                                corner[0] + 36.0, corner[1] + 24.0, button=1))
    editor._on_generated_button_release(MouseEvent("button_release_event", editor._canvas,
                                                   corner[0] + 36.0, corner[1] + 24.0, button=1))
    saved = editor._generated_figure_object_by_id(payload["id"])
    assert saved["style"]["font_size"] > 12.0
    assert saved["width"] == pytest.approx(payload["bounds"]["width"])
    assert saved["height"] == pytest.approx(payload["bounds"]["height"])
    editor._on_annotation_undo()
    assert editor._generated_figure_object_by_id(payload["id"])["style"]["font_size"] == 12.0
    editor._on_annotation_redo()
    assert editor._generated_figure_object_by_id(payload["id"])["style"]["font_size"] == saved["style"]["font_size"]
```

- [ ] **Step 4: Add a failing double-click geometry assertion and text-export selection assertion**

```python
assert editor._inline_text_editor.height() == 24
assert editor._inline_text_editor.y() == expected_top

editor._select_generated_object("tight-label", "list")
editor._save_generated_document_figure(target)
assert not any(gid.startswith("pn-selection-") for gid in exported_gids)
```

- [ ] **Step 5: Run the new tests and confirm they fail for the intended legacy behavior**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py -q
```

Expected: the old persisted-box selection and geometry-resize assertions fail; unaffected existing tests stay green.

### Task 2: Render generated Axes text as labels

**Files:**
- Modify: `polynexus/core/figures/renderer.py:392-438`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py:680-724`
- Test: `tests/test_chart_editor_curve.py:86-174`

- [ ] **Step 1: Add a label-only rendering predicate in both renderer paths**

Use the existing coordinate marker rather than a new serialized field:

```python
is_label = is_axes_text_box(figure_object)
text_kwargs = {} if is_label else (
    {"wrap": True, "clip_on": True} if has_box else {}
)
```

Keep `text_box_anchor(...)` for positioning so existing `x`, `y`, alignment, and legacy size payloads remain readable; only remove box-driven wrapping/clipping for marked Axes text.

- [ ] **Step 2: Run the rendering test**

Run:

```powershell
python -m pytest tests/test_chart_editor_curve.py -q
```

Expected: PASS, including the new unwrapped/unclipped label assertion.

- [ ] **Step 3: Commit the rendering slice**

```powershell
python scripts/auto_commit.py --message "feat(editor): render generated text as labels" --files polynexus/core/figures/renderer.py polynexus/gui/widgets/chart_editor_generated_document_mixin.py tests/test_chart_editor_curve.py
```

Expected: one local checkpoint commit; no push.

### Task 3: Derive text overlays from the rendered display extent

**Files:**
- Modify: `polynexus/gui/figure_render_adapter.py:1-345`
- Modify: `polynexus/gui/widgets/chart_editor_generated_hit_testing_mixin.py:358-385`
- Test: `tests/test_chart_editor_workflow.py:1010-1053`

- [ ] **Step 1: Implement one padded display-bounds helper in `FigureRenderAdapter`**

```python
from matplotlib.transforms import IdentityTransform

TEXT_SELECTION_PADDING_PX = 4.0

def rendered_text_selection_bbox(self, object_id: str, *, padding_px=TEXT_SELECTION_PADDING_PX):
    artist = next((item for item in self.artists_for_object_id(object_id)
                   if hasattr(item, "get_window_extent")), None)
    renderer = self._renderer_for_artist(artist)
    if artist is None or renderer is None:
        return None
    bbox = artist.get_window_extent(renderer).padded(float(padding_px))
    if not all(math.isfinite(float(value)) for value in (bbox.x0, bbox.y0, bbox.x1, bbox.y1)):
        return None
    return bbox
```

Extract the existing canvas/Agg renderer lookup from `_artist_selection_frame()` into `_renderer_for_artist()` so it has one fallback path.

- [ ] **Step 2: Use the helper for text selection frame and corners**

For `object_type == "text"`, create the frame and `PathCollection` in display coordinates:

```python
bbox = self.rendered_text_selection_bbox(object_id)
frame = Rectangle((bbox.x0, bbox.y0), bbox.width, bbox.height,
                  fill=False, edgecolor="#0072B2", linestyle="--", linewidth=1.5,
                  zorder=10_000, transform=IdentityTransform(), clip_on=False)
points = [(bbox.x0, bbox.y0), (bbox.x1, bbox.y0), (bbox.x1, bbox.y1), (bbox.x0, bbox.y1)]
handles = ax.scatter(*zip(*points), transform=IdentityTransform(), clip_on=False,
                     s=64, facecolors="#FFFFFF", edgecolors="#D55E00", linewidths=2.0,
                     zorder=10_000)
```

Leave rectangle, line, curve, legend, and plot-series overlay paths unchanged.

- [ ] **Step 3: Make text-handle hit testing respect the display transform**

```python
if str(figure_object.get("type", "") or "") == "text":
    pixel_offsets = offsets
else:
    transform = axes.transAxes if is_axes_text_box(figure_object) else axes.transData
    pixel_offsets = transform.transform(offsets)
```

- [ ] **Step 4: Run selection and handle tests**

Run:

```powershell
python -m pytest tests/test_chart_editor_workflow.py -q
```

Expected: PASS for the new tight-frame test and existing non-text selection tests.

- [ ] **Step 5: Commit the overlay slice**

```powershell
python scripts/auto_commit.py --message "feat(editor): fit text selection to labels" --files polynexus/gui/figure_render_adapter.py polynexus/gui/widgets/chart_editor_generated_hit_testing_mixin.py tests/test_chart_editor_workflow.py
```

Expected: one local checkpoint commit; no push.

### Task 4: Preview and commit font-size scaling for text corners

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py:118-132`
- Modify: `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py:247-307`
- Modify: `polynexus/gui/widgets/chart_editor_generated_preview_mixin.py:249-465`
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_mixin.py:75-192`
- Test: `tests/test_chart_editor_workflow.py:1010-1053`

- [ ] **Step 1: Change the text-drag call to pass display pixels**

```python
elif drag_kind == "text":
    changed = self._apply_generated_text_handle_drag(
        object_id,
        int(drag_state.get("handle_index", 0) or 0),
        float(getattr(event, "x", 0.0) or 0.0),
        float(getattr(event, "y", 0.0) or 0.0),
    )
```

- [ ] **Step 2: Capture the original rendered extent and calculate a clamped scale**

On first preview, store `original_text_bbox`, `opposite_corner`, and
`original_font_size` in the active drag state.  Use the handle/opposite
diagonal lengths, so all four handles use the same rule:

```python
old_distance = math.dist(original_corner, opposite_corner)
new_distance = max(1.0, math.dist((event_x, event_y), opposite_corner))
font_size = min(96.0, max(6.0, original_font_size * new_distance / max(1.0, old_distance)))
```

Store `{"font_size": round(font_size, 3)}` as `preview_style`, never modify
`x`, `y`, `width`, or `height` for a text-handle path.

- [ ] **Step 3: Preview font and transient opposite-corner anchoring**

Extend `_update_generated_drag_preview()` to accept `style_updates=None`.
For a text preview, call `artist.set_fontsize(style_updates["font_size"])`,
draw the canvas, measure the new extent, and translate the preview artist by
the display delta from the measured opposite corner to the recorded
`opposite_corner`.  Then refresh the selection frame and handles via
`FigureRenderAdapter` display bounds.  Do not write preview position/style
into `_figure_document` or `EditSession`.

- [ ] **Step 4: Commit exactly one `UpdateStyleCommand` for a text handle**

Before the generic geometry branch in `_commit_generated_drag()`, add:

```python
if drag_kind == "text":
    preview_style = drag_state.get("preview_style")
    font_size = preview_style.get("font_size") if isinstance(preview_style, dict) else None
    if session is None or font_size is None:
        return False
    result = self._execute_edit(UpdateStyleCommand(object_id, {"font_size": float(font_size)}))
    if result is None or not result.changed:
        return False
    self._sync_generated_object_property_controls(object_id)
    self._show_generated_figure_document()
    self._clear_generated_drag_preview()
    self._generated_viewport_snapshot = None
    return True
```

Keep generic `UpdateGeometryCommand` handling for text body drags by treating
`drag_kind == "body"` with `object_type == "text"` as its existing movement
transaction.  Remove `"text"` from the generic corner `geometry_keys` map.

- [ ] **Step 5: Run the scaling and history tests**

Run:

```powershell
python -m pytest tests/test_chart_editor_workflow.py -q
```

Expected: PASS; the former persisted-box-resize test is replaced with the
style-only font scaling, undo, and redo assertions.

- [ ] **Step 6: Commit the interaction slice**

```powershell
python scripts/auto_commit.py --message "feat(editor): scale text labels by font size" --files polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py polynexus/gui/widgets/chart_editor_generated_preview_mixin.py polynexus/gui/widgets/chart_editor_generated_drag_mixin.py tests/test_chart_editor_workflow.py
```

Expected: one local checkpoint commit; no push.

### Task 5: Keep inline label editing compact and document completion

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_inline_text_mixin.py:38-56`
- Modify: `tests/test_chart_editor_workflow.py:693-732`
- Modify: `docs/agent/tasks/2026-07-22-origin-label-text.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Make the shared editor a one-line control**

```python
font_height = self._inline_text_editor.fontMetrics().height()
height = max(24, font_height + 8)
content_width = self._inline_text_editor.fontMetrics().horizontalAdvance(
    str(payload.get("initial_text", "") or "")
)
width = max(96, min(max(geometry.width(), content_width + 24), host.width()))
self._inline_text_editor.setGeometry(top_left.x(), top_left.y(), width, height)
```

The `top_left` continues to come from the rendered text extent in
`_begin_generated_text_edit()`, so double click starts at the label's top edge.

- [ ] **Step 2: Run the double-click and export tests**

Run:

```powershell
python -m pytest tests/test_chart_editor_workflow.py -q
```

Expected: PASS for compact double-click input, Enter commit, Escape cancel,
and export that temporarily removes all selection frame and handle artists.

- [ ] **Step 3: Record evidence and task completion**

Mark every task-card criterion complete.  Add a dated `active-work.md` entry
that lists the task card, focused test count, both verifier commands, and the
known limitation that a running GUI must be restarted for manual inspection.

- [ ] **Step 4: Run final verification**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py tests/test_figure_text_geometry.py tests/test_figure_render_plan_core.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-22-origin-label-text.md --changed --types
python scripts/verify.py --changed --types
```

Expected: all commands exit 0.  Report the exact pass counts and any existing
Matplotlib warnings without calling warnings a test failure.

- [ ] **Step 5: Create the final local checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(editor): use Origin-style text labels" --files polynexus/gui/widgets/chart_editor_inline_text_mixin.py tests/test_chart_editor_workflow.py docs/agent/tasks/2026-07-22-origin-label-text.md docs/agent/memory/active-work.md
```

Expected: one local checkpoint commit; no push, merge, deployment, or cleanup.

## Plan self-review

- Spec coverage: Task 2 removes persistent box wrapping/clipping; Task 3 makes the selected frame and corners follow glyph metrics; Task 4 preserves body movement while turning corner drag into a one-command `font_size` edit with display-space opposite-corner preview; Task 5 keeps double click/Enter/Escape compact and checks exports.  `coordinate_space: "axes"`, legacy width/height readability, inspector font value, and undo/redo remain on existing contracts and are asserted by the focused matrix.
- Placeholder scan: this plan contains no unfilled markers, vague testing instructions, or unnamed code paths.  Every implementation step names a file, method boundary, concrete data shape, and command.
- Type consistency: `preview_style` is a `dict` containing `font_size`; it is produced in Task 4, consumed by `_update_generated_drag_preview()` and `_commit_generated_drag()`, and committed through the existing `UpdateStyleCommand`.  Display-space `Bbox` offsets and `IdentityTransform` are used together in Task 3 and Task 4.
