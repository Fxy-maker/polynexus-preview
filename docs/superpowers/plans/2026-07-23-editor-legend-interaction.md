# Editor Legend Interaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make generated multi-series legends responsive, stable on selection, and editable through a double-click name dialog.

**Architecture:** Add one shared core legend-presentation policy and consume it from the export renderer and editor preview. Route a generated-legend double-click to a small dialog that edits the represented `plot_series.name` values as one document replacement, preserving the legend object's placement and lifecycle behavior.

**Tech Stack:** Python 3, PySide6, Matplotlib, pytest with Qt offscreen rendering.

---

## File structure

- Create `polynexus/core/figures/legend_presentation.py`: pure responsive legend policy shared by both Matplotlib paths.
- Create `polynexus/gui/widgets/chart_editor_legend_dialog.py`: compact modal series-name editor with explicit accept/cancel semantics.
- Modify `polynexus/core/figures/renderer.py`: calculate rendering width and pass policy-derived legend kwargs.
- Modify `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`: use the same policy for live generated previews.
- Modify `polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py`: route legend double-click and commit all accepted series names atomically.
- Modify `polynexus/gui/widgets/chart_editor.py`: provide Qt dialog dependencies to the interaction mixin.
- Modify `tests/test_figure_render_plan_core.py`: cover renderer responsive behavior.
- Modify `tests/test_chart_editor.py`: cover stable selection and dialog commit/cancel behavior.
- Create `docs/agent/tasks/2026-07-23-editor-legend-interaction.md`: structured-task scope and verification record.

### Task 1: Define and test a shared legend presentation policy

**Files:**
- Create: `polynexus/core/figures/legend_presentation.py`
- Modify: `tests/test_figure_render_plan_core.py`

- [ ] **Step 1: Write the failing pure-policy tests**

```python
from polynexus.core.figures.legend_presentation import legend_presentation


def test_automatic_multiseries_legend_becomes_single_column_on_narrow_canvas():
    presentation = legend_presentation(
        {"auto_generated": True, "style": {"ncol": 2}},
        handle_count=5,
        available_width_px=360,
        default_fontsize=9.0,
    )
    assert presentation.ncol == 1
    assert presentation.fontsize < 9.0


def test_automatic_multiseries_legend_retains_two_columns_on_wide_canvas():
    presentation = legend_presentation(
        {"auto_generated": True, "style": {"ncol": 2}},
        handle_count=5,
        available_width_px=900,
        default_fontsize=9.0,
    )
    assert presentation.ncol == 2
    assert presentation.fontsize == 9.0
```

- [ ] **Step 2: Run the new policy tests and verify they fail**

Run: `python -m pytest tests/test_figure_render_plan_core.py -k legend_presentation -q`
Expected: FAIL because `legend_presentation` does not exist.

- [ ] **Step 3: Implement a pure immutable policy**

```python
@dataclass(frozen=True)
class LegendPresentation:
    ncol: int
    fontsize: float | None


def legend_presentation(figure_object, *, handle_count, available_width_px, default_fontsize):
    style = figure_object.get("style", {}) if isinstance(figure_object, dict) else {}
    automatic = bool(isinstance(figure_object, dict) and figure_object.get("auto_generated"))
    compact = automatic and handle_count > 3 and available_width_px < 560
    columns = 1 if compact else max(1, int(style.get("ncol") or (2 if handle_count > 3 else 1)))
    return LegendPresentation(columns, default_fontsize * 0.85 if compact else default_fontsize)
```

Keep explicit, non-automatic `style.ncol` authoritative. Do not return or mutate `loc` or `bbox_to_anchor`.

- [ ] **Step 4: Run the policy tests**

Run: `python -m pytest tests/test_figure_render_plan_core.py -k legend_presentation -q`
Expected: PASS.

- [ ] **Step 5: Commit the policy checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(editor): add responsive legend policy" --files polynexus/core/figures/legend_presentation.py tests/test_figure_render_plan_core.py
```

### Task 2: Apply the policy in export and editor render paths

**Files:**
- Modify: `polynexus/core/figures/renderer.py:131-199`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py:944-1017`
- Modify: `tests/test_figure_render_plan_core.py`
- Modify: `tests/test_chart_editor.py`

- [ ] **Step 1: Add failing renderer and preview assertions**

```python
legend = MatplotlibFigureRenderer().render(plan, dpi=100).axes[0].get_legend()
assert legend._ncols == 1
assert legend.get_texts()[0].get_fontsize() < 9.0

editor._canvas.resize(360, 520)
editor._show_generated_figure_document()
assert editor._figure.axes[0].get_legend()._ncols == 1
```

Use five named visible series. Preserve the existing wide-preview assertion that `legend._ncols == 2`.

- [ ] **Step 2: Run the focused render tests and verify they fail**

Run: `python -m pytest tests/test_figure_render_plan_core.py tests/test_chart_editor.py -k "multiseries_legend or responsive_legend" -q`
Expected: FAIL because each path still calculates its own column count.

- [ ] **Step 3: Wire the core renderer to the policy**

