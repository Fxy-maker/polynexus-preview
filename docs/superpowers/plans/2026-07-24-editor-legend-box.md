# Editor Legend Box Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep selected legends visually stable and allow body/handle editing as persistent, undoable boxes.

**Architecture:** `style.box_size` is the single persisted axes-fraction layout contract.  The presentation policy turns it into column constraints; the ChartEditor uses transient display-space overlays and the existing style-command transaction to update it.

**Tech Stack:** Python 3, PySide6, Matplotlib, pytest.

---

### Task 1: Make stored legend typography and box width render-authoritative

**Files:**
- Modify: `polynexus/core/figures/legend_presentation.py`
- Modify: `polynexus/core/figures/renderer.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`
- Test: `tests/test_figure_render_plan_core.py`

- [x] **Step 1: Write failing policy tests**

```python
presentation = legend_presentation(
    {"style": {"font_size": 15.0, "box_size": [0.34, 0.18]}},
    handle_count=5, available_width_px=1_200, labels=("long label",) * 5,
    default_fontsize=9.0,
)
assert presentation.fontsize == 15.0
assert presentation.ncol == 1
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_figure_render_plan_core.py -k legend_box -q`

Expected: FAIL because `box_size` is ignored.

- [x] **Step 3: Implement the pure policy**

```python
box_size = _positive_box_size(style.get("box_size"))
if box_size is not None:
    available_width_px = min(available_width_px, box_size[0] * panel_width_px)
```

Use the stored positive explicit font size without generic editor overrides.

- [x] **Step 4: Verify GREEN and commit**

Run: `python -m pytest tests/test_figure_render_plan_core.py -k "legend_box or legend" -q`

Commit: `fix(editor): honor persistent legend box layout`

### Task 2: Draw a non-exported legend selection box and handles

**Files:**
- Modify: `polynexus/gui/figure_render_adapter.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`
- Test: `tests/test_chart_editor.py`

- [x] **Step 1: Write a failing selected-legend overlay test**

```python
editor._object_list.setCurrentRow(legend_row)
assert _artist_by_gid(editor, "pn-selection-frame:legend") is not None
assert _artist_by_gid(editor, "pn-selection-handles:legend") is not None
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_chart_editor.py -k selected_legend_frame -q`

Expected: FAIL because adapter only frames text, rectangles, lines, and series.

- [x] **Step 3: Add display-space legend overlays**

```python
bbox = legend.get_window_extent(renderer)
frame = Rectangle((bbox.x0, bbox.y0), bbox.width, bbox.height,
                  transform=IdentityTransform(), fill=False, clip_on=False)
```

Create four display-space corner handle points with the normal selection GIDs;
do not register them as legend artists or include them in exports.

- [x] **Step 4: Verify GREEN and commit**

Run: `python -m pytest tests/test_chart_editor.py -k "selected_legend_frame or legend" -q`

Commit: `feat(editor): show legend resize handles`

### Task 3: Route legend corner drags through one style transaction

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_generated_press_target_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py`
- Test: `tests/test_chart_editor.py`

- [x] **Step 1: Write failing drag/undo tests**

```python
drag_corner(editor, "legend", corner="lower_right", delta=(80, -30))
assert legend_style(editor)["box_size"][0] > original_width
editor._on_annotation_undo()
assert "box_size" not in legend_style(editor)
```

- [x] **Step 2: Verify RED**

Run: `python -m pytest tests/test_chart_editor.py -k legend_resize -q`

Expected: FAIL because legends only create `kind="legend"` body drags.

- [x] **Step 3: Implement the minimal drag contract**

```python
if handle_hit is not None:
    return {"object_id": object_id, "kind": "legend-resize",
            "handle_index": handle_hit, "dirty": False}
```

Convert display pixels to `axes.transAxes`, clamp both dimensions to a
positive minimum, preview with the existing temporary drag state, and commit
`{"loc": "upper left", "bbox_to_anchor": anchor, "box_size": size}` using
one `UpdateStyleCommand`.

- [x] **Step 4: Verify GREEN and commit**

Run: `python -m pytest tests/test_chart_editor.py -k "legend_resize or legend_drag" -q`

Commit: `feat(editor): resize legends from canvas handles`

### Task 4: Complete integration verification and durable record

**Files:**
- Modify: `docs/agent/tasks/2026-07-24-editor-legend-box.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the focused matrix**

Run: `python -m pytest tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py -q`

- [x] **Step 2: Run structured verification**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-07-24-editor-legend-box.md --changed --types`

- [x] **Step 3: Record results and commit**

Commit: `docs(editor): record legend box verification`
