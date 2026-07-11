from __future__ import annotations

import importlib
import importlib.util

from polynexus.gui.main_window import MainWindow


def test_main_window_reuses_settings_and_recent_project_helpers_from_settings_mixin() -> None:
    spec = importlib.util.find_spec("polynexus.gui.main_window_settings_mixin")
    assert spec is not None

    module = importlib.import_module("polynexus.gui.main_window_settings_mixin")
    mixin = module.MainWindowSettingsMixin

    assert MainWindow._load_settings is mixin._load_settings
    assert MainWindow._get_last_dir is mixin._get_last_dir
    assert MainWindow._save_last_dir is mixin._save_last_dir
    assert MainWindow._save_settings is mixin._save_settings
    assert MainWindow._browse_output is mixin._browse_output
    assert MainWindow._open_last_export_bundle is mixin._open_last_export_bundle
    assert MainWindow._add_recent is mixin._add_recent
    assert MainWindow._refresh_recent_list is mixin._refresh_recent_list
    assert MainWindow._open_recent is mixin._open_recent
    assert (
        MainWindow._copy_recent_projects_to_clipboard
        is mixin._copy_recent_projects_to_clipboard
    )


def test_main_window_settings_mixin_load_settings_reads_recent_projects_and_paths() -> None:
    module = importlib.import_module("polynexus.gui.main_window_settings_mixin")

    class _Settings:
        def value(self, key, default=""):
            values = {
                "recent_projects": '["A", "B"]',
                "output_dir": "D:/exports",
                "last_export_bundle": "D:/exports/bundle",
            }
            return values.get(key, default)

    class _Window(module.MainWindowSettingsMixin):
        def __init__(self):
            self._settings = _Settings()
            self._recent_projects = []
            self._output_dir = ""
            self._last_export_bundle = ""

    window = _Window()

    window._load_settings()

    assert window._recent_projects == ["A", "B"]
    assert window._output_dir == "D:/exports"
    assert window._last_export_bundle == "D:/exports/bundle"


def test_main_window_settings_mixin_save_last_dir_uses_parent_for_file_paths() -> None:
    module = importlib.import_module("polynexus.gui.main_window_settings_mixin")

    class _Settings:
        def __init__(self):
            self.values = {}

        def setValue(self, key, value):
            self.values[key] = value

        def value(self, key, default="", type=None):
            result = self.values.get(key, default)
            if type is str:
                return str(result)
            return result

    class _Window(module.MainWindowSettingsMixin):
        def __init__(self):
            self._settings = _Settings()

    window = _Window()

    window._save_last_dir("D:/workspace/sample/data.csv")

    assert window._settings.values["last_browse_dir"].replace("\\", "/").endswith(
        "D:/workspace/sample"
    )


def test_main_window_settings_mixin_browse_output_persists_selected_directory(monkeypatch, tmp_path) -> None:
    module = importlib.import_module("polynexus.gui.main_window_settings_mixin")
    selected_dir = tmp_path / "exports"
    selected_dir.mkdir()
    start_dir = tmp_path / "workspace"
    start_dir.mkdir()

    class _LineEdit:
        def __init__(self):
            self.value = ""

        def setText(self, text):
            self.value = text

    class _Settings:
        def __init__(self):
            self.values = {}

        def setValue(self, key, value):
            self.values[key] = value

        def value(self, key, default="", type=None):
            result = self.values.get(key, default)
            if type is str:
                return str(result)
            return result

    class _Window(module.MainWindowSettingsMixin):
        def __init__(self):
            self._settings = _Settings()
            self._recent_projects = []
            self._output_dir = ""
            self._last_export_bundle = ""
            self._output_input = _LineEdit()

    def fake_get_existing_directory(parent, title, start_dir):
        assert parent is window
        assert start_dir == str(start_path)
        return str(selected_dir)

    monkeypatch.setattr(module.QFileDialog, "getExistingDirectory", fake_get_existing_directory)

    window = _Window()
    start_path = start_dir.resolve()
    window._settings.setValue("last_browse_dir", str(start_path))

    window._browse_output()

    expected_dir = str(selected_dir.resolve())
    assert window._output_dir == expected_dir
    assert window._output_input.value == expected_dir
    assert window._settings.values["output_dir"] == expected_dir
    assert window._settings.values["last_browse_dir"] == expected_dir
