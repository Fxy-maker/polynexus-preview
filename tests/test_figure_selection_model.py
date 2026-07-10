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
