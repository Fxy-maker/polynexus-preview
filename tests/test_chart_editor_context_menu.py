from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMenu

from polynexus.gui.widgets.chart_editor import ChartEditor


def _action_names(menu: QMenu) -> set[str]:
    names = set()
    for action in menu.actions():
        names.add(action.objectName())
        submenu = action.menu()
        if submenu is not None:
            names.update(_action_names(submenu))
    return names


def test_editor_context_menu_exposes_common_object_actions():
    QApplication.instance() or QApplication([])
    editor = ChartEditor()

    menu = editor._build_object_context_menu()

    assert {
        "editor_context_toggle_visibility",
        "editor_context_toggle_lock",
        "editor_context_delete",
        "editor_context_bring_front",
        "editor_context_send_back",
        "editor_context_align_left",
        "editor_context_align_center",
        "editor_context_align_right",
        "editor_context_align_top",
        "editor_context_align_middle",
        "editor_context_align_bottom",
        "editor_context_distribute_horizontal",
        "editor_context_distribute_vertical",
        "editor_context_group",
        "editor_context_ungroup",
    } <= _action_names(menu)
    menu.deleteLater()
    editor.deleteLater()


def test_editor_shortcuts_include_visibility_group_and_distribution_actions():
    QApplication.instance() or QApplication([])
    editor = ChartEditor()

    shortcuts = {shortcut.key().toString(): shortcut for shortcut in editor._editor_shortcuts}

    assert {"H", "Ctrl+G", "Ctrl+Shift+G", "Ctrl+Alt+H"} <= set(shortcuts)
    for key in ("H", "Ctrl+G", "Ctrl+Shift+G", "Ctrl+Alt+H"):
        assert shortcuts[key].parent() is editor._canvas
    editor.deleteLater()
