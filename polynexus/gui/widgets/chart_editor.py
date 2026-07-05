"""Live chart editor and exported-figure settings panel."""

import logging
logger = logging.getLogger(__name__)

import shutil
from pathlib import Path

from PySide6.QtCore import QRect, QRectF, QSize, QSizeF, Qt, Signal
from PySide6.QtGui import QImage, QPageSize, QPainter, QPdfWriter
from PySide6.QtSvg import QSvgGenerator
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
    QDoubleSpinBox,
    QSlider,
    QSpinBox,
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
from .annotation_canvas import AnnotationCanvas
from .chart_viewer import FigureFilePreview
from ...core.figure_assets import discover_figure_asset
from ...core.plot_edits import (
    COLOUR_SCHEMES,
    FIGURE_SIZES,
    FONT_SIZES,
    LINE_WIDTHS,
    delete_style_preset,
    load_figure_edit,
    load_figure_annotations,
    load_style_preset,
    list_style_presets,
    save_figure_annotations,
    save_figure_asset_spec,
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
        self._asset_spec = None
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
        self._annotation_canvas = AnnotationCanvas()
        self._annotation_canvas.setVisible(False)
        self._annotation_canvas.tool_changed.connect(self._sync_annotation_tool_buttons)
        self._annotation_canvas.selection_changed.connect(self._sync_annotation_property_controls)
        figure_layout.addWidget(self._toolbar)
        figure_layout.addWidget(self._canvas, 1)
        figure_layout.addWidget(self._source_preview, 1)
        figure_layout.addWidget(self._annotation_canvas, 1)
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

        annotation_text_row = QWidget()
        annotation_text_layout = QHBoxLayout(annotation_text_row)
        annotation_text_layout.setContentsMargins(0, 0, 0, 0)
        annotation_text_layout.setSpacing(6)

        self._annotation_text_edit = QLineEdit()
        self._annotation_text_edit.setPlaceholderText(
            tr("EDITOR_ANNOTATION_TEXT_PLACEHOLDER")
        )
        annotation_text_layout.addWidget(self._annotation_text_edit, 1)

        self._btn_annotation_add_text = QPushButton(tr("EDITOR_ANNOTATION_ADD_TEXT"))
        self._btn_annotation_add_text.clicked.connect(self._on_add_text_annotation)
        annotation_text_layout.addWidget(self._btn_annotation_add_text)

        self._btn_annotation_update_text = QPushButton(
            tr("EDITOR_ANNOTATION_UPDATE_TEXT")
        )
        self._btn_annotation_update_text.clicked.connect(
            self._on_update_selected_text_annotation
        )
        annotation_text_layout.addWidget(self._btn_annotation_update_text)
        form.addRow(annotation_text_row)

        annotation_style = QWidget()
        annotation_style_layout = QHBoxLayout(annotation_style)
        annotation_style_layout.setContentsMargins(0, 0, 0, 0)
        annotation_style_layout.setSpacing(6)

        self._annotation_color_edit = QLineEdit("#D55E00")
        self._annotation_color_edit.setPlaceholderText("#RRGGBB")
        annotation_style_layout.addWidget(self._annotation_color_edit, 1)

        self._annotation_font_size_spin = QSpinBox()
        self._annotation_font_size_spin.setRange(6, 72)
        self._annotation_font_size_spin.setValue(12)
        self._annotation_font_size_spin.setSuffix(" pt")
        annotation_style_layout.addWidget(self._annotation_font_size_spin)

        self._annotation_line_width_spin = QDoubleSpinBox()
        self._annotation_line_width_spin.setRange(0.1, 20.0)
        self._annotation_line_width_spin.setSingleStep(0.5)
        self._annotation_line_width_spin.setValue(2.0)
        self._annotation_line_width_spin.setSuffix(" px")
        annotation_style_layout.addWidget(self._annotation_line_width_spin)

        self._annotation_alpha_spin = QDoubleSpinBox()
        self._annotation_alpha_spin.setRange(0.0, 1.0)
        self._annotation_alpha_spin.setSingleStep(0.05)
        self._annotation_alpha_spin.setValue(0.35)
        annotation_style_layout.addWidget(self._annotation_alpha_spin)

        self._btn_annotation_apply_style = QPushButton(
            tr("EDITOR_ANNOTATION_APPLY_STYLE")
        )
        self._btn_annotation_apply_style.clicked.connect(self._on_annotation_apply_style)
        annotation_style_layout.addWidget(self._btn_annotation_apply_style)
        form.addRow(tr("EDITOR_ANNOTATION_STYLE_LABEL"), annotation_style)

        annotation_actions = QWidget()
        annotation_actions_layout = QHBoxLayout(annotation_actions)
        annotation_actions_layout.setContentsMargins(0, 0, 0, 0)
        annotation_actions_layout.setSpacing(6)

        self._btn_annotation_add_line = QPushButton(tr("EDITOR_ANNOTATION_ADD_LINE"))
        self._btn_annotation_add_line.setCheckable(True)
        self._btn_annotation_add_line.clicked.connect(self._on_add_line_annotation)
        annotation_actions_layout.addWidget(self._btn_annotation_add_line)

        self._btn_annotation_add_arrow = QPushButton(tr("EDITOR_ANNOTATION_ADD_ARROW"))
        self._btn_annotation_add_arrow.setCheckable(True)
        self._btn_annotation_add_arrow.clicked.connect(self._on_add_arrow_annotation)
        annotation_actions_layout.addWidget(self._btn_annotation_add_arrow)

        self._btn_annotation_add_rect = QPushButton(tr("EDITOR_ANNOTATION_ADD_RECT"))
        self._btn_annotation_add_rect.setCheckable(True)
        self._btn_annotation_add_rect.clicked.connect(self._on_add_rectangle_annotation)
        annotation_actions_layout.addWidget(self._btn_annotation_add_rect)

        self._btn_annotation_add_highlight = QPushButton(
            tr("EDITOR_ANNOTATION_ADD_HIGHLIGHT")
        )
        self._btn_annotation_add_highlight.setCheckable(True)
        self._btn_annotation_add_highlight.clicked.connect(
            self._on_add_highlight_annotation
        )
        annotation_actions_layout.addWidget(self._btn_annotation_add_highlight)

        self._btn_annotation_delete = QPushButton(tr("EDITOR_ANNOTATION_DELETE"))
        self._btn_annotation_delete.clicked.connect(self._on_annotation_delete)
        annotation_actions_layout.addWidget(self._btn_annotation_delete)

        self._btn_annotation_copy = QPushButton(tr("EDITOR_ANNOTATION_COPY"))
        self._btn_annotation_copy.clicked.connect(self._on_annotation_copy)
        annotation_actions_layout.addWidget(self._btn_annotation_copy)

        self._btn_annotation_paste = QPushButton(tr("EDITOR_ANNOTATION_PASTE"))
        self._btn_annotation_paste.clicked.connect(self._on_annotation_paste)
        annotation_actions_layout.addWidget(self._btn_annotation_paste)

        self._btn_annotation_front = QPushButton(tr("EDITOR_ANNOTATION_FRONT"))
        self._btn_annotation_front.clicked.connect(self._on_annotation_front)
        annotation_actions_layout.addWidget(self._btn_annotation_front)

        self._btn_annotation_back = QPushButton(tr("EDITOR_ANNOTATION_BACK"))
        self._btn_annotation_back.clicked.connect(self._on_annotation_back)
        annotation_actions_layout.addWidget(self._btn_annotation_back)

        self._btn_annotation_undo = QPushButton(tr("EDITOR_ANNOTATION_UNDO"))
        self._btn_annotation_undo.clicked.connect(self._on_annotation_undo)
        annotation_actions_layout.addWidget(self._btn_annotation_undo)

        self._btn_annotation_redo = QPushButton(tr("EDITOR_ANNOTATION_REDO"))
        self._btn_annotation_redo.clicked.connect(self._on_annotation_redo)
        annotation_actions_layout.addWidget(self._btn_annotation_redo)
        form.addRow(annotation_actions)

        annotation_zoom = QWidget()
        annotation_zoom_layout = QHBoxLayout(annotation_zoom)
        annotation_zoom_layout.setContentsMargins(0, 0, 0, 0)
        annotation_zoom_layout.setSpacing(6)

        self._btn_annotation_fit = QPushButton(tr("EDITOR_ANNOTATION_FIT"))
        self._btn_annotation_fit.clicked.connect(self._on_annotation_fit)
        annotation_zoom_layout.addWidget(self._btn_annotation_fit)

        self._btn_annotation_zoom_100 = QPushButton(tr("EDITOR_ANNOTATION_ZOOM_100"))
        self._btn_annotation_zoom_100.clicked.connect(self._on_annotation_zoom_100)
        annotation_zoom_layout.addWidget(self._btn_annotation_zoom_100)

        self._btn_annotation_zoom_out = QPushButton(tr("EDITOR_ANNOTATION_ZOOM_OUT"))
        self._btn_annotation_zoom_out.clicked.connect(self._on_annotation_zoom_out)
        annotation_zoom_layout.addWidget(self._btn_annotation_zoom_out)

        self._btn_annotation_zoom_in = QPushButton(tr("EDITOR_ANNOTATION_ZOOM_IN"))
        self._btn_annotation_zoom_in.clicked.connect(self._on_annotation_zoom_in)
        annotation_zoom_layout.addWidget(self._btn_annotation_zoom_in)
        form.addRow(annotation_zoom)

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
        self._annotation_text_edit.setPlaceholderText(
            tr("EDITOR_ANNOTATION_TEXT_PLACEHOLDER")
        )
        self._btn_annotation_add_text.setText(tr("EDITOR_ANNOTATION_ADD_TEXT"))
        self._btn_annotation_update_text.setText(
            tr("EDITOR_ANNOTATION_UPDATE_TEXT")
        )
        self._btn_annotation_apply_style.setText(
            tr("EDITOR_ANNOTATION_APPLY_STYLE")
        )
        label = self._form.labelForField(self._annotation_color_edit.parentWidget())
        if label is not None:
            label.setText(tr("EDITOR_ANNOTATION_STYLE_LABEL"))
        self._btn_annotation_add_line.setText(tr("EDITOR_ANNOTATION_ADD_LINE"))
        self._btn_annotation_add_arrow.setText(tr("EDITOR_ANNOTATION_ADD_ARROW"))
        self._btn_annotation_add_rect.setText(tr("EDITOR_ANNOTATION_ADD_RECT"))
        self._btn_annotation_add_highlight.setText(
            tr("EDITOR_ANNOTATION_ADD_HIGHLIGHT")
        )
        self._btn_annotation_delete.setText(tr("EDITOR_ANNOTATION_DELETE"))
        self._btn_annotation_copy.setText(tr("EDITOR_ANNOTATION_COPY"))
        self._btn_annotation_paste.setText(tr("EDITOR_ANNOTATION_PASTE"))
        self._btn_annotation_front.setText(tr("EDITOR_ANNOTATION_FRONT"))
        self._btn_annotation_back.setText(tr("EDITOR_ANNOTATION_BACK"))
        self._btn_annotation_undo.setText(tr("EDITOR_ANNOTATION_UNDO"))
        self._btn_annotation_redo.setText(tr("EDITOR_ANNOTATION_REDO"))
        self._btn_annotation_fit.setText(tr("EDITOR_ANNOTATION_FIT"))
        self._btn_annotation_zoom_100.setText(tr("EDITOR_ANNOTATION_ZOOM_100"))
        self._btn_annotation_zoom_out.setText(tr("EDITOR_ANNOTATION_ZOOM_OUT"))
        self._btn_annotation_zoom_in.setText(tr("EDITOR_ANNOTATION_ZOOM_IN"))
        self._btn_sci_defaults.setText(tr("EDITOR_SCI_DEFAULTS"))
        self._btn_save_as.setText(tr("EDITOR_SAVE_AS"))
        self._btn_svg.setText(tr("EDITOR_BTN_SAVE_SVG"))
        self._btn_png.setText(tr("EDITOR_BTN_SAVE_PNG"))
        self._btn_save_current.setText(tr("EDITOR_SAVE_CURRENT"))
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
        self._asset_spec = None
        self._static_file_mode = bool(self._source_path)
        self._fig_generator = None
        self._fig_args = ()
        self._fig_kwargs = {}

        self._toolbar.setVisible(False)
        self._canvas.setVisible(False)
        self._source_preview.setVisible(False)
        self._annotation_canvas.setVisible(False)
        self._set_export_buttons_enabled(False)
        self._btn_save_current.setText(tr("EDITOR_SAVE_CURRENT"))

        if self._source_path:
            self._asset_spec = discover_figure_asset(self._source_path)
            self._source_preview.load_figure(self._source_path)
            self.set_output_target(self._source_path)
            self._status_label.setText(tr("EDITOR_STATIC_MODE_HINT"))
            if self._annotation_canvas.load_image(self._asset_spec.preview_path):
                self._annotation_canvas.load_annotation_state(
                    load_figure_annotations(self._source_path)
                )
                self._annotation_canvas.setVisible(True)
            else:
                self._source_preview.setVisible(True)
                self._canvas.setVisible(True)
                self._show_style_preview_figure()
        else:
            self._source_preview.clear()
            self._annotation_canvas.setVisible(False)
            self.set_output_target("")

    def set_initial_labels(self, title="", xlabel="", ylabel=""):
        self._set_line_edit(self._title_edit, title or "")
        self._set_line_edit(self._xlabel_edit, xlabel or "")
        self._set_line_edit(self._ylabel_edit, ylabel or "")
        self._render()

    def set_figure_generator(self, func, *args, **kwargs):
        self._static_file_mode = False
        self._source_path = ""
        self._asset_spec = None
        self._toolbar.setVisible(True)
        self._canvas.setVisible(True)
        self._source_preview.setVisible(False)
        self._annotation_canvas.setVisible(False)
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
            logger.warning("Chart editor render failed.", exc_info=True)

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
                    logger.warning("Chart editor collection recolor failed.", exc_info=True)

        # Recolour patches (bar charts, rectangles)
        for i, patch in enumerate(ax.patches):
            try:
                patch.set_facecolor(self._current_colours[i % len(self._current_colours)])
            except Exception:
                logger.warning("Chart editor patch recolor failed.", exc_info=True)

        # Recolour error bars (containers)
        for container in ax.containers:
            try:
                for child in container.get_children():
                    child.set_color(self._current_colours[0])
                    child.set_linewidth(self._line_width)
            except Exception:
                logger.warning("Chart editor errorbar recolor failed.", exc_info=True)

        # Resize text annotations to match current font size
        for txt in ax.texts:
            try:
                txt.set_fontsize(max(6, self._label_size - 2))
            except Exception:
                logger.warning("Chart editor text resize failed.", exc_info=True)

        # Resize legend if present
        legend = ax.get_legend()
        if legend is not None:
            try:
                for leg_text in legend.get_texts():
                    leg_text.set_fontsize(self._tick_size)
            except Exception:
                logger.warning("Chart editor legend resize failed.", exc_info=True)

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
                self._backup_current_static_source(path)
                state_path, _ = save_figure_edit(str(path), self._collect_style_state())
                annotations = self._annotation_state()
                save_figure_annotations(str(path), annotations)
                save_figure_asset_spec(
                    str(path),
                    discover_figure_asset(str(path)).to_dict(),
                )
                if annotations and self._save_static_canvas_to_path(path):
                    pass
                elif not self._save_static_rendered_figure(path):
                    source = Path(self._source_path)
                    if source.exists() and source.resolve() != path.resolve():
                        shutil.copy2(source, path)
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
            logger.warning("Chart editor save-with-edits failed; using direct save.", exc_info=True)
            self._figure.savefig(
                str(path), format=ext,
                dpi=300 if ext in {"png", "jpeg", "jpg", "tiff"} else self._dpi,
                bbox_inches="tight", facecolor=self._bg_color,
            )

        self._status_label.setText(tr("EDITOR_SAVE_DONE", state_path.name))
        self.figure_saved.emit(str(path))

    def _backup_current_static_source(self, path):
        if not self._source_path:
            return None
        source = Path(self._source_path)
        if not source.exists():
            return None
        if source.resolve() != path.resolve():
            return None
        backup_path = path.with_name(f"{path.name}.bak")
        if backup_path.exists():
            return backup_path
        shutil.copy2(path, backup_path)
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
                logger.warning("Chart editor DPI restore failed; keeping current DPI.", exc_info=True)
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

    def _on_add_text_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        text = self._annotation_text_edit.text().strip() or "Annotation"
        self._annotation_canvas.add_text_annotation(text, 20, 20)
        self.figure_changed.emit()

    def _on_update_selected_text_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        text = self._annotation_text_edit.text().strip()
        if text and self._annotation_canvas.update_selected_text(text):
            self.figure_changed.emit()

    def _on_annotation_apply_style(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        color = self._annotation_color_edit.text().strip() or None
        if self._annotation_canvas.update_selected_properties(
            color=color,
            font_size=self._annotation_font_size_spin.value(),
            line_width=self._annotation_line_width_spin.value(),
            alpha=self._annotation_alpha_spin.value(),
        ):
            self.figure_changed.emit()

    def _on_add_rectangle_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.set_tool("rectangle")

    def _on_add_line_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.set_tool("line")

    def _on_add_arrow_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.set_tool("arrow")

    def _on_add_highlight_annotation(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.set_tool("highlight")

    def _on_annotation_undo(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.undo():
            self.figure_changed.emit()

    def _on_annotation_redo(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.redo():
            self.figure_changed.emit()

    def _on_annotation_delete(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.delete_selected_annotation():
            self.figure_changed.emit()

    def _on_annotation_copy(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.copy_selected_annotation()

    def _on_annotation_paste(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.paste_annotation():
            self.figure_changed.emit()

    def _on_annotation_front(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.bring_selected_to_front():
            self.figure_changed.emit()

    def _on_annotation_back(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        if self._annotation_canvas.send_selected_to_back():
            self.figure_changed.emit()

    def _sync_annotation_tool_buttons(self, tool):
        mapping = {
            "line": self._btn_annotation_add_line,
            "arrow": self._btn_annotation_add_arrow,
            "rectangle": self._btn_annotation_add_rect,
            "highlight": self._btn_annotation_add_highlight,
        }
        for name, button in mapping.items():
            button.blockSignals(True)
            button.setChecked(name == tool)
            button.blockSignals(False)

    def _sync_annotation_property_controls(self, _annotation_id=""):
        if self._annotation_canvas is None:
            return
        annotation = self._annotation_canvas.selected_annotation()
        if not annotation:
            return
        color = str(annotation.get("color", "") or "")
        if color:
            self._annotation_color_edit.blockSignals(True)
            self._annotation_color_edit.setText(color)
            self._annotation_color_edit.blockSignals(False)
        if "font_size" in annotation:
            self._annotation_font_size_spin.blockSignals(True)
            self._annotation_font_size_spin.setValue(int(annotation.get("font_size", 12) or 12))
            self._annotation_font_size_spin.blockSignals(False)
        if "line_width" in annotation:
            self._annotation_line_width_spin.blockSignals(True)
            self._annotation_line_width_spin.setValue(float(annotation.get("line_width", 2.0) or 2.0))
            self._annotation_line_width_spin.blockSignals(False)
        if "alpha" in annotation:
            self._annotation_alpha_spin.blockSignals(True)
            self._annotation_alpha_spin.setValue(float(annotation.get("alpha", 0.35) or 0.35))
            self._annotation_alpha_spin.blockSignals(False)

    def _on_annotation_fit(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.fit_to_window()

    def _on_annotation_zoom_100(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.set_zoom_100()

    def _on_annotation_zoom_out(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.zoom_out()

    def _on_annotation_zoom_in(self):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return
        self._annotation_canvas.zoom_in()

    def _show_style_preview_figure(self):
        """Create a live preview for static-file edits."""
        if self._source_path and self._show_source_image_figure():
            return

        self._show_placeholder_style_preview()

    def _show_source_image_figure(self):
        image = self._load_source_image_array()
        if image is None:
            return False

        fig = Figure(figsize=self._fig_size, dpi=self._dpi, facecolor=self._bg_color)
        ax = fig.add_subplot(111)
        ax.imshow(image)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

        title = self._title_edit.text()
        if title:
            ax.set_title(title, fontsize=self._title_size, fontweight="bold")

        xlabel = self._xlabel_edit.text()
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=self._label_size)

        ylabel = self._ylabel_edit.text()
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=self._label_size)

        fig.tight_layout()
        self._replace_canvas_figure(fig)
        return True

    def _load_source_image_array(self):
        if not self._source_path:
            return None
        try:
            pixmap = self._source_preview._load_pixmap(self._source_path)
            if pixmap is None or pixmap.isNull():
                return None
            image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
            width = image.width()
            height = image.height()
            if width <= 0 or height <= 0:
                return None
            bytes_per_line = image.bytesPerLine()
            buffer = bytes(image.constBits())
            import numpy as np

            array = np.frombuffer(buffer, dtype=np.uint8).reshape((height, bytes_per_line))
            array = array[:, : width * 4].reshape((height, width, 4))
            return array.copy()
        except Exception:
            logger.warning("Failed to render static source figure for editing.", exc_info=True)
            return None

    def _save_static_rendered_figure(self, path):
        if not self._show_source_image_figure():
            return False
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
            return True
        except Exception:
            logger.warning("Failed to save static rendered figure.", exc_info=True)
            return False

    def _save_static_canvas_to_path(self, path):
        if self._annotation_canvas is None or self._annotation_canvas.isHidden():
            return False
        ext = path.suffix.lower().lstrip(".") or "png"
        if ext == "jpg":
            ext = "jpeg"
        if ext in {"pdf", "svg"}:
            return self._save_static_canvas_vector(path, ext)
        image = self._annotation_canvas.render_to_image(self._bg_color)
        if image.isNull():
            return False
        if ext not in {"png", "jpeg", "jpg", "bmp", "tiff", "tif"}:
            return False
        return bool(image.save(str(path), ext.upper()))

    def _save_static_canvas_vector(self, path, ext):
        scene = self._annotation_canvas._scene
        rect = scene.sceneRect()
        if rect.isNull():
            return False

        width = max(1, int(rect.width()))
        height = max(1, int(rect.height()))
        if ext == "pdf":
            device = QPdfWriter(str(path))
            device.setResolution(72)
            device.setPageSize(QPageSize(QSizeF(width, height), QPageSize.Point))
        elif ext == "svg":
            device = QSvgGenerator()
            device.setFileName(str(path))
            device.setSize(QSize(width, height))
            device.setViewBox(QRect(0, 0, width, height))
        else:
            return False

        painter = QPainter()
        if not painter.begin(device):
            return False
        try:
            target = QRectF(0, 0, width, height)
            painter.fillRect(target, self._bg_color)
            scene.render(painter, target, rect)
        finally:
            painter.end()
        return path.exists() and path.stat().st_size > 0

    def _replace_canvas_figure(self, fig):
        import matplotlib.pyplot as plt

        old = self._canvas.figure
        self._canvas.figure = fig
        self._figure = fig
        self._canvas.draw()
        if old:
            plt.close(old)

    def _show_placeholder_style_preview(self):
        """Create a placeholder figure showing current style when the source cannot render."""
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

        self._replace_canvas_figure(fig)

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
