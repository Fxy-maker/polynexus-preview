from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_chart_editor_exposes_export_preset_controls():
    QApplication.instance() or QApplication([])
    editor = ChartEditor()

    assert editor._export_preset_combo is not None
    assert editor._btn_export_preset_save is not None
    assert editor._btn_export_preset_apply is not None
    editor.deleteLater()
