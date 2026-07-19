import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.gui.figure_selection_model import FigureSelectionModel


def test_figure_selection_model_emits_only_for_real_selection_changes():
    app = QApplication.instance() or QApplication([])
    model = FigureSelectionModel()
    captured = []

    model.selection_changed.connect(lambda object_id, source: captured.append((object_id, source)))

    model.select("series-a", "canvas")
    model.select("series-a", "canvas")
    model.select("series-a", "object_list")
    model.clear("toolbar")
    model.clear("toolbar")
    app.processEvents()

    assert captured == [
        ("series-a", "canvas"),
        ("series-a", "object_list"),
        ("", "toolbar"),
    ]
    assert model.object_id == ""
    assert model.source == "toolbar"


def test_figure_selection_model_normalizes_empty_values_before_emitting():
    app = QApplication.instance() or QApplication([])
    model = FigureSelectionModel()
    captured = []

    model.selection_changed.connect(lambda object_id, source: captured.append((object_id, source)))

    model.select(None, None)
    model.select("", "")
    app.processEvents()

    assert captured == []
    assert model.object_id == ""
    assert model.source == ""


def test_figure_selection_model_exposes_ordered_multi_selection_with_first_id_compatibility():
    app = QApplication.instance() or QApplication([])
    model = FigureSelectionModel()
    captured = []
    model.selection_changed.connect(lambda object_id, source: captured.append((object_id, source)))

    model.select_many(["line-2", "line-1", "line-2"], "object-list")
    app.processEvents()

    assert model.selected_ids == ("line-2", "line-1")
    assert model.object_id == "line-2"
    assert model.source == "object-list"
    assert captured[-1] == ("line-2", "object-list")

    model.clear("escape")
    assert model.selected_ids == ()
