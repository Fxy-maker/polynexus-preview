# Editor Interaction Reliability Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with the repository
> `AGENTS.md` contract. Keep the explicit changed-file allowlist for the final
> checkpoint.

**Goal:** Stabilize direct canvas editing for annotations and generated objects,
without changing scientific or export semantics.

**Architecture:** Keep annotation state authoritative in the existing canvas
and edit-session contracts. Fix coordinate conversion and transaction timing at
their source, and make the context bar a non-layout-affecting surface.

**Tech Stack:** Python, PySide6, pytest, repository verifier.

---

### Task 1: Establish failing interaction regressions

**Files:**
- Modify: `tests/test_annotation_canvas.py`
- Modify: `tests/test_chart_editor_curve.py`
- Modify: `tests/test_chart_editor_context_style_mixin.py`
- Modify: `tests/test_chart_editor_workflow.py`

- [x] Add one test for each observable failure: text/rectangle movement and
  handles, line endpoint independence, large curve bend, context-bar geometry
  stability, one undo command per drag, and selection zoom invariance.
- [x] Run only the new tests and confirm they fail for behavior reasons rather
  than collection or fixture errors.

### Task 2: Stabilize annotation scene geometry

**Files:**
- Modify: `polynexus/gui/widgets/annotation_canvas.py`
- Modify: `tests/test_annotation_canvas.py`

- [x] Trace `_scene_point_from_event`, scene rebuild/sync, selection handles,
  and `_finish_mouse_draw` for each annotation type.
- [x] Preserve explicit `x/y/width/height` geometry for text and rectangles,
  and ensure selection/movement writes back in the same normalized coordinate
  space used for rendering.
- [x] Keep line endpoints independent during movement and resize; do not infer a
  vertical line from a single pointer coordinate.
- [x] Make curve defaults distance-aware and keep `control_x/control_y`
  independently editable over the full usable normalized canvas range.
- [x] Ensure selecting or dragging never calls `fit_to_window`, changes zoom,
  or replaces the active view transform.
- [x] Run the annotation-focused tests and confirm the new tests pass.

### Task 3: Make context controls layout-stable

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_context_style_mixin.py`
- Modify: `tests/test_chart_editor_context_style_mixin.py`

- [x] Reserve the context-bar footprint once or place it in an overlay while
  keeping the canvas stack geometry fixed.
- [x] Keep controls enabled/disabled and populated from selection state without
  changing the canvas's available height when visibility changes.
- [x] Verify the context-bar regression before and after the implementation.

### Task 4: Repair edit transaction and undo/redo routing

**Files:**
- Modify: `polynexus/gui/widgets/annotation_canvas.py`
- Modify: `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_edit_session_mixin.py`
- Modify: `tests/test_chart_editor_curve.py`
- Modify: `tests/test_chart_editor_workflow.py`

- [x] Identify duplicate history pushes and the handoff between canvas change
  signals and `EditSession` commands.
- [x] Make a completed drag produce one command, clear redo only after a real
  mutation, and route toolbar/keyboard undo and redo through the active history
  owner.
- [x] Verify undo and redo restore exact pre/post geometry and do not trigger an
  extra fit or selection reset.

### Task 5: Full verification and checkpoint

**Files:**
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] Run focused interaction tests and inspect the complete output.
- [x] Run `python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-interaction-reliability.md --changed --types`.
- [x] Run `python scripts/verify.py --changed --types`.
- [x] Review `git diff` and preserve all pre-existing untracked files.
- [x] Create one checkpoint with `scripts/auto_commit.py` using the explicit
  changed-file allowlist.
