# Origin Editor Inspector Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the Origin-style editor into a canvas-first layout with a mode-aware Inspector while preserving existing rendering, persistence, and entry behavior.

**Architecture:** Keep `ChartEditor` as the composition root and move presentation assembly into a focused layout mixin. The layout exposes stable widget references already used by the behavior mixins, adds a header/Inspector/status structure, and routes existing handlers rather than duplicating document or save logic. Use a four-page `QTabWidget` for Object, Style, Annotation, and Export so only one control group is visible at a time.

**Tech Stack:** Python, PySide6, Matplotlib QtAgg, pytest, existing PolyNexus i18n and figure-document services.

---

## Files and responsibilities

- Create: `polynexus/gui/widgets/chart_editor_layout_mixin.py` — header, splitter, Inspector tabs, footer, dirty-state helpers, and keyboard shortcut wiring.
- Modify: `polynexus/gui/widgets/chart_editor.py:7-25, 131-250, 329-686, 688-785` — include the layout mixin, keep behavior fields stable, and remove the old flat-panel assembly after the new layout is covered by tests.
- Modify: `polynexus/gui/widgets/chart_editor_render_mixin.py:17-119` — mark user renders dirty and provide a debounced text-render path without delaying direct canvas interactions.
- Modify: `polynexus/gui/widgets/chart_editor_save_mixin.py:20-130` — clear dirty state only after successful working-save, save-as, or publish completion.
- Modify: `polynexus/gui/widgets/chart_editor_generated_status_mixin.py:1-95` — update the footer status and header selection/hover summary through the existing status helpers.
- Modify: `polynexus/gui/i18n.py` — add Chinese and English labels for Inspector groups, mode/dirty badges, header actions, export menu, and source identity fallback.
- Create: `tests/test_chart_editor_layout.py` — focused offscreen Qt tests for layout composition, mode visibility, selection sync, dirty state, and action routing.
- Preserve: `tests/test_chart_editor.py`, `tests/test_chart_editor_style_context.py`, `tests/test_chart_editor_save_mixin.py`, and strict-entry tests as regression coverage.

## Task 1: Add failing layout and state tests

**Files:**

- Create: `tests/test_chart_editor_layout.py`

- [ ] **Step 1: Add the Qt fixture and layout contract tests**

Use the same offscreen setup as `tests/test_chart_editor.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap

from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.gui.i18n import tr
from polynexus.core.figure_document import save_generated_figure_document


def _app():
    return QApplication.instance() or QApplication([])


def _write_static_source(tmp_path):
    path = tmp_path / "figure.png"
    image = QImage(16, 16, QImage.Format_RGBA8888)
    image.fill(0xFFFFFFFF)
    assert image.save(str(path))
    return path


def test_editor_uses_canvas_first_inspector_layout():
    _app()
    editor = ChartEditor()

    assert editor._inspector_tabs.count() == 4
    assert [editor._inspector_tabs.tabText(i) for i in range(4)] == [
        tr("EDITOR_INSPECTOR_OBJECT"),
        tr("EDITOR_INSPECTOR_STYLE"),
        tr("EDITOR_INSPECTOR_ANNOTATION"),
        tr("EDITOR_INSPECTOR_EXPORT"),
    ]
    assert not editor._editor_header.isHidden()
    assert not editor._editor_status_bar.isHidden()

    editor.deleteLater()
    _app().processEvents()
```

- [ ] **Step 2: Add mode and source-identity tests**

The test must use the existing `set_figure_generator` path for object mode and
the existing static source path fixture/helper already used by
`tests/test_chart_editor.py`. Assert that object mode shows the canvas and
object Inspector, while static mode shows annotation controls and a static
mode badge. Also assert that a missing entry title falls back to the source
filename instead of an empty header.

```python
def test_object_and_static_modes_update_header_and_inspector(tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
    assert editor._mode_badge.text() == tr("EDITOR_MODE_OBJECT")
    assert editor._inspector_tabs.currentIndex() == 0

    editor.set_source_figure(str(_write_static_source(tmp_path)))
    assert editor._mode_badge.text() == tr("EDITOR_MODE_STATIC")
    assert editor._inspector_tabs.currentIndex() == 2
    assert editor._source_title_label.text()

    editor.deleteLater()
    _app().processEvents()
```

The exact static fixture should reuse the smallest existing static-file setup
from `tests/test_chart_editor.py`; do not introduce a new document schema.

- [ ] **Step 3: Add failing dirty-state and action-routing tests**

