from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ..i18n import tr
from ..plot_gallery_service import build_active_manifest_gallery_entries
from ...core.figures.project_service import FigureProjectService


class ChartEditorSaveMixin:
    @staticmethod
    def _chart_editor_module():
        from . import chart_editor as chart_editor_module

        return chart_editor_module

    @classmethod
    def _logger(cls):
        return cls._chart_editor_module().logger

    def save_to_target(self):
        if self._has_manifest_project_context():
            self._save_manifest_working()
            return
        if not self._target_path:
            self.save_as()
            return
        self._save_to_path(self._target_path)

    def publish_complete_assets(self):
        context = self._manifest_project_context()
        if context is None:
            self._status_label.setText(tr("EDITOR_NO_DATA"))
            return
        output_root, run_id, figure_id = context
        update = FigureProjectService(Path(output_root)).publish(
            run_id=run_id,
            figure_id=figure_id,
        )
        self._refresh_manifest_project_entry(update)
        self._status_label.setText(
            tr("EDITOR_PUBLISH_DONE", update.entry.published_revision)
        )

    def _save_manifest_working(self):
        context = self._manifest_project_context()
        if context is None:
            return
        output_root, run_id, figure_id = context
        update = FigureProjectService(Path(output_root)).save_working(
            run_id=run_id,
            figure_id=figure_id,
            document=self._generated_document_for_save(),
        )
        self._refresh_manifest_project_entry(update)
        self._status_label.setText(
            tr("EDITOR_WORKING_SAVE_DONE", update.entry.working_revision)
        )

    def _has_manifest_project_context(self):
        return self._manifest_project_context() is not None

    def _manifest_project_context(self):
        entry = getattr(self, "_source_entry_context", None)
        output_root = str(getattr(entry, "output_root", "") or "").strip()
        run_id = str(getattr(entry, "run_id", "") or "").strip()
        figure_id = str(getattr(entry, "figure_id", "") or "").strip()
        document_path = str(getattr(entry, "document_path", "") or "").strip()
        if not all((output_root, run_id, figure_id, document_path)):
            return None
        return output_root, run_id, figure_id

    def _refresh_manifest_project_entry(self, update):
        output_root = str(
            getattr(self._source_entry_context, "output_root", "") or ""
        ).strip()
        entries = build_active_manifest_gallery_entries(output_root)
        refreshed = next(
            (
                entry
                for entry in entries
                if entry.run_id == update.manifest.run_id
                and entry.figure_id == update.entry.figure_id
            ),
            None,
        )
        if refreshed is None:
            raise RuntimeError(
                f"published figure is missing from active manifest: "
                f"{update.entry.figure_id}"
            )
        preview_path = refreshed.preview_path or refreshed.primary_path
        self.set_source_figure(
            preview_path,
            source_entry_context=refreshed,
            force_static=False,
        )
        self.figure_saved.emit(preview_path)
        return refreshed

    def save_as(self, fmt=None):
        chart_editor_module = self._chart_editor_module()
        selected_filter = ""
        if fmt:
            selected_filter = f"{fmt.upper()} (*.{fmt})"
            filters = selected_filter
            default_name = f"figure.{fmt}"
        else:
            filters = "SVG (*.svg);;PNG (*.png);;PDF (*.pdf);;JPG (*.jpg)"
            default_name = (
                chart_editor_module.Path(self._target_path).name
                if self._target_path
                else "figure.svg"
            )
        path, _ = chart_editor_module.QFileDialog.getSaveFileName(
            self,
            tr("EDITOR_SAVE_DIALOG_TITLE"),
            default_name,
            filters,
        )
        if path:
            if fmt and not path.lower().endswith(f".{fmt}"):
                path = f"{path}.{fmt}"
            self._save_to_path(path)
            self.set_output_target(path)

    def _save_to_path(self, filepath):
        chart_editor_module = self._chart_editor_module()
        path = chart_editor_module.Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        if self._fig_generator is None:
            if self._generated_document_mode and self._source_path:
                self._save_generated_document_figure(path)
                return
            if self._static_file_mode and self._source_path:
                self._backup_current_static_source(path)
                style_state = self._collect_style_state()
                state_path, _ = chart_editor_module.save_figure_edit(str(path), style_state)
                annotations = self._annotation_state()
                chart_editor_module.save_figure_annotations(str(path), annotations)
                if self._should_save_static_canvas(path, annotations) and self._save_static_canvas_to_path(path):
                    pass
                elif not self._save_static_rendered_figure(path):
                    source = chart_editor_module.Path(self._source_path)
                    if source.exists() and source.resolve() != path.resolve():
                        chart_editor_module.shutil.copy2(source, path)
                asset_spec = chart_editor_module.discover_figure_asset(str(path)).to_dict()
                chart_editor_module.save_figure_asset_spec(str(path), asset_spec)
                document = chart_editor_module.create_static_figure_document(
                    str(path),
                    asset_spec=asset_spec,
                    style=style_state,
                    annotations=annotations,
                )
                document_path = chart_editor_module.save_figure_document(str(path), document)
                chart_editor_module.save_figure_document_path(str(path), str(document_path))
                self._status_label.setText(tr("EDITOR_SAVE_STATE_DONE", state_path.name))
                self.figure_saved.emit(str(path))
                return
            self._status_label.setText(tr("EDITOR_NO_DATA"))
            return

        state_path, _ = chart_editor_module.save_figure_edit(
            str(path),
            self._collect_style_state(),
        )

        ext = path.suffix.lower().lstrip(".") or "svg"
        if ext == "jpg":
            ext = "jpeg"

        from ...core.plot_edits import savefig_with_edits

        try:
            savefig_with_edits(
                self._figure,
                str(path),
                format=ext,
                dpi=300 if ext in {"png", "jpeg", "jpg", "tiff"} else self._dpi,
                bbox_inches="tight",
                facecolor=self._bg_color,
            )
        except Exception:
            self._logger().warning(
                "Chart editor save-with-edits failed; using direct save.",
                exc_info=True,
            )
            self._figure.savefig(
                str(path),
                format=ext,
                dpi=300 if ext in {"png", "jpeg", "jpg", "tiff"} else self._dpi,
                bbox_inches="tight",
                facecolor=self._bg_color,
            )

        self._status_label.setText(tr("EDITOR_SAVE_DONE", state_path.name))
        self.figure_saved.emit(str(path))

    def _save_generated_document_figure(self, path):
        chart_editor_module = self._chart_editor_module()
        self._backup_current_static_source(path)
        style_state = self._collect_style_state()
        state_path, _ = chart_editor_module.save_figure_edit(str(path), style_state)
        if not self._show_generated_figure_document():
            self._status_label.setText(tr("EDITOR_NO_DATA"))
            return

        ext = path.suffix.lower().lstrip(".") or "png"
        if ext == "jpg":
            ext = "jpeg"
        try:
            self._figure.savefig(
                str(path),
                format=ext,
                dpi=300 if ext in {"png", "jpeg", "jpg", "tiff"} else self._dpi,
                bbox_inches="tight",
                facecolor=self._bg_color,
            )
        except Exception:
            self._logger().warning(
                "Failed to save generated figure document render.",
                exc_info=True,
            )
            self._status_label.setText(tr("EDITOR_NO_DATA"))
            return

        asset_spec = chart_editor_module.discover_figure_asset(str(path)).to_dict()
        chart_editor_module.save_figure_asset_spec(str(path), asset_spec)
        document = self._generated_document_for_save()
        document["asset_spec"] = asset_spec
        document_path = chart_editor_module.save_figure_document(str(path), document)
        chart_editor_module.save_figure_document_path(str(path), str(document_path))
        self._figure_document = document
        self._status_label.setText(tr("EDITOR_SAVE_STATE_DONE", state_path.name))
        self.figure_saved.emit(str(path))

    def _generated_document_for_save(self):
        document = deepcopy(self._figure_document) if isinstance(self._figure_document, dict) else {}
        document["mode"] = "object"
        style = (
            deepcopy(document.get("style", {}))
            if isinstance(document.get("style"), dict)
            else {}
        )
        style_state = self._collect_style_state()
        for key in (
            "colour_scheme",
            "font",
            "line_width",
            "figure_size",
            "grid_on",
            "grid_alpha",
            "bg_color",
            "dpi",
        ):
            style[key] = style_state[key]
        for key in ("title", "xlabel", "ylabel"):
            style[key] = str(style_state.get(key, "") or "")
        document["style"] = style
        return document

    def _backup_current_static_source(self, path):
        chart_editor_module = self._chart_editor_module()
        if not self._source_path:
            return None
        source = chart_editor_module.Path(self._source_path)
        if not source.exists():
            return None
        if source.resolve() != path.resolve():
            return None
        backup_path = path.with_name(f"{path.name}.bak")
        if backup_path.exists():
            return backup_path
        chart_editor_module.shutil.copy2(path, backup_path)
        return backup_path

    def _collect_style_state(self):
        return {
            "title": self._title_edit.text(),
            "xlabel": self._xlabel_edit.text(),
            "ylabel": self._ylabel_edit.text(),
            "colour_scheme": self._colour_cb.currentText(),
            "font": self._font_cb.currentText(),
            "line_width": self._lw_cb.currentText(),
            "figure_size": self._figsize_cb.currentText(),
            "grid_on": self._grid_on,
            "grid_alpha": self._grid_alpha,
            "bg_color": self._bg_color,
            "dpi": self._dpi,
        }

    def _annotation_state(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return []
        return self._annotation_canvas.annotation_state()

    def _should_save_static_canvas(self, path, annotations):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return False
        if annotations:
            return True
        if self._asset_spec is None:
            return False
        canvas_width, canvas_height = self._annotation_canvas.image_size()
        return (
            int(getattr(self._asset_spec, "width_px", 0) or 0) != canvas_width
            or int(getattr(self._asset_spec, "height_px", 0) or 0) != canvas_height
        )

    def _apply_saved_style(self, style):
        if not style:
            return
        self._set_line_edit(self._title_edit, style.get("title", self._title_edit.text()))
        self._set_line_edit(self._xlabel_edit, style.get("xlabel", self._xlabel_edit.text()))
        self._set_line_edit(self._ylabel_edit, style.get("ylabel", self._ylabel_edit.text()))
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
        self._bg_color = style.get("bg_color", self._bg_color)
        self._render()

    def _apply_generated_document_style_controls(self):
        style = self._figure_document.get("style", {})
        if not isinstance(style, dict):
            return
        if "title" in style:
            self._set_line_edit(self._title_edit, str(style.get("title", "") or ""))
        if "xlabel" in style:
            self._set_line_edit(self._xlabel_edit, str(style.get("xlabel", "") or ""))
        if "ylabel" in style:
            self._set_line_edit(self._ylabel_edit, str(style.get("ylabel", "") or ""))
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
            try:
                alpha = max(0.0, min(1.0, float(style["grid_alpha"])))
            except Exception:
                alpha = self._grid_alpha
            self._grid_sl.blockSignals(True)
            self._grid_sl.setValue(int(round(alpha * 10)))
            self._grid_sl.blockSignals(False)
            self._grid_alpha = alpha
        if "bg_color" in style:
            self._bg_color = str(style["bg_color"] or self._bg_color)
        if "dpi" in style:
            try:
                self._dpi = int(style["dpi"])
            except Exception:
                self._logger().warning(
                    "Generated figure document DPI restore failed; keeping current DPI.",
                    exc_info=True,
                )

    def _set_line_edit(self, widget, value):
        widget.blockSignals(True)
        widget.setText(value)
        widget.blockSignals(False)

    def _set_combo(self, combo, value):
        chart_editor_module = self._chart_editor_module()
        if not value:
            return
        idx = combo.findText(value)
        if idx >= 0:
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
            if combo is self._colour_cb:
                self._current_colours = list(chart_editor_module.COLOUR_SCHEMES[value])
            elif combo is self._font_cb:
                self._set_font_size(value)
            elif combo is self._lw_cb:
                self._line_width = chart_editor_module.LINE_WIDTHS[value]
            elif combo is self._figsize_cb:
                self._fig_size = chart_editor_module.FIGURE_SIZES[value]
