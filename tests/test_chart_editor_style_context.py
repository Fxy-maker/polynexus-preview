from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QPixmap

from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.gui.widgets.chart_editor_save_mixin import ChartEditorSaveMixin
from polynexus.core.figure_document import save_generated_figure_document


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class _LineEdit:
    def __init__(self, text: str = "") -> None:
        self.value = text

    def text(self) -> str:
        return self.value

    def setText(self, value: object) -> None:
        self.value = str(value)

    def blockSignals(self, _blocked: bool) -> None:
        pass


class _Combo(_LineEdit):
    def __init__(self, items: list[str], text: str = "") -> None:
        super().__init__(text)
        self.items = list(items)

    def findText(self, value: object) -> int:
        try:
            return self.items.index(str(value))
        except ValueError:
            return -1

    def setCurrentIndex(self, index: int) -> None:
        self.value = self.items[index]

    def currentText(self) -> str:
        return self.value


class _Check:
    def __init__(self, checked: bool = False) -> None:
        self.value = checked

    def setChecked(self, value: object) -> None:
        self.value = bool(value)

    def blockSignals(self, _blocked: bool) -> None:
        pass


class _Slider:
    def __init__(self, value: int = 0) -> None:
        self.value = value

    def setValue(self, value: int) -> None:
        self.value = value

    def blockSignals(self, _blocked: bool) -> None:
        pass


def _harness() -> SimpleNamespace:
    editor = SimpleNamespace()
    editor._title_edit = _LineEdit("old title")
    editor._xlabel_edit = _LineEdit("old x")
    editor._ylabel_edit = _LineEdit("old y")
    editor._colour_cb = _Combo(["Default Blue", "Viridis"], "Viridis")
    editor._font_cb = _Combo(["Small", "Medium"], "Medium")
    editor._lw_cb = _Combo(["Thin", "Normal"], "Normal")
    editor._figsize_cb = _Combo(["Small (4in)", "Medium (6in)"], "Medium (6in)")
    editor._grid_cb = _Check(True)
    editor._grid_sl = _Slider(9)
    editor._grid_on = True
    editor._grid_alpha = 0.9
    editor._bg_color = "#dddddd"
    editor._dpi = 600
    editor._figure_document = {}
    editor._current_colours = []
    editor._line_width = None
    editor._fig_size = None
    editor._render = lambda: None
    editor._set_font_size = lambda _value: None
    editor._logger = lambda: SimpleNamespace(warning=lambda *args, **kwargs: None)
    editor._chart_editor_module = lambda: SimpleNamespace(
        COLOUR_SCHEMES={"Default Blue": ["#000000"], "Viridis": ["#111111"]},
        FIGURE_SIZES={"Small (4in)": (4, 3), "Medium (6in)": (8, 6)},
        LINE_WIDTHS={"Thin": 0.5, "Normal": 1.0},
    )
    editor._set_line_edit = ChartEditorSaveMixin._set_line_edit.__get__(editor)
    editor._set_combo = ChartEditorSaveMixin._set_combo.__get__(editor)
    editor._hydrate_generated_document_style_context = (
        ChartEditorSaveMixin._hydrate_generated_document_style_context.__get__(editor)
    )
    editor._reset_style_context = ChartEditorSaveMixin._reset_style_context.__get__(editor)
    return editor


def test_generated_style_context_hydrates_all_current_document_fields() -> None:
    editor = _harness()
    editor._figure_document = {
        "mode": "object",
        "style": {
            "title": "Current title",
            "xlabel": "q",
            "ylabel": "I(q)",
            "colour_scheme": "Viridis",
            "font": "Small",
            "line_width": "Thin",
            "figure_size": "Small (4in)",
            "grid_on": True,
            "grid_alpha": 0.3,
            "bg_color": "#ffffff",
            "dpi": 450,
        },
    }

    editor._hydrate_generated_document_style_context()

    assert editor._title_edit.text() == "Current title"
    assert editor._xlabel_edit.text() == "q"
    assert editor._ylabel_edit.text() == "I(q)"
    assert editor._colour_cb.currentText() == "Viridis"
    assert editor._font_cb.currentText() == "Small"
    assert editor._lw_cb.currentText() == "Thin"
    assert editor._figsize_cb.currentText() == "Small (4in)"
    assert editor._grid_cb.value is True
    assert editor._grid_sl.value == 3
    assert editor._bg_color == "#ffffff"
    assert editor._dpi == 450


def test_generated_style_context_resets_omitted_fields_before_hydration() -> None:
    editor = _harness()
    editor._figure_document = {"mode": "object", "style": {"title": "Only title"}}

    editor._hydrate_generated_document_style_context()

    assert editor._title_edit.text() == "Only title"
    assert editor._xlabel_edit.text() == ""
    assert editor._ylabel_edit.text() == ""
    assert editor._colour_cb.currentText() == "Default Blue"
    assert editor._font_cb.currentText() == "Medium"
    assert editor._lw_cb.currentText() == "Normal"
    assert editor._figsize_cb.currentText() == "Medium (6in)"
    assert editor._grid_cb.value is True
    assert editor._grid_sl.value == 2
    assert editor._bg_color == "#FFFFFF"
    assert editor._dpi == 150


def test_generated_source_target_does_not_load_legacy_edit_overlay(qapp, monkeypatch) -> None:
    calls: list[bool] = []
    editor = ChartEditor()
    editor._apply_saved_style = lambda _style: calls.append(True)

    ChartEditor.set_output_target(editor, "figure.svg", apply_saved_style=False)

    assert calls == []
    assert editor._target_path == "figure.svg"


def test_generated_style_context_keeps_default_for_invalid_dpi() -> None:
    editor = _harness()
    editor._figure_document = {
        "mode": "object",
        "style": {"dpi": "not-a-number"},
    }

    editor._hydrate_generated_document_style_context()

    assert editor._dpi == 150


def test_source_switch_rehydrates_current_document_without_stale_style(tmp_path, qapp) -> None:
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    for path in (first_path, second_path):
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(path))

    objects = [
        {
            "id": "series",
            "type": "plot_series",
            "name": "Series",
            "data": {"x": [0.1, 0.2], "y": [1.0, 0.5]},
        }
    ]
    save_generated_figure_document(
        str(first_path),
        technique="saxs",
        figure_id="first",
        style={
            "title": "First",
            "xlabel": "q-first",
            "colour_scheme": "Viridis",
            "grid_on": False,
            "dpi": 450,
        },
        objects=objects,
    )
    save_generated_figure_document(
        str(second_path),
        technique="saxs",
        figure_id="second",
        style={"title": "Second"},
        objects=objects,
    )

    editor = ChartEditor()
    editor.set_source_figure(str(first_path))
    assert editor._title_edit.text() == "First"
    assert editor._xlabel_edit.text() == "q-first"
    assert editor._colour_cb.currentText() == "Viridis"
    assert editor._grid_cb.isChecked() is False
    assert editor._dpi == 450

    editor.set_source_figure(str(second_path))

    assert editor._generated_document_mode is True
    assert editor._title_edit.text() == "Second"
    assert editor._xlabel_edit.text() == ""
    assert editor._colour_cb.currentText() == "Default Blue"
    assert editor._grid_cb.isChecked() is True
    assert editor._dpi == 150
    editor.deleteLater()
    qapp.processEvents()
