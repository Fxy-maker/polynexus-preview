"""Live chart editor and exported-figure settings panel."""

import logging
import shutil  # noqa: F401 - runtime API consumed by save mixin
from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,  # noqa: F401 - runtime API consumed by save mixin
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,  # noqa: F401 - runtime API consumed by style-preset mixin
    QPushButton,
    QScrollArea,
    QDoubleSpinBox,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
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
from .chart_editor_batch_edit_mixin import ChartEditorBatchEditMixin
from .chart_editor_context_style_mixin import ChartEditorContextStyleMixin
from .chart_editor_generated_drag_mixin import ChartEditorGeneratedDragMixin
from .chart_editor_generated_drag_execution_mixin import (
    ChartEditorGeneratedDragExecutionMixin,
)
from .chart_editor_generated_document_mixin import (
    ChartEditorGeneratedDocumentMixin,
)
from .chart_editor_generated_preview_mixin import ChartEditorGeneratedPreviewMixin
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
from .chart_editor_layout_mixin import ChartEditorLayoutMixin
from .chart_editor_layer_widget import LayerTreeWidget
from .chart_editor_inline_text_mixin import ChartEditorInlineTextMixin
from .chart_editor_inspector_drawer_mixin import ChartEditorInspectorDrawerMixin
from .chart_editor_edit_session_mixin import ChartEditorEditSessionMixin
from .chart_editor_export_preset_mixin import ChartEditorExportPresetMixin
from .chart_editor_origin_mixin import ChartEditorOriginMixin
from .chart_editor_object_list_mixin import ChartEditorObjectListMixin
from .chart_editor_save_mixin import ChartEditorSaveMixin
from .chart_editor_style_preset_mixin import ChartEditorStylePresetMixin
from .chart_viewer import FigureFilePreview
from ..figure_render_adapter import FigureRenderAdapter
from ..figure_selection_model import FigureSelectionModel
from ...core.figure_document import (
    create_static_figure_document,  # noqa: F401 - runtime API for save mixin
    load_figure_document_report,
    save_figure_document,  # noqa: F401 - runtime API consumed by save mixin
)
from ...core.figure_assets import discover_figure_asset
from ...core.figure_edit_commands import (  # noqa: F401 - runtime API for editor mixins
    ReplaceDocumentCommand,
    UpdateStyleCommand,
)
from ...core.figure_style_bundle import (  # noqa: F401 - runtime API for editor mixins
    apply_style_bundle,
    capture_style_bundle,
)
from ...core.figure_template_service import (  # noqa: F401 - runtime API for template mixin
    apply_template,
    list_templates,
    load_template,
    save_template,
    template_from_document,
)
from ...core.figure_export_preset_service import (  # noqa: F401 - runtime API for export-preset mixin
    list_export_presets,
    load_export_preset,
    save_export_preset,
)
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
    ChartEditorInspectorDrawerMixin,
    ChartEditorLayoutMixin,
    ChartEditorBatchEditMixin,
    ChartEditorContextStyleMixin,
    ChartEditorInlineTextMixin,
    ChartEditorEditSessionMixin,
    ChartEditorExportPresetMixin,
    ChartEditorOriginMixin,
    ChartEditorAnnotationControlsMixin,
    ChartEditorSaveMixin,
    ChartEditorStylePresetMixin,
    ChartEditorObjectListMixin,
    ChartEditorGeneratedDragMixin,
    ChartEditorGeneratedDragExecutionMixin,
    ChartEditorGeneratedDocumentMixin,
    ChartEditorGeneratedPreviewMixin,
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
        self._document_load_report = None
        self._edit_session = None
        self._last_edit_result = None
        self._shared_render_plan = None
        self._generated_document_mode = False
        self._generated_draw_tool = "select"
        self._generated_draw_start_data = None
        self._generated_draw_start_display = None
        self._generated_draw_preview_artists = []
        self._generated_handle_preview_artists = []
        self._generated_viewport_snapshot = None
        self._generated_draw_preview_start = None
        self._generated_draw_preview_start_display = None
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
        self._selected_figure_object_ids = ()
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
        self._editor_dirty = False
        self._loading_editor_state = False
        self._origin_export_thread = None
        self._origin_export_worker = None
        self._origin_export_service = None
        self._format_clipboard = None
        self._text_render_timer = QTimer(self)
        self._text_render_timer.setSingleShot(True)
        self._text_render_timer.setInterval(0)
        self._text_render_timer.timeout.connect(self._render)
        self._connected_canvas_figure = None
        self._figure_selection_model = FigureSelectionModel(self)
        self._figure_selection_model.selection_changed.connect(
            self._on_generated_selection_changed
        )
        self._figure_render_adapter = FigureRenderAdapter()
        self._build_ui()
        self._reset_edit_session_from_document(self._figure_document)
        self.figure_changed.connect(self._mark_editor_dirty)
        self.figure_saved.connect(lambda _path: self._set_editor_dirty(False))
        self._set_mode_header("")
        self._connect_canvas_interaction_events()

    def _build_ui(self):
        self._editor_splitter = QSplitter(Qt.Horizontal)
        split = self._editor_splitter
        split.setChildrenCollapsible(False)

        figure_panel = QWidget()
        figure_panel.setMinimumWidth(220)
        figure_layout = QVBoxLayout(figure_panel)
        figure_layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(
            figsize=self._fig_size, dpi=self._dpi, facecolor=self._bg_color
        )
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._canvas.setFocusPolicy(Qt.StrongFocus)
        self._canvas.installEventFilter(self)
        self._toolbar = NavToolbar(self._canvas, self)
        self._editor_toolbar = self._build_editor_toolbar()
        self._editor_toolbar.setOrientation(Qt.Vertical)
        self._source_preview = FigureFilePreview(show_edit_button=False)
        self._source_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._source_preview.setVisible(False)
        self._annotation_canvas = AnnotationCanvas()
        self._annotation_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._annotation_canvas.setVisible(False)
        self._annotation_canvas.tool_changed.connect(self._sync_annotation_tool_buttons)
        self._annotation_canvas.selection_changed.connect(self._sync_annotation_property_controls)
        self._annotation_canvas.annotations_changed.connect(self._on_annotation_canvas_changed)
        self._annotation_canvas.text_entry_requested.connect(
            self._on_annotation_text_entry_requested
        )
        self._annotation_canvas.object_create_requested.connect(
            self._on_annotation_object_create_requested
        )

        self._canvas_tool_shell = QWidget()
        canvas_tool_layout = QHBoxLayout(self._canvas_tool_shell)
        canvas_tool_layout.setContentsMargins(0, 0, 0, 0)
        canvas_tool_layout.setSpacing(0)
        canvas_tool_layout.addWidget(self._editor_toolbar, 0, Qt.AlignTop)

        canvas_stack = QWidget()
        canvas_stack_layout = QVBoxLayout(canvas_stack)
        canvas_stack_layout.setContentsMargins(0, 0, 0, 0)
        canvas_stack_layout.addWidget(self._canvas, 1)
        canvas_stack_layout.addWidget(self._source_preview, 1)
        canvas_stack_layout.addWidget(self._annotation_canvas, 1)
        canvas_stack_layout.addWidget(self._build_context_style_bar())
        self._build_inline_text_editor()
        canvas_tool_layout.addWidget(canvas_stack, 1)

        figure_layout.addWidget(self._toolbar)
        figure_layout.addWidget(self._canvas_tool_shell, 1)
        split.addWidget(figure_panel)

        self._editor_header = self._build_editor_header()
        self._editor_status_bar = self._build_editor_status_bar()
        inspector_panel = self._build_inspector_drawer(self._build_panel())
        split.addWidget(inspector_panel)
        split.setSizes([760, 390])
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor_header)
        layout.addWidget(split, 1)
        layout.addWidget(self._editor_status_bar)
        self._set_inspector_collapsed(False)

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
                if self._cancel_active_draw():
                    event.accept()
                    return True
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
                if self._cancel_active_draw():
                    event.accept()
                    return True
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

    def closeEvent(self, event):
        """Protect edits when the editor window is closed."""
        if not getattr(self, "_editor_dirty", False):
            event.accept()
            return

        choice = QMessageBox.question(
            self,
            tr("EDITOR_CLOSE_TITLE"),
            tr("EDITOR_CLOSE_UNSAVED"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if choice == QMessageBox.StandardButton.Discard:
            event.accept()
            return
        if choice == QMessageBox.StandardButton.Save:
            try:
                self.save_to_target()
            except Exception as exc:
                logger.warning("Chart editor close-save failed.", exc_info=True)
                status_label = getattr(self, "_status_label", None)
                if status_label is not None:
                    status_label.setText(f"{tr('EDITOR_STATUS_SAVE_FAILED')}: {exc}")
                event.ignore()
                return
            if not getattr(self, "_editor_dirty", False):
                event.accept()
                return
        event.ignore()

    def _build_panel(self):
        self._inspector_tabs = QTabWidget()
        self._inspector_tabs.setObjectName("editor_inspector_tabs")
        self._inspector_tabs.setMinimumWidth(280)
        self._inspector_tabs.setAccessibleName(tr("EDITOR_INSPECTOR"))

        def make_page():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            panel = QWidget()
            form = QFormLayout(panel)
            form.setSpacing(8)
            form.setContentsMargins(12, 12, 12, 12)
            scroll.setWidget(panel)
            return scroll, form

        object_page, object_form = make_page()
        style_page, style_form = make_page()
        annotation_page, annotation_form = make_page()
        export_page, export_form = make_page()
        self._forms = [object_form, style_form, annotation_form, export_form]
        form = object_form

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

        self._object_search_edit = QLineEdit()
        self._object_search_edit.setPlaceholderText(tr("EDITOR_OBJECT_SEARCH_PLACEHOLDER"))
        self._object_search_edit.textChanged.connect(
            lambda _text: self._refresh_object_list(self._selected_figure_object_id)
        )
        form.addRow(tr("EDITOR_OBJECT_SEARCH_LABEL"), self._object_search_edit)

        self._object_list = LayerTreeWidget()
        self._object_list.setHeaderHidden(True)
        self._object_list.setMinimumHeight(96)
        self._object_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._object_list.installEventFilter(self)
        self._object_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._object_list.customContextMenuRequested.connect(
            self._show_object_context_menu
        )
        self._object_list.currentItemChanged.connect(
            self._on_object_list_selection_changed
        )
        self._object_list.itemChanged.connect(self._on_object_list_item_changed)
        form.addRow(tr("EDITOR_OBJECT_LIST_LABEL"), self._object_list)

        self._object_action_bar = self._build_object_action_bar()
        form.addRow(self._object_action_bar)

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

        self._annotation_curve_control = QWidget()
        annotation_curve_control_layout = QHBoxLayout(self._annotation_curve_control)
        annotation_curve_control_layout.setContentsMargins(0, 0, 0, 0)
        annotation_curve_control_layout.setSpacing(6)
        self._annotation_curve_control_x_label = QLabel("X")
        annotation_curve_control_layout.addWidget(self._annotation_curve_control_x_label)
        self._annotation_curve_control_x_spin = QDoubleSpinBox()
        self._annotation_curve_control_x_spin.setRange(0.0, 1.0)
        self._annotation_curve_control_x_spin.setDecimals(4)
        self._annotation_curve_control_x_spin.setSingleStep(0.01)
        self._annotation_curve_control_x_spin.valueChanged.connect(
            self._on_annotation_curve_control_changed
        )
        annotation_curve_control_layout.addWidget(self._annotation_curve_control_x_spin)
        self._annotation_curve_control_y_label = QLabel("Y")
        annotation_curve_control_layout.addWidget(self._annotation_curve_control_y_label)
        self._annotation_curve_control_y_spin = QDoubleSpinBox()
        self._annotation_curve_control_y_spin.setRange(0.0, 1.0)
        self._annotation_curve_control_y_spin.setDecimals(4)
        self._annotation_curve_control_y_spin.setSingleStep(0.01)
        self._annotation_curve_control_y_spin.valueChanged.connect(
            self._on_annotation_curve_control_changed
        )
        annotation_curve_control_layout.addWidget(self._annotation_curve_control_y_spin)
        self._annotation_curve_control_label = QLabel(tr("EDITOR_CURVE_CONTROL_LABEL"))
        form.addRow(self._annotation_curve_control_label, self._annotation_curve_control)
        self._set_curve_control_enabled(False)

        form = style_form
        preset_row = QWidget()
        preset_layout = QGridLayout(preset_row)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(6)

        self._style_preset_combo = QComboBox()
        self._style_preset_combo.setEditable(True)
        self._style_preset_combo.setInsertPolicy(QComboBox.NoInsert)
        self._style_preset_combo.editTextChanged.connect(self._on_style_preset_name_changed)
        preset_layout.addWidget(self._style_preset_combo, 0, 0, 1, 3)

        self._btn_style_preset_save = QPushButton(tr("EDITOR_STYLE_PRESET_SAVE"))
        self._btn_style_preset_save.clicked.connect(self._on_save_style_preset)
        preset_layout.addWidget(self._btn_style_preset_save, 1, 0)

        self._btn_style_preset_apply = QPushButton(tr("EDITOR_STYLE_PRESET_APPLY"))
        self._btn_style_preset_apply.clicked.connect(self._on_apply_style_preset)
        preset_layout.addWidget(self._btn_style_preset_apply, 1, 1)

        self._btn_style_preset_delete = QPushButton(tr("EDITOR_STYLE_PRESET_DELETE"))
        self._btn_style_preset_delete.clicked.connect(self._on_delete_style_preset)
        preset_layout.addWidget(self._btn_style_preset_delete, 1, 2)

        form.addRow(tr("EDITOR_STYLE_PRESET_LABEL"), preset_row)

        template_row = QWidget()
        template_layout = QGridLayout(template_row)
        template_layout.setContentsMargins(0, 0, 0, 0)
        template_layout.setSpacing(6)
        self._template_combo = QComboBox()
        self._template_combo.setEditable(True)
        self._template_combo.setInsertPolicy(QComboBox.NoInsert)
        self._template_combo.editTextChanged.connect(self._on_template_name_changed)
        template_layout.addWidget(self._template_combo, 0, 0, 1, 2)
        self._btn_template_save = QPushButton(tr("EDITOR_TEMPLATE_SAVE"))
        self._btn_template_save.clicked.connect(self._on_save_template)
        template_layout.addWidget(self._btn_template_save, 1, 0)
        self._btn_template_apply = QPushButton(tr("EDITOR_TEMPLATE_APPLY"))
        self._btn_template_apply.clicked.connect(self._on_apply_template)
        template_layout.addWidget(self._btn_template_apply, 1, 1)
        form.addRow(tr("EDITOR_TEMPLATE_LABEL"), template_row)

        format_row = QWidget()
        format_layout = QHBoxLayout(format_row)
        format_layout.setContentsMargins(0, 0, 0, 0)
        format_layout.setSpacing(6)
        self._btn_copy_format = QPushButton(tr("EDITOR_FORMAT_COPY"))
        self._btn_copy_format.clicked.connect(self._copy_selected_format)
        format_layout.addWidget(self._btn_copy_format)
        self._btn_paste_format = QPushButton(tr("EDITOR_FORMAT_PASTE"))
        self._btn_paste_format.clicked.connect(self._paste_selected_format)
        format_layout.addWidget(self._btn_paste_format)
        form.addRow(tr("EDITOR_FORMAT_LABEL"), format_row)

        self._title_edit = QLineEdit()
        self._title_edit.textChanged.connect(self._schedule_text_render)
        form.addRow(tr("EDITOR_FIELD_TITLE"), self._title_edit)

        self._xlabel_edit = QLineEdit()
        self._xlabel_edit.textChanged.connect(self._schedule_text_render)
        form.addRow(tr("EDITOR_FIELD_XLABEL"), self._xlabel_edit)

        self._ylabel_edit = QLineEdit()
        self._ylabel_edit.textChanged.connect(self._schedule_text_render)
        form.addRow(tr("EDITOR_FIELD_YLABEL"), self._ylabel_edit)

        self._colour_cb = QComboBox()
        self._colour_cb.addItems(COLOUR_SCHEMES.keys())
        self._colour_cb.currentTextChanged.connect(self._on_colour_scheme_changed)
        form.addRow(tr("EDITOR_FIELD_COLOURS"), self._colour_cb)

        self._font_cb = QComboBox()
        self._font_cb.addItems(FONT_SIZES.keys())
        self._font_cb.setCurrentText("Medium")
        self._font_cb.currentTextChanged.connect(self._on_font_changed)
        form.addRow(tr("EDITOR_FIELD_FONT"), self._font_cb)

        self._lw_cb = QComboBox()
        self._lw_cb.addItems(LINE_WIDTHS.keys())
        self._lw_cb.setCurrentText("Normal")
        self._lw_cb.currentTextChanged.connect(self._on_line_width_changed)
        form.addRow(tr("EDITOR_FIELD_LINE"), self._lw_cb)

        self._figsize_cb = QComboBox()
        self._figsize_cb.addItems(FIGURE_SIZES.keys())
        self._figsize_cb.setCurrentText("Medium (6in)")
        self._figsize_cb.currentTextChanged.connect(self._on_figure_size_changed)
        form.addRow(tr("EDITOR_FIELD_SIZE"), self._figsize_cb)

        self._grid_cb = QCheckBox("Grid")
        self._grid_cb.setChecked(True)
        self._grid_cb.toggled.connect(self._on_grid_toggled)
        form.addRow(self._grid_cb)

        self._grid_sl = QSlider(Qt.Horizontal)
        self._grid_sl.setRange(0, 10)
        self._grid_sl.setValue(2)
        self._grid_sl.valueChanged.connect(self._on_grid_alpha_changed)
        form.addRow(tr("EDITOR_FIELD_GRID_ALPHA"), self._grid_sl)

        btn_bg = QPushButton(tr("EDITOR_BTN_BG"))
        btn_bg.clicked.connect(self._pick_bg)
        form.addRow(btn_bg)

        form = annotation_form
        annotation_text_row = QWidget()
        annotation_text_layout = QGridLayout(annotation_text_row)
        annotation_text_layout.setContentsMargins(0, 0, 0, 0)
        annotation_text_layout.setSpacing(6)

        self._annotation_text_edit = QLineEdit()
        self._annotation_text_edit.setPlaceholderText(
            tr("EDITOR_ANNOTATION_TEXT_PLACEHOLDER")
        )
        annotation_text_layout.addWidget(self._annotation_text_edit, 0, 0, 1, 2)

        self._btn_annotation_add_text = QPushButton(tr("EDITOR_ANNOTATION_ADD_TEXT"))
        self._btn_annotation_add_text.clicked.connect(self._on_add_text_annotation)
        self._btn_annotation_add_text.hide()

        self._btn_annotation_update_text = QPushButton(
            tr("EDITOR_ANNOTATION_UPDATE_TEXT")
        )
        self._btn_annotation_update_text.clicked.connect(
            self._on_update_selected_text_annotation
        )
        self._btn_annotation_update_text.setEnabled(False)
        annotation_text_layout.addWidget(self._btn_annotation_update_text, 1, 0, 1, 2)
        form.addRow(annotation_text_row)

        annotation_style = QWidget()
        annotation_style_layout = QGridLayout(annotation_style)
        annotation_style_layout.setContentsMargins(0, 0, 0, 0)
        annotation_style_layout.setSpacing(6)

        self._annotation_color_edit = QLineEdit("#D55E00")
        self._annotation_color_edit.setPlaceholderText("#RRGGBB")
        annotation_style_layout.addWidget(self._annotation_color_edit, 0, 0, 1, 2)

        self._annotation_font_size_spin = QSpinBox()
        self._annotation_font_size_spin.setRange(6, 72)
        self._annotation_font_size_spin.setValue(12)
        self._annotation_font_size_spin.setSuffix(" pt")
        annotation_style_layout.addWidget(self._annotation_font_size_spin, 1, 0)

        self._annotation_line_width_spin = QDoubleSpinBox()
        self._annotation_line_width_spin.setRange(0.1, 20.0)
        self._annotation_line_width_spin.setSingleStep(0.5)
        self._annotation_line_width_spin.setValue(2.0)
        self._annotation_line_width_spin.setSuffix(" px")
        annotation_style_layout.addWidget(self._annotation_line_width_spin, 1, 1)

        self._annotation_alpha_spin = QDoubleSpinBox()
        self._annotation_alpha_spin.setRange(0.0, 1.0)
        self._annotation_alpha_spin.setSingleStep(0.05)
        self._annotation_alpha_spin.setValue(0.35)
        annotation_style_layout.addWidget(self._annotation_alpha_spin, 2, 0)

        self._annotation_line_style_combo = QComboBox()
        self._annotation_line_style_combo.addItems(LINE_STYLE_OPTIONS.keys())
        self._annotation_line_style_combo.setCurrentText("Solid")
        annotation_style_layout.addWidget(self._annotation_line_style_combo, 2, 1)

        self._annotation_marker_combo = QComboBox()
        self._annotation_marker_combo.addItems(MARKER_OPTIONS.keys())
        self._annotation_marker_combo.setCurrentText("None")
        annotation_style_layout.addWidget(self._annotation_marker_combo, 3, 0)

        self._annotation_marker_size_spin = QDoubleSpinBox()
        self._annotation_marker_size_spin.setRange(1.0, 40.0)
        self._annotation_marker_size_spin.setSingleStep(1.0)
        self._annotation_marker_size_spin.setValue(6.0)
        self._annotation_marker_size_spin.setSuffix(" pt")
        annotation_style_layout.addWidget(self._annotation_marker_size_spin, 3, 1)
        self._set_style_controls_enabled(False, False, False, color_enabled=False)

        self._btn_annotation_apply_style = QPushButton(
            tr("EDITOR_ANNOTATION_APPLY_STYLE")
        )
        self._btn_annotation_apply_style.clicked.connect(self._on_annotation_apply_style)
        annotation_style_layout.addWidget(self._btn_annotation_apply_style, 4, 0, 1, 2)
        self._btn_annotation_apply_style.setEnabled(False)
        form.addRow(tr("EDITOR_ANNOTATION_STYLE_LABEL"), annotation_style)

        annotation_actions = QWidget()
        annotation_actions_layout = QGridLayout(annotation_actions)
        annotation_actions_layout.setContentsMargins(0, 0, 0, 0)
        annotation_actions_layout.setSpacing(6)

        self._btn_annotation_add_line = QPushButton(tr("EDITOR_ANNOTATION_ADD_LINE"))
        self._btn_annotation_add_line.setCheckable(True)
        self._btn_annotation_add_line.clicked.connect(self._on_add_line_annotation)
        self._btn_annotation_add_line.hide()

        self._btn_annotation_add_arrow = QPushButton(tr("EDITOR_ANNOTATION_ADD_ARROW"))
        self._btn_annotation_add_arrow.setCheckable(True)
        self._btn_annotation_add_arrow.clicked.connect(self._on_add_arrow_annotation)
        self._btn_annotation_add_arrow.hide()

        self._btn_annotation_add_rect = QPushButton(tr("EDITOR_ANNOTATION_ADD_RECT"))
        self._btn_annotation_add_rect.setCheckable(True)
        self._btn_annotation_add_rect.clicked.connect(self._on_add_rectangle_annotation)
        self._btn_annotation_add_rect.hide()

        self._btn_annotation_add_highlight = QPushButton(
            tr("EDITOR_ANNOTATION_ADD_HIGHLIGHT")
        )
        self._btn_annotation_add_highlight.setCheckable(True)
        self._btn_annotation_add_highlight.clicked.connect(
            self._on_add_highlight_annotation
        )
        self._btn_annotation_add_highlight.hide()

        self._btn_annotation_crop = QPushButton(tr("EDITOR_ANNOTATION_CROP"))
        self._btn_annotation_crop.setCheckable(True)
        self._btn_annotation_crop.clicked.connect(self._on_crop_annotation_canvas)
        self._btn_annotation_crop.hide()

        self._btn_annotation_delete = QPushButton(tr("EDITOR_ANNOTATION_DELETE"))
        self._btn_annotation_delete.clicked.connect(self._on_annotation_delete)
        annotation_actions_layout.addWidget(self._btn_annotation_delete, 1, 2)

        self._btn_annotation_copy = QPushButton(tr("EDITOR_ANNOTATION_COPY"))
        self._btn_annotation_copy.clicked.connect(self._on_annotation_copy)
        self._btn_annotation_copy.hide()

        self._btn_annotation_paste = QPushButton(tr("EDITOR_ANNOTATION_PASTE"))
        self._btn_annotation_paste.clicked.connect(self._on_annotation_paste)
        self._btn_annotation_paste.hide()

        self._btn_annotation_front = QPushButton(tr("EDITOR_ANNOTATION_FRONT"))
        self._btn_annotation_front.clicked.connect(self._on_annotation_front)
        annotation_actions_layout.addWidget(self._btn_annotation_front, 1, 0)

        self._btn_annotation_back = QPushButton(tr("EDITOR_ANNOTATION_BACK"))
        self._btn_annotation_back.clicked.connect(self._on_annotation_back)
        annotation_actions_layout.addWidget(self._btn_annotation_back, 1, 1)
        self._set_object_action_buttons_enabled(False)

        self._btn_annotation_undo = QPushButton(tr("EDITOR_ANNOTATION_UNDO"))
        self._btn_annotation_undo.clicked.connect(self._on_annotation_undo)
        annotation_actions_layout.addWidget(self._btn_annotation_undo, 1, 2)

        self._btn_annotation_redo = QPushButton(tr("EDITOR_ANNOTATION_REDO"))
        self._btn_annotation_redo.clicked.connect(self._on_annotation_redo)
        annotation_actions_layout.addWidget(self._btn_annotation_redo, 3, 2)

        self._btn_annotation_lock = QPushButton(tr("EDITOR_OBJECT_LOCK"))
        self._btn_annotation_lock.setCheckable(True)
        self._btn_annotation_lock.clicked.connect(self._on_toggle_selected_lock)
        annotation_actions_layout.addWidget(self._btn_annotation_lock, 4, 0, 1, 3)

        batch_actions = QWidget()
        batch_layout = QHBoxLayout(batch_actions)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        batch_layout.setSpacing(4)
        for name, label_key, callback in (
            ("_btn_annotation_align_left", "EDITOR_ALIGN_LEFT", lambda: self._align_selected_objects("left")),
            ("_btn_annotation_align_center", "EDITOR_ALIGN_CENTER", lambda: self._align_selected_objects("center")),
            ("_btn_annotation_align_right", "EDITOR_ALIGN_RIGHT", lambda: self._align_selected_objects("right")),
            ("_btn_annotation_align_top", "EDITOR_ALIGN_TOP", lambda: self._align_selected_objects("top")),
            ("_btn_annotation_align_middle", "EDITOR_ALIGN_MIDDLE", lambda: self._align_selected_objects("middle")),
            ("_btn_annotation_align_bottom", "EDITOR_ALIGN_BOTTOM", lambda: self._align_selected_objects("bottom")),
            ("_btn_annotation_distribute_horizontal", "EDITOR_DISTRIBUTE_HORIZONTAL", lambda: self._distribute_selected_objects("horizontal")),
            ("_btn_annotation_distribute_vertical", "EDITOR_DISTRIBUTE_VERTICAL", lambda: self._distribute_selected_objects("vertical")),
            ("_btn_annotation_group", "EDITOR_GROUP", self._group_selected_objects),
            ("_btn_annotation_ungroup", "EDITOR_UNGROUP", self._ungroup_selected_objects),
        ):
            button = QPushButton(tr(label_key))
            button.setObjectName(name)
            button.clicked.connect(callback)
            setattr(self, name, button)
            batch_layout.addWidget(button)
        annotation_actions_layout.addWidget(batch_actions, 5, 0, 1, 3)
        self._sync_batch_action_buttons()
        form.addRow(annotation_actions)

        annotation_zoom = QWidget()
        annotation_zoom_layout = QGridLayout(annotation_zoom)
        annotation_zoom_layout.setContentsMargins(0, 0, 0, 0)
        annotation_zoom_layout.setSpacing(6)

        self._btn_annotation_fit = QPushButton(tr("EDITOR_ANNOTATION_FIT"))
        self._btn_annotation_fit.clicked.connect(self._on_annotation_fit)
        annotation_zoom_layout.addWidget(self._btn_annotation_fit, 0, 0)

        self._btn_annotation_zoom_100 = QPushButton(tr("EDITOR_ANNOTATION_ZOOM_100"))
        self._btn_annotation_zoom_100.clicked.connect(self._on_annotation_zoom_100)
        annotation_zoom_layout.addWidget(self._btn_annotation_zoom_100, 0, 1)

        self._btn_annotation_zoom_out = QPushButton(tr("EDITOR_ANNOTATION_ZOOM_OUT"))
        self._btn_annotation_zoom_out.clicked.connect(self._on_annotation_zoom_out)
        annotation_zoom_layout.addWidget(self._btn_annotation_zoom_out, 1, 0)

        self._btn_annotation_zoom_in = QPushButton(tr("EDITOR_ANNOTATION_ZOOM_IN"))
        self._btn_annotation_zoom_in.clicked.connect(self._on_annotation_zoom_in)
        annotation_zoom_layout.addWidget(self._btn_annotation_zoom_in, 1, 1)
        form.addRow(annotation_zoom)

        self._btn_sci_defaults = QPushButton(tr("EDITOR_SCI_DEFAULTS"))
        self._btn_sci_defaults.clicked.connect(self._apply_sci_defaults)
        form.addRow(self._btn_sci_defaults)

        form = export_form
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

        export_preset_row = QWidget()
        export_preset_layout = QGridLayout(export_preset_row)
        export_preset_layout.setContentsMargins(0, 0, 0, 0)
        export_preset_layout.setSpacing(6)
        self._export_preset_combo = QComboBox()
        self._export_preset_combo.setEditable(True)
        self._export_preset_combo.setInsertPolicy(QComboBox.NoInsert)
        self._export_preset_combo.editTextChanged.connect(self._on_export_preset_name_changed)
        export_preset_layout.addWidget(self._export_preset_combo, 0, 0, 1, 2)
        self._btn_export_preset_save = QPushButton(tr("EDITOR_EXPORT_PRESET_SAVE"))
        self._btn_export_preset_save.clicked.connect(self._on_save_export_preset)
        export_preset_layout.addWidget(self._btn_export_preset_save, 1, 0)
        self._btn_export_preset_apply = QPushButton(tr("EDITOR_EXPORT_PRESET_APPLY"))
        self._btn_export_preset_apply.clicked.connect(self._on_apply_export_preset)
        export_preset_layout.addWidget(self._btn_export_preset_apply, 1, 1)
        form.addRow(tr("EDITOR_EXPORT_PRESET_LABEL"), export_preset_row)

        self._export_format_combo = QComboBox()
        for label, value in (
            ("PNG", "png"),
            ("SVG", "svg"),
            ("PDF", "pdf"),
            ("Origin", "origin"),
            ("Project", "project"),
        ):
            self._export_format_combo.addItem(label, value)
        form.addRow(tr("EDITOR_EXPORT_FORMAT_LABEL"), self._export_format_combo)
        self._btn_export_preset_run = QPushButton(tr("EDITOR_EXPORT_PRESET_RUN"))
        self._btn_export_preset_run.clicked.connect(self._export_with_preset)
        form.addRow(self._btn_export_preset_run)
        self._build_origin_export_control(form)

        self._form = object_form
        self._btn_bg = btn_bg
        self._inspector_tabs.addTab(object_page, tr("EDITOR_INSPECTOR_OBJECT"))
        self._inspector_tabs.addTab(style_page, tr("EDITOR_INSPECTOR_STYLE"))
        self._inspector_tabs.addTab(
            annotation_page,
            tr("EDITOR_INSPECTOR_ANNOTATION"),
        )
        self._inspector_tabs.addTab(export_page, tr("EDITOR_INSPECTOR_EXPORT"))
        tab_bar = self._inspector_tabs.tabBar()
        tab_bar.setUsesScrollButtons(False)
        tab_bar.setExpanding(True)
        tab_bar.setElideMode(Qt.ElideRight)
        self._refresh_style_preset_controls()
        self._refresh_template_controls()
        self._refresh_export_preset_controls()
        return self._inspector_tabs

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
        if hasattr(self, "_mode_badge"):
            self._mode_badge.setText(
                tr(self._mode_banner_key) if self._mode_banner_key else ""
            )
            self._set_source_identity_ui()
            self._sync_header_actions()
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
        if hasattr(self, "_inspector_tabs"):
            for index, key in enumerate(
                (
                    "EDITOR_INSPECTOR_OBJECT",
                    "EDITOR_INSPECTOR_STYLE",
                    "EDITOR_INSPECTOR_ANNOTATION",
                    "EDITOR_INSPECTOR_EXPORT",
                )
            ):
                self._inspector_tabs.setTabText(index, tr(key))
        self.retranslate_layout()
        self.retranslate_context_style_bar()
        self.retranslate_inline_text_editor()
        if hasattr(self, "_target_label"):
            if self._target_path:
                self._target_label.setText(str(Path(self._target_path).name))
            else:
                self._target_label.setText(tr("EDITOR_TARGET_NONE"))

        if hasattr(self, "_form"):
            for widget, text in [
                (self._target_label, tr("EDITOR_TARGET_LABEL")),
                (self._object_search_edit, tr("EDITOR_OBJECT_SEARCH_LABEL")),
                (self._object_list, tr("EDITOR_OBJECT_LIST_LABEL")),
                (self._selected_object_label, tr("EDITOR_SELECTED_OBJECT_LABEL")),
                (self._annotation_x_spin.parentWidget(), tr("EDITOR_OBJECT_GEOMETRY_LABEL")),
                (self._annotation_curve_control, tr("EDITOR_CURVE_CONTROL_LABEL")),
                (self._style_preset_combo.parentWidget(), tr("EDITOR_STYLE_PRESET_LABEL")),
                (self._title_edit, tr("EDITOR_FIELD_TITLE")),
                (self._xlabel_edit, tr("EDITOR_FIELD_XLABEL")),
                (self._ylabel_edit, tr("EDITOR_FIELD_YLABEL")),
                (self._colour_cb, tr("EDITOR_FIELD_COLOURS")),
                (self._font_cb, tr("EDITOR_FIELD_FONT")),
                (self._lw_cb, tr("EDITOR_FIELD_LINE")),
                (self._figsize_cb, tr("EDITOR_FIELD_SIZE")),
                (self._grid_sl, tr("EDITOR_FIELD_GRID_ALPHA")),
            ]:
                label = next(
                    (
                        candidate
                        for form in getattr(self, "_forms", [self._form])
                        if (candidate := form.labelForField(widget)) is not None
                    ),
                    None,
                )
                if label is not None:
                    label.setText(text)

        self._grid_cb.setText(tr("EDITOR_GRID"))
        self._btn_style_preset_save.setText(tr("EDITOR_STYLE_PRESET_SAVE"))
        self._btn_style_preset_apply.setText(tr("EDITOR_STYLE_PRESET_APPLY"))
        self._btn_style_preset_delete.setText(tr("EDITOR_STYLE_PRESET_DELETE"))
        self._btn_template_save.setText(tr("EDITOR_TEMPLATE_SAVE"))
        self._btn_template_apply.setText(tr("EDITOR_TEMPLATE_APPLY"))
        self._btn_copy_format.setText(tr("EDITOR_FORMAT_COPY"))
        self._btn_paste_format.setText(tr("EDITOR_FORMAT_PASTE"))
        self._btn_bg.setText(tr("EDITOR_BTN_BG"))
        self._annotation_text_edit.setPlaceholderText(
            tr("EDITOR_ANNOTATION_TEXT_PLACEHOLDER")
        )
        self._object_search_edit.setPlaceholderText(
            tr("EDITOR_OBJECT_SEARCH_PLACEHOLDER")
        )
        self._btn_annotation_add_text.setText(tr("EDITOR_ANNOTATION_ADD_TEXT"))
        self._btn_annotation_update_text.setText(
            tr("EDITOR_ANNOTATION_UPDATE_TEXT")
        )
        self._btn_annotation_apply_style.setText(
            tr("EDITOR_ANNOTATION_APPLY_STYLE")
        )
        label = next(
            (
                candidate
                for form in getattr(self, "_forms", [self._form])
                if (candidate := form.labelForField(self._annotation_color_edit.parentWidget())) is not None
            ),
            None,
        )
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
        self._btn_annotation_lock.setText(tr("EDITOR_OBJECT_LOCK"))
        for button_name, key in (
            ("_btn_annotation_align_left", "EDITOR_ALIGN_LEFT"),
            ("_btn_annotation_align_center", "EDITOR_ALIGN_CENTER"),
            ("_btn_annotation_align_right", "EDITOR_ALIGN_RIGHT"),
            ("_btn_annotation_align_top", "EDITOR_ALIGN_TOP"),
            ("_btn_annotation_align_middle", "EDITOR_ALIGN_MIDDLE"),
            ("_btn_annotation_align_bottom", "EDITOR_ALIGN_BOTTOM"),
            ("_btn_annotation_distribute_horizontal", "EDITOR_DISTRIBUTE_HORIZONTAL"),
            ("_btn_annotation_distribute_vertical", "EDITOR_DISTRIBUTE_VERTICAL"),
            ("_btn_annotation_group", "EDITOR_GROUP"),
            ("_btn_annotation_ungroup", "EDITOR_UNGROUP"),
        ):
            getattr(self, button_name).setText(tr(key))
        self._btn_annotation_fit.setText(tr("EDITOR_ANNOTATION_FIT"))
        self._btn_annotation_zoom_100.setText(tr("EDITOR_ANNOTATION_ZOOM_100"))
        self._btn_annotation_zoom_out.setText(tr("EDITOR_ANNOTATION_ZOOM_OUT"))
        self._btn_annotation_zoom_in.setText(tr("EDITOR_ANNOTATION_ZOOM_IN"))
        self._btn_sci_defaults.setText(tr("EDITOR_SCI_DEFAULTS"))
        self._btn_save_as.setText(tr("EDITOR_SAVE_AS_COPY"))
        self._btn_svg.setText(tr("EDITOR_EXPORT_SVG"))
        self._btn_png.setText(tr("EDITOR_EXPORT_PNG"))
        self._btn_export_preset_save.setText(tr("EDITOR_EXPORT_PRESET_SAVE"))
        self._btn_export_preset_apply.setText(tr("EDITOR_EXPORT_PRESET_APPLY"))
        self._btn_export_preset_run.setText(tr("EDITOR_EXPORT_PRESET_RUN"))
        self._btn_save_current.setText(tr("EDITOR_SAVE_EDITS"))
        self._btn_publish.setText(tr("EDITOR_PUBLISH_COMPLETE"))
        self.retranslate_origin_export()
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
        self._text_render_timer.stop()
        self._loading_editor_state = True
        self._source_path = filepath or ""
        self._source_entry_context = source_entry_context
        self._btn_publish.setEnabled(self._has_manifest_project_context())
        self._force_static_source_mode = bool(force_static)
        self._asset_spec = None
        self._figure_document = {}
        self._shared_render_plan = None
        self._selected_figure_object_id = ""
        self._selected_figure_object_ids = ()
        self._hovered_figure_object_id = ""
        self._selection_status_text = ""
        self._hover_status_text = ""
        self._drag_status_text = ""
        self._last_deleted_figure_object_id = ""
        self._generated_handle_drag_state = None
        self._clear_generated_draw_preview(redraw=False)
        self._generated_viewport_snapshot = None
        self._clear_selected_generated_plot_series_handle_context()
        self._reset_generated_handle_memory()
        self._figure_render_adapter.clear_hover_highlight()
        self._reset_generated_selection_model()
        self._reset_generated_canvas_cursor()
        self._generated_document_mode = False
        self._generated_draw_tool = "select"
        self._generated_draw_start_data = None
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
            document_report = load_figure_document_report(
                document_path or self._source_path
            )
            self._document_load_report = document_report
            self._figure_document = (
                document_report.document if document_report.status == "valid" else {}
            )
            self._reset_edit_session_from_document(self._figure_document)
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
                    self._set_editor_mode_ui(object_mode=True)
                    self._refresh_object_list()
                    self._set_editor_dirty(False)
                    self._sync_origin_export_enabled()
                    self._loading_editor_state = False
                    return
            self._apply_saved_style(load_figure_edit(self._source_path))
            self._static_file_mode = True
            self._set_mode_header(
                self._source_mode_title(),
                mode_key="EDITOR_MODE_STATIC",
                summary_key="EDITOR_MODE_STATIC_SUMMARY",
            )
            self._set_editor_mode_ui(object_mode=False)
            self._status_label.setText(tr("EDITOR_STATIC_MODE_HINT"))
            if self._annotation_canvas.load_image(self._asset_spec.preview_path):
                annotations = load_figure_annotations(self._source_path)
                if not self._figure_document.get("objects"):
                    asset_payload = (
                        self._asset_spec.to_dict()
                        if hasattr(self._asset_spec, "to_dict")
                        else {}
                    )
                    self._figure_document = create_static_figure_document(
                        self._source_path,
                        asset_spec=asset_payload,
                        annotations=annotations,
                    )
                    self._reset_edit_session_from_document(self._figure_document)
                canonical_annotations = [
                    item
                    for item in self._figure_document.get("objects", [])
                    if isinstance(item, dict)
                    and item.get("type") != "image_background"
                ]
                if annotations or not canonical_annotations:
                    self._annotation_canvas.load_annotation_state(annotations)
                    self._annotation_canvas.set_document_interaction_enabled(True)
                else:
                    self._annotation_canvas.set_document_objects(
                        self._figure_document.get("objects", [])
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
            self._set_editor_mode_ui(object_mode=False)
            self._refresh_object_list()
        self._set_editor_dirty(False)
        if self._document_load_report is not None and self._document_load_report.status in {
            "corrupt",
            "unsupported",
        }:
            self._status_label.setText(
                tr("EDITOR_DOCUMENT_WARNING", self._document_load_report.message)
            )
        self._sync_origin_export_enabled()
        self._loading_editor_state = False

    def set_initial_labels(self, title="", xlabel="", ylabel=""):
        self._set_line_edit(self._title_edit, title or "")
        self._set_line_edit(self._xlabel_edit, xlabel or "")
        self._set_line_edit(self._ylabel_edit, ylabel or "")
        self._render()

    def set_figure_generator(self, func, *args, **kwargs):
        self._text_render_timer.stop()
        self._loading_editor_state = True
        self._static_file_mode = False
        self._generated_document_mode = False
        self._generated_draw_tool = "select"
        self._generated_draw_start_data = None
        self._source_path = ""
        self._source_entry_context = None
        self._btn_publish.setEnabled(False)
        self._asset_spec = None
        self._figure_document = {}
        self._reset_edit_session_from_document(self._figure_document)
        self._shared_render_plan = None
        self._selected_figure_object_id = ""
        self._selected_figure_object_ids = ()
        self._hovered_figure_object_id = ""
        self._selection_status_text = ""
        self._hover_status_text = ""
        self._drag_status_text = ""
        self._last_deleted_figure_object_id = ""
        self._generated_handle_drag_state = None
        self._clear_generated_draw_preview(redraw=False)
        self._generated_viewport_snapshot = None
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
        self._set_editor_mode_ui(object_mode=True)
        self._fig_generator = func
        self._fig_args = args
        self._fig_kwargs = kwargs
        self._render()
        self._set_editor_dirty(False)
        self._sync_origin_export_enabled()
        self._loading_editor_state = False

    def is_static_file_mode(self):
        return self._static_file_mode

    def _set_export_buttons_enabled(self, enabled):
        for button in (self._btn_save_as, self._btn_svg, self._btn_png):
            button.setEnabled(enabled)
        if hasattr(self, "_btn_origin_export"):
            self._btn_origin_export.setEnabled(bool(enabled))

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