```python
def test_edit_marks_dirty_and_successful_save_clears_it(monkeypatch, tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))

    assert editor._dirty_badge.text() == tr("EDITOR_STATE_SAVED")
    editor._on_grid_toggled(False)
    assert editor._dirty_badge.text() == tr("EDITOR_STATE_UNSAVED")

    monkeypatch.setattr(editor, "_save_to_path", lambda _path: editor._set_editor_dirty(False))
    editor._target_path = str(tmp_path / "figure.svg")
    editor.save_to_target()
    assert editor._dirty_badge.text() == tr("EDITOR_STATE_SAVED")

    editor.deleteLater()
    _app().processEvents()
```

- [ ] **Step 4: Add the failing stale-selection safety test**

Use the existing generated-document fixture/helper from `tests/test_chart_editor.py`
to select one object, remove it through the existing object-store path, refresh
the object list, and assert the current item is either empty or the background
item while the Inspector tab remains enabled:

```python
def test_refresh_clears_selection_when_selected_object_disappears(tmp_path):
    _app()
    figure_path = tmp_path / "generated.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [0.1, 0.2], "y": [1.0, 2.0]},
            }
        ],
    )
    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._refresh_object_list()
    editor._object_list.setCurrentRow(1)
    selected_id = editor._object_list.currentItem().data(Qt.UserRole)
    editor._generated_store().soft_delete(selected_id)
    editor._refresh_object_list()

    current = editor._object_list.currentItem()
    assert current is None or current.data(Qt.UserRole) == "__background__"
    assert editor._inspector_tabs.isEnabled()

    editor.deleteLater()
    _app().processEvents()
```

The exact object-store removal helper should match the existing store API used
by `ChartEditorObjectListMixin`; do not add a second deletion mechanism.

- [ ] **Step 5: Run the new tests and confirm they fail for the missing layout contract**

Run:

```powershell
pytest tests/test_chart_editor_layout.py -q
```

Expected: FAIL because `_inspector_tabs`, `_editor_header`, `_editor_status_bar`,
`_mode_badge`, `_dirty_badge`, and the new translation keys do not exist yet.

## Task 2: Build the canvas-first layout

**Files:**

- Create: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor.py:7-25, 131-150, 211-250, 329-686`

- [ ] **Step 1: Add the layout mixin with stable widget fields**

The mixin must preserve the existing field names (`_canvas`, `_toolbar`,
`_source_preview`, `_annotation_canvas`, `_object_list`, `_status_label`,
`_btn_save_current`, `_btn_publish`, `_btn_save_as`, `_btn_svg`, and `_btn_png`)
because behavior mixins and tests already use them.

Use this composition shape:

```python
class ChartEditorLayoutMixin:
    def _build_ui(self):
        self._editor_header = self._build_editor_header()
        self._editor_status_bar = self._build_editor_status_bar()

        split = QSplitter(Qt.Horizontal)
        split.addWidget(self._build_figure_panel())
        split.addWidget(self._build_inspector())
        split.setSizes([760, 320])
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        self._editor_splitter = split

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor_header)
        layout.addWidget(split, 1)
        layout.addWidget(self._editor_status_bar)
```

`_build_figure_panel()` must contain the existing Matplotlib toolbar, figure
canvas, source preview, and annotation canvas with the same visibility rules.

- [ ] **Step 2: Build four Inspector pages from the existing controls**

Create a `QTabWidget` stored as `_inspector_tabs`. Move existing controls into
four page builders without changing their signals or handler names:

```python
self._inspector_tabs.addTab(self._build_object_page(), tr("EDITOR_INSPECTOR_OBJECT"))
self._inspector_tabs.addTab(self._build_style_page(), tr("EDITOR_INSPECTOR_STYLE"))
self._inspector_tabs.addTab(self._build_annotation_page(), tr("EDITOR_INSPECTOR_ANNOTATION"))
self._inspector_tabs.addTab(self._build_export_page(), tr("EDITOR_INSPECTOR_EXPORT"))
```

The Object page owns `_object_list`, `_selected_object_label`, and geometry
controls. The Style page owns style presets, title/axis fields, colour/font/
line/size/grid/background controls. The Annotation page owns annotation text,
annotation style, tools, ordering, annotation undo/redo, and zoom. The Export
page owns target display, save/publish, Save As Copy, PNG, and SVG controls.

Keep the current default tab at index 0 and do not persist tab selection across
figure switches in this first slice.

- [ ] **Step 3: Add the header and footer without duplicating behavior**

The header must expose `_source_title_label`, `_mode_badge`, `_dirty_badge`,
`_btn_header_save`, and `_btn_header_export`. `_btn_header_save` triggers the
existing `save_to_target`; the export button opens a `QMenu` whose actions call
the existing `save_as()`, `save_as("png")`, `save_as("svg")`, and
`publish_complete_assets()` handlers.

Keep the existing export buttons on the Export page so current tests and
keyboard-accessible fallback paths remain valid; the header menu is a compact
shortcut, not a second implementation.

The footer must reuse `_status_label` so all existing status-producing mixins
continue to update the visible feedback area.

- [ ] **Step 4: Add mode-aware tab selection**

Add these helpers to the layout mixin:

```python
def _set_editor_mode_ui(self, *, object_mode: bool):
    self._inspector_tabs.setCurrentIndex(0 if object_mode else 2)
    self._object_list.setEnabled(bool(object_mode or self._static_file_mode))

