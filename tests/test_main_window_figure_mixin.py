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
    assert (
        MainWindow._open_legacy_recovery_view
        is MainWindowFigureMixin._open_legacy_recovery_view
    )


def test_legacy_recovery_view_is_separate_from_active_gallery(monkeypatch):
    from polynexus.gui import main_window_figure_mixin as module

    entries = [object(), object()]

    class _Signal:
        def __init__(self):
            self.connected = []

        def connect(self, callback):
            self.connected.append(callback)

    class _Gallery:
        def __init__(self):
            self.edit_requested = _Signal()
            self.status_message = _Signal()
            self.entries = []
            self.title = ""
            self.shown = False

        def setWindowTitle(self, title):
            self.title = title

        def load_entries(self, values):
            self.entries = list(values)

        def resize(self, *_args):
            pass

        def show(self):
            self.shown = True

        def raise_(self):
            pass

        def activateWindow(self):
            pass

    monkeypatch.setattr(
        module,
        "build_legacy_recovery_gallery_entries",
        lambda _root: entries,
        raising=False,
    )
    monkeypatch.setattr(module, "ChartGallery", _Gallery, raising=False)

    class _Window(MainWindowFigureMixin):
        def __init__(self):
            self._output_dir = "legacy-root"
            self._chart_gallery = object()
            self._current_figure_path = "active.svg"
            self.logs = []

        def log(self, message):
            self.logs.append(message)

    window = _Window()
    active_gallery = window._chart_gallery

    viewer = window._open_legacy_recovery_view()

    assert viewer.entries == entries
    assert viewer.shown is True
    assert window._chart_gallery is active_gallery
    assert window._current_figure_path == "active.svg"


def test_current_figure_viewer_receives_selected_gallery_entry(monkeypatch):
    from polynexus.gui import main_window_figure_mixin as module

    captured = {}

    def _open(path, raw_data, **kwargs):
        captured.update(path=path, raw_data=raw_data, kwargs=kwargs)
        return "viewer"

    monkeypatch.setattr(module, "open_chart_viewer", _open)

    entry = type("Entry", (), {"figure_id": "fig-a", "preview_path": "figure.svg"})()

    class _Gallery:
        def current_entry(self):
            return entry

    class _Window(MainWindowFigureMixin):
        def __init__(self):
            self._current_figure_path = "figure.svg"
            self._chart_gallery = _Gallery()
            self._results = {"technique": {"raw_data": {"wrong": [1]}}}
            self._current_technique = "technique"
            self._figure_viewer = None
            self.logs = []

        def log(self, message):
            self.logs.append(message)

    monkeypatch.setattr(module.os.path, "exists", lambda _path: True)

    window = _Window()
    window._open_current_figure_viewer()

    assert captured["kwargs"]["entry"] is entry
