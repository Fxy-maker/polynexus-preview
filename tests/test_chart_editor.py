import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_style_preset_round_trip(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    editor = ChartEditor()
    editor._colour_cb.setCurrentText("Warm")
    editor._font_cb.setCurrentText("Large")
    editor._lw_cb.setCurrentText("Thick")
    editor._figsize_cb.setCurrentText("Square")
    editor._grid_cb.setChecked(False)
    editor._grid_sl.setValue(1)
    editor._bg_color = "#F0F0F0"

    editor._style_preset_combo.setEditText("Paper Warm")
    editor._on_save_style_preset()

    editor._colour_cb.setCurrentText("Cool")
    editor._font_cb.setCurrentText("Small")
    editor._lw_cb.setCurrentText("Thin")
    editor._figsize_cb.setCurrentText("Medium (6in)")
    editor._grid_cb.setChecked(True)
    editor._grid_sl.setValue(8)
    editor._bg_color = "#FFFFFF"

    editor._style_preset_combo.setEditText("Paper Warm")
    editor._on_apply_style_preset()

    assert editor._colour_cb.currentText() == "Warm"
    assert editor._font_cb.currentText() == "Large"
    assert editor._lw_cb.currentText() == "Thick"
    assert editor._figsize_cb.currentText() == "Square"
    assert editor._grid_cb.isChecked() is False
    assert editor._grid_sl.value() == 1
    assert editor._bg_color == "#F0F0F0"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_retranslate_updates_style_preset_text(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    editor = ChartEditor()
    previous = get_language()
    try:
        set_language("zh")
        editor.retranslate()

        assert editor._btn_style_preset_save.text() == tr("EDITOR_STYLE_PRESET_SAVE")
        assert editor._grid_cb.text() == tr("EDITOR_GRID")
        assert editor._style_preset_combo.lineEdit().placeholderText() == tr(
            "EDITOR_STYLE_PRESET_PLACEHOLDER"
        )
    finally:
        set_language(previous)

    editor.deleteLater()
    app.processEvents()
