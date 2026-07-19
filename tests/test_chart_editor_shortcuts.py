from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_editor import ChartEditor


def test_editor_shortcuts_cover_primary_actions_with_canvas_scope_for_tools():
    QApplication.instance() or QApplication([])
    editor = ChartEditor()

    shortcuts = {shortcut.key().toString(): shortcut for shortcut in editor._editor_shortcuts}
    assert {
        "Ctrl+S",
        "Ctrl+Shift+S",
        "Ctrl+Z",
        "Ctrl+Shift+Z",
        "V",
        "T",
        "L",
        "A",
        "R",
        "Del",
    } <= set(shortcuts)
    for key in ("V", "T", "L", "A", "R", "Del"):
        assert shortcuts[key].parent() is editor._canvas

    editor.deleteLater()


def test_editor_exposes_all_alignment_modes():
    QApplication.instance() or QApplication([])
    editor = ChartEditor()

    for button_name in (
        "_btn_annotation_align_left",
        "_btn_annotation_align_center",
        "_btn_annotation_align_right",
        "_btn_annotation_align_top",
        "_btn_annotation_align_middle",
        "_btn_annotation_align_bottom",
    ):
        assert getattr(editor, button_name).isEnabled() is False

    editor.deleteLater()
