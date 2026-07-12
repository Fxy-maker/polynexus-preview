"""Live chart editor and exported-figure settings panel."""

import logging
import shutil  # noqa: F401 - runtime API consumed by save mixin
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,  # noqa: F401 - runtime API consumed by save mixin
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,  # noqa: F401 - runtime API consumed by style-preset mixin
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
from ..chart_editor_plot_helpers import (
    make_bar_plot as _shared_make_bar_plot,
    make_line_plot as _shared_make_line_plot,
)
from .annotation_canvas import AnnotationCanvas
from .chart_editor_annotation_controls_mixin import (
    ChartEditorAnnotationControlsMixin,
)
from .chart_editor_generated_drag_mixin import ChartEditorGeneratedDragMixin
from .chart_editor_generated_drag_execution_mixin import (
    ChartEditorGeneratedDragExecutionMixin,
)
from .chart_editor_generated_document_mixin import (
    ChartEditorGeneratedDocumentMixin,
)
from .chart_editor_generated_hover_mixin import ChartEditorGeneratedHoverMixin
from .chart_editor_generated_hit_testing_mixin import (
    ChartEditorGeneratedHitTestingMixin,
)
from .chart_editor_generated_interaction_mixin import (
    ChartEditorGeneratedInteractionMixin,
)
from .chart_editor_generated_geometry_mixin import (
    ChartEditorGeneratedGeometryMixin,
)
from .chart_editor_generated_pointer_feedback_mixin import (
    ChartEditorGeneratedPointerFeedbackMixin,
)
from .chart_editor_generated_pick_mixin import ChartEditorGeneratedPickMixin
from .chart_editor_generated_press_target_mixin import (
    ChartEditorGeneratedPressTargetMixin,
)
from .chart_editor_render_mixin import ChartEditorRenderMixin
from .chart_editor_generated_selection_mixin import (
    ChartEditorGeneratedSelectionMixin,
)
from .chart_editor_generated_status_mixin import ChartEditorGeneratedStatusMixin
from .chart_editor_object_list_mixin import ChartEditorObjectListMixin
from .chart_editor_save_mixin import ChartEditorSaveMixin
from .chart_editor_style_preset_mixin import ChartEditorStylePresetMixin
from .chart_viewer import FigureFilePreview
from ..figure_render_adapter import FigureRenderAdapter
from ..figure_selection_model import FigureSelectionModel
from ...core.figure_document import (
    create_static_figure_document,  # noqa: F401 - runtime API for save mixin
    load_figure_document,
    save_figure_document,  # noqa: F401 - runtime API consumed by save mixin
)
from ...core.figure_assets import discover_figure_asset
from ...core.plot_edits import (
    COLOUR_SCHEMES,
    FIGURE_SIZES,
    FONT_SIZES,
    LINE_WIDTHS,
    delete_style_preset,  # noqa: F401 - runtime API for style-preset mixin
    load_figure_edit,
    load_figure_annotations,
    load_style_preset,  # noqa: F401 - runtime API for style-preset mixin
    list_style_presets,  # noqa: F401 - runtime API for style-preset mixin
    save_figure_annotations,  # noqa: F401 - runtime API for save mixin
    save_figure_asset_spec,  # noqa: F401 - runtime API for save mixin
    save_figure_document_path,  # noqa: F401 - runtime API for save mixin
    save_figure_edit,  # noqa: F401 - runtime API for save mixin
    save_style_preset,  # noqa: F401 - runtime API for style-preset mixin
)
from ...plotting.sci_style import set_sci_style as _apply_sci_style  # noqa: F401

logger = logging.getLogger(__name__)

LINE_STYLE_OPTIONS = {
    "Solid": "-",
    "Dashed": "--",
    "Dotted": ":",
    "Dash Dot": "-.",
}

MARKER_OPTIONS = {
    "None": "",
    "Circle": "o",
    "Square": "s",
    "Triangle": "^",
    "Diamond": "D",
    "Plus": "+",
    "Cross": "x",
}