def _set_source_identity_ui(self):
    title = self._source_mode_title() or tr("EDITOR_SOURCE_UNNAMED")
    self._source_title_label.setText(title)
    self._source_title_label.setToolTip(str(self._source_path or ""))
```

Call `_set_editor_mode_ui()` and `_set_source_identity_ui()` from the existing
`set_source_figure()` and `set_figure_generator()` branches after mode state is
known. Do not change the object/static compatibility decision.

- [ ] **Step 5: Run the basic layout tests**

Run:

```powershell
pytest tests/test_chart_editor_layout.py tests/test_chart_editor_style_context.py -q
```

Expected: the header, four Inspector tabs, mode labels, and existing
style-context tests pass; the stale-selection test may remain failing until
the next step.

- [ ] **Step 6: Implement selection and resize safety**

Set the Inspector minimum width to 280 px and let the splitter restore a
usable canvas width when the window is narrowed. After every existing
`_refresh_object_list()` call, keep the current selection if its object ID is
still present; otherwise clear the selection and return the Object page to the
figure-level state. The failing test from Task 1 must pass without changing
the object-store deletion API.

- [ ] **Step 7: Run the complete layout-focused test set**

Run:

```powershell
pytest tests/test_chart_editor_layout.py tests/test_chart_editor_style_context.py -q
```

Expected: PASS, including the stale-selection case.

## Task 3: Add dirty state, action semantics, and shortcuts

**Files:**

- Modify: `polynexus/gui/widgets/chart_editor.py:154-213, 817-906`
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_render_mixin.py:17-119`
- Modify: `polynexus/gui/widgets/chart_editor_save_mixin.py:20-130`

- [ ] **Step 1: Add guarded dirty-state helpers**

Initialize `_editor_dirty = False` and `_loading_editor_state = False` in
`ChartEditor.__init__`. Add the following methods to the layout mixin:

```python
def _set_editor_dirty(self, dirty: bool):
    self._editor_dirty = bool(dirty)
    self._dirty_badge.setText(
        tr("EDITOR_STATE_UNSAVED") if self._editor_dirty else tr("EDITOR_STATE_SAVED")
    )

def _mark_editor_dirty(self):
    if not getattr(self, "_loading_editor_state", False):
        self._set_editor_dirty(True)
```

Set `_loading_editor_state = True` at the start of source/generator hydration
and back to `False` immediately before the method returns to the user. Reset
dirty state after a successful source load and after successful save/publish.

- [ ] **Step 2: Connect existing change signals to dirty state**

Connect `figure_changed` to `_mark_editor_dirty` once in `__init__`:

```python
self.figure_changed.connect(self._mark_editor_dirty)
```

This captures existing object, annotation, and render mutation paths without
duplicating persistence logic. The hydration guard prevents source loading,
style restoration, and selection refresh from falsely showing unsaved changes.

- [ ] **Step 3: Clear dirty state only on successful saves**

In `ChartEditorSaveMixin`, call `_set_editor_dirty(False)` immediately before
each successful `figure_saved.emit(...)` and after a successful manifest
publish refresh. Do not clear dirty state in exception paths or when no target
exists.

- [ ] **Step 4: Add keyboard shortcuts**

In the layout mixin, install `QShortcut` objects on the editor:

```python
save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
save_shortcut.activated.connect(self.save_to_target)
undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
undo_shortcut.activated.connect(self._on_annotation_undo)
redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
redo_shortcut.activated.connect(self._on_annotation_redo)
```

Use `QKeySequence("Meta+S")`, `Meta+Z`, and `Meta+Shift+Z` on macOS when the
platform requires it. Keep the existing Delete, Copy, Paste, and Escape event
filter behavior unchanged.

- [ ] **Step 5: Run dirty-state and save regressions**

Run:

