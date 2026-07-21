from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget,
)

from ...core.figure_edit_commands import SetVisibilityCommand
from ..i18n import tr
from .chart_editor_tool_icons import editor_tool_icon


class _EditorContextToolbar(QToolBar):
    """Stable action surface for the canvas-first editor context."""

    _ACTION_KEYS = (
        ("select", "EDITOR_TOOL_SELECT"),
        ("text", "EDITOR_TOOL_TEXT"),
        ("line", "EDITOR_TOOL_LINE"),
        ("arrow", "EDITOR_TOOL_ARROW"),
        ("curve", "EDITOR_TOOL_CURVE"),
        ("rectangle", "EDITOR_TOOL_RECTANGLE"),
        ("undo", "EDITOR_TOOL_UNDO"),
        ("redo", "EDITOR_TOOL_REDO"),
        ("export", "EDITOR_TOOL_EXPORT"),
    )
    _TOOL_ACTION_IDS = frozenset(
        {"select", "text", "line", "arrow", "curve", "rectangle"}
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("editor_toolbar")
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(20, 20))
        self.setFixedWidth(78)
        self.setMovable(False)
        self.setFloatable(False)
        self._actions_by_id = {}
        self._buttons_by_id = {}
        self._tool_action_group = QActionGroup(self)
        self._tool_action_group.setExclusive(True)
        self.setStyleSheet(
            "QToolButton[editor-tool-active=\"true\"] {"
            " background-color: #dbeafe; color: #1d4ed8;"
            " border: 1px solid #2563eb; border-radius: 4px;"
            "}"
        )
        for action_id, translation_key in self._ACTION_KEYS:
            if action_id in {"undo", "export"}:
                self.addSeparator()
            text = tr(translation_key)
            action = QAction(text, self)
            action.setObjectName(f"editor_toolbar_{action_id}")
            action.setIcon(editor_tool_icon(action_id, size=18))
            action.setToolTip(tr(translation_key))
            if action_id in self._TOOL_ACTION_IDS:
                action.setCheckable(True)
                self._tool_action_group.addAction(action)
            self._actions_by_id[action_id] = action
            self.addAction(action)
            button = self.widgetForAction(action)
            if button is not None:
                button.setAutoRaise(True)
                button.setMinimumHeight(48)
                button.setAccessibleName(text)
                button.setAccessibleDescription(text)
                self._buttons_by_id[action_id] = button

        self._actions_by_id["select"].setChecked(True)
        self._buttons_by_id["select"].setProperty("editor-tool-active", True)

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
            button = self._buttons_by_id.get(action_id)
            if button is not None:
                button.setAccessibleName(text)
                button.setAccessibleDescription(text)


