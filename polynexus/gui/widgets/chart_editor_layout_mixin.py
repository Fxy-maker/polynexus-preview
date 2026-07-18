from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QToolBar,
    QToolButton,
    QWidget,
)

from ..i18n import tr


class _EditorContextToolbar(QToolBar):
    """Stable action surface for the canvas-first editor context."""

    _ACTION_KEYS = (
        ("select", "EDITOR_TOOL_SELECT"),
        ("text", "EDITOR_TOOL_TEXT"),
        ("line", "EDITOR_TOOL_LINE"),
        ("arrow", "EDITOR_TOOL_ARROW"),
        ("rectangle", "EDITOR_TOOL_RECTANGLE"),
        ("undo", "EDITOR_TOOL_UNDO"),
        ("redo", "EDITOR_TOOL_REDO"),
        ("export", "EDITOR_TOOL_EXPORT"),
    )
    _TOOL_ACTION_IDS = frozenset({"select", "text", "line", "arrow", "rectangle"})

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("editor_toolbar")
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._actions_by_id = {}
        self._tool_action_group = QActionGroup(self)
        self._tool_action_group.setExclusive(True)
        for action_id, translation_key in self._ACTION_KEYS:
            action = QAction(tr(translation_key), self)
            action.setObjectName(f"editor_toolbar_{action_id}")
            action.setToolTip(tr(translation_key))
            if action_id in self._TOOL_ACTION_IDS:
                action.setCheckable(True)
                self._tool_action_group.addAction(action)
            self._actions_by_id[action_id] = action
            self.addAction(action)

    def action_ids(self):
        return [action_id for action_id, _ in self._ACTION_KEYS]

    def action(self, action_id):
        return self._actions_by_id[str(action_id)]

    def retranslate(self):
        for action_id, translation_key in self._ACTION_KEYS:
            action = self._actions_by_id[action_id]
            text = tr(translation_key)
            action.setText(text)
            action.setToolTip(text)


