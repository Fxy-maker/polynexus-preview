# Legend Object Geometry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make generated legends one Origin-like editable object whose rendered content and interaction geometry cannot diverge.

**Architecture:** Add a pure `LegendGeometry` model that imports legacy style fields once, stores normalized axes geometry for persistence, and exposes measured display geometry for a live artist. Route both shared and legacy renderers through one legend render/measure boundary; route selection, hit testing, drag, resize, undo, status, and export through the same geometry snapshot.

**Tech Stack:** Python 3.12, Matplotlib, PySide6, pytest, existing figure document/edit-command contracts.

---

## Task 1: Core geometry model and migration boundary

**Files:**
- Create: `polynexus/core/figures/legend_geometry.py`
- Modify: `polynexus/core/figures/legend_layout.py`
- Test: `tests/test_legend_geometry.py`
- Modify: `tests/test_legend_layout.py`

- [ ] **Step 1: Write failing core tests**

  Add tests for importing `legend_geometry`, two-value upper anchors, four-value
  anchors, invalid values, axes/display conversion, opposite-corner resize,
  monotonic font scaling, and serialization that emits only the new geometry
  plus font/column presentation.

- [ ] **Step 2: Run the focused tests and verify the expected failures**

  Run:

  ```powershell
  python -m pytest tests/test_legend_geometry.py tests/test_legend_layout.py -q
  ```

  Expected: collection fails for the missing `legend_geometry` module or the
  new model methods, while existing legacy-layout tests remain runnable.

- [ ] **Step 3: Implement the pure model**

  Implement immutable geometry data and pure helpers:

  ```python
  @dataclass(frozen=True)
  class LegendGeometry:
      panel_id: str
      rect_axes: tuple[float, float, float, float]
      rect_display: Bbox | None
      font_size: float
      ncol: int
  ```

  Add `import_style`, `measure`, `move`, `resize`, and `serialize` helpers.
  Import legacy `loc` semantics once, validate finite positive dimensions, and
  give `legend_geometry` precedence when both formats exist. Keep
  `resolve_legend_layout` as a compatibility wrapper for non-editor callers,
  but route new editor-facing code through the new model.

- [ ] **Step 4: Run the focused tests and refactor only after green**

  Run:

  ```powershell
  python -m pytest tests/test_legend_geometry.py tests/test_legend_layout.py -q
  ```

  Expected: all new and existing core legend tests pass.

- [ ] **Step 5: Commit the core checkpoint**

  ```powershell
  python scripts/auto_commit.py --message "refactor(legend): add canonical geometry model" --files polynexus/core/figures/legend_geometry.py polynexus/core/figures/legend_layout.py tests/test_legend_geometry.py tests/test_legend_layout.py
  ```

## Task 2: Shared renderer and display-space adapter

**Files:**
- Modify: `polynexus/core/figures/renderer.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`
- Modify: `polynexus/gui/figure_render_adapter.py`
- Test: `tests/test_figure_render_plan_core.py`
- Test: `tests/test_chart_editor.py`

- [ ] **Step 1: Add failing renderer/adapter alignment tests**

  Build a generated multi-series legend with a deliberately disjoint legacy
  anchor. Assert after rendering that the adapter's selection bounds equal the
  live legend's `get_window_extent(renderer)` and that all four handles equal
  the frame corners.

- [ ] **Step 2: Run the alignment tests and verify they fail on the old split path**

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  python -m pytest tests/test_figure_render_plan_core.py::test_renderer_legend_geometry_round_trip tests/test_chart_editor.py::test_chart_editor_generated_legend_selection_frame_matches_rendered_bounds -q
  ```

  Expected: the new tests fail because renderer and adapter currently resolve
  separate rectangles.

- [ ] **Step 3: Introduce one legend render/measure boundary**

  Make both the shared renderer and legacy generated renderer consume
  `LegendGeometry`, apply font/column presentation, draw, and then measure the
  actual legend artist. Register the measured display rectangle in
  `FigureRenderAdapter`; make `legend_selection_bbox` and legend handles return
  that registered rectangle rather than resolving persisted box fields.

- [ ] **Step 4: Run renderer and editor alignment tests**

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_object_renderer'
  python -m pytest tests/test_figure_render_plan_core.py tests/test_chart_editor.py -q
  ```

  Expected: the alignment regression passes and the existing renderer/editor
  matrix remains green.

- [ ] **Step 5: Commit the renderer checkpoint**

  ```powershell
  python scripts/auto_commit.py --message "refactor(legend): unify render and display geometry" --files polynexus/core/figures/renderer.py polynexus/gui/widgets/chart_editor_generated_document_mixin.py polynexus/gui/figure_render_adapter.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py
  ```