class ChartEditorLayoutMixin:
    """Presentation helpers for the canvas-first chart editor shell."""

    def _deactivate_navigation_toolbar(self):
        toolbar = getattr(self, "_toolbar", None)
        if toolbar is None:
            return False
        mode = getattr(toolbar, "mode", None)
        mode_name = str(getattr(mode, "name", "") or "").upper()
        if mode_name == "PAN":
            toolbar.pan()
            return True
        if mode_name == "ZOOM":
            toolbar.zoom()
            return True
        return False

    def _build_editor_toolbar(self):
        toolbar = _EditorContextToolbar(self)
        for action_id, callback in (
            ("select", lambda: self.set_tool("select")),
            ("text", lambda: self.set_tool("text")),
            ("line", lambda: self.set_tool("line")),
            ("arrow", lambda: self.set_tool("arrow")),
            ("curve", lambda: self.set_tool("curve")),
            ("rectangle", lambda: self.set_tool("rectangle")),
            ("undo", lambda: self._on_annotation_undo()),
            ("redo", lambda: self._on_annotation_redo()),
            ("export", lambda: self.save_as()),
        ):
            toolbar.action(action_id).triggered.connect(callback)
        return toolbar

    def _build_object_action_bar(self):
        """Build high-frequency selection actions beside the layer tree."""
        bar = QWidget()
        bar.setObjectName("editor_object_action_bar")
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QGridLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(4)
        layout.setVerticalSpacing(4)
        self._object_action_buttons = {}

        def add_button(action_id, label_key, callback, row, column):
            button = QToolButton(bar)
            button.setObjectName(f"editor_object_action_{action_id}")
            button.setText(tr(label_key))
            button.setToolTip(tr(label_key))
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setMinimumHeight(28)
            button.clicked.connect(callback)
            self._object_action_buttons[action_id] = button
            layout.addWidget(button, row, column)
            return button

        def add_menu(action_id, label_key, actions, row, column):
            button = QToolButton(bar)
            button.setObjectName(f"editor_object_action_{action_id}")
            button.setText(tr(label_key))
            button.setToolTip(tr(label_key))
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setPopupMode(QToolButton.InstantPopup)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setMinimumHeight(28)
            menu = QMenu(button)
            for mode, mode_key, callback in actions:
                action = QAction(tr(mode_key), menu)
                action.triggered.connect(
                    lambda _checked=False, mode=mode, callback=callback: callback(mode)
                )
                menu.addAction(action)
            button.setMenu(menu)
            self._object_action_buttons[action_id] = button
            layout.addWidget(button, row, column)
            return button

        add_button("visibility", "EDITOR_CONTEXT_VISIBILITY", self._toggle_selected_visibility, 0, 0)
        add_button("lock", "EDITOR_OBJECT_LOCK", self._on_toggle_selected_lock, 0, 1)
        add_menu(
            "align",
            "EDITOR_CONTEXT_ALIGN",
            (
                ("left", "EDITOR_ALIGN_LEFT", self._align_selected_objects),
                ("center", "EDITOR_ALIGN_CENTER", self._align_selected_objects),
                ("right", "EDITOR_ALIGN_RIGHT", self._align_selected_objects),
                ("top", "EDITOR_ALIGN_TOP", self._align_selected_objects),
                ("middle", "EDITOR_ALIGN_MIDDLE", self._align_selected_objects),
                ("bottom", "EDITOR_ALIGN_BOTTOM", self._align_selected_objects),
            ),
            0,
            2,
        )
        add_menu(
            "distribute",
            "EDITOR_CONTEXT_DISTRIBUTE",
            (
                ("horizontal", "EDITOR_DISTRIBUTE_HORIZONTAL", self._distribute_selected_objects),
                ("vertical", "EDITOR_DISTRIBUTE_VERTICAL", self._distribute_selected_objects),
            ),
            0,
            3,
        )
        add_button("group", "EDITOR_GROUP", self._group_selected_objects, 1, 0)
        add_button("ungroup", "EDITOR_UNGROUP", self._ungroup_selected_objects, 1, 1)
        add_button("delete", "EDITOR_ANNOTATION_DELETE", self._delete_selected_from_canvas, 1, 2)
        for column in range(4):
            layout.setColumnStretch(column, 1)
        return bar

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

        self._mode_badge = QLabel("")
        self._mode_badge.setObjectName("editor_mode_badge")
        self._mode_badge.setAccessibleName(tr("EDITOR_MODE_BADGE"))
        layout.addWidget(self._mode_badge)

        self._dirty_badge = QLabel(tr("EDITOR_STATE_SAVED"))
        self._dirty_badge.setObjectName("editor_dirty_badge")
        self._dirty_badge.setAccessibleName(tr("EDITOR_DIRTY_STATE"))
        layout.addWidget(self._dirty_badge)

        self._btn_header_inspector = QToolButton()
        self._btn_header_inspector.setCheckable(True)
        self._btn_header_inspector.setText(tr("EDITOR_INSPECTOR"))
        self._btn_header_inspector.setAccessibleName(tr("EDITOR_INSPECTOR"))
        self._btn_header_inspector.clicked.connect(self._toggle_inspector_drawer)
        layout.addWidget(self._btn_header_inspector)

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
        self._add_header_export_action(
            "origin",
            tr("EDITOR_EXPORT_ORIGIN"),
            self._export_to_origin,
        )
        self._add_header_export_action(
            "project",
            tr("EDITOR_PROJECT_EXPORT"),
            self.export_project_package,
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
        self._sync_inspector_toggle()
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
            ("Ctrl+Shift+S", self.export_project_package),
            ("Ctrl+Z", self._on_annotation_undo),
            ("Ctrl+Shift+Z", self._on_annotation_redo),
        ):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self._editor_shortcuts.append(shortcut)
        canvas = getattr(self, "_canvas", None)
        if canvas is None:
            return
        for sequence, callback in (
            ("V", lambda: self.set_tool("select")),
            ("T", lambda: self.set_tool("text")),
            ("L", lambda: self.set_tool("line")),
            ("A", lambda: self.set_tool("arrow")),
            ("R", lambda: self.set_tool("rectangle")),
            ("Delete", self._delete_selected_from_canvas),
            ("H", self._toggle_selected_visibility),
            ("Ctrl+G", self._group_selected_objects),
            ("Ctrl+Shift+G", self._ungroup_selected_objects),
            ("Ctrl+Alt+H", lambda: self._set_selected_visibility(True)),
        ):
            shortcut = QShortcut(QKeySequence(sequence), canvas)
            shortcut.setContext(Qt.WidgetShortcut)
            shortcut.activated.connect(callback)
            self._editor_shortcuts.append(shortcut)

    def _build_object_context_menu(self):
        menu = QMenu(self)
        self._object_context_actions = {}

        def add_action(action_id, label_key, callback, parent=menu):
            action = QAction(tr(label_key), parent)
            action.setObjectName(f"editor_context_{action_id}")
            action.triggered.connect(callback)
            parent.addAction(action)
            self._object_context_actions[action_id] = action
            return action

        add_action("toggle_visibility", "EDITOR_CONTEXT_VISIBILITY", self._toggle_selected_visibility)
        add_action("toggle_lock", "EDITOR_OBJECT_LOCK", self._on_toggle_selected_lock)
        add_action("delete", "EDITOR_ANNOTATION_DELETE", self._delete_selected_from_canvas)
        menu.addSeparator()
        add_action("bring_front", "EDITOR_ANNOTATION_FRONT", lambda: self._move_selected_generated_object(to_front=True))
        add_action("send_back", "EDITOR_ANNOTATION_BACK", lambda: self._move_selected_generated_object(to_front=False))

        align_menu = menu.addMenu(tr("EDITOR_CONTEXT_ALIGN"))
        align_menu.setObjectName("editor_context_align_menu")
        for mode, label_key in (
            ("left", "EDITOR_ALIGN_LEFT"),
            ("center", "EDITOR_ALIGN_CENTER"),
            ("right", "EDITOR_ALIGN_RIGHT"),
            ("top", "EDITOR_ALIGN_TOP"),
            ("middle", "EDITOR_ALIGN_MIDDLE"),
            ("bottom", "EDITOR_ALIGN_BOTTOM"),
        ):
            add_action(f"align_{mode}", label_key, lambda _checked=False, mode=mode: self._align_selected_objects(mode), align_menu)

        distribute_menu = menu.addMenu(tr("EDITOR_CONTEXT_DISTRIBUTE"))
        distribute_menu.setObjectName("editor_context_distribute_menu")
        for mode, label_key in (
            ("horizontal", "EDITOR_DISTRIBUTE_HORIZONTAL"),
            ("vertical", "EDITOR_DISTRIBUTE_VERTICAL"),
        ):
            add_action(
                f"distribute_{mode}",
                label_key,
                lambda _checked=False, mode=mode: self._distribute_selected_objects(mode),
                distribute_menu,
            )

        menu.addSeparator()
        add_action("group", "EDITOR_GROUP", self._group_selected_objects)
        add_action("ungroup", "EDITOR_UNGROUP", self._ungroup_selected_objects)
        return menu

    def _show_object_context_menu(self, position):
        menu = self._build_object_context_menu()
        viewport = getattr(self._object_list, "viewport", lambda: self._object_list)()
        menu.exec(viewport.mapToGlobal(position))

    def _set_selected_visibility(self, visible: bool):
        object_id = str(getattr(self, "_selected_figure_object_id", "") or "").strip()
        if not object_id:
            return False
        if getattr(self, "_generated_document_mode", False) and not self._session_has_object(object_id):
            self._reset_edit_session_from_document(self._figure_document)
        result = self._execute_edit(SetVisibilityCommand(object_id, bool(visible)))
        if result is not None and getattr(result, "changed", False):
            if getattr(self, "_generated_document_mode", False):
                self._persist_generated_document()
                self._show_generated_figure_document()
                self._refresh_object_list(object_id)
            return True
        return False

    def _toggle_selected_visibility(self):
        object_id = str(getattr(self, "_selected_figure_object_id", "") or "").strip()
        if not object_id:
            return False
        payload = self._generated_figure_object_by_id_including_deleted(object_id)
        visible = bool(payload.get("visible", True)) if isinstance(payload, dict) else True
        return self._set_selected_visibility(not visible)

    def _delete_selected_from_canvas(self):
        if getattr(self, "_generated_document_mode", False) and getattr(
            self, "_selected_figure_object_id", ""
        ):
            self._soft_delete_selected_generated_object()
            return
        canvas = getattr(self, "_annotation_canvas", None)
        if canvas is not None and not canvas.isHidden():
            canvas.delete_selected_annotation()

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
        self._deactivate_navigation_toolbar()
        navigation_toolbar = getattr(self, "_toolbar", None)
        if navigation_toolbar is not None:
            navigation_toolbar.setVisible(not object_mode)
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
                    and action_id
                    in {"select", "text", "line", "arrow", "curve", "rectangle"}
                )
            )
            action.blockSignals(True)
            action.setChecked(action_id == current_tool)
            action.blockSignals(False)
            button = toolbar.widgetForAction(action)
            if button is not None:
                button.setProperty("editor-tool-active", action_id == current_tool)
                button.style().unpolish(button)
                button.style().polish(button)
                button.update()

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
        sync_origin_export = getattr(self, "_sync_origin_export_enabled", None)
        if sync_origin_export is not None:
            sync_origin_export()

    def retranslate_layout(self):
        if not hasattr(self, "_editor_header"):
            return
        self._source_title_label.setAccessibleName(tr("EDITOR_SOURCE_IDENTITY"))
        self._inspector_tabs.setAccessibleName(tr("EDITOR_INSPECTOR"))
        self._mode_badge.setAccessibleName(tr("EDITOR_MODE_BADGE"))
        self._dirty_badge.setAccessibleName(tr("EDITOR_DIRTY_STATE"))
        self._btn_header_inspector.setText(tr("EDITOR_INSPECTOR"))
        self._btn_header_inspector.setAccessibleName(tr("EDITOR_INSPECTOR"))
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
            ("origin", "EDITOR_EXPORT_ORIGIN"),
            ("project", "EDITOR_PROJECT_EXPORT"),
            ("publish", "EDITOR_PUBLISH_COMPLETE"),
        ):
            self._header_export_actions[key].setText(tr(translation_key))
        self._set_editor_dirty(self._editor_dirty)