GENERATED_DRAG_START_THRESHOLD_PX = 3.0
GENERATED_LINE_BODY_HIT_RADIUS_PX = 10.0
GENERATED_LINE_ENDPOINT_HIT_RADIUS_PX = 14.0
GENERATED_SCATTER_POINT_HIT_RADIUS_PX = 14.0
GENERATED_LINE_SERIES_BODY_HIT_RADIUS_PX = 10.0
GENERATED_MARKER_POINT_HIT_MAX_RADIUS_PX = 20.0


class ChartEditor(
    ChartEditorAnnotationControlsMixin,
    ChartEditorSaveMixin,
    ChartEditorStylePresetMixin,
    ChartEditorObjectListMixin,
    ChartEditorGeneratedDragMixin,
    ChartEditorGeneratedDragExecutionMixin,
    ChartEditorGeneratedDocumentMixin,
    ChartEditorGeneratedGeometryMixin,
    ChartEditorGeneratedHoverMixin,
    ChartEditorGeneratedHitTestingMixin,
    ChartEditorGeneratedInteractionMixin,
    ChartEditorGeneratedPointerFeedbackMixin,
    ChartEditorGeneratedPickMixin,
    ChartEditorGeneratedPressTargetMixin,
    ChartEditorRenderMixin,
    ChartEditorGeneratedSelectionMixin,
    ChartEditorGeneratedStatusMixin,
    QWidget,
):
    figure_changed = Signal()
    figure_saved = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fig_generator = None
        self._fig_args = ()
        self._fig_kwargs = {}
        self._target_path = ""
        self._source_path = ""
        self._source_entry_context = None
        self._force_static_source_mode = False
        self._mode_title_text = ""
        self._mode_banner_key = ""
        self._mode_summary_key = ""
        self._asset_spec = None
        self._figure_document = {}
        self._shared_render_plan = None
        self._generated_document_mode = False
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
        self._syncing_object_list = False
        self._syncing_geometry_controls = False
        self._selected_figure_object_id = ""
        self._hovered_figure_object_id = ""
        self._selection_status_text = ""
        self._selection_cycle_hint_active = False
        self._hover_status_text = ""
        self._drag_status_text = ""
        self._last_deleted_figure_object_id = ""
        self._last_generated_pick_signature = None
        self._last_generated_pick_candidates = []
        self._last_generated_pick_gui_event_id = None
        self._last_generated_pointer_state = None
        self._last_generated_pointer_drag_target = None
        self._suppress_generated_hover_until_pointer_move = False
        self._selected_generated_line_object_id = ""
        self._selected_generated_line_handle_index = None
        self._selected_generated_plot_series_object_id = ""
        self._selected_generated_plot_series_handle_index = None
        self._generated_last_line_handle_indices = {}
        self._generated_last_plot_series_handle_indices = {}
        self._hover_preview_figure_object_id = ""
        self._hover_preview_handle_index = None
        self._generated_handle_drag_state = None
        self._connected_canvas_figure = None
        self._figure_selection_model = FigureSelectionModel(self)
        self._figure_selection_model.selection_changed.connect(
            self._on_generated_selection_changed
        )
        self._figure_render_adapter = FigureRenderAdapter()
        self._build_ui()
        self._set_mode_header("")
        self._connect_canvas_interaction_events()

    def _build_ui(self):
        split = QSplitter(Qt.Horizontal)

        figure_panel = QWidget()
        figure_layout = QVBoxLayout(figure_panel)
        figure_layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(
            figsize=self._fig_size, dpi=self._dpi, facecolor=self._bg_color
        )
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setFocusPolicy(Qt.StrongFocus)
        self._canvas.installEventFilter(self)
        self._toolbar = NavToolbar(self._canvas, self)
        self._source_preview = FigureFilePreview(show_edit_button=False)
        self._source_preview.setVisible(False)
        self._annotation_canvas = AnnotationCanvas()
        self._annotation_canvas.setVisible(False)
        self._annotation_canvas.tool_changed.connect(self._sync_annotation_tool_buttons)
        self._annotation_canvas.selection_changed.connect(self._sync_annotation_property_controls)
        self._annotation_canvas.annotations_changed.connect(self._on_annotation_canvas_changed)
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

    def _connect_canvas_interaction_events(self):
        if self._canvas is None:
            return
        figure = getattr(self._canvas, "figure", None)
        if figure is None or figure is self._connected_canvas_figure:
            return
        self._connected_canvas_figure = figure
        self._canvas.mpl_connect("pick_event", self._on_generated_pick_event)
        self._canvas.mpl_connect("button_press_event", self._on_generated_button_press)
        self._canvas.mpl_connect("motion_notify_event", self._on_generated_mouse_move)
        self._canvas.mpl_connect("button_release_event", self._on_generated_button_release)
        self._canvas.mpl_connect("figure_leave_event", self._on_generated_figure_leave)

    def eventFilter(self, watched, event):
        if watched is getattr(self, "_canvas", None):
            if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                if self._generated_handle_drag_state and self._cancel_generated_drag():
                    event.accept()
                    return True
                if self._generated_document_mode and self._selected_figure_object_id:
                    self._select_generated_object("", "escape")
                    self._clear_generated_hover_highlight(redraw=False)
                    if not self._refresh_generated_feedback_from_last_pointer():
                        self._reset_generated_canvas_cursor()
                    event.accept()
                    return True
        if watched is getattr(self, "_object_list", None):
            if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                if self._generated_handle_drag_state and self._cancel_generated_drag():
                    event.accept()
                    return True
                if self._generated_document_mode and self._selected_figure_object_id:
                    self._select_generated_object("", "escape")
                    self._clear_generated_hover_highlight(redraw=False)
                    if not self._refresh_generated_feedback_from_last_pointer():
                        self._reset_generated_canvas_cursor()
                    event.accept()
                    return True
                if (
                    self._annotation_canvas is not None
                    and not self._annotation_canvas.isHidden()
                    and self._annotation_canvas.selected_annotation_id()
                ):
                    self._annotation_canvas.clear_selection()
                    event.accept()
                    return True
            if event.type() == QEvent.KeyPress and event.modifiers() & Qt.ControlModifier:
                item = self._object_list.currentItem()
                object_id = item.data(Qt.UserRole) if item is not None else ""
                object_role = item.data(Qt.UserRole + 1) if item is not None else ""
                if event.key() == Qt.Key_C:
                    if object_role == "annotation" and self._annotation_canvas is not None:
                        self._annotation_canvas.select_annotation(str(object_id))
                        if self._annotation_canvas.copy_selected_annotation():
                            event.accept()
                            return True
                if event.key() == Qt.Key_V and self._annotation_canvas is not None:
                    if self._annotation_canvas.paste_annotation():
                        self._refresh_object_list(self._annotation_canvas.selected_annotation_id())
                        event.accept()
                        return True
            if event.type() == QEvent.KeyPress and event.key() in {Qt.Key_Delete, Qt.Key_Backspace}:
                item = self._object_list.currentItem()
                object_id = item.data(Qt.UserRole) if item is not None else ""
                object_role = item.data(Qt.UserRole + 1) if item is not None else ""
                if object_role == "figure_object":
                    self._selected_figure_object_id = str(object_id or "")
                    self._soft_delete_selected_generated_object()
                    event.accept()
                    return True
                if object_role == "annotation" and self._annotation_canvas is not None:
                    self._annotation_canvas.select_annotation(str(object_id))
                    if self._annotation_canvas.delete_selected_annotation():
                        self._refresh_object_list()
                        event.accept()
                        return True
        return super().eventFilter(watched, event)

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

        self._mode_title_label = QLabel("")
        self._mode_title_label.setWordWrap(True)
        self._mode_title_label.setObjectName("editor_mode_title")
        form.addRow(self._mode_title_label)

        self._mode_banner_label = QLabel("")
        self._mode_banner_label.setWordWrap(True)
        self._mode_banner_label.setObjectName("editor_mode_banner")
        form.addRow(self._mode_banner_label)

        self._mode_summary_label = QLabel("")
        self._mode_summary_label.setWordWrap(True)
        self._mode_summary_label.setObjectName("editor_mode_summary")
        form.addRow(self._mode_summary_label)

        self._object_list = QListWidget()
        self._object_list.setMinimumHeight(96)
        self._object_list.installEventFilter(self)
        self._object_list.currentItemChanged.connect(
            self._on_object_list_selection_changed
        )
        self._object_list.itemChanged.connect(self._on_object_list_item_changed)
        form.addRow(tr("EDITOR_OBJECT_LIST_LABEL"), self._object_list)

        self._selected_object_label = QLabel(tr("EDITOR_OBJECT_BACKGROUND"))
        form.addRow(tr("EDITOR_SELECTED_OBJECT_LABEL"), self._selected_object_label)

        annotation_geometry = QWidget()
        annotation_geometry_layout = QHBoxLayout(annotation_geometry)
        annotation_geometry_layout.setContentsMargins(0, 0, 0, 0)
        annotation_geometry_layout.setSpacing(6)

        self._annotation_x_spin = QDoubleSpinBox()
        self._annotation_x_spin.setRange(0.0, 1.0)
        self._annotation_x_spin.setDecimals(4)
        self._annotation_x_spin.setSingleStep(0.01)
        self._annotation_x_spin.valueChanged.connect(self._on_annotation_geometry_changed)
        self._annotation_x_label = QLabel("X")
        annotation_geometry_layout.addWidget(self._annotation_x_label)
        annotation_geometry_layout.addWidget(self._annotation_x_spin)

        self._annotation_y_spin = QDoubleSpinBox()
        self._annotation_y_spin.setRange(0.0, 1.0)
        self._annotation_y_spin.setDecimals(4)
        self._annotation_y_spin.setSingleStep(0.01)
        self._annotation_y_spin.valueChanged.connect(self._on_annotation_geometry_changed)
        self._annotation_y_label = QLabel("Y")
        annotation_geometry_layout.addWidget(self._annotation_y_label)
        annotation_geometry_layout.addWidget(self._annotation_y_spin)

        self._annotation_w_spin = QDoubleSpinBox()
        self._annotation_w_spin.setRange(0.0, 1.0)
        self._annotation_w_spin.setDecimals(4)
        self._annotation_w_spin.setSingleStep(0.01)
        self._annotation_w_spin.valueChanged.connect(self._on_annotation_geometry_changed)
        self._annotation_w_label = QLabel("W")
        annotation_geometry_layout.addWidget(self._annotation_w_label)
        annotation_geometry_layout.addWidget(self._annotation_w_spin)

        self._annotation_h_spin = QDoubleSpinBox()
        self._annotation_h_spin.setRange(0.0, 1.0)
        self._annotation_h_spin.setDecimals(4)
        self._annotation_h_spin.setSingleStep(0.01)
        self._annotation_h_spin.valueChanged.connect(self._on_annotation_geometry_changed)
        self._annotation_h_label = QLabel("H")
        annotation_geometry_layout.addWidget(self._annotation_h_label)
        annotation_geometry_layout.addWidget(self._annotation_h_spin)
        form.addRow(tr("EDITOR_OBJECT_GEOMETRY_LABEL"), annotation_geometry)
        self._set_geometry_controls_enabled(False)

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
        self._btn_annotation_update_text.setEnabled(False)
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

        self._annotation_line_style_combo = QComboBox()
        self._annotation_line_style_combo.addItems(LINE_STYLE_OPTIONS.keys())
        self._annotation_line_style_combo.setCurrentText("Solid")
        annotation_style_layout.addWidget(self._annotation_line_style_combo)

        self._annotation_marker_combo = QComboBox()
        self._annotation_marker_combo.addItems(MARKER_OPTIONS.keys())
        self._annotation_marker_combo.setCurrentText("None")
        annotation_style_layout.addWidget(self._annotation_marker_combo)

        self._annotation_marker_size_spin = QDoubleSpinBox()
        self._annotation_marker_size_spin.setRange(1.0, 40.0)
        self._annotation_marker_size_spin.setSingleStep(1.0)
        self._annotation_marker_size_spin.setValue(6.0)
        self._annotation_marker_size_spin.setSuffix(" pt")
        annotation_style_layout.addWidget(self._annotation_marker_size_spin)
        self._set_style_controls_enabled(False, False, False, color_enabled=False)

        self._btn_annotation_apply_style = QPushButton(
            tr("EDITOR_ANNOTATION_APPLY_STYLE")
        )
        self._btn_annotation_apply_style.clicked.connect(self._on_annotation_apply_style)
        annotation_style_layout.addWidget(self._btn_annotation_apply_style)
        self._btn_annotation_apply_style.setEnabled(False)
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

        self._btn_annotation_crop = QPushButton(tr("EDITOR_ANNOTATION_CROP"))
        self._btn_annotation_crop.setCheckable(True)
        self._btn_annotation_crop.clicked.connect(self._on_crop_annotation_canvas)
        annotation_actions_layout.addWidget(self._btn_annotation_crop)

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
        self._set_object_action_buttons_enabled(False)

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

        self._btn_save_current = QPushButton(tr("EDITOR_SAVE_EDITS"))
        self._btn_save_current.setObjectName("primary_btn")
        self._btn_save_current.clicked.connect(self.save_to_target)
        form.addRow(self._btn_save_current)

        self._btn_publish = QPushButton(tr("EDITOR_PUBLISH_COMPLETE"))
        self._btn_publish.clicked.connect(self.publish_complete_assets)
        self._btn_publish.setEnabled(False)
        form.addRow(self._btn_publish)

        self._btn_save_as = QPushButton(tr("EDITOR_SAVE_AS_COPY"))
        self._btn_save_as.clicked.connect(self.save_as)
        form.addRow(self._btn_save_as)

        self._btn_svg = QPushButton(tr("EDITOR_EXPORT_SVG"))
        self._btn_svg.clicked.connect(lambda: self.save_as("svg"))
        form.addRow(self._btn_svg)

        self._btn_png = QPushButton(tr("EDITOR_EXPORT_PNG"))
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

    def _set_mode_header(self, title: str, *, mode_key: str = "", summary_key: str = "") -> None:
        self._mode_title_text = str(title or "")
        self._mode_banner_key = str(mode_key or "")
        self._mode_summary_key = str(summary_key or "")
        self._mode_title_label.setText(self._mode_title_text)
        self._mode_banner_label.setText(
            tr(self._mode_banner_key) if self._mode_banner_key else ""
        )
        self._mode_summary_label.setText(
            tr(self._mode_summary_key) if self._mode_summary_key else ""
        )
        has_title = bool(self._mode_title_text)
        self._mode_title_label.setVisible(has_title)
        self._mode_banner_label.setVisible(bool(self._mode_banner_label.text()))
        self._mode_summary_label.setVisible(bool(self._mode_summary_label.text()))

    def _source_mode_title(self) -> str:
        entry_title = str(
            getattr(getattr(self, "_source_entry_context", None), "title", "") or ""
        ).strip()
        if entry_title:
            return entry_title
        if isinstance(self._figure_document, dict):
            figure_id = str(self._figure_document.get("figure_id") or "").strip()
            if figure_id:
                return figure_id.replace("_", " ")
        if self._source_path:
            return Path(self._source_path).stem.replace("_", " ")
        return ""

    def retranslate(self):
        if hasattr(self, "_target_label"):
            if self._target_path:
                self._target_label.setText(str(Path(self._target_path).name))
            else:
                self._target_label.setText(tr("EDITOR_TARGET_NONE"))

        if hasattr(self, "_form"):
            for widget, text in [
                (self._target_label, tr("EDITOR_TARGET_LABEL")),
                (self._object_list, tr("EDITOR_OBJECT_LIST_LABEL")),
                (self._selected_object_label, tr("EDITOR_SELECTED_OBJECT_LABEL")),
                (self._annotation_x_spin.parentWidget(), tr("EDITOR_OBJECT_GEOMETRY_LABEL")),
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
        self._btn_annotation_crop.setText(tr("EDITOR_ANNOTATION_CROP"))
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
        self._btn_save_as.setText(tr("EDITOR_SAVE_AS_COPY"))
        self._btn_svg.setText(tr("EDITOR_EXPORT_SVG"))
        self._btn_png.setText(tr("EDITOR_EXPORT_PNG"))
        self._btn_save_current.setText(tr("EDITOR_SAVE_EDITS"))
        self._btn_publish.setText(tr("EDITOR_PUBLISH_COMPLETE"))
        self._set_mode_header(
            self._mode_title_text,
            mode_key=self._mode_banner_key,
            summary_key=self._mode_summary_key,
        )
        self._refresh_style_preset_controls()

    def set_output_target(self, filepath, *, apply_saved_style=True):
        self._target_path = filepath or ""
        if self._target_path:
            self._target_label.setText(str(Path(self._target_path).name))
            self._btn_save_current.setEnabled(True)
            if apply_saved_style:
                self._apply_saved_style(load_figure_edit(self._target_path))
        else:
            self._target_label.setText(tr("EDITOR_TARGET_NONE"))
            self._btn_save_current.setEnabled(False)

    def set_source_figure_entry(self, entry, *, force_static: bool = False):
        path = (
            str(getattr(entry, "editable_path", "") or "")
            or str(getattr(entry, "primary_path", "") or "")
            or str(getattr(entry, "preview_path", "") or "")
        )
        self.set_source_figure(
            path,
            source_entry_context=entry,
            force_static=force_static,
        )

    def set_source_figure(self, filepath, *, source_entry_context=None, force_static=False):
        """Edit persisted settings for an already-exported figure file."""
        self._source_path = filepath or ""
        self._source_entry_context = source_entry_context
        self._btn_publish.setEnabled(self._has_manifest_project_context())
        self._force_static_source_mode = bool(force_static)
        self._asset_spec = None
        self._figure_document = {}
        self._shared_render_plan = None
        self._selected_figure_object_id = ""
        self._hovered_figure_object_id = ""
        self._selection_status_text = ""
        self._hover_status_text = ""
        self._drag_status_text = ""
        self._last_deleted_figure_object_id = ""
        self._generated_handle_drag_state = None
        self._clear_selected_generated_plot_series_handle_context()
        self._reset_generated_handle_memory()
        self._figure_render_adapter.clear_hover_highlight()
        self._reset_generated_selection_model()
        self._reset_generated_canvas_cursor()
        self._generated_document_mode = False
        self._static_file_mode = False
        self._fig_generator = None
        self._fig_args = ()
        self._fig_kwargs = {}
        self._reset_style_context()

        self._toolbar.setVisible(False)
        self._canvas.setVisible(False)
        self._source_preview.setVisible(False)
        self._annotation_canvas.setVisible(False)
        self._set_export_buttons_enabled(False)
        self._btn_save_current.setText(tr("EDITOR_SAVE_EDITS"))
        self._set_mode_header("")

        if self._source_path:
            document_path = str(
                getattr(self._source_entry_context, "document_path", "") or ""
            ).strip()
            self._figure_document = load_figure_document(
                document_path or self._source_path
            )
            self._asset_spec = discover_figure_asset(self._source_path)
            self._source_preview.load_figure(self._source_path)
            self.set_output_target(
                self._source_path,
                apply_saved_style=False,
            )
            if self._is_generated_figure_document() and not self._force_static_source_mode:
                self._hydrate_generated_document_style_context()
                if self._show_generated_figure_document():
                    self._generated_document_mode = True
                    self._set_mode_header(
                        self._source_mode_title(),
                        mode_key="EDITOR_MODE_OBJECT",
                        summary_key="EDITOR_MODE_OBJECT_SUMMARY",
                    )
                    self._status_label.setText(tr("EDITOR_OBJECT_MODE_HINT"))
                    self._toolbar.setVisible(True)
                    self._canvas.setVisible(True)
                    self._source_preview.setVisible(False)
                    self._annotation_canvas.setVisible(False)
                    self._refresh_object_list()
                    return
            self._apply_saved_style(load_figure_edit(self._source_path))
            self._static_file_mode = True
            self._set_mode_header(
                self._source_mode_title(),
                mode_key="EDITOR_MODE_STATIC",
                summary_key="EDITOR_MODE_STATIC_SUMMARY",
            )
            self._status_label.setText(tr("EDITOR_STATIC_MODE_HINT"))
            if self._annotation_canvas.load_image(self._asset_spec.preview_path):
                self._annotation_canvas.load_annotation_state(
                    load_figure_annotations(self._source_path)
                )
                self._annotation_canvas.setVisible(True)
                self._refresh_object_list()
            else:
                self._source_preview.setVisible(True)
                self._canvas.setVisible(True)
                self._show_style_preview_figure()
                self._refresh_object_list()
        else:
            self._source_preview.clear()
            self._annotation_canvas.setVisible(False)
            self.set_output_target("")
            self._set_mode_header("")
            self._refresh_object_list()

    def set_initial_labels(self, title="", xlabel="", ylabel=""):
        self._set_line_edit(self._title_edit, title or "")
        self._set_line_edit(self._xlabel_edit, xlabel or "")
        self._set_line_edit(self._ylabel_edit, ylabel or "")
        self._render()

    def set_figure_generator(self, func, *args, **kwargs):
        self._static_file_mode = False
        self._generated_document_mode = False
        self._source_path = ""
        self._source_entry_context = None
        self._btn_publish.setEnabled(False)
        self._asset_spec = None
        self._figure_document = {}
        self._shared_render_plan = None
        self._selected_figure_object_id = ""
        self._hovered_figure_object_id = ""
        self._selection_status_text = ""
        self._hover_status_text = ""
        self._drag_status_text = ""
        self._last_deleted_figure_object_id = ""
        self._generated_handle_drag_state = None
        self._clear_selected_generated_plot_series_handle_context()
        self._reset_generated_handle_memory()
        self._figure_render_adapter.clear_hover_highlight()
        self._reset_generated_selection_model()
        self._reset_generated_canvas_cursor()
        self._toolbar.setVisible(True)
        self._canvas.setVisible(True)
        self._source_preview.setVisible(False)
        self._annotation_canvas.setVisible(False)
        self._refresh_object_list()
        self._set_export_buttons_enabled(True)
        self._btn_save_current.setText(tr("EDITOR_SAVE_EDITS"))
        self._set_mode_header(
            "figure",
            mode_key="EDITOR_MODE_OBJECT",
            summary_key="EDITOR_MODE_OBJECT_SUMMARY",
        )
        self._fig_generator = func
        self._fig_args = args
        self._fig_kwargs = kwargs
        self._render()

    def is_static_file_mode(self):
        return self._static_file_mode

    def _set_export_buttons_enabled(self, enabled):
        for button in (self._btn_save_as, self._btn_svg, self._btn_png):
            button.setEnabled(enabled)

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

    def _generated_line_handle_hit(self, event, object_id):
        handle_index = self._generated_point_handle_hit(event, object_id)
        if handle_index is not None:
            return handle_index
        figure_object = self._generated_figure_object_by_id(object_id)
        return self._generated_line_endpoint_hit(event, figure_object)

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

make_line_plot = _shared_make_line_plot
make_bar_plot = _shared_make_bar_plot
