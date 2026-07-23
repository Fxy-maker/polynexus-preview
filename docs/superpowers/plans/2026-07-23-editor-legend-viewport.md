# Editor Legend Viewport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent long formal-preview legends from collapsing the plot area and make their font size an undoable, export-safe property.

**Architecture:** The shared renderer receives optional live-preview viewport context only from ChartEditor; normal exports retain the FigureRenderPlan canvas. The shared legend policy uses the available width, visible labels, and the requested/default font size to select a safe column count before layout. Legend `style.font_size` uses the existing style command and capability pipeline.

**Tech Stack:** Python 3, PySide6, Matplotlib, pytest.

---

### Task 1: Make formal legend policy viewport- and label-aware

**Files:**
- Modify: `polynexus/core/figures/legend_presentation.py`
- Modify: `polynexus/core/figures/renderer.py:35-170`
- Modify: `tests/test_figure_render_plan_core.py`

- [ ] **Step 1: Write failing policy and formal renderer tests**

```python
presentation = legend_presentation(
    automatic_legend,
    handle_count=5,
    available_width_px=780,
    labels=("PA6-250-170-S_0_00000",) * 5,
    default_fontsize=9.0,
)
assert presentation.ncol == 1

editor_figure = renderer.render(plan, dpi=150, viewport_width_px=780)
assert editor_figure.axes[0].get_legend()._ncols == 1
assert renderer.render(plan, dpi=150).axes[0].get_legend()._ncols == 2
```

- [ ] **Step 2: Run the new test and verify it fails**

Run: `python -m pytest tests/test_figure_render_plan_core.py -k "viewport or long_name" -q`

Expected: FAIL because `render()` has no viewport parameter and the policy does not accept labels.

- [ ] **Step 3: Extend the pure policy without mutating the document**

```python
def legend_presentation(..., labels=()):
    font_size = explicit_font_size(style, default_fontsize)
    estimated_entry_width = max(
        72.0,
        max((len(label) for label in labels), default=1) * font_size * 0.78 + 54.0,
    )
    maximum_columns = max(1, int(available_width_px * 0.42 // estimated_entry_width))
    ncol = min(requested_columns, maximum_columns)
```

Use an explicit `style.font_size` unchanged. Compact scaling applies only when
no explicit font size is stored. Keep `loc` and `bbox_to_anchor` out of the
policy result.

- [ ] **Step 4: Pass optional preview width from the renderer boundary**

```python
def render(self, plan, *, dpi, viewport_width_px=None):
    panel_width = viewport_width_px or plan.width_in * dpi
    presentation = legend_presentation(
        legend_object,
        handle_count=len(handles),
        labels=tuple(str(label) for label in labels),
        available_width_px=panel_width * panel.column_span / plan.columns,
        default_fontsize=9.0,
    )
```

Preserve the existing public call sites by making the parameter keyword-only
and optional.

- [ ] **Step 5: Run focused renderer tests**

Run: `python -m pytest tests/test_figure_render_plan_core.py -k "legend" -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
python scripts/auto_commit.py --message "fix(editor): adapt formal legends to viewport width" --files polynexus/core/figures/legend_presentation.py polynexus/core/figures/renderer.py tests/test_figure_render_plan_core.py
```

### Task 2: Supply live canvas context through formal ChartEditor preview

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py:72-105`
- Modify: `tests/test_chart_editor_generated_document_mixin.py`
- Modify: `tests/test_manifest_editor_shared_plan.py`

- [ ] **Step 1: Write a failing manifest-editor viewport regression**

```python
editor._canvas.resize(780, 620)
editor.set_source_figure_entry(entry_with_five_long_series)
legend = editor._figure.axes[0].get_legend()
assert legend._ncols == 1
assert editor._figure.axes[0].get_position().width > 0.42
```

- [ ] **Step 2: Run the regression and verify it fails**

Run: `python -m pytest tests/test_manifest_editor_shared_plan.py -k long_series -q`

Expected: FAIL because the formal renderer only sees publication-plan width.

- [ ] **Step 3: Forward the actual drawable width before renderer creation**

```python
canvas = getattr(self, "_canvas", None)
viewport_width = float(canvas.width()) if canvas is not None else None
figure = renderer.render(
    plan,
    dpi=self._dpi,
    viewport_width_px=viewport_width,
)
```

Do not alter the post-replacement canvas fit, document canvas size, or export
caller behavior.

- [ ] **Step 4: Run the manifest and legacy renderer regressions**

Run: `python -m pytest tests/test_manifest_editor_shared_plan.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor.py -k "legend or manifest" -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
python scripts/auto_commit.py --message "fix(editor): use live viewport for formal legend preview" --files polynexus/gui/widgets/chart_editor_generated_document_mixin.py tests/test_chart_editor_generated_document_mixin.py tests/test_manifest_editor_shared_plan.py
```

### Task 3: Make legend font size editable and persistent

**Files:**
- Modify: `polynexus/core/figure_edit_capabilities.py:169-170`
- Modify: `polynexus/core/figures/legend_presentation.py`
- Modify: `tests/test_figure_edit_capabilities.py`
- Modify: `tests/test_chart_editor.py`

- [ ] **Step 1: Write failing legend capability/style regressions**

```python
assert capabilities_for({"type": "legend"}).font_size is True
editor._select_generated_object("legend", "list")
assert editor._annotation_font_size_spin.isEnabled()
editor._annotation_font_size_spin.setValue(15)
editor._apply_style_to_selected_generated_object()
assert editor._generated_figure_object_by_id("legend")["style"]["font_size"] == 15.0
editor._on_annotation_undo()
assert "font_size" not in editor._generated_figure_object_by_id("legend")["style"]
```

- [ ] **Step 2: Run the regressions and verify they fail**

Run: `python -m pytest tests/test_figure_edit_capabilities.py tests/test_chart_editor.py -k legend_font_size -q`

Expected: FAIL because legend capability disables the control and policy ignores `style.font_size`.

- [ ] **Step 3: Enable the existing style path and honor the stored size**

```python
elif object_type == "legend":
    base.update(style=True, text=True, font_size=True, geometry=True, deletable=True, reorderable=True)
```

Resolve `style["font_size"]` only when it is a finite positive number;
otherwise fall back to the policy default. Do not enable irrelevant color,
line, marker, or alpha controls for legends.

- [ ] **Step 4: Run focused edit, undo, preview, and export tests**

Run: `python -m pytest tests/test_figure_edit_capabilities.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py -k "legend and font_size" -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
python scripts/auto_commit.py --message "feat(editor): support editable legend font size" --files polynexus/core/figure_edit_capabilities.py polynexus/core/figures/legend_presentation.py tests/test_figure_edit_capabilities.py tests/test_chart_editor.py
```

### Task 4: Verify and record the task

**Files:**
- Create: `docs/agent/tasks/2026-07-23-editor-legend-viewport.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the complete focused matrix**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_figure_edit_capabilities.py tests/test_figure_object_store.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_manifest_editor_shared_plan.py -q
```

- [ ] **Step 2: Run structured and default verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-23-editor-legend-viewport.md --changed --types
python scripts/verify.py --changed --types
```

- [ ] **Step 3: Commit durable evidence**

```powershell
python scripts/auto_commit.py --message "docs(editor): record viewport-safe legend verification" --files docs/agent/tasks/2026-07-23-editor-legend-viewport.md docs/agent/memory/active-work.md
```
