from __future__ import annotations

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_figure_mixin import MainWindowFigureMixin


def test_main_window_reuses_figure_helpers_from_figure_mixin():
    assert MainWindow._populate_plots is MainWindowFigureMixin._populate_plots
    assert MainWindow._on_chart_selected is MainWindowFigureMixin._on_chart_selected
    assert MainWindow._close_figure_preview is MainWindowFigureMixin._close_figure_preview
    assert MainWindow._open_current_figure_viewer is MainWindowFigureMixin._open_current_figure_viewer
    assert MainWindow._on_chart_viewer_status is MainWindowFigureMixin._on_chart_viewer_status
    assert MainWindow._open_selected_chart_editor is MainWindowFigureMixin._open_selected_chart_editor
    assert MainWindow._open_exported_figure_editor is MainWindowFigureMixin._open_exported_figure_editor
    assert MainWindow._open_figure is MainWindowFigureMixin._open_figure
    assert MainWindow._on_chart_editor_saved is MainWindowFigureMixin._on_chart_editor_saved
