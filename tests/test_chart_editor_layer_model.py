from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from polynexus.gui.widgets.chart_editor_layer_model import build_layer_tree


def test_layer_tree_groups_objects_and_preserves_input_order():
    nodes = build_layer_tree(
        [
            {"id": "line-a", "type": "line", "name": "A", "group_id": "group-1"},
            {"id": "free", "type": "text", "name": "Free"},
            {"id": "line-b", "type": "line", "name": "B", "group_id": "group-1"},
        ]
    )

    assert [node.role for node in nodes] == ["group", "object"]
    assert nodes[0].node_id == "group:group-1"
    assert [child.object_id for child in nodes[0].children] == ["line-a", "line-b"]
    assert nodes[1].object_id == "free"


def test_layer_tree_filter_keeps_matching_group_ancestor():
    nodes = build_layer_tree(
        [
            {"id": "line-a", "type": "line", "name": "Baseline", "group_id": "group-1"},
            {"id": "line-b", "type": "line", "name": "Peak", "group_id": "group-1"},
            {"id": "free", "type": "text", "name": "Other"},
        ],
        query="peak",
    )

    assert len(nodes) == 1
    assert nodes[0].role == "group"
    assert [child.object_id for child in nodes[0].children] == ["line-b"]


def test_layer_tree_group_label_can_match_without_hiding_children():
    nodes = build_layer_tree(
        [
            {"id": "line-a", "type": "line", "name": "A", "group_id": "group-1"},
            {"id": "line-b", "type": "line", "name": "B", "group_id": "group-1"},
        ],
        query="group-1",
    )

    assert len(nodes) == 1
    assert [child.object_id for child in nodes[0].children] == ["line-a", "line-b"]


def test_chart_editor_uses_tree_widget_for_object_surface():
    from PySide6.QtWidgets import QApplication, QTreeWidget

    from polynexus.gui.widgets.chart_editor import ChartEditor

    QApplication.instance() or QApplication([])
    editor = ChartEditor()

    assert isinstance(editor._object_list, QTreeWidget)
