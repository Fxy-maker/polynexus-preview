# LegendLayout Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development when explicitly selected) to implement this plan task-by-task. Every task ends with focused tests and an allowlisted checkpoint commit.

**Goal:** Replace split legend geometry calculations with one backwards-compatible `LegendLayout` resolver consumed by rendering, selection, interaction, persistence, and export.

**Architecture:** Add a pure resolver/value model under `polynexus/core/figures/legend_layout.py`. It parses legacy `loc`/`bbox_to_anchor`/`box_size` once, derives display and axes-fraction boxes, and serializes only normalized style updates. Renderers and ChartEditor adapters call the resolver instead of reading placement fields directly; transient overlays remain outside the figure document.

**Tech Stack:** Python 3.12+, dataclasses, Matplotlib transforms/Bbox, PySide6 ChartEditor, pytest, repository verifier.

---

### Task 1: Add the pure layout model and compatibility resolver

**Files:**
- Create: `polynexus/core/figures/legend_layout.py`
- Create: `tests/test_legend_layout.py`
- Modify: `polynexus/core/figures/__init__.py` only if public exports are used by existing figure modules

- [ ] **Step 1: Write failing resolver tests**

Add tests covering: no style produces `mode="auto"`; a valid two-value upper-left legacy anchor plus `box_size` produces fixed mode; a four-value anchor preserves its lower-left and size; invalid/non-finite dimensions fall back to auto with a diagnostic; and serialization emits derived `loc`, `bbox_to_anchor`, and `box_size` without deleting unknown style keys.

- [ ] **Step 2: Run the resolver tests and verify the expected failure**

Run `python -m pytest tests/test_legend_layout.py -q` with `QT_QPA_PLATFORM=offscreen` omitted because the tests are pure. Expected result: collection/import failure because `legend_layout` does not exist.

- [ ] **Step 3: Implement the minimal pure dataclasses and functions**

Implement frozen `LegendLayout` plus `resolve_legend_layout(style, *, axes=None, content_bbox_display=None, renderer=None)` and `legend_style_updates(layout, original_style)`. Keep all numeric validation local, use lower-left axes fractions for canonical persistence, and return a diagnostic string for malformed legacy input. Do not import Qt or ChartEditor modules.

- [ ] **Step 4: Run focused tests and then the existing presentation tests**

Run `python -m pytest tests/test_legend_layout.py tests/test_figure_render_plan_core.py -q`. Expected result: all new compatibility assertions and the existing automatic-column/font-size tests pass.

- [ ] **Step 5: Commit the atomic core slice**

Run `python scripts/auto_commit.py --message "feat(legend): add unified layout resolver" --files polynexus/core/figures/legend_layout.py tests/test_legend_layout.py`.

### Task 2: Make formal and legacy rendering consume the resolver

**Files:**
- Modify: `polynexus/core/figures/renderer.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`
- Modify: `polynexus/core/figures/legend_presentation.py` if its API needs a resolved fixed width
- Test: `tests/test_figure_render_plan_core.py`

- [ ] **Step 1: Add renderer parity tests before changing production code**

Add tests that render the same object document through the core renderer and generated ChartEditor path, then assert equivalent anchor and positive fixed geometry for two-value and four-value legacy styles. Add a regression asserting explicit font size and column choice are unchanged before and after resolving layout.

- [ ] **Step 2: Run the new parity tests and verify they fail**

Run `python -m pytest tests/test_figure_render_plan_core.py -q`. Expected result: the new parity assertion fails because the two paths still parse legacy fields independently.

- [ ] **Step 3: Route both render paths through the resolver**

In `renderer.py` and `_apply_generated_document_axes_style`, resolve the legend style once, use its canonical anchor/size to build `bbox_to_anchor`, and pass the same fixed width into presentation column calculation. Preserve auto mode behavior and existing visibility rules.

- [ ] **Step 4: Run renderer regression tests**

Run `python -m pytest tests/test_legend_layout.py tests/test_figure_render_plan_core.py -q`. Expected result: new parity tests and all existing renderer tests pass.

- [ ] **Step 5: Commit the rendering slice**

Run `python scripts/auto_commit.py --message "refactor(legend): unify formal and editor rendering" --files polynexus/core/figures/renderer.py polynexus/gui/widgets/chart_editor_generated_document_mixin.py polynexus/core/figures/legend_presentation.py tests/test_figure_render_plan_core.py`.

### Task 3: Unify selection bounds, hit testing, and handles

**Files:**
- Modify: `polynexus/gui/figure_render_adapter.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_hit_testing_mixin.py` only where direct legend extents remain
- Test: `tests/test_chart_editor.py`
- Test: `tests/test_chart_editor_generated_object_helpers.py`

- [ ] **Step 1: Add a regression for one interaction rectangle**

Create a generated legend with a persisted fixed box whose content is smaller than the box. Assert that the adapter selection frame, four handles, hover hit test, and geometry helper all return the same display/axes rectangle and never fall back to a separate stale rectangle.

