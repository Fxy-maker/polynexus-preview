from __future__ import annotations

from polynexus.gui.main_window import MainWindow
from polynexus.gui.main_window_import_mixin import MainWindowImportMixin


def test_main_window_reuses_import_and_input_helpers_from_import_mixin():
    import polynexus.gui.main_window_import_mixin as import_mixin_module

    assert MainWindow._set_input_path is MainWindowImportMixin._set_input_path
    assert MainWindow._apply_import_selection is MainWindowImportMixin._apply_import_selection
    assert MainWindow._import_target_summary is MainWindowImportMixin._import_target_summary
    assert MainWindow._apply_import_suggestion is MainWindowImportMixin._apply_import_suggestion
    assert MainWindow._import_submodule_options is MainWindowImportMixin._import_submodule_options
    assert MainWindow._confirm_import_suggestion is MainWindowImportMixin._confirm_import_suggestion
    assert MainWindow._choose_import_manually is MainWindowImportMixin._choose_import_manually
    assert MainWindow._handle_import_candidate is MainWindowImportMixin._handle_import_candidate
    assert MainWindow._browse_file is import_mixin_module.MainWindowImportMixin._browse_file
    assert MainWindow._browse_folder is import_mixin_module.MainWindowImportMixin._browse_folder


def test_main_window_import_mixin_browse_file_routes_selected_path_to_import_handler(monkeypatch) -> None:
    import polynexus.gui.main_window_import_mixin as import_mixin_module

    calls = []

    class _Window(MainWindowImportMixin):
        def _get_last_dir(self):
            return "D:/workspace"

        def _handle_import_candidate(self, path, *, is_dir=False, source="browse"):
            calls.append((path, is_dir, source))

    def fake_get_open_file_name(parent, title, start_dir, selected_filter):
        assert parent is window
        assert start_dir == "D:/workspace"
        assert selected_filter
        return ("D:/workspace/data.csv", selected_filter)

    monkeypatch.setattr(import_mixin_module.QFileDialog, "getOpenFileName", fake_get_open_file_name)

    window = _Window()
    window._browse_file()

    assert calls == [("D:/workspace/data.csv", False, "browse")]


def test_main_window_import_mixin_browse_folder_routes_selected_path_to_import_handler(monkeypatch) -> None:
    import polynexus.gui.main_window_import_mixin as import_mixin_module

    calls = []

    class _Window(MainWindowImportMixin):
        def _get_last_dir(self):
            return "D:/workspace"

        def _handle_import_candidate(self, path, *, is_dir=False, source="browse"):
            calls.append((path, is_dir, source))

    def fake_get_existing_directory(parent, title, start_dir):
        assert parent is window
        assert start_dir == "D:/workspace"
        return "D:/workspace/folder"

    monkeypatch.setattr(
        import_mixin_module.QFileDialog,
        "getExistingDirectory",
        fake_get_existing_directory,
    )

    window = _Window()
    window._browse_folder()

    assert calls == [("D:/workspace/folder", True, "browse")]
