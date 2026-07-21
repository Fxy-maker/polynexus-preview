# Unified canvas interaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make text, rectangle, line, arrow, and curve feel like one canvas tool in both generated and static editor modes: the drag boundary is the persisted geometry, the viewport never jumps, body/handle drags use one transaction, and undo removes the whole gesture.

**Architecture:** Add a small renderer-neutral geometry module for box/segment/curve normalization and translation. Generated Matplotlib and static Qt adapters keep their existing renderers, but consume the same normalized geometry for previews, selection bounds, and commits. `EditorInteractionController` remains the gesture state authority and `EditSession` remains the history authority.

**Tech Stack:** Python 3.12+, PySide6, Matplotlib, existing `FigureRenderAdapter`, `AnnotationCanvas`, `EditSession`, pytest with offscreen Qt.

---

### Task 1: Add the shared geometry contract

**Files:**

- Create: `polynexus/gui/widgets/editor_geometry.py`
- Test: `tests/test_editor_geometry.py`

- [x] **Step 1: Write the failing tests.**

```python
from polynexus.gui.widgets.editor_geometry import Box, Curve, Segment


def test_box_normalizes_reversed_drag_and_preserves_size():
    box = Box.from_drag((8, 24), (2, 10))
    assert box == Box(2.0, 10.0, 6.0, 14.0)


def test_segment_translation_moves_both_endpoints():
    assert Segment(1, 2, 5, 7).translated(3, -1) == Segment(4, 1, 8, 6)


def test_curve_translation_moves_control_point_too():
    curve = Curve(1, 2, 4, 8, 7, 3)
    assert curve.translated(2, -2) == Curve(3, 0, 6, 6, 9, 1)


def test_payload_helpers_accept_legacy_top_level_and_nested_geometry():
    assert Box.from_payload({"bounds": {"x": 1, "y": 2, "width": 3, "height": 4}}).width == 3
    assert Segment.from_payload({"x1": 1, "y1": 2, "x2": 3, "y2": 4}).x2 == 3
```

- [x] **Step 2: Run the focused tests and confirm the API is missing.**

Run: `python -m pytest tests/test_editor_geometry.py -q --basetemp D:\\PolyNexus\\.pytest_tmp_alt`

Expected: collection fails with `ModuleNotFoundError` for `editor_geometry`.

- [x] **Step 3: Implement only the immutable geometry records and payload adapters.**

Use frozen dataclasses `Box(x, y, width, height)`, `Segment(x1, y1, x2, y2)`, and `Curve(x1, y1, control_x, control_y, x2, y2)`. `Box.from_drag()` must normalize direction and clamp a zero-size drag to `MIN_SIZE = 1e-9`; `from_payload()` must read `geometry`, `bounds`, then top-level fields. `translated()` must return a new record and never mutate the source.

- [x] **Step 4: Run the tests and commit this atomic contract.**

Run: `python -m pytest tests/test_editor_geometry.py -q --basetemp D:\\PolyNexus\\.pytest_tmp_alt`

Expected: all tests pass.

Commit with: `python scripts/auto_commit.py --message "feat(editor): add shared interaction geometry" --files polynexus/gui/widgets/editor_geometry.py tests/test_editor_geometry.py`

### Task 2: Make generated text and rectangle use the same dragged box

**Files:**

- Modify: `polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_hit_testing_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_preview_mixin.py`
- Modify: `polynexus/gui/figure_render_adapter.py`
- Test: `tests/test_chart_editor_workflow.py`
- Test: `tests/test_figure_render_adapter.py`

- [x] **Step 1: Add failing regression tests.**

Cover three user-visible contracts: a generated text drag stores the exact `Box` used for the inline editor; moving a text object updates its preview frame and persisted `width/height` without changing them; and a rectangle body drag moves the box while a corner drag resizes it. Assert x/y limits and figure size before and after each gesture are identical.

- [x] **Step 2: Run only the new tests and record the expected failure.**

