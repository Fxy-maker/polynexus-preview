from __future__ import annotations

from ..i18n import tr


class ChartEditorExportPresetMixin:
    @staticmethod
    def _export_preset_module():
        from . import chart_editor as chart_editor_module

        return chart_editor_module

    def _refresh_export_preset_controls(self):
        names = self._export_preset_module().list_export_presets()
        current = str(self._export_preset_combo.currentText() or "").strip()
        self._export_preset_combo.blockSignals(True)
        self._export_preset_combo.clear()
        self._export_preset_combo.addItems(names)
        if current:
            self._export_preset_combo.setEditText(current)
        self._export_preset_combo.blockSignals(False)
        self._btn_export_preset_apply.setEnabled(bool(current and current in names))

    def _on_export_preset_name_changed(self, _text):
        names = self._export_preset_module().list_export_presets()
        self._btn_export_preset_apply.setEnabled(
            str(self._export_preset_combo.currentText() or "").strip() in names
        )

    def _on_save_export_preset(self):
        name = str(self._export_preset_combo.currentText() or "").strip()
        if not name:
            self._status_label.setText(tr("EDITOR_EXPORT_PRESET_NAME_REQUIRED"))
            return
        payload = {
            "formats": [str(self._export_format_combo.currentData() or "png")],
            "dpi": int(getattr(self, "_dpi", 150)),
        }
        path = self._export_preset_module().save_export_preset(name, payload)
        self._refresh_export_preset_controls()
        self._export_preset_combo.setEditText(name)
        self._status_label.setText(tr("EDITOR_EXPORT_PRESET_SAVED", name, path.name))

    def _on_apply_export_preset(self):
        name = str(self._export_preset_combo.currentText() or "").strip()
        payload = self._export_preset_module().load_export_preset(name)
        if not payload:
            self._status_label.setText(tr("EDITOR_EXPORT_PRESET_MISSING", name))
            return
        formats = payload.get("formats", [])
        if formats:
            index = self._export_format_combo.findData(str(formats[0]))
            if index >= 0:
                self._export_format_combo.setCurrentIndex(index)
        if payload.get("dpi"):
            self._dpi = int(payload["dpi"])
        self._active_export_preset = payload
        self._status_label.setText(tr("EDITOR_EXPORT_PRESET_APPLIED", name))

    def _export_with_preset(self):
        format_name = str(self._export_format_combo.currentData() or "png")
        if format_name == "project":
            return self.export_project_package()
        if format_name == "origin":
            return self._export_to_origin()
        return self.save_as(format_name)


__all__ = ["ChartEditorExportPresetMixin"]
