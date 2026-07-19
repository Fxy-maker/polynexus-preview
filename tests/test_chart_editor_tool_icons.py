from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_editor_toolbar_uses_non_empty_icons_and_accessible_tooltips():
    QApplication.instance() or QApplication([])
    editor = ChartEditor()

    assert editor._editor_toolbar.toolButtonStyle() == Qt.ToolButtonIconOnly
    for action_id in editor._editor_toolbar.action_ids():
        assert editor._editor_toolbar.action(action_id).icon().isNull() is False
        assert editor._editor_toolbar.action(action_id).toolTip()

    editor.deleteLater()
