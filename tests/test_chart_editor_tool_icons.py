import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.gui.widgets.chart_editor_tool_icons import editor_tool_icon


def _app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    "action_id",
    (
        "select",
        "text",
        "line",
        "arrow",
        "curve",
        "rectangle",
        "undo",
        "redo",
        "export",
    ),
)
def test_editor_tool_icon_paints_each_context_toolbar_action(action_id):
    _app()

    icon = editor_tool_icon(action_id)
    pixmap = icon.pixmap(QSize(18, 18))

    assert not icon.isNull()
    assert not pixmap.isNull()
    assert any(
        pixmap.toImage().pixelColor(x, y).alpha() > 0
        for x in range(pixmap.width())
        for y in range(pixmap.height())
    )


def test_editor_tool_icon_honors_requested_size_and_rejects_unknown_actions():
    _app()

    assert editor_tool_icon("select", size=24).pixmap(QSize(24, 24)).size() == QSize(24, 24)
    assert editor_tool_icon("unknown").isNull()


def test_editor_toolbar_uses_non_empty_icons_and_accessible_tooltips():
    _app()
    editor = ChartEditor()

    assert editor._editor_toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextUnderIcon
    for action_id in editor._editor_toolbar.action_ids():
        assert editor._editor_toolbar.action(action_id).icon().isNull() is False
        assert editor._editor_toolbar.action(action_id).toolTip()

    editor.deleteLater()
