"""Live chart editor and exported-figure settings panel."""

import logging
logger = logging.getLogger(__name__)

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import matplotlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavToolbar
from matplotlib.figure import Figure

from ..i18n import tr
from .chart_viewer import FigureFilePreview
from ...core.plot_edits import (
    COLOUR_SCHEMES,
    FIGURE_SIZES,
    FONT_SIZES,
    LINE_WIDTHS,
    delete_style_preset,
    load_figure_edit,
    load_style_preset,
    list_style_presets,
    save_figure_edit,
    save_style_preset,
)
from ...plotting.sci_style import set_sci_style as _apply_sci_style


class ChartEditor(QWidget):
    figure_changed = Signal()
    figure_saved = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fig_generator = None
        self._fig_args = ()
        self._fig_kwargs = {}
        self._target_path = ""
        self._source_path = ""
        self._static_file_mode = False
        self._current_colours = list(COLOUR_SCHEMES["Default Blue"])
        self._title_size = 14
        self._label_size = 12
        self._tick_size = 11
        self._line_width = 1.0
        self._grid_on = True
        self._grid_alpha = 0.2
        self._fig_size = FIGURE_SIZES["Medium (6in)"]
        self._bg_color = "#FFFFFF"
        self._dpi = 150
        self._build_ui()

    def _build_ui(self):
        split = QSplitter(Qt.Horizontal)

        figure_panel = QWidget()
        figure_layout = QVBoxLayout(figure_panel)
        figure_layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(
            figsize=self._fig_size, dpi=self._dpi, facecolor=self._bg_color
        )
        self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavToolbar(self._canvas, self)
        self._source_preview = FigureFilePreview(show_edit_button=False)
        self._source_preview.setVisible(False)
        figure_layout.addWidget(self._toolbar)
        figure_layout.addWidget(self._canvas, 1)
        figure_layout.addWidget(self._source_preview, 1)
        split.addWidget(figure_panel)

        split.addWidget(self._build_panel())
        split.setSizes([760, 320])
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(split)

    def _build_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        panel = QWidget()
        form = QFormLayout(panel)
        form.setSpacing(8)
        form.setContentsMargins(12, 12, 12, 12)

        self._target_label = QLabel(tr("EDITOR_TARGET_NONE"))
        self._target_label.setWordWrap(True)
        form.addRow(tr("EDITOR_TARGET_LABEL"), self._target_label)

        preset_row = QWidget()
        preset_layout = QHBoxLayout(preset_row)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(6)

        self._style_preset_combo = QComboBox()
        self._style_preset_combo.setEditable(True)
        self._style_preset_combo.setInsertPolicy(QComboBox.NoInsert)
        self._style_preset_combo.editTextChanged.connect(self._on_style_preset_name_changed)
        preset_layout.addWidget(self._style_preset_combo, 1)

        self._btn_style_preset_save = QPushButton(tr("EDITOR_STYLE_PRESET_SAVE"))
        self._btn_style_preset_save.clicked.connect(self._on_save_style_preset)
        preset_layout.addWidget(self._btn_style_preset_save)

        self._btn_style_preset_apply = QPushButton(tr("EDITOR_STYLE_PRESET_APPLY"))
        self._btn_style_preset_apply.clicked.connect(self._on_apply_style_preset)
        preset_layout.addWidget(self._btn_style_preset_apply)

        self._btn_style_preset_delete = QPushButton(tr("EDITOR_STYLE_PRESET_DELETE"))
        self._btn_style_preset_delete.clicked.connect(self._on_delete_style_preset)
        preset_layout.addWidget(self._btn_style_preset_delete)

        form.addRow(tr("EDITOR_STYLE_PRESET_LABEL"), preset_row)

        self._title_edit = QLineEdit()
        self._title_edit.textChanged.connect(self._render)
        form.addRow("Title:", self._title_edit)

        self._xlabel_edit = QLineEdit()
        self._xlabel_edit.textChanged.connect(self._render)
        form.addRow("X:", self._xlabel_edit)

        self._ylabel_edit = QLineEdit()
        self._ylabel_edit.textChanged.connect(self._render)
        form.addRow("Y:", self._ylabel_edit)

        self._colour_cb = QComboBox()
        self._colour_cb.addItems(COLOUR_SCHEMES.keys())
        self._colour_cb.currentTextChanged.connect(self._on_colour_scheme_changed)
        form.addRow("Colours:", self._colour_cb)

        self._font_cb = QComboBox()
        self._font_cb.addItems(FONT_SIZES.keys())
        self._font_cb.setCurrentText("Medium")
        self._font_cb.currentTextChanged.connect(self._on_font_changed)
        form.addRow("Font:", self._font_cb)

        self._lw_cb = QComboBox()
        self._lw_cb.addItems(LINE_WIDTHS.keys())
        self._lw_cb.setCurrentText("Normal")
        self._lw_cb.currentTextChanged.connect(self._on_line_width_changed)
        form.addRow("Line:", self._lw_cb)

        self._figsize_cb = QComboBox()
        self._figsize_cb.addItems(FIGURE_SIZES.keys())
        self._figsize_cb.setCurrentText("Medium (6in)")
        self._figsize_cb.currentTextChanged.connect(self._on_figure_size_changed)
        form.addRow("Size:", self._figsize_cb)

        self._grid_cb = QCheckBox("Grid")
        self._grid_cb.setChecked(True)
        self._grid_cb.toggled.connect(self._on_grid_toggled)
        form.addRow(self._grid_cb)

        self._grid_sl = QSlider(Qt.Horizontal)
        self._grid_sl.setRange(0, 10)
        self._grid_sl.setValue(2)
        self._grid_sl.valueChanged.connect(self._on_grid_alpha_changed)
        form.addRow("Grid alpha:", self._grid_sl)

        btn_bg = QPushButton(tr("EDITOR_BTN_BG"))
        btn_bg.clicked.connect(self._pick_bg)
        form.addRow(btn_bg)

        self._btn_sci_defaults = QPushButton(tr("EDITOR_SCI_DEFAULTS"))
        self._btn_sci_defaults.clicked.connect(self._apply_sci_defaults)
        form.addRow(self._btn_sci_defaults)

        self._btn_save_current = QPushButton(tr("EDITOR_SAVE_CURRENT"))
        self._btn_save_current.setObjectName("primary_btn")
        self._btn_save_current.clicked.connect(self.save_to_target)
        form.addRow(self._btn_save_current)

        self._btn_save_as = QPushButton(tr("EDITOR_SAVE_AS"))
        self._btn_save_as.clicked.connect(self.save_as)
        form.addRow(self._btn_save_as)

        self._btn_svg = QPushButton(tr("EDITOR_BTN_SAVE_SVG"))
        self._btn_svg.clicked.connect(lambda: self.save_as("svg"))
        form.addRow(self._btn_svg)

        self._btn_png = QPushButton(tr("EDITOR_BTN_SAVE_PNG"))
        self._btn_png.clicked.connect(lambda: self.save_as("png"))
        form.addRow(self._btn_png)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        form.addRow(self._status_label)

        self._form = form
        self._btn_bg = btn_bg
        scroll.setWidget(panel)
        self._refresh_style_preset_controls()
        return scroll

    def retranslate(self):
        if hasattr(self, "_target_label"):
            if self._target_path:
                self._target_label.setText(str(Path(self._target_path).name))
            else:
                self._target_label.setText(tr("EDITOR_TARGET_NONE"))

        if hasattr(self, "_form"):
            for widget, text in [
                (self._target_label, tr("EDITOR_TARGET_LABEL")),
                (self._style_preset_combo.parentWidget(), tr("EDITOR_STYLE_PRESET_LABEL")),
                (self._title_edit, "Title:"),
                (self._xlabel_edit, "X:"),
                (self._ylabel_edit, "Y:"),
                (self._colour_cb, tr("EDITOR_FIELD_COLOURS")),
                (self._font_cb, tr("EDITOR_FIELD_FONT")),
                (self._lw_cb, tr("EDITOR_FIELD_LINE")),
                (self._figsize_cb, tr("EDITOR_FIELD_SIZE")),
                (self._grid_sl, tr("EDITOR_FIELD_GRID_ALPHA")),
            ]:
                label = self._form.labelForField(widget)
                if label is not None:
                    label.setText(text)

        self._grid_cb.setText(tr("EDITOR_GRID"))
        self._btn_style_preset_save.setText(tr("EDITOR_STYLE_PRESET_SAVE"))
        self._btn_style_preset_apply.setText(tr("EDITOR_STYLE_PRESET_APPLY"))
        self._btn_style_preset_delete.setText(tr("EDITOR_STYLE_PRESET_DELETE"))
        self._btn_bg.setText(tr("EDITOR_BTN_BG"))
        self._btn_sci_defaults.setText(tr("EDITOR_SCI_DEFAULTS"))
        self._btn_save_as.setText(tr("EDITOR_SAVE_AS"))
        self._btn_svg.setText(tr("EDITOR_BTN_SAVE_SVG"))
        self._btn_png.setText(tr("EDITOR_BTN_SAVE_PNG"))
        self._btn_save_current.setText(
            tr("EDITOR_SAVE_SETTINGS") if self._static_file_mode else tr("EDITOR_SAVE_CURRENT")
        )
        self._refresh_style_preset_controls()

    def set_output_target(self, filepath):
        self._target_path = filepath or ""
        if self._target_path:
            self._target_label.setText(str(Path(self._target_path).name))
            self._btn_save_current.setEnabled(True)
            self._apply_saved_style(load_figure_edit(self._target_path))
        else:
            self._target_label.setText(tr("EDITOR_TARGET_NONE"))
            self._btn_save_current.setEnabled(False)

    def set_source_figure(self, filepath):
        """Edit persisted settings for an already-exported figure file."""
        self._source_path = filepath or ""
        self._static_file_mode = bool(self._source_path)
        self._fig_generator = None
        self._fig_args = ()
        self._fig_kwargs = {}

        # Keep BOTH preview AND canvas visible for live style feedback
        self._toolbar.setVisible(False)
        self._canvas.setVisible(True)
        self._source_preview.setVisible(True)
        self._set_export_buttons_enabled(False)
        self._btn_save_current.setText(tr("EDITOR_SAVE_SETTINGS"))

        if self._source_path:
            self._source_preview.load_figure(self._source_path)
            self.set_output_target(self._source_path)
            self._status_label.setText(tr("EDITOR_STATIC_MODE_HINT"))
            # Show a minimal live figure so style changes are visible
            self._show_style_preview_figure()
        else:
            self._source_preview.clear()
            self.set_output_target("")

    def set_initial_labels(self, title="", xlabel="", ylabel=""):
        self._set_line_edit(self._title_edit, title or "")
        self._set_line_edit(self._xlabel_edit, xlabel or "")
        self._set_line_edit(self._ylabel_edit, ylabel or "")
        self._render()

    def set_figure_generator(self, func, *args, **kwargs):
        self._static_file_mode = False
        self._source_path = ""
        self._toolbar.setVisible(True)
        self._canvas.setVisible(True)
        self._source_preview.setVisible(False)
        self._set_export_buttons_enabled(True)
        self._btn_save_current.setText(tr("EDITOR_SAVE_CURRENT"))
        self._fig_generator = func
        self._fig_args = args
        self._fig_kwargs = kwargs
        self._render()

    def is_static_file_mode(self):
        return self._static_file_mode

    def _set_export_buttons_enabled(self, enabled):
        for button in (self._btn_save_as, self._btn_svg, self._btn_png):
            button.setEnabled(enabled)

    def save_to_target(self):
        if not self._target_path:
            self.save_as()
            return
        self._save_to_path(self._target_path)

    def save_as(self, fmt=None):
        selected_filter = ""
        if fmt:
            selected_filter = f"{fmt.upper()} (*.{fmt})"
            filters = selected_filter
            default_name = f"figure.{fmt}"
        else:
            filters = "SVG (*.svg);;PNG (*.png);;PDF (*.pdf);;JPG (*.jpg)"
            default_name = Path(self._target_path).name if self._target_path else "figure.svg"
        path, _ = QFileDialog.getSaveFileName(
            self, tr("EDITOR_SAVE_DIALOG_TITLE"), default_name, filters
        )
        if path:
            if fmt and not path.lower().endswith(f".{fmt}"):
                path = f"{path}.{fmt}"
            self._save_to_path(path)
            self.set_output_target(path)

    def _render(self, *_):
        if self._fig_generator is None:
            if self._static_file_mode:
                self._show_style_preview_figure()
            return

        # Apply global SCI style baseline BEFORE creating axes
        _apply_sci_style(font_size=8.0)

        fig = Figure(figsize=self._fig_size, dpi=self._dpi, facecolor=self._bg_color)
        ax = fig.add_subplot(111)
        try:
            self._fig_generator(ax, *self._fig_args, **self._fig_kwargs)
        except Exception as exc:
            import sys as _sys

            _sys.stderr.write(f"ChartEditor render failed: {exc}\n")
            logger.warning("异常已处理", exc_info=True)

        # Recolour lines (user palette overrides SCI baseline)
        for i, line in enumerate(ax.lines):
            line.set_color(self._current_colours[i % len(self._current_colours)])
            line.set_linewidth(self._line_width)

        # Recolour collections (fill_between, scatter, etc.)
        for i, coll in enumerate(ax.collections):
            try:
                coll.set_color(self._current_colours[i % len(self._current_colours)])
            except Exception:
                try:
                    coll.set_edgecolor(self._current_colours[i % len(self._current_colours)])
                except Exception:
                    logger.warning("静默异常", exc_info=True)

        # Recolour patches (bar charts, rectangles)
        for i, patch in enumerate(ax.patches):
            try:
                patch.set_facecolor(self._current_colours[i % len(self._current_colours)])
            except Exception:
                logger.warning("静默异常", exc_info=True)

        # Recolour error bars (containers)
        for container in ax.containers:
            try:
                for child in container.get_children():
                    child.set_color(self._current_colours[0])
                    child.set_linewidth(self._line_width)
            except Exception:
                logger.warning("静默异常", exc_info=True)

        # Resize text annotations to match current font size
        for txt in ax.texts:
            try:
                txt.set_fontsize(max(6, self._label_size - 2))
            except Exception:
                logger.warning("静默异常", exc_info=True)

        # Resize legend if present
        legend = ax.get_legend()
        if legend is not None:
            try:
                for leg_text in legend.get_texts():
                    leg_text.set_fontsize(self._tick_size)
            except Exception:
                logger.warning("静默异常", exc_info=True)

        title = self._title_edit.text()
        if title:
            ax.set_title(title, fontsize=self._title_size, fontweight="bold")

        xlabel = self._xlabel_edit.text()
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=self._label_size)

        ylabel = self._ylabel_edit.text()
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=self._label_size)

        ax.tick_params(labelsize=self._tick_size)
        ax.grid(
            self._grid_on,
            alpha=self._grid_alpha,
            linestyle="--",
            linewidth=0.5,
        )
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)

        import matplotlib.pyplot as plt

        old = self._canvas.figure
        self._canvas.figure = fig
        self._figure = fig
        self._canvas.draw()
        if old:
            plt.close(old)
        self.figure_changed.emit()

    def _save_to_path(self, filepath):
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        if self._fig_generator is None:
            if self._static_file_mode and self._source_path:
                source = Path(self._source_path)
                if source.exists() and source.resolve() != path.resolve():
                    shutil.copy2(source, path)
                state_path, _ = save_figure_edit(str(path), self._collect_style_state())
                self._status_label.setText(tr("EDITOR_SAVE_STATE_DONE", state_path.name))
                self.figure_saved.emit(str(path))
                return
            self._status_label.setText(tr("EDITOR_NO_DATA"))
            return

        # Save edit state FIRST so savefig_with_edits can apply it
        state_path, _ = save_figure_edit(str(path), self._collect_style_state())

        ext = path.suffix.lower().lstrip(".") or "svg"
        if ext == "jpg":
            ext = "jpeg"

        from ...core.plot_edits import savefig_with_edits
        try:
            savefig_with_edits(
                self._figure, str(path),
                format=ext,
                dpi=300 if ext in {"png", "jpeg", "jpg", "tiff"} else self._dpi,
                bbox_inches="tight",
                facecolor=self._bg_color,
            )
        except Exception:
            # Fallback: direct save if edit apply fails
            self._figure.savefig(
                str(path), format=ext,
                dpi=300 if ext in {"png", "jpeg", "jpg", "tiff"} else self._dpi,
                bbox_inches="tight", facecolor=self._bg_color,
            )
            logger.warning("异常已处理", exc_info=True)

        self._status_label.setText(tr("EDITOR_SAVE_DONE", state_path.name))
        self.figure_saved.emit(str(path))

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
                logger.warning("闈欓粯寮傚父", exc_info=True)
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
            names = list_style_presets()
        current_name = self._current_style_preset_name()
        has_existing = bool(current_name) and current_name in names
        self._btn_style_preset_save.setEnabled(True)
        self._btn_style_preset_apply.setEnabled(has_existing)
        self._btn_style_preset_delete.setEnabled(has_existing)

    def _refresh_style_preset_controls(self):
        names = list_style_presets()
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

    def _on_save_style_preset(self):
        preset_name = self._current_style_preset_name()
        if not preset_name:
            QMessageBox.warning(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_NAME_REQUIRED"),
            )
            return

        existing = load_style_preset(preset_name)
        if existing:
            reply = QMessageBox.question(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_OVERWRITE", preset_name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        path, _ = save_style_preset(preset_name, self._collect_style_preset_state())
        self._refresh_style_preset_controls()
        self._style_preset_combo.setEditText(preset_name)
        self._status_label.setText(tr("EDITOR_STYLE_PRESET_SAVED", preset_name, path.name))

    def _on_apply_style_preset(self):
        preset_name = self._current_style_preset_name()
        if not preset_name:
            QMessageBox.warning(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_NAME_REQUIRED"),
            )
            return

        style = load_style_preset(preset_name)
        if not style:
            QMessageBox.warning(
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
        if not preset_name:
            QMessageBox.warning(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_NAME_REQUIRED"),
            )
            return

        if not load_style_preset(preset_name):
            QMessageBox.warning(
                self,
                tr("EDITOR_STYLE_PRESET_TITLE"),
                tr("EDITOR_STYLE_PRESET_MISSING", preset_name),
            )
            self._refresh_style_preset_controls()
            return

        reply = QMessageBox.question(
            self,
            tr("EDITOR_STYLE_PRESET_TITLE"),
            tr("EDITOR_STYLE_PRESET_DELETE_CONFIRM", preset_name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        delete_style_preset(preset_name)
        self._refresh_style_preset_controls()
        self._style_preset_combo.setEditText("")
        self._status_label.setText(tr("EDITOR_STYLE_PRESET_DELETED", preset_name))

    def _set_line_edit(self, widget, value):
        widget.blockSignals(True)
        widget.setText(value)
        widget.blockSignals(False)

    def _set_combo(self, combo, value):
        if not value:
            return
        idx = combo.findText(value)
        if idx >= 0:
            combo.blockSignals(True)
            combo.setCurrentIndex(idx)
            combo.blockSignals(False)
            if combo is self._colour_cb:
                self._current_colours = list(COLOUR_SCHEMES[value])
            elif combo is self._font_cb:
                self._set_font_size(value)
            elif combo is self._lw_cb:
                self._line_width = LINE_WIDTHS[value]
            elif combo is self._figsize_cb:
                self._fig_size = FIGURE_SIZES[value]

    def _on_colour_scheme_changed(self, name):
        self._current_colours = list(COLOUR_SCHEMES[name])
        self._render()

    def _on_font_changed(self, name):
        self._set_font_size(name)
        self._render()

    def _set_font_size(self, name):
        size = FONT_SIZES[name]
        self._title_size = size + 2
        self._label_size = size
        self._tick_size = max(6, size - 1)

    def _on_line_width_changed(self, name):
        self._line_width = LINE_WIDTHS[name]
        self._render()

    def _on_figure_size_changed(self, name):
        self._fig_size = FIGURE_SIZES[name]
        self._render()

    def _on_grid_toggled(self, value):
        self._grid_on = value
        self._render()

    def _on_grid_alpha_changed(self, value):
        self._grid_alpha = value / 10.0
        self._render()

    def _pick_bg(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self._bg_color = color.name()
            self._render()

    def _show_style_preview_figure(self):
        """Create a placeholder figure showing current style (used in static file mode)."""
        _apply_sci_style(font_size=8.0)

        fig = Figure(figsize=self._fig_size, dpi=self._dpi, facecolor=self._bg_color)
        ax = fig.add_subplot(111)

        # Draw placeholder data so style changes are visible
        import numpy as np
        x = np.linspace(0, 10, 200)
        for i, color in enumerate(self._current_colours[:3]):
            ax.plot(x, np.sin(x + i * 1.5) + i * 2,
                    color=color, linewidth=self._line_width,
                    label=f"Curve {i + 1}")

        # Apply current title/labels
        title = self._title_edit.text()
        if title:
            ax.set_title(title, fontsize=self._title_size, fontweight="bold")

        xlabel = self._xlabel_edit.text()
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=self._label_size)

        ylabel = self._ylabel_edit.text()
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=self._label_size)

        ax.tick_params(labelsize=self._tick_size)
        ax.grid(self._grid_on, alpha=self._grid_alpha, linestyle="--", linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_linewidth(0.8)

        if self._current_colours:
            ax.legend(fontsize=self._tick_size, frameon=False)
        ax.text(0.02, 0.98, "Style Preview — data for illustration only",
                transform=ax.transAxes, fontsize=7, color="#999999",
                va="top", ha="left")

        import matplotlib.pyplot as plt
        old = self._canvas.figure
        self._canvas.figure = fig
        self._figure = fig
        self._canvas.draw()
        if old:
            plt.close(old)

    def _apply_sci_defaults(self):
        """Reset all ChartEditor controls to SCI journal defaults."""
        # SCI journal standard: 8pt base, white bg, Wong palette, no grid, ~single-col size
        self._set_line_edit(self._title_edit, "")
        self._bg_color = "#FFFFFF"

        # Colour → Wong (SCI)
        idx = self._colour_cb.findText("Wong (SCI)")
        if idx >= 0:
            self._colour_cb.setCurrentIndex(idx)
        self._current_colours = list(COLOUR_SCHEMES["Wong (SCI)"])

        # Font → Small (8pt base)
        idx = self._font_cb.findText("Small")
        if idx >= 0:
            self._font_cb.setCurrentIndex(idx)
        self._set_font_size("Small")

        # Line → Normal (1.0pt)
        idx = self._lw_cb.findText("Normal")
        if idx >= 0:
            self._lw_cb.setCurrentIndex(idx)
        self._line_width = LINE_WIDTHS["Normal"]

        # Figure size → Small (4in), closest to single-col (3.35in)
        idx = self._figsize_cb.findText("Small (4in)")
        if idx >= 0:
            self._figsize_cb.setCurrentIndex(idx)
        self._fig_size = FIGURE_SIZES["Small (4in)"]

        # Grid → OFF
        self._grid_cb.setChecked(False)
        self._grid_on = False
        self._grid_alpha = 0.0

        self._render()
        self._status_label.setText(tr("EDITOR_APPLY_SCI_DONE"))


def make_line_plot(ax, x, y, title="", xlabel="X", ylabel="Y", label="Data", **kw):
    ax.plot(x, y, label=label, **kw)
    ax.legend()
    return ax


def make_bar_plot(ax, labels, values, title="", ylabel="Value", colors=None, **kw):
    if colors is None:
        colors = ["#2166AC", "#B2182B", "#1B7837", "#E69F00", "#762A83"]
    ax.bar(
        range(len(labels)),
        values,
        color=colors[: len(labels)],
        edgecolor="white",
        linewidth=0.5,
    )
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    return ax
