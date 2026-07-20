from __future__ import annotations

from ..i18n import tr


class ChartEditorStylePresetMixin:
    @staticmethod
    def _chart_editor_module():
        from . import chart_editor as chart_editor_module

        return chart_editor_module

    @classmethod
    def _message_box_class(cls):
        return cls._chart_editor_module().QMessageBox

    @classmethod
    def _list_style_presets_fn(cls):
        return cls._chart_editor_module().list_style_presets

    @classmethod
    def _load_style_preset_fn(cls):
        return cls._chart_editor_module().load_style_preset

    @classmethod
    def _save_style_preset_fn(cls):
        return cls._chart_editor_module().save_style_preset

    @classmethod
    def _delete_style_preset_fn(cls):
        return cls._chart_editor_module().delete_style_preset

    @classmethod
    def _list_templates_fn(cls):
        return cls._chart_editor_module().list_templates

    @classmethod
    def _load_template_fn(cls):
        return cls._chart_editor_module().load_template

    @classmethod
    def _save_template_fn(cls):
        return cls._chart_editor_module().save_template

    @classmethod
    def _template_from_document_fn(cls):
        return cls._chart_editor_module().template_from_document

    @classmethod
    def _apply_template_fn(cls):
        return cls._chart_editor_module().apply_template

    @classmethod
    def _capture_style_bundle_fn(cls):
        return cls._chart_editor_module().capture_style_bundle

    @classmethod
    def _apply_style_bundle_fn(cls):
        return cls._chart_editor_module().apply_style_bundle

    @classmethod
    def _replace_document_command(cls):
        return cls._chart_editor_module().ReplaceDocumentCommand

    @classmethod
    def _update_style_command(cls):
        return cls._chart_editor_module().UpdateStyleCommand

    @classmethod
    def _logger(cls):
        return cls._chart_editor_module().logger

    def _collect_style_preset_state(self):
        return {
            "colour_scheme": self._colour_cb.currentText(),
            "font": self._font_cb.currentText(),
            "line_width": self._lw_cb.currentText(),
            "figure_size": self._figsize_cb.currentText(),
            "grid_on": self._grid_on,
            "grid_alpha": self._grid_alpha,
            "bg_color": self._bg_color,
            "dpi": self._dpi,
        }

    def _apply_style_preset(self, style):
        if not style:
            return
        self._set_combo(self._colour_cb, style.get("colour_scheme"))
        self._set_combo(self._font_cb, style.get("font"))
        self._set_combo(self._lw_cb, style.get("line_width"))
        self._set_combo(self._figsize_cb, style.get("figure_size"))
        if "grid_on" in style:
            self._grid_cb.blockSignals(True)
            self._grid_cb.setChecked(bool(style["grid_on"]))
            self._grid_cb.blockSignals(False)
            self._grid_on = bool(style["grid_on"])
        if "grid_alpha" in style:
            self._grid_sl.blockSignals(True)
            self._grid_sl.setValue(int(float(style["grid_alpha"]) * 10))
            self._grid_sl.blockSignals(False)
            self._grid_alpha = float(style["grid_alpha"])
        if "bg_color" in style:
            self._bg_color = style["bg_color"]
        if "dpi" in style:
            try:
                self._dpi = int(style["dpi"])
            except Exception:
                self._logger().warning("Chart editor DPI restore failed; keeping current DPI.", exc_info=True)
        self._render()

    def _current_style_preset_name(self):
        return str(self._style_preset_combo.currentText() or "").strip()

    def _set_style_preset_placeholder(self, text):
        line_edit = self._style_preset_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(text)

    def _on_style_preset_name_changed(self, _text):
        self._update_style_preset_action_state()

    def _update_style_preset_action_state(self, names=None):
        if names is None:
            names = self._list_style_presets_fn()()
        current_name = self._current_style_preset_name()
        has_existing = bool(current_name) and current_name in names
        self._btn_style_preset_save.setEnabled(True)
        self._btn_style_preset_apply.setEnabled(has_existing)
        self._btn_style_preset_delete.setEnabled(has_existing)

    def _refresh_style_preset_controls(self):
        names = self._list_style_presets_fn()()
        current_text = self._current_style_preset_name()
        self._style_preset_combo.blockSignals(True)
        self._style_preset_combo.clear()
        if names:
            self._style_preset_combo.addItems(names)
        if current_text:
            self._style_preset_combo.setEditText(current_text)
        elif names:
            self._style_preset_combo.setCurrentIndex(0)
        self._style_preset_combo.blockSignals(False)
        self._set_style_preset_placeholder(tr("EDITOR_STYLE_PRESET_PLACEHOLDER"))
        self._update_style_preset_action_state(names=names)

    def _current_template_name(self):
        return str(self._template_combo.currentText() or "").strip()

    def _on_template_name_changed(self, _text):
        names = self._list_templates_fn()()
        self._btn_template_apply.setEnabled(self._current_template_name() in names)

    def _refresh_template_controls(self):
        names = self._list_templates_fn()()
        current = self._current_template_name()
        self._template_combo.blockSignals(True)
        self._template_combo.clear()
        self._template_combo.addItems(names)
        if current:
            self._template_combo.setEditText(current)
        self._template_combo.blockSignals(False)
        self._btn_template_apply.setEnabled(bool(current and current in names))

    def _on_save_template(self):
        name = self._current_template_name()
        if not name:
            self._message_box_class().warning(
                self,
                tr("EDITOR_TEMPLATE_TITLE"),
                tr("EDITOR_TEMPLATE_NAME_REQUIRED"),
            )
            return
        try:
            template = self._template_from_document_fn()(self._figure_document, name)
            path = self._save_template_fn()(name, template)
        except (TypeError, ValueError, OSError) as exc:
            self._message_box_class().warning(
                self,
                tr("EDITOR_TEMPLATE_TITLE"),
                str(exc),
            )
            return
        self._refresh_template_controls()
        self._template_combo.setEditText(name)
        self._status_label.setText(tr("EDITOR_TEMPLATE_SAVED", name, path.name))

    def _on_apply_template(self):
        name = self._current_template_name()
        template = self._load_template_fn()(name)
        if not template:
            self._message_box_class().warning(
                self,
                tr("EDITOR_TEMPLATE_TITLE"),
                tr("EDITOR_TEMPLATE_MISSING", name),
            )
            return
        updated = self._apply_template_fn()(self._figure_document, template)
        result = self._execute_edit(self._replace_document_command()(updated))
        if result is None or not getattr(result, "changed", False):
            return
        if getattr(self, "_generated_document_mode", False):
            self._persist_generated_document()
            self._show_generated_figure_document()
        self._status_label.setText(tr("EDITOR_TEMPLATE_APPLIED", name))

    def _copy_selected_format(self):
        object_payload = self._selected_canonical_object()
        if not isinstance(object_payload, dict):
            return
        self._format_clipboard = self._capture_style_bundle_fn()(object_payload)
        self._status_label.setText(tr("EDITOR_FORMAT_COPIED"))

    def _paste_selected_format(self):
        object_payload = self._selected_canonical_object()
        bundle = getattr(self, "_format_clipboard", None)
        if not isinstance(object_payload, dict) or not isinstance(bundle, dict):
            return
        applied = self._apply_style_bundle_fn()(object_payload, bundle)
        if not applied.applied:
            self._status_label.setText(tr("EDITOR_FORMAT_SKIPPED"))
            return
        object_id = str(object_payload.get("id", "") or "")
        result = self._execute_edit(
            self._update_style_command()(object_id, applied.object.get("style", {}))
        )
        if result is not None and getattr(result, "changed", False):
            if getattr(self, "_generated_document_mode", False):
                self._persist_generated_document()
                self._show_generated_figure_document()
            skipped = ", ".join(applied.skipped)
            self._status_label.setText(
                tr("EDITOR_FORMAT_APPLIED", skipped) if skipped else tr("EDITOR_STATUS_APPLIED")
            )

    def _on_save_style_preset(self):
        preset_name = self._current_style_preset_name()
        message_box = self._message_box_class()
        if not preset_name:
            message_box.warning(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_NAME_REQUIRED"),
            )
            return

        existing = self._load_style_preset_fn()(preset_name)
        if existing:
            reply = message_box.question(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_OVERWRITE", preset_name),
                message_box.Yes | message_box.No,
                message_box.No,
            )
            if reply != message_box.Yes:
                return

        path, _ = self._save_style_preset_fn()(preset_name, self._collect_style_preset_state())
        self._refresh_style_preset_controls()
        self._style_preset_combo.setEditText(preset_name)
        self._status_label.setText(tr("EDITOR_STYLE_PRESET_SAVED", preset_name, path.name))

    def _on_apply_style_preset(self):
        preset_name = self._current_style_preset_name()
        message_box = self._message_box_class()
        if not preset_name:
            message_box.warning(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_NAME_REQUIRED"),
            )
            return

        style = self._load_style_preset_fn()(preset_name)
        if not style:
            message_box.warning(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_MISSING", preset_name),
            )
            self._refresh_style_preset_controls()
            return

        self._apply_style_preset(style)
        self._status_label.setText(tr("EDITOR_STYLE_PRESET_APPLIED", preset_name))

    def _on_delete_style_preset(self):
        preset_name = self._current_style_preset_name()
        message_box = self._message_box_class()
        if not preset_name:
            message_box.warning(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_NAME_REQUIRED"),
            )
            return

        if not self._load_style_preset_fn()(preset_name):
            message_box.warning(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_MISSING", preset_name),
            )
            self._refresh_style_preset_controls()
            return

        reply = message_box.question(
            self,
            tr("EDITOR_STYLE_PRESET_TITLE"),
            tr("EDITOR_STYLE_PRESET_DELETE_CONFIRM", preset_name),
            message_box.Yes | message_box.No,
            message_box.No,
        )
        if reply != message_box.Yes:
            return

        self._delete_style_preset_fn()(preset_name)
        self._refresh_style_preset_controls()
        self._style_preset_combo.setEditText("")
        self._status_label.setText(tr("EDITOR_STYLE_PRESET_DELETED", preset_name))
