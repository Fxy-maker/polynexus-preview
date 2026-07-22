# Viewport-Anchored Text Box Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move generated editable text boxes to one Axes-relative geometry contract so their screen position, hit region, preview, and persisted state remain stable across linear, logarithmic, reversed, and zoomed axes.

**Architecture:** Keep the existing edit-session and `UpdateGeometryCommand` history authority, but represent new/edited generated text with `coordinate_space: "axes"` and normalized `x`, `y`, `width`, and `height`. A shared geometry helper converts the box to display pixels through `axes.transAxes`; renderer, preview, hit testing, handles, Inspector, and save all consume that conversion. Legacy data-coordinate text remains readable and is converted lazily at the editor boundary without rewriting on open.

**Tech Stack:** Python 3.14, PySide6, Matplotlib, pytest, existing `Box` geometry records, `FigureObjectStore`, `FigureDocument`, and `ChartEditor` mixins.

---

### Task 1: Add the canonical Axes-relative text-box contract

**Files:**
- Modify: `polynexus/gui/widgets/editor_geometry.py`
- Modify: `polynexus/core/figure_objects.py`
- Modify: `polynexus/core/figure_document.py`
- Create: `tests/test_figure_text_geometry.py` (extend existing tests)
- Modify: `tests/test_figure_document.py`

- [x] Add `Box` helpers for clamping normalized Axes coordinates, converting a display-space rectangle through `axes.transAxes`, and identifying an object as an Axes text box without changing the public `Box` constructor.
- [x] Normalize new text objects with `coordinate_space: "axes"` and retain the existing `bounds` mirror for compatibility. Do not add the marker to legacy objects merely because they were loaded.
- [x] Add focused tests for normalized geometry, reversed/oversized boxes, and round-trip preservation through `save_figure_document` / `load_figure_document`.
- [x] Run the new core/document tests and confirm the baseline remains green before GUI changes.

### Task 2: Render and preview text from one Axes transform

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_preview_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`
- Modify: `tests/test_chart_editor_curve.py`
- Modify: `tests/test_chart_editor_workflow.py`

- [x] Make the generated renderer use `axes.transAxes` for marked text boxes and preserve the existing data-coordinate path for legacy text.
- [x] Ensure the shared text anchor helper receives the same normalized box used by the renderer; selection frames and transient drag artists must not mutate a `Text` artist independently of the preview geometry.
- [x] Update preview replacement and figure redraw paths so changing axis scale/limits leaves an Axes text box at the same display rectangle.
- [x] Add regression tests for log-axis move up/down, zoom/pan/reverse redraw stability, and preview-vs-committed artist positions.

### Task 3: Separate text-body hits from corner-handle hits

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_generated_hit_testing_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_press_target_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_interaction_adapter.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`
- Modify: `tests/test_chart_editor_generated_interaction_adapter.py`
- Modify: `tests/test_chart_editor_workflow.py`

- [x] Convert the persisted Axes box to display pixels before hit testing; prioritize the text artist/content region, then allow corner handles only outside that region.
- [x] Return distinct `body` and `text-handle` hit targets while preserving line, curve, rectangle, legend, and plot-series target contracts.
- [x] Calculate body translation in display/Axes space so movement is independent of data transforms; calculate corner resize against the opposite corner and clamp to the Axes rectangle.
- [x] Add tests proving downward log-axis movement works, content wins over the top-left handle, and all four corners resize the expected normalized box.

### Task 4: Commit one undoable viewport transaction and preserve editor controls

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_status_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_save_mixin.py`
- Modify: `tests/test_chart_editor_workflow.py`
- Modify: `tests/test_chart_editor_save_mixin.py`

- [x] Start body and handle transactions from the same Axes-box snapshot and keep document/history unchanged during preview.
- [x] On release, submit exactly one `UpdateGeometryCommand` containing the complete normalized box; Escape restores the snapshot without history; undo/redo restores the same box and visible frame.
- [x] Hydrate and submit Inspector geometry fields through the same Axes-relative contract, and mark legacy objects as Axes-relative only after edit/save.
- [x] Add tests for preview, commit, cancel, undo, redo, reload, Inspector edits, and export behavior.

### Task 5: Verify, document, and hand off the atomic checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-22-viewport-text-box-refactor.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] Run:

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
  python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py tests/test_figure_text_geometry.py tests/test_figure_document.py -q
  python scripts/verify.py --task docs/agent/tasks/2026-07-22-viewport-text-box-refactor.md --changed --types
  python scripts/verify.py --changed --types
  git diff --check
  ```

- [x] Record exact pass counts and any known limitations in the task card and durable memory; leave unrelated untracked drafts and local diagnostics untouched.
- [ ] Review the cumulative diff, then create the local checkpoint with `scripts/auto_commit.py` and an explicit changed-file allowlist. Do not push, merge, deploy, or delete data.
