# Editor Style Context Hydration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent chart-editor style state from leaking between manifest/generated figures by resetting and hydrating controls from the current document.

**Architecture:** Keep `ChartEditor` and its existing mixins. Add a narrow style-context reset/hydration boundary in `ChartEditorSaveMixin`, invoke it from `set_source_figure()` before generated-document rendering, and leave static-file edit overlays on their existing path. Tests use lightweight control doubles for deterministic mixin behavior and retain the existing GUI regression suite for integration coverage.

**Tech Stack:** Python 3.10+, PySide6 widget methods, pytest, existing chart-editor mixins and document contracts.

---

## File map

- Modify: `polynexus/gui/widgets/chart_editor_save_mixin.py` — add reset and document-style hydration helpers.
- Modify: `polynexus/gui/widgets/chart_editor.py:807-913` — establish the style-context boundary during source switching.
- Create: `tests/test_chart_editor_style_context.py` — focused reset/hydration and source-switch contract tests.
- Existing: `tests/test_chart_editor_generated_document_mixin.py`, `tests/test_chart_editor_save_mixin.py`, and `tests/test_chart_editor.py` — integration/regression coverage.

## Task 1: Write the failing style-context tests

**Files:**
- Create: `tests/test_chart_editor_style_context.py`

- [ ] **Step 1: Add lightweight control doubles and an editor harness**

Implement test-only doubles with the methods used by the mixin:

```python
class _LineEdit:
    def __init__(self, text=""):
        self.value = text
    def text(self): return self.value
    def setText(self, value): self.value = str(value)
    def blockSignals(self, _blocked): pass

class _Combo(_LineEdit):
    def __init__(self, items, text=""):
        super().__init__(text)
        self.items = list(items)
    def findText(self, value):
        try: return self.items.index(value)
        except ValueError: return -1
    def setCurrentIndex(self, index): self.value = self.items[index]
    def currentText(self): return self.value

class _Check:
    def __init__(self, checked=False): self.value = checked
    def setChecked(self, value): self.value = bool(value)
    def blockSignals(self, _blocked): pass

class _Slider:
    def __init__(self, value=0): self.value = value
    def setValue(self, value): self.value = value
    def blockSignals(self, _blocked): pass
```

Build a `SimpleNamespace` harness by mixing in `ChartEditorSaveMixin` and
providing `_title_edit`, `_xlabel_edit`, `_ylabel_edit`, `_colour_cb`,
`_font_cb`, `_lw_cb`, `_figsize_cb`, `_grid_cb`, `_grid_sl`, `_grid_on`,
`_grid_alpha`, `_bg_color`, `_dpi`, `_figure_document`, `_set_font_size`,
`_render`, and `_logger`. Patch `_chart_editor_module()` to expose the existing
`COLOUR_SCHEMES`, `FIGURE_SIZES`, and `LINE_WIDTHS` dictionaries.

- [ ] **Step 2: Add a failing test for complete current-document hydration**

```python
def test_generated_style_context_hydrates_all_current_document_fields():
    editor = _harness_with_non_default_previous_state()
    editor._figure_document = {
        "mode": "object",
        "style": {
            "title": "Current title",
            "xlabel": "q",
            "ylabel": "I(q)",
            "colour_scheme": "Okabe-Ito",
            "font": "Arial",
            "line_width": "Thin",
            "figure_size": "Small",
            "grid_on": True,
            "grid_alpha": 0.3,
            "bg_color": "#ffffff",
            "dpi": 450,
        },
    }

    editor._hydrate_generated_document_style_context()

    assert editor._title_edit.text() == "Current title"
    assert editor._xlabel_edit.text() == "q"
    assert editor._colour_cb.currentText() == "Okabe-Ito"
    assert editor._grid_cb.value is True
    assert editor._grid_sl.value == 3
    assert editor._bg_color == "#ffffff"
    assert editor._dpi == 450
```

Run:

```powershell
python -m pytest tests/test_chart_editor_style_context.py::test_generated_style_context_hydrates_all_current_document_fields -q
```

Expected: FAIL because the new hydration method does not exist.

- [ ] **Step 3: Add a failing stale-state reset test**

