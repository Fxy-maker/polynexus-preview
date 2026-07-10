from __future__ import annotations

import os

from .figure_window_service import (
    chart_viewer_status_line,
    current_chart_raw_data,
    normalize_figure_path,
    open_chart_editor,
    open_chart_viewer,
    refresh_saved_figure_in_gallery,
    show_chart_preview,
)
from .i18n import tr
from .legacy_figure_recovery_service import build_legacy_recovery_gallery_entries
from .plot_gallery_service import (
    build_active_manifest_gallery_entries,
    select_plot_gallery_entry,
)
from .widgets.chart_viewer import ChartViewer


class MainWindowFigureMixin:
    def _populate_plots(self):
        """Load analysis figures into the ChartGallery."""
        entries = build_active_manifest_gallery_entries(self._output_dir)
        if not entries:
            self._plots_label.setVisible(True)
            self._chart_gallery.setVisible(False)
            self._chart_gallery.clear()
            self._current_figure_path = ""

            if hasattr(self, "_btn_view_current_figure"):
                self._btn_view_current_figure.setEnabled(False)

            if hasattr(self, "_figure_preview"):
                self._figure_preview.clear()
                self._figure_preview.setVisible(False)

            return

        preview_was_visible = bool(hasattr(self, "_figure_preview") and self._figure_preview.isVisible())
        self._plots_label.setVisible(False)
        self._chart_gallery.setVisible(True)
        self._chart_gallery.load_entries(entries)

        selection = select_plot_gallery_entry(
            entries,
            preferred_path=self._current_figure_path,
            preview_visible=preview_was_visible,
        )
        self._current_figure_path = selection.selected_path
        self._chart_gallery.select_figure(
            selection.selected_figure_id or selection.selected_path,
            emit=selection.emit_preview,
        )

    def _on_chart_selected(self, filepath):
        """Show the selected exported figure in the embedded preview."""
        self._current_figure_path = normalize_figure_path(filepath)
        if not self._current_figure_path or not hasattr(self, "_figure_preview"):
            return
        current_entry = self._chart_gallery.current_entry() if hasattr(self, "_chart_gallery") else None
        show_chart_preview(
            self._figure_preview,
            self._current_figure_path,
            view_button=getattr(self, "_btn_view_current_figure", None),
            entry=current_entry,
        )

    def _close_figure_preview(self):
        """Hide the focused exported-figure preview."""
        if hasattr(self, "_figure_preview"):
            self._figure_preview.setVisible(False)

    def _open_current_figure_viewer(self, filepath=None):
        """Open a separate viewer for the selected exported figure."""
        figure_path = normalize_figure_path(filepath, self._current_figure_path)
        if not figure_path:
            self.log(tr("LOG_FIGURE_NOT_SELECTED"))
            return
        if not os.path.exists(figure_path):
            self.log(tr("LOG_FIGURE_MISSING", figure_path))
            return
        self._figure_viewer = open_chart_viewer(
            figure_path,
            current_chart_raw_data(self._results.get(self._current_technique)),
            viewer=getattr(self, "_figure_viewer", None),
            edit_requested_handler=self._open_selected_chart_editor,
            status_message_handler=self._on_chart_viewer_status,
        )

    def _open_legacy_recovery_view(self):
        """Open explicit historical discovery without replacing active gallery state."""
        entries = build_legacy_recovery_gallery_entries(self._output_dir)
        if not entries:
            self.log(tr("LEGACY_RECOVERY_EMPTY"))
            return None
        viewer = ChartViewer()
        viewer.setWindowTitle(tr("LEGACY_RECOVERY_WINDOW_TITLE"))
        viewer.edit_requested.connect(self._open_selected_chart_editor)
        viewer.status_message.connect(self._on_chart_viewer_status)
        viewer.load_entries(entries)
        viewer.resize(1180, 820)
        viewer.show()
        viewer.raise_()
        viewer.activateWindow()
        self._legacy_figure_viewer = viewer
        return viewer

    def _on_chart_viewer_status(self, message, level="info"):
        line = chart_viewer_status_line(message, level=level)
        self._log_panel.append(line)
        sb = self._log_panel.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _open_selected_chart_editor(self, filepath=None):
        """Open settings for the selected exported figure file."""
        entry = filepath if hasattr(filepath, "figure_id") else None
        figure_path = normalize_figure_path(
            getattr(entry, "editable_path", "") if entry is not None else filepath,
            self._current_figure_path,
        )
        if entry is None and hasattr(self, "_chart_gallery"):
            current_entry = self._chart_gallery.current_entry()
            if current_entry is not None:
                entry = current_entry
                if not figure_path:
                    figure_path = normalize_figure_path(
                        current_entry.editable_path
                        or current_entry.primary_path
                        or current_entry.preview_path
                    )
        self._open_exported_figure_editor(figure_path, entry=entry)

    def _open_exported_figure_editor(self, figure_path=None, *, entry=None, force_static=False):
        """Open an editor that is bound to the selected exported figure."""
        figure_path = normalize_figure_path(
            figure_path,
            getattr(entry, "editable_path", "")
            or getattr(entry, "primary_path", "")
            or getattr(entry, "preview_path", "")
            or self._current_figure_path,
        )
        if not figure_path:
            self.log(tr("LOG_FIGURE_NOT_SELECTED"))
            return
        if not os.path.exists(figure_path):
            self.log(tr("LOG_FIGURE_MISSING", figure_path))
            return
        self._chart_editor = open_chart_editor(
            figure_path,
            entry=entry,
            force_static=force_static,
            editor=None,
            saved_handler=self._on_chart_editor_saved,
        )

    def _open_figure(self, item):
        fig_path = os.path.join(self._output_dir, "figures", item.text())
        if os.path.exists(fig_path):
            os.startfile(fig_path)

    def _on_chart_editor_saved(self, filepath):
        """Refresh gallery and preview after ChartEditor saves a figure."""
        if not filepath:
            return
        self._current_figure_path = filepath
        refresh_saved_figure_in_gallery(getattr(self, "_chart_gallery", None), filepath)
        if hasattr(self, "_figure_preview") and self._figure_preview.isVisible():
            current_entry = self._chart_gallery.current_entry() if hasattr(self, "_chart_gallery") else None
            preview_path = self._chart_gallery.current_file() if hasattr(self, "_chart_gallery") else filepath
            show_chart_preview(
                self._figure_preview,
                preview_path or filepath,
                view_button=getattr(self, "_btn_view_current_figure", None),
                entry=current_entry,
            )
        self.log(tr("LOG_CHART_SAVED", filepath))