```python
presentation = legend_presentation(
    legend_object,
    handle_count=len(handles),
    available_width_px=max(1.0, plan.width_in * dpi / max(1, plan.columns)),
    default_fontsize=None,
)
axis.legend(**self._legend_kwargs(legend_object, presentation))
```

`_legend_kwargs` must retain `loc` and `bbox_to_anchor`, then append `ncol` and `fontsize` only when the policy provides them.

- [ ] **Step 4: Wire the editor preview to the same policy**

```python
presentation = legend_presentation(
    legend_object,
    handle_count=len(handles),
    available_width_px=max(1.0, ax.bbox.width / self._generated_canvas_device_ratio()),
    default_fontsize=self._tick_size,
)
ax.legend(fontsize=presentation.fontsize, ncol=presentation.ncol, ...)
```

Do not alter `legend_style`, `loc`, `bbox_to_anchor`, or the existing automatic one-series suppression condition.

- [ ] **Step 5: Run the focused render tests**

Run: `python -m pytest tests/test_figure_render_plan_core.py tests/test_chart_editor.py -k "multiseries_legend or responsive_legend" -q`
Expected: PASS.

- [ ] **Step 6: Commit the shared-rendering checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(editor): adapt legend layout to canvas width" --files polynexus/core/figures/renderer.py polynexus/gui/widgets/chart_editor_generated_document_mixin.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py
```

### Task 3: Add the legend name dialog and double-click route

**Files:**
- Create: `polynexus/gui/widgets/chart_editor_legend_dialog.py`
- Modify: `polynexus/gui/widgets/chart_editor.py:8-34`
- Modify: `polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py:15-34,334-430`
- Modify: `tests/test_chart_editor.py`

- [ ] **Step 1: Write failing interaction tests**

```python
_send_matplotlib_canvas_click(editor._canvas, legend_x, legend_y, dblclick=True)
dialog = editor._active_legend_name_dialog
assert dialog is not None
dialog._name_edits[2].setText("PA6 revised")
dialog.accept()
assert _series_names(editor) == ["PA6-250-170-S_0_00000", "PA6-250-185-S_0_00000", "PA6 revised", ...]

before = _series_names(editor)
_open_legend_dialog(editor).reject()
assert _series_names(editor) == before
```

Also snapshot `legend.get_window_extent(renderer).bounds` before a normal click and assert it is unchanged after selection.

- [ ] **Step 2: Run the interaction tests and verify they fail**

Run: `python -m pytest tests/test_chart_editor.py -k "legend_double_click or legend_selection_preserves_layout" -q`
Expected: FAIL because legend double-click has no edit route.

- [ ] **Step 3: Implement the compact dialog**

```python
class LegendSeriesNameDialog(QDialog):
    def __init__(self, series, parent=None):
        super().__init__(parent)
        self._name_edits = []
        form = QFormLayout(self)
        for index, item in enumerate(series, start=1):
            edit = QLineEdit(str(item["name"]))
            form.addRow(f"{index}.", edit)
            self._name_edits.append(edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def names(self):
        return [edit.text().strip() for edit in self._name_edits]
```

Set the first field focused, make Enter accept through the default OK button, and leave Esc mapped to `reject`.

- [ ] **Step 4: Route and commit the edited names atomically**

```python
if self._generated_legend_edit_target(event):
    self._select_generated_object("legend", "double-click")
    self._begin_generated_legend_name_edit()
    return

if dialog.exec() == QDialog.Accepted:
    updated = self._generated_legend_document_with_names(dialog.names())
    result = self._execute_edit(self._replace_document_command()(updated))
    if result is not None and result.changed:
        self._persist_generated_document()
        self._show_generated_figure_document()
        self.figure_changed.emit()
```

Use the existing document replacement/undo integration rather than calling
`FigureObjectStore.rename` repeatedly. Ignore blank submitted names and retain
the corresponding old name. Refresh the object list and keep `legend` selected.

- [ ] **Step 5: Run interaction tests and the existing legend drag/undo slice**

Run: `python -m pytest tests/test_chart_editor.py -k "legend_double_click or legend_selection_preserves_layout or generated_legend" -q`
Expected: PASS.

- [ ] **Step 6: Commit the interaction checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(editor): edit legend series names on double-click" --files polynexus/gui/widgets/chart_editor_legend_dialog.py polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py tests/test_chart_editor.py
```

### Task 4: Verify the structured task and record durable state

**Files:**
- Create: `docs/agent/tasks/2026-07-23-editor-legend-interaction.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md` only if the completed behavior changes the current checkpoint summary.

- [ ] **Step 1: Run the full focused matrix**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_figure_object_store.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the required repository checks**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python scripts/verify.py --task docs/agent/tasks/2026-07-23-editor-legend-interaction.md --changed --types
python scripts/verify.py --changed --types
```

Expected: PASS, including whitespace, type, and changed-file checks.

- [ ] **Step 3: Record exact evidence and commit the documentation checkpoint**

```powershell
python scripts/auto_commit.py --message "docs(editor): record legend interaction verification" --files docs/agent/tasks/2026-07-23-editor-legend-interaction.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

Do not add unrelated existing drafts or diagnostics. Do not push, merge, or
deploy. Remind the user to restart the GUI from `D:\PolyNexus` for live visual
verification.