```powershell
pytest tests/test_chart_editor_layout.py tests/test_chart_editor_save_mixin.py tests/test_chart_editor.py -q
```

Expected: all selected tests pass, including existing status-label and save
behavior assertions.

## Task 4: Finish status, i18n, and render responsiveness

**Files:**

- Modify: `polynexus/gui/i18n.py`
- Modify: `polynexus/gui/widgets/chart_editor.py:688-785`
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_render_mixin.py:17-119`
- Modify: `tests/test_chart_editor_layout.py`

- [ ] **Step 1: Add all new Chinese and English translation keys**

Add matching keys to both language dictionaries for:

```python
EDITOR_INSPECTOR_OBJECT
EDITOR_INSPECTOR_STYLE
EDITOR_INSPECTOR_ANNOTATION
EDITOR_INSPECTOR_EXPORT
EDITOR_STATE_SAVED
EDITOR_STATE_UNSAVED
EDITOR_STATE_PUBLISHING
EDITOR_SOURCE_UNNAMED
EDITOR_EXPORT_MENU
```

Use the existing `tr()` mechanism and update `ChartEditor.retranslate()` so
all four tab labels, header badges, and menu actions update after a language
switch. Do not leave the hard-coded `Title:`, `X:`, `Y:`, `Colours:`, `Font:`,
`Line:`, `Size:`, and `Grid alpha:` labels untranslated.

- [ ] **Step 2: Debounce only user text edits**

Add a single-shot `QTimer` with a 120 ms interval. Connect title/x/y
`textEdited` signals to `_schedule_text_render()` and keep programmatic loading
through `_set_line_edit()` plus explicit `_render()` calls. The method must
restart the timer when typing continues and call `_render()` once after the
interval. Style-combo changes and direct drag updates remain immediate.

```python
def _schedule_text_render(self):
    self._text_render_timer.start(120)
```

The timer must be stopped during widget destruction or source replacement so a
delayed render cannot target a cleared document.

- [ ] **Step 3: Verify retranslation and mode copy**

Extend `tests/test_chart_editor_layout.py` to switch the existing language
setting and assert tab labels, mode badge, dirty badge, and header action text
update. Restore the original language in a `try/finally` block.

- [ ] **Step 4: Add keyboard-accessible names**

Set an accessible name on the header save/export controls, mode and dirty
badges, the Inspector tab widget, and the footer status label. The visible
Chinese/English text remains the user-facing label; accessible names should
describe the action or state, for example `Save current figure` and `Editor
status`.

- [ ] **Step 5: Run focused verification**

Run:

```powershell
pytest tests/test_chart_editor_layout.py tests/test_chart_editor_style_context.py tests/test_chart_editor_save_mixin.py tests/test_chart_editor_status_service.py -q
```

Expected: PASS with no untranslated new labels and no dirty-state regressions.

## Task 5: Full regression and handoff

**Files:**

- Modify only files listed in Tasks 1–4.

- [ ] **Step 1: Run the complete chart-editor test set**

Run:

```powershell
$files = Get-ChildItem tests -File -Filter 'test_chart_editor*.py' | Select-Object -ExpandProperty FullName
pytest $files tests/test_annotation_canvas.py -q
```

Expected: PASS.

- [ ] **Step 2: Run lint/compile checks on changed Python files**

Run:

```powershell
python -m compileall polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_layout_mixin.py polynexus/gui/widgets/chart_editor_render_mixin.py polynexus/gui/widgets/chart_editor_save_mixin.py polynexus/gui/widgets/chart_editor_generated_status_mixin.py polynexus/gui/i18n.py
git diff --check
```

Expected: compile succeeds and `git diff --check` produces no output.

- [ ] **Step 3: Verify no contract drift**

Review the diff for these invariants:

- `set_source_figure_entry()` and strict object/static gating are unchanged in
  behavior.
- Existing widget field names used by tests and mixins still exist.
- Save, publish, annotation persistence, figure-document persistence, and
  gallery entry refresh still call their existing services.
- No new persisted UI state or second document schema was introduced.

- [ ] **Step 4: Commit the implementation as one focused change**

Run:

```powershell
git add polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_layout_mixin.py polynexus/gui/widgets/chart_editor_render_mixin.py polynexus/gui/widgets/chart_editor_save_mixin.py polynexus/gui/widgets/chart_editor_generated_status_mixin.py polynexus/gui/i18n.py tests/test_chart_editor_layout.py
git commit -m "feat: add canvas-first Origin editor Inspector layout"
```

Expected: one focused commit containing only the layout, state, i18n, and
regression-test changes.