```python
def test_generated_style_context_resets_omitted_fields_before_hydration():
    editor = _harness_with_non_default_previous_state()
    editor._reset_style_context()
    editor._figure_document = {"mode": "object", "style": {"title": "Only title"}}

    editor._hydrate_generated_document_style_context()

    assert editor._title_edit.text() == "Only title"
    assert editor._xlabel_edit.text() == ""
    assert editor._ylabel_edit.text() == ""
    assert editor._grid_cb.value is False
    assert editor._grid_sl.value == 5
    assert editor._bg_color == "white"
    assert editor._dpi == 300
```

Run:

```powershell
python -m pytest tests/test_chart_editor_style_context.py -q
```

Expected: FAIL because reset/hydration methods do not exist.

- [ ] **Step 4: Commit RED tests**

```powershell
git add tests/test_chart_editor_style_context.py
git commit -m "test(editor): define generated style context hydration"
```

## Task 2: Implement reset and current-document hydration

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor_save_mixin.py:340-420`
- Test: `tests/test_chart_editor_style_context.py`

- [ ] **Step 1: Implement `_reset_style_context()` using existing editor defaults**

Reset title/axis labels to empty strings, combo controls to their first/default
values, grid off, grid alpha `0.5`, background `"white"`, DPI `300`, and update
the matching internal fields. Use existing `_set_line_edit` and `_set_combo`
helpers, block signals while changing controls, and do not call `_render()` from
the reset helper.

- [ ] **Step 2: Implement `_hydrate_generated_document_style_context()`**

Read `self._figure_document.get("style", {})` only when it is a mapping. Call
`_reset_style_context()` first. Apply title/axis labels, combo values, grid
state/alpha, background, and valid integer DPI. Keep defaults for missing or
invalid values and log invalid DPI with the existing logger. Do not call
`load_figure_edit()` and do not write to the document.

- [ ] **Step 3: Run the focused tests GREEN**

```powershell
python -m pytest tests/test_chart_editor_style_context.py -q
```

Expected: all focused style-context tests pass.

- [ ] **Step 4: Commit the implementation**

```powershell
git add polynexus/gui/widgets/chart_editor_save_mixin.py tests/test_chart_editor_style_context.py
git commit -m "fix(editor): hydrate style context from current document"
```

## Task 3: Wire source switching and verify integration

**Files:**
- Modify: `polynexus/gui/widgets/chart_editor.py:807-913`
- Test: `tests/test_chart_editor_style_context.py`, existing chart-editor suites.

- [ ] **Step 1: Add a source-switch regression test**

Patch `load_figure_document`, `discover_figure_asset`, `FigureRenderPlanBuilder`,
and the editor display methods so `set_source_figure()` can run without file
IO/rendering. Load document A then document B through the real method and
assert that the controls reflect B, including fields omitted by B falling back
to defaults. The test must also assert `_generated_document_mode` is true after
the second load.

- [ ] **Step 2: Wire the hydration boundary**

In `set_source_figure()`, reset the style context after clearing the previous
document state. After loading the current document, call
`_hydrate_generated_document_style_context()` only in the generated/object
branch before `_show_generated_figure_document()`. Keep `set_output_target()`
for static edit overlays; prevent it from applying a stale edit state to the
generated branch by either moving the call into the static branch or adding an
explicit generated-mode guard.

- [ ] **Step 3: Run targeted integration tests**

```powershell
python -m pytest tests/test_chart_editor_style_context.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor_save_mixin.py tests/test_chart_editor_style_preset_mixin.py -q
```

Expected: all tests pass with no Qt warnings or errors.

- [ ] **Step 4: Run the broader editor regression slice**

```powershell
python -m pytest tests/test_chart_editor.py tests/test_chart_editor_panel_mixin.py tests/test_chart_editor_render_mixin.py tests/test_chart_editor_generated_selection_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_chart_editor_save_mixin.py -q
```

- [ ] **Step 5: Run changed-scope verification and inspect the diff**

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-07-12-editor-style-context.md
python scripts/verify.py --changed --types
git diff --check
git status --short
```

- [ ] **Step 6: Record task evidence**

Update `docs/agent/memory/active-work.md` with the branch, focused test result,
and any known limitation. Commit the task card and memory update separately
from code:

```powershell
git add docs/agent/tasks/2026-07-12-editor-style-context.md docs/agent/memory/active-work.md
git commit -m "docs: record editor style context verification"
```
