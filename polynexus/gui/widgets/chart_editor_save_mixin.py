from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path

from ..i18n import tr
from ..plot_gallery_service import build_active_manifest_gallery_entries
from ...core.figure_edit_persistence import try_save_edit_bundle
from ...core.figure_project_bundle import (
    FigureProjectBundleError,
    export_figure_project_bundle,
)
from ...core.figures.project_service import FigureProjectService


class ChartEditorSaveMixin:
    @staticmethod
    def _chart_editor_module():
        from . import chart_editor as chart_editor_module

        return chart_editor_module

    @classmethod
    def _logger(cls):
        return cls._chart_editor_module().logger

    def _save_edit_bundle(self, path, document, rendered_bytes, style=None, annotations=None):
        result = try_save_edit_bundle(
            path,
            document,
            rendered_bytes,
            legacy_style=style,
            legacy_annotations=annotations,
        )
        if not result.ok:
            set_dirty = getattr(self, "_set_editor_dirty", None)
            if callable(set_dirty):
                set_dirty(True)
            else:
                self._editor_dirty = True
            status_label = getattr(self, "_status_label", None)
            if status_label is not None:
                status_label.setText(f"Save failed: {result.message}")
            return None

        session = getattr(self, "_edit_session", None)
        mark_saved = getattr(session, "mark_saved", None)
        if callable(mark_saved):
            mark_saved()
        return result

    def save_to_target(self):
        if self._has_manifest_project_context():
            self._save_manifest_working()
            return
        if not self._target_path:
            self.save_as()
            return
        self._save_to_path(self._target_path)

    def export_project_package(self):
        """Export the current figure, document, and data as one relocatable file."""
        chart_editor_module = self._chart_editor_module()
        figure_path = str(
            getattr(self, "_source_path", "") or getattr(self, "_target_path", "")
        ).strip()
        if not figure_path:
            self._status_label.setText(tr("EDITOR_NO_DATA"))
            return None

        default_name = f"{Path(figure_path).stem}.pnproject.zip"
        output_path, _ = chart_editor_module.QFileDialog.getSaveFileName(
            self,
            tr("EDITOR_PROJECT_EXPORT_TITLE"),
            default_name,
            "PolyNexus Project (*.pnproject.zip)",
        )
        if not output_path:
            return None
        if not str(output_path).lower().endswith(".pnproject.zip"):
            output_path = f"{output_path}.pnproject.zip"

        document = (
            self._generated_document_for_save()
            if getattr(self, "_generated_document_mode", False)
            else deepcopy(getattr(self, "_figure_document", {}) or {})
        )
        entry = getattr(self, "_source_entry_context", None)
        source_root = str(getattr(entry, "run_root", "") or "").strip() or None
        try:
            result = export_figure_project_bundle(
                document=document,
                figure_path=Path(figure_path),
                output_path=Path(output_path),
                source_root=Path(source_root) if source_root else None,
            )
        except FigureProjectBundleError as exc:
            self._status_label.setText(tr("EDITOR_PROJECT_EXPORT_FAILED", str(exc)))
            return None

        self._status_label.setText(
            tr("EDITOR_PROJECT_EXPORT_DONE", str(result.output_path))
        )
        return result

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
                annotations = self._annotation_state()
                render_path = path.with_name(f".{path.stem}.origin-render{path.suffix}")
                render_asset_spec = {}
                try:
                    rendered = False
                    if self._should_save_static_canvas(render_path, annotations):
                        rendered = self._save_static_canvas_to_path(render_path)
                    if not rendered:
                        rendered = self._save_static_rendered_figure(render_path)
                    if not rendered:
                        source = chart_editor_module.Path(self._source_path)
                        if source.exists():
                            chart_editor_module.shutil.copy2(source, render_path)
                            rendered = True
                    if rendered and render_path.exists():
                        render_asset_spec = chart_editor_module.discover_figure_asset(
                            str(render_path)
                        ).to_dict()
                    rendered_bytes = render_path.read_bytes() if rendered and render_path.exists() else b""
                finally:
                    render_path.unlink(missing_ok=True)

                asset_spec = render_asset_spec or (
                    self._asset_spec.to_dict()
                    if self._asset_spec is not None and hasattr(self._asset_spec, "to_dict")
                    else {}
                )
                asset_spec["figure_id"] = path.stem
                asset_spec["preview_path"] = str(path.resolve())
                document = chart_editor_module.create_static_figure_document(
                    str(path),
                    asset_spec=asset_spec,
                    style=style_state,
                    annotations=annotations,
                )
                result = self._save_edit_bundle(
                    path,
                    document,
                    rendered_bytes,
                    style_state,
                    annotations,
                )
                if result is None:
                    return
                chart_editor_module.save_figure_asset_spec(str(path), asset_spec)
                self._figure_document = document
                self._status_label.setText(
                    tr("EDITOR_SAVE_STATE_DONE", result.compatibility_path.name)
                )
                self.figure_saved.emit(str(path))
                return
            self._status_label.setText(tr("EDITOR_NO_DATA"))
            return

        style_state = self._collect_style_state()

        ext = path.suffix.lower().lstrip(".") or "svg"
        if ext == "jpg":
            ext = "jpeg"

        rendered_buffer = BytesIO()
        try:
            self._figure.savefig(
                rendered_buffer,
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
            rendered_buffer = BytesIO()
            self._figure.savefig(
                rendered_buffer,
                format=ext,
                dpi=300 if ext in {"png", "jpeg", "jpg", "tiff"} else self._dpi,
                bbox_inches="tight",
                facecolor=self._bg_color,
            )
        document = (
            deepcopy(self._figure_document)
            if isinstance(getattr(self, "_figure_document", None), dict)
            else {"version": 1, "mode": "object", "objects": []}
        )
        document.setdefault("mode", "object")
        document["style"] = style_state
        result = self._save_edit_bundle(
            path,
            document,
            rendered_buffer.getvalue(),
            style_state,
            self._annotation_state(),
        )
        if result is None:
            return
        self._figure_document = document
        self._status_label.setText(tr("EDITOR_SAVE_DONE", result.compatibility_path.name))
        self.figure_saved.emit(str(path))

    def _save_generated_document_figure(self, path):
        chart_editor_module = self._chart_editor_module()
        self._backup_current_static_source(path)
        style_state = self._collect_style_state()
        state_path, _ = chart_editor_module.save_figure_edit(str(path), style_state)
        selected_object_id = str(self._selected_figure_object_id or "")
        try:
            self._selected_figure_object_id = ""
            if not self._show_generated_figure_document():
                self._status_label.setText(tr("EDITOR_NO_DATA"))
                return
            ext = path.suffix.lower().lstrip(".") or "png"
            if ext == "jpg":
                ext = "jpeg"
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
        finally:
            self._selected_figure_object_id = selected_object_id
            self._show_generated_figure_document()

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
        convert_legacy = getattr(
            self,
            "_convert_legacy_generated_text_objects_for_save",
            None,
        )
        if callable(convert_legacy):
            convert_legacy(document)
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
        self._hydrate_generated_document_style_context()

    def _reset_style_context(self):
        self._set_line_edit(self._title_edit, "")
        self._set_line_edit(self._xlabel_edit, "")
        self._set_line_edit(self._ylabel_edit, "")
        for combo, default_value in (
            (self._colour_cb, "Default Blue"),
            (self._font_cb, "Medium"),
            (self._lw_cb, "Normal"),
            (self._figsize_cb, "Medium (6in)"),
        ):
            self._set_combo(combo, default_value)
        self._grid_cb.blockSignals(True)
        self._grid_cb.setChecked(True)
        self._grid_cb.blockSignals(False)
        self._grid_on = True
        self._grid_sl.blockSignals(True)
        self._grid_sl.setValue(2)
        self._grid_sl.blockSignals(False)
        self._grid_alpha = 0.2
        self._bg_color = "#FFFFFF"
        self._dpi = 150

    def _hydrate_generated_document_style_context(self):
        self._reset_style_context()
        style = self._figure_document.get("style", {})
        if not isinstance(style, dict):
            return
        for field, widget in (
            ("title", self._title_edit),
            ("xlabel", self._xlabel_edit),
            ("ylabel", self._ylabel_edit),
        ):
            if field in style:
                self._set_line_edit(widget, str(style.get(field, "") or ""))
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
            except (TypeError, ValueError):
                alpha = self._grid_alpha
            self._grid_sl.blockSignals(True)
            self._grid_sl.setValue(int(round(alpha * 10)))
            self._grid_sl.blockSignals(False)
            self._grid_alpha = alpha
        if "bg_color" in style and style["bg_color"]:
            self._bg_color = str(style["bg_color"])
        if "dpi" in style:
            try:
                dpi = int(style["dpi"])
                if dpi > 0:
                    self._dpi = dpi
            except (TypeError, ValueError):
                self._logger().warning(
                    "Generated figure document DPI restore failed; keeping default DPI.",
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
