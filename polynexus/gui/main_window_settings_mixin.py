from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QListWidgetItem

from .i18n import tr
from ..core.engine import logger


class MainWindowSettingsMixin:
    def _load_settings(self):
        raw = self._settings.value("recent_projects", "")
        if raw:
            try:
                self._recent_projects = json.loads(raw)
            except Exception:
                self._recent_projects = []
                logger.warning("Failed to load recent projects from settings.", exc_info=True)

        output_dir = self._settings.value("output_dir", "")
        if output_dir:
            self._output_dir = output_dir

        last_export = self._settings.value("last_export_bundle", "")
        if last_export:
            self._last_export_bundle = str(last_export)

    def _get_last_dir(self) -> str:
        return self._settings.value("last_browse_dir", str(Path.home()), type=str)

    def _save_last_dir(self, path: str):
        directory = path if Path(path).is_dir() else str(Path(path).parent)
        self._settings.setValue("last_browse_dir", directory)

    def _save_settings(self):
        self._settings.setValue("recent_projects", json.dumps(self._recent_projects[-10:]))
        self._settings.setValue("output_dir", self._output_dir)
        self._settings.setValue("last_export_bundle", self._last_export_bundle)

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(
            self,
            tr("FILE_DIALOG_DIR"),
            self._get_last_dir(),
        )
        if path:
            self._save_last_dir(path)
            self._output_dir = path
            self._output_input.setText(path)
            self._save_settings()

    def _open_last_export_bundle(self):
        bundle = str(getattr(self, "_last_export_bundle", "") or "").strip()
        if bundle and os.path.isdir(bundle):
            try:
                os.startfile(bundle)
                return
            except OSError:
                pass
        if self._output_dir and os.path.isdir(self._output_dir):
            try:
                os.startfile(self._output_dir)
            except OSError:
                pass

    def _add_recent(self, path):
        if path in self._recent_projects:
            self._recent_projects.remove(path)
        self._recent_projects.insert(0, path)
        self._recent_projects = self._recent_projects[:10]
        self._save_settings()
        self._refresh_recent_list()

    def _refresh_recent_list(self):
        self._recent_list.clear()
        for path in self._recent_projects:
            item = QListWidgetItem(os.path.basename(path.rstrip("/\\")) or path)
            item.setToolTip(path)
            self._recent_list.addItem(item)
        self._recent_list_copy_button.setEnabled(bool(self._recent_projects))

    def _open_recent(self, item):
        idx = self._recent_list.row(item)
        if 0 <= idx < len(self._recent_projects):
            path = self._recent_projects[idx]
            if os.path.exists(path):
                is_dir = os.path.isdir(path)
                self._set_input_path(path, is_dir=is_dir, input_mode="directory" if is_dir else "")
                self.log(tr("LOG_OPENED_PATH", path))

    def _copy_recent_projects_to_clipboard(self):
        recent_list = getattr(self, "_recent_list", None)
        if recent_list is None:
            return

        selected = [item.toolTip() or item.text() for item in recent_list.selectedItems()]
        selected = [str(path).strip() for path in selected if str(path or "").strip()]
        if not selected:
            selected = [
                str(path).strip()
                for path in getattr(self, "_recent_projects", [])
                if str(path).strip()
            ]
        if selected:
            QApplication.clipboard().setText("\n".join(selected))
