import os
from copy import deepcopy
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from polynexus.core.figure_document import save_generated_figure_document
from polynexus.core.figure_edit_commands import UpdateGeometryCommand
from polynexus.gui.widgets.chart_editor import ChartEditor


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def make_static_editor(tmp_path, source=None):
    path = Path(source or (tmp_path / "source.png"))
    if source is None:
        image = QImage(160, 100, QImage.Format_RGBA8888)
        image.fill(QColor("white"))
        assert image.save(str(path))
    editor = ChartEditor()
    editor.set_source_figure(str(path))
    return editor


def make_generated_editor(tmp_path):
    path = tmp_path / "generated.png"
    image = QImage(160, 100, QImage.Format_RGBA8888)
    image.fill(QColor("white"))
    assert image.save(str(path))
    save_generated_figure_document(
        str(path),
        figure_id="generated",
        objects=[
            {
                "id": "line-1",
                "type": "line",
                "name": "Line 01",
                "x1": 0.1,
                "y1": 0.2,
                "x2": 0.8,
                "y2": 0.9,
                "style": {
                    "color": "#000000",
                    "line_width": 1.0,
                    "line_style": "-",
                },
            }
        ],
    )
    editor = ChartEditor()
    editor.generated_line_path = str(path)
    editor.set_source_figure(str(path))
    return editor


@pytest.fixture
def editor(tmp_path, app):
    return make_generated_editor(tmp_path)


def test_selected_generated_line_color_update_reaches_document(editor):
    editor._select_generated_object("line-1", "list")
    editor._annotation_color_edit.setText("#0072B2")
    editor._btn_annotation_apply_style.click()

    assert editor._generated_store().get("line-1")["style"]["color"] == "#0072B2"
    assert editor._last_edit_result.changed is True


def test_generated_style_and_geometry_share_one_edit_history(editor):
    editor._select_generated_object("line-1", "list")
    editor._annotation_color_edit.setText("#0072B2")
    editor._btn_annotation_apply_style.click()
    before_geometry = editor._generated_store().get("line-1")["x1"]

    editor._execute_edit(UpdateGeometryCommand("line-1", {"x1": 0.25}))
    assert len(editor._edit_session.history) == 2

    editor._on_annotation_undo()
    assert editor._generated_store().get("line-1")["x1"] == before_geometry
    assert editor._generated_store().get("line-1")["style"]["color"] == "#0072B2"

    editor._on_annotation_undo()
    assert editor._generated_store().get("line-1")["style"]["color"] == "#000000"


def test_static_text_annotation_round_trips_through_one_history(tmp_path, app):
    editor = make_static_editor(tmp_path)
    editor._annotation_text_edit.setText("Peak")
    editor._btn_annotation_add_text.click()
    annotation_id = editor._annotation_canvas.selected_annotation_id()
    assert editor._edit_session.can_undo is True

    editor._annotation_text_edit.setText("Peak value")
    editor._btn_annotation_update_text.click()
    assert editor._annotation_canvas.selected_annotation()["text"] == "Peak value"
    editor._on_annotation_undo()
    assert editor._annotation_canvas.selected_annotation()["text"] == "Peak"
    editor._on_annotation_redo()
    assert editor._annotation_canvas.selected_annotation()["text"] == "Peak value"

    target = tmp_path / "edited.png"
    editor._save_to_path(str(target))
    reloaded = make_static_editor(tmp_path, source=target)
    assert reloaded._annotation_canvas.annotation_state()[0]["id"] == annotation_id
    assert reloaded._annotation_canvas.annotation_state()[0]["text"] == "Peak value"


def test_invalid_color_keeps_object_and_history_unchanged(editor):
    editor._select_generated_object("line-1", "list")
    before = deepcopy(editor._generated_store().get("line-1"))
    editor._annotation_color_edit.setText("not-a-color")
    editor._btn_annotation_apply_style.click()

    assert editor._generated_store().get("line-1") == before
    assert "invalid" in editor._status_label.text().lower()