- [ ] **Step 2: Run the interaction regression and observe the failure**

Run `python -m pytest tests/test_chart_editor.py::test_chart_editor_generated_legend_uses_persisted_box_bounds tests/test_chart_editor_generated_object_helpers.py -q`. Expected result: the new equality assertion fails while the existing compatibility tests remain informative.

- [ ] **Step 3: Use the resolver from adapter and geometry helpers**

Replace direct `bbox_to_anchor`/`box_size` parsing in `legend_selection_bbox`, `_generated_legend_anchor_for_drag`, and `_generated_legend_box_geometry` with one resolved layout. Use `interaction_bbox_display` for frame/handles and its axes counterpart for drag math. Preserve the measured content box only as the auto-mode interaction box.

- [ ] **Step 4: Run focused ChartEditor geometry tests**

Run `python -m pytest tests/test_chart_editor.py -q` with `$env:QT_QPA_PLATFORM='offscreen'` and `$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_refactor'`. Expected result: the full ChartEditor suite passes.

- [ ] **Step 5: Commit the selection slice**

Run `python scripts/auto_commit.py --message "refactor(legend): share interaction geometry" --files polynexus/gui/figure_render_adapter.py polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py polynexus/gui/widgets/chart_editor_generated_hit_testing_mixin.py tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py`.

### Task 4: Route drag, inspector, undo, and persistence through normalized layout

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`
- Test: `tests/test_chart_editor.py`

- [ ] **Step 1: Add transaction and round-trip tests**

Add tests proving body drag and corner resize each create one undoable style command, update the same canonical anchor/size values shown in X/Y/W/H, restore the original layout on Escape, and survive save/reload without a visual jump.

- [ ] **Step 2: Run the transaction tests and verify the pre-refactor failure**

Run the new test node ids with the offscreen environment and dedicated basetemp. Expected result: at least one assertion fails because preview and committed style still construct independent dictionaries.

- [ ] **Step 3: Serialize updates through the resolver**

Make preview and commit use `legend_style_updates(resolved_layout, original_style)` plus only the changed anchor/size. Keep `UpdateStyleCommand` as the sole undo boundary. Ensure inspector edits call the same helper and do not rewrite auto legends until a user edit occurs.

- [ ] **Step 4: Run drag/undo/persistence tests**

Run `python -m pytest tests/test_chart_editor.py -q` with the offscreen and basetemp settings. Expected result: all existing and new legend transaction tests pass.

- [ ] **Step 5: Commit the interaction transaction slice**

Run `python scripts/auto_commit.py --message "refactor(legend): normalize drag and inspector updates" --files polynexus/gui/widgets/chart_editor_generated_drag_mixin.py polynexus/gui/widgets/chart_editor_generated_drag_execution_mixin.py polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py tests/test_chart_editor.py`.

### Task 5: Verify export, static fallback, diagnostics, and full matrix

**Files:**
- Modify: `polynexus/gui/chart_editor_status_service.py` for resolver diagnostics in user-visible status
- Modify: `polynexus/gui/widgets/chart_editor_render_mixin.py` only if export overlay handling needs the shared bounds
- Test: `tests/test_chart_editor.py`
- Test: `tests/test_figure_render_plan_core.py`
- Update: `docs/agent/memory/current-state.md`
- Update: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Add export/static/error regression tests**

Assert selection frame/handles are absent from a saved export, static-image documents remain read-only for legend layout, malformed legacy styles produce a concise diagnostic and still render the measured legend, and log-axis multi-series documents keep their legend geometry.

- [ ] **Step 2: Run focused matrix and repair ordinary failures**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_refactor'
python -m pytest tests/test_legend_layout.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py -q
```

- [ ] **Step 3: Run structured and default verification**

Run `python scripts/verify.py --task docs/agent/tasks/2026-07-24-legend-layout-refactor.md --changed --types` followed by `python scripts/verify.py --changed --types`. Record exact pass counts and any pre-existing warnings in the task card and memory.

- [ ] **Step 4: Commit evidence and durable memory**

Run `python scripts/auto_commit.py --message "test(legend): verify unified layout compatibility" --files polynexus/gui/chart_editor_status_service.py polynexus/gui/widgets/chart_editor_render_mixin.py tests/test_chart_editor.py tests/test_figure_render_plan_core.py docs/agent/memory/current-state.md docs/agent/memory/active-work.md`.

## Plan self-review

- Every design requirement maps to Tasks 1–5: resolver/compatibility, renderer parity, one interaction rectangle, normalized transactions, and export/static/error verification.
- No task introduces a second renderer or changes static annotation semantics.
- Each production change is preceded by a focused failing test and each task ends with an explicit allowlisted checkpoint commit.
- The only known environment limitation is unavailable Chromium for the optional visual companion; deterministic Qt/Matplotlib tests remain the source of verification.