Run: `python -m pytest tests/test_chart_editor_workflow.py -q -k 'exact_text_box or text_body_drag_preserves_box or rectangle_body_drag_preserves_size' --basetemp D:\\PolyNexus\\.pytest_tmp_alt`

Expected: the tests fail because generated text preview updates only `Text.set_position()` and the inline geometry is not retained as a shared box.

- [x] **Step 3: Route generated creation through `Box`.**

Create one `Box` in `_finish_generated_draw()`, store its `x/y/width/height` in the pending payload, and use the same box for `_generated_canvas_rect()` and `_commit_generated_text_payload()`. For a click, use the renderer-neutral minimum box and keep the viewport snapshot until commit/cancel finishes.

- [x] **Step 4: Route generated body preview through geometry records.**

In `_apply_generated_body_drag()`, translate a `Box` for text/rectangle, a `Segment` for lines, and a `Curve` for curves. In `_update_generated_drag_preview()`, update text selection frame and handles from the preview geometry; update rectangle artist and frame from the same box. Never call document redraw/autoscale during motion; restore the captured viewport after a preview draw.

- [x] **Step 5: Run the focused workflow and adapter tests.**

Run: `python -m pytest tests/test_chart_editor_workflow.py tests/test_figure_render_adapter.py -q --basetemp D:\\PolyNexus\\.pytest_tmp_alt`

Expected: the new regressions and existing generated editor tests pass.

### Task 3: Normalize static canvas creation and body transactions

**Files:**

- Modify: `polynexus/gui/widgets/annotation_canvas.py`
- Test: `tests/test_annotation_canvas.py`

- [x] **Step 1: Add failing static parity tests.**

Send real Qt drag events for text, rectangle, line, and curve. Assert the preview bounds equal the committed bounds, text remains a box after commit, reversed drags produce positive width/height, and one body drag adds exactly one undo entry.

- [x] **Step 2: Run the tests and verify the current mismatch.**

Run: `python -m pytest tests/test_annotation_canvas.py -q -k 'parity or reversed_drag or one_undo' --basetemp D:\\PolyNexus\\.pytest_tmp_alt`

Expected: at least the text parity case fails if the scene item's implicit text height differs from the requested box.

- [x] **Step 3: Use shared records at the static adapter boundary.**

Convert `_finish_mouse_draw()`, `_selection_handle_points()`, and body-drag updates to `Box`, `Segment`, and `Curve` before converting to image pixels. Preserve normalized document fields and existing document-mode signals. Use the same `Box` for the text `QGraphicsTextItem` text width, selection frame, and resize handles.

- [x] **Step 4: Verify static undo/export behavior.**

Run: `python -m pytest tests/test_annotation_canvas.py -q --basetemp D:\\PolyNexus\\.pytest_tmp_alt`

Expected: all static canvas tests pass and transient frames/previews remain absent from `render_to_image()`.

### Task 4: Cross-mode verification and durable handoff

**Files:**

- Modify: `docs/agent/tasks/2026-07-21-unified-canvas-interaction.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the focused cross-mode matrix.**

Run: `python -m pytest tests/test_editor_geometry.py tests/test_editor_interaction_controller.py tests/test_chart_editor_workflow.py tests/test_annotation_canvas.py tests/test_figure_render_adapter.py -q --basetemp D:\\PolyNexus\\.pytest_tmp_alt`

- [x] **Step 2: Run the structured and default verifiers.**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-07-21-unified-canvas-interaction.md --changed --types` and `python scripts/verify.py --changed --types`.

- [x] **Step 3: Record exact evidence, known limitations, and the pre-existing `.pytest_tmp` lock.**

Mark acceptance items only after fresh commands pass. Do not add `.superpowers/`, `.pytest_tmp_worktree_clean.txt`, or other existing drafts to the checkpoint.

- [x] **Step 4: Create the explicit checkpoint.**

Run `python scripts/auto_commit.py --message "feat(editor): unify canvas object interactions" --files docs/agent/tasks/2026-07-21-unified-canvas-interaction.md docs/agent/memory/active-work.md` after all production/test files have already been committed atomically.
