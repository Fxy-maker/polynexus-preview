"""PolyNexus application state — singleton with signal-driven updates.

Usage:
    from polynexus.gui.state import AppState
    state = AppState.instance()
    state.switch_technique("saxs")
    state.technique_changed.connect(my_widget.on_tech_change)
"""

from typing import Dict, Optional, Any
from PySide6.QtCore import QObject, Signal, QSettings


class AppState(QObject):
    """Singleton application state manager."""

    technique_changed = Signal(str)
    filepath_changed = Signal(str)
    output_dir_changed = Signal(str)
    project_name_changed = Signal(str)
    results_changed = Signal(object)
    batch_running = Signal(bool)
    recent_projects_changed = Signal(list)

    _instance: Optional["AppState"] = None

    @classmethod
    def instance(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent=None):
        if AppState._instance is not None:
            raise RuntimeError("Use AppState.instance()")
        super().__init__(parent)
        AppState._instance = self
        self._technique: str = "saxs"
        self._filepath: str = ""
        self._output_dir: str = ""
        self._project_name: str = ""
        self._results: dict = {}
        self._is_running: bool = False
        self._recent_projects: list = self._load_recent()

    @property
    def technique(self) -> str:
        return self._technique

    @property
    def filepath(self) -> str:
        return self._filepath

    @property
    def output_dir(self) -> str:
        return self._output_dir

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def results(self) -> dict:
        return self._results

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def recent_projects(self) -> list:
        return list(self._recent_projects)

    def switch_technique(self, name: str):
        if name != self._technique:
            self._technique = name
            self.technique_changed.emit(name)

    def set_filepath(self, path: str):
        if path != self._filepath:
            self._filepath = path
            self.filepath_changed.emit(path)
            if path:
                import os
                self.set_project_name(os.path.splitext(os.path.basename(path))[0])

    def set_output_dir(self, path: str):
        if path != self._output_dir:
            self._output_dir = path
            self.output_dir_changed.emit(path)

    def set_project_name(self, name: str):
        if name != self._project_name:
            self._project_name = name
            self.project_name_changed.emit(name)

    def set_results(self, technique: str, result: Any):
        self._results[technique] = result
        self.results_changed.emit(result)

    def set_running(self, running: bool):
        self._is_running = running
        self.batch_running.emit(running)

    def add_recent_project(self, path: str):
        if path not in self._recent_projects:
            self._recent_projects.insert(0, path)
            self._recent_projects = self._recent_projects[:10]
            self._save_recent()
            self.recent_projects_changed.emit(list(self._recent_projects))

    def clear_recent(self):
        self._recent_projects = []
        self._save_recent()
        self.recent_projects_changed.emit([])

    def _load_recent(self) -> list:
        s = QSettings("PolyNexus", "PolyNexus")
        val = s.value("recent_projects", [])
        return list(val) if isinstance(val, list) else []

    def _save_recent(self):
        s = QSettings("PolyNexus", "PolyNexus")
        s.setValue("recent_projects", self._recent_projects)