## Task 3: Generated editor interaction transaction

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_preview_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_press_target_mixin.py`
- Test: `tests/test_chart_editor.py`

- [ ] **Step 1: Add failing interaction tests**

  Add tests that select a legend whose content and legacy box are disjoint,
  assert the frame and handles are on the content, drag the body and verify
  content/frame move together, drag each corner and verify preview font changes
  before release, and verify one undo/redo restores geometry and typography.

- [ ] **Step 2: Run the interaction tests and verify the old behavior fails**

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_object_interaction'
  python -m pytest tests/test_chart_editor.py -k "legend and geometry" -q
  ```

  Expected: at least the disjoint-frame and preview-scaling assertions fail on
  the split implementation.

- [ ] **Step 3: Replace direct legacy-field reads in interaction code**

  Capture a `LegendGeometry` snapshot at press time. Route body movement,
  corner resize, preview redraw, handle updates, and release through the core
  geometry service. Keep body moves font-neutral; keep corner resizes
  opposite-corner anchored and font-scaled. Store the full before/after state in
  one `UpdateStyleCommand` or equivalent replacement transaction.

- [ ] **Step 4: Run the focused interaction matrix**

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_object_interaction_green'
  python -m pytest tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py tests/test_chart_editor_status_service.py -q
  ```

  Expected: all legend, drag, undo, helper, and status tests pass.

- [ ] **Step 5: Commit the interaction checkpoint**

  ```powershell
  python scripts/auto_commit.py --message "refactor(legend): drive editor interactions from geometry" --files polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py polynexus/gui/widgets/chart_editor_generated_preview_mixin.py polynexus/gui/widgets/chart_editor_generated_drag_mixin.py polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py polynexus/gui/widgets/chart_editor_generated_press_target_mixin.py tests/test_chart_editor.py
  ```

## Task 4: Persistence, status, and export migration

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_generated_selection_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_status_service.py`
- Modify: `polynexus/core/figure_edit_commands.py`
- Modify: `polynexus/core/figure_object_store.py`
- Modify: `polynexus/gui/widgets/chart_editor_save_mixin.py`
- Test: `tests/test_chart_editor_status_service.py`
- Test: `tests/test_chart_editor.py`

- [ ] **Step 1: Add failing persistence/migration tests**

  Verify legacy styles import into `legend_geometry`, new saves omit the legacy
  keys, invalid geometry produces a diagnostic, and undo/redo survives reload.

- [ ] **Step 2: Run the migration tests and verify the expected failures**

  ```powershell
  python -m pytest tests/test_chart_editor_status_service.py tests/test_chart_editor.py -k "legend and (save or status or undo)" -q
  ```

- [ ] **Step 3: Centralize import/serialization and update status/export paths**

  Make the document/store boundary normalize legacy input once, write the new
  schema on save, show status from `LegendGeometry`, and clear selection
  overlays before generated export. Remove direct legacy-field reads from
  status and edit-command code.

- [ ] **Step 4: Run migration, export, and static fallback tests**

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_object_migration'
  python -m pytest tests/test_chart_editor.py tests/test_chart_editor_status_service.py tests/test_figure_render_plan_core.py -q
  ```

- [ ] **Step 5: Commit the migration checkpoint**

  ```powershell
  python scripts/auto_commit.py --message "feat(legend): persist canonical geometry" --files polynexus/gui/widgets/chart_editor_generated_selection_mixin.py polynexus/gui/widgets/chart_editor_status_service.py polynexus/core/figure_edit_commands.py polynexus/core/figure_object_store.py polynexus/gui/widgets/chart_editor_save_mixin.py tests/test_chart_editor_status_service.py tests/test_chart_editor.py
  ```

## Task 5: Full verification and durable evidence

**Files:**
- Modify: `docs/agent/tasks/2026-07-24-legend-object-geometry.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [ ] **Step 1: Run the complete focused legend/editor matrix**

  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_object_full'
  python -m pytest tests/test_legend_geometry.py tests/test_legend_layout.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py tests/test_chart_editor_status_service.py -q
  ```

  Expected: all focused tests pass with no new failures.

- [ ] **Step 2: Run structured and default verification**

  ```powershell
  $env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_object_verify'
  python scripts/verify.py --task docs/agent/tasks/2026-07-24-legend-object-geometry.md --changed --types
  python scripts/verify.py --changed --types
  ```

  Expected: task check, memory check, Ruff, compile, quality gate, preprocessing
  gate, whitespace, and type baseline checks pass.

- [ ] **Step 3: Update evidence and commit the final checkpoint**

  Record exact test counts, the remaining manual GUI walkthrough requirement,
  and intentionally untouched untracked files in the task card and memory.

  ```powershell
  python scripts/auto_commit.py --message "refactor(legend): complete unified object geometry" --files docs/agent/tasks/2026-07-24-legend-object-geometry.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
  ```