class ChartEditorLayoutMixin:
    """Presentation helpers for the canvas-first chart editor shell."""

    def _build_editor_toolbar(self):
        toolbar = _EditorContextToolbar(self)
        for action_id, callback in (
            ("select", lambda: self.set_tool("select")),
            ("text", lambda: self.set_tool("text")),
            ("line", lambda: self.set_tool("line")),
            ("arrow", lambda: self.set_tool("arrow")),
            ("rectangle", lambda: self.set_tool("rectangle")),
            ("undo", lambda: self._on_annotation_undo()),
            ("redo", lambda: self._on_annotation_redo()),
            ("export", lambda: self.save_as()),
        ):
            toolbar.action(action_id).triggered.connect(callback)
        return toolbar

    def _build_editor_header(self):
        header = QWidget()
        header.setObjectName("editor_header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        self._source_title_label = QLabel(tr("EDITOR_SOURCE_UNNAMED"))
        self._source_title_label.setObjectName("editor_source_title")
        self._source_title_label.setAccessibleName(tr("EDITOR_SOURCE_IDENTITY"))
        self._source_title_label.setToolTip(tr("EDITOR_SOURCE_UNNAMED"))
        layout.addWidget(self._source_title_label, 1)

        self._editor_toolbar = self._build_editor_toolbar()
        layout.addWidget(self._editor_toolbar)

        self._mode_badge = QLabel("")
        self._mode_badge.setObjectName("editor_mode_badge")
        self._mode_badge.setAccessibleName(tr("EDITOR_MODE_BADGE"))
        layout.addWidget(self._mode_badge)

        self._dirty_badge = QLabel(tr("EDITOR_STATE_SAVED"))
        self._dirty_badge.setObjectName("editor_dirty_badge")
        self._dirty_badge.setAccessibleName(tr("EDITOR_DIRTY_STATE"))
        layout.addWidget(self._dirty_badge)

        self._btn_header_save = QPushButton(tr("EDITOR_SAVE_EDITS"))
        self._btn_header_save.setObjectName("editor_header_save")
        self._btn_header_save.setAccessibleName(tr("EDITOR_SAVE_EDITS"))
        self._btn_header_save.clicked.connect(self.save_to_target)
        layout.addWidget(self._btn_header_save)

        self._btn_header_export = QToolButton()
        self._btn_header_export.setText(tr("EDITOR_EXPORT_MENU"))
        self._btn_header_export.setPopupMode(QToolButton.InstantPopup)
        self._btn_header_export.setAccessibleName(tr("EDITOR_EXPORT_MENU"))
        self._header_export_menu = QMenu(self._btn_header_export)
        self._header_export_actions = {}
        self._add_header_export_action(
            "save_as",
            tr("EDITOR_SAVE_AS_COPY"),
            self.save_as,
        )
        self._add_header_export_action(
            "png",
            tr("EDITOR_EXPORT_PNG"),
            lambda: self.save_as("png"),
        )
        self._add_header_export_action(
            "svg",
            tr("EDITOR_EXPORT_SVG"),
            lambda: self.save_as("svg"),
        )
        self._action_header_publish = self._add_header_export_action(
            "publish",
            tr("EDITOR_PUBLISH_COMPLETE"),
            self.publish_complete_assets,
        )
        self._btn_header_export.setMenu(self._header_export_menu)
        layout.addWidget(self._btn_header_export)

        self._install_editor_shortcuts()
        self._set_editor_dirty(False)
        return header

    def _add_header_export_action(self, key, text, callback):
        action = QAction(text, self._header_export_menu)
        action.triggered.connect(callback)
        self._header_export_menu.addAction(action)
        self._header_export_actions[key] = action
        return action

    def _build_editor_status_bar(self):
        footer = QWidget()
        footer.setObjectName("editor_status_bar")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setAccessibleName(tr("EDITOR_STATUS"))
        layout.addWidget(self._status_label, 1)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setAccessibleName(tr("EDITOR_ZOOM_STATUS"))
        layout.addWidget(self._zoom_label)
        return footer

    def _install_editor_shortcuts(self):
        self._editor_shortcuts = []
        for sequence, callback in (
            ("Ctrl+S", self.save_to_target),
            ("Ctrl+Z", self._on_annotation_undo),
            ("Ctrl+Shift+Z", self._on_annotation_redo),
        ):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self._editor_shortcuts.append(shortcut)

    def _set_editor_dirty(self, dirty: bool):
        self._editor_dirty = bool(dirty)
        if not hasattr(self, "_dirty_badge"):
            return
        self._dirty_badge.setText(
            tr("EDITOR_STATE_UNSAVED") if self._editor_dirty else tr("EDITOR_STATE_SAVED")
        )
        self._sync_editor_toolbar()

    def _mark_editor_dirty(self):
        if not getattr(self, "_loading_editor_state", False):
            self._set_editor_dirty(True)

    def _set_editor_mode_ui(self, *, object_mode: bool):
        if not hasattr(self, "_inspector_tabs"):
            return
        self._inspector_tabs.setCurrentIndex(0 if object_mode else 2)
        self._sync_header_actions()
        self._sync_editor_toolbar()

    def _sync_editor_toolbar(self):
        toolbar = getattr(self, "_editor_toolbar", None)
        if toolbar is None:
            return

        canvas = getattr(self, "_annotation_canvas", None)
        annotation_canvas_visible = bool(canvas is not None and not canvas.isHidden())
        object_mode = bool(
            getattr(self, "_generated_document_mode", False)
            or getattr(self, "_fig_generator", None) is not None
        )
        current_tool = str(getattr(self, "_generated_draw_tool", "select") or "select")
        if annotation_canvas_visible:
            current_tool = str(getattr(canvas, "current_tool", lambda: "select")())

        for action_id in _EditorContextToolbar._TOOL_ACTION_IDS:
            action = toolbar.action(action_id)
            action.setEnabled(
                annotation_canvas_visible
                or (
                    object_mode
                    and action_id in {"select", "text", "line", "arrow", "rectangle"}
                )
            )
            action.blockSignals(True)
            action.setChecked(action_id == current_tool)
            action.blockSignals(False)

        session = getattr(self, "_edit_session", None)
        toolbar.action("undo").setEnabled(
            bool(getattr(session, "can_undo", False))
            or bool(getattr(self, "_last_deleted_figure_object_id", ""))
        )
        toolbar.action("redo").setEnabled(bool(getattr(session, "can_redo", False)))
        toolbar.action("export").setEnabled(
            bool(
                getattr(self, "_source_path", "")
                or getattr(self, "_target_path", "")
                or getattr(self, "_fig_generator", None) is not None
                or getattr(self, "_generated_document_mode", False)
                or getattr(self, "_static_file_mode", False)
            )
        )

    def _set_source_identity_ui(self):
        if not hasattr(self, "_source_title_label"):
            return
        title = self._source_mode_title() or tr("EDITOR_SOURCE_UNNAMED")
        self._source_title_label.setText(title)
        self._source_title_label.setToolTip(str(self._source_path or ""))

    def _sync_header_actions(self):
        if not hasattr(self, "_action_header_publish"):
            return
        self._action_header_publish.setEnabled(bool(self._has_manifest_project_context()))

    def retranslate_layout(self):
        if not hasattr(self, "_editor_header"):
            return
        self._source_title_label.setAccessibleName(tr("EDITOR_SOURCE_IDENTITY"))
        self._inspector_tabs.setAccessibleName(tr("EDITOR_INSPECTOR"))
        self._mode_badge.setAccessibleName(tr("EDITOR_MODE_BADGE"))
        self._dirty_badge.setAccessibleName(tr("EDITOR_DIRTY_STATE"))
        self._status_label.setAccessibleName(tr("EDITOR_STATUS"))
        self._zoom_label.setAccessibleName(tr("EDITOR_ZOOM_STATUS"))
        if hasattr(self, "_editor_toolbar"):
            self._editor_toolbar.retranslate()
        self._btn_header_save.setText(tr("EDITOR_SAVE_EDITS"))
        self._btn_header_save.setAccessibleName(tr("EDITOR_SAVE_EDITS"))
        self._btn_header_export.setText(tr("EDITOR_EXPORT_MENU"))
        self._btn_header_export.setAccessibleName(tr("EDITOR_EXPORT_MENU"))
        for key, translation_key in (
            ("save_as", "EDITOR_SAVE_AS_COPY"),
            ("png", "EDITOR_EXPORT_PNG"),
            ("svg", "EDITOR_EXPORT_SVG"),
            ("publish", "EDITOR_PUBLISH_COMPLETE"),
        ):
            self._header_export_actions[key].setText(tr(translation_key))
        self._set_editor_dirty(self._editor_dirty)
