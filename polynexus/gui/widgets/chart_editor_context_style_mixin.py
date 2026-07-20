from __future__ import annotations

from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSpinBox,
    QToolButton,
    QWidget,
)

from ...core.figure_edit_commands import UpdateStyleCommand
from ..i18n import tr


_LINE_STYLE_VALUES = {
    "Solid": "-",
    "Dashed": "--",
    "Dotted": ":",
    "Dash Dot": "-.",
}


class ChartEditorContextStyleMixin:
    """Compact, canvas-adjacent controls for the active draw tool or selection."""

    _CONTEXT_COLORS = ("#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7")

    def _build_context_style_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("editor_context_style_bar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self._context_tool_hint = QLabel()
        self._context_tool_hint.setObjectName("editor_context_tool_hint")
        layout.addWidget(self._context_tool_hint)

        self._context_color = QToolButton()
        self._context_color.setObjectName("editor_context_color")
        self._context_color.setToolTip(tr("EDITOR_CONTEXT_COLOR"))
        self._context_color.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        color_menu = QMenu(self._context_color)
        for color in self._CONTEXT_COLORS:
            action = QAction(self._color_icon(color), color, color_menu)
            action.triggered.connect(lambda _checked=False, value=color: self._apply_context_color(value))
            color_menu.addAction(action)
        self._context_color.setMenu(color_menu)
        layout.addWidget(self._context_color)

        self._context_line_width = QComboBox()
        self._context_line_width.setObjectName("editor_context_line_width")
        self._context_line_width.setToolTip(tr("EDITOR_CONTEXT_LINE_WIDTH"))
        for value in (1.0, 1.5, 2.0, 3.0, 4.0):
            self._context_line_width.addItem(f"{value:g} px", value)
        self._context_line_width.currentIndexChanged.connect(self._on_context_line_width_changed)
        layout.addWidget(self._context_line_width)

        self._context_line_style = QComboBox()
        self._context_line_style.setObjectName("editor_context_line_style")
        self._context_line_style.setToolTip(tr("EDITOR_CONTEXT_LINE_STYLE"))
        self._context_line_style.addItems(_LINE_STYLE_VALUES)
        self._context_line_style.currentTextChanged.connect(self._apply_context_line_style)
        layout.addWidget(self._context_line_style)

        self._context_font_size = QSpinBox()
        self._context_font_size.setObjectName("editor_context_font_size")
        self._context_font_size.setRange(6, 72)
        self._context_font_size.setSuffix(" pt")
        self._context_font_size.setToolTip(tr("EDITOR_CONTEXT_FONT_SIZE"))
        self._context_font_size.valueChanged.connect(self._apply_context_font_size)
        layout.addWidget(self._context_font_size)

        self._context_advanced = QToolButton()
        self._context_advanced.setObjectName("editor_context_advanced")
        self._context_advanced.setText(tr("EDITOR_CONTEXT_ADVANCED"))
        self._context_advanced.setToolTip(tr("EDITOR_CONTEXT_ADVANCED"))
        self._context_advanced.clicked.connect(self._toggle_inspector_drawer)
        layout.addWidget(self._context_advanced)
        layout.addStretch(1)

        self._context_draw_style = {
            "color": "#D55E00",
            "line_width": 2.0,
            "line_style": "-",
            "font_size": 12.0,
            "alpha": 1.0,
        }
        self._context_style_bar = bar
        bar.setMinimumHeight(32)
        bar.setMaximumHeight(32)
        return bar

    @staticmethod
    def _color_icon(color: str) -> QIcon:
        pixmap = QPixmap(14, 14)
        pixmap.fill(QColor(color))
        return QIcon(pixmap)

    def _current_draw_tool(self) -> str:
        canvas = getattr(self, "_annotation_canvas", None)
        if canvas is not None and not canvas.isHidden():
            return str(canvas.current_tool() or "select")
        return str(getattr(self, "_generated_draw_tool", "select") or "select")

    def _context_target_object(self) -> dict | None:
        if self._current_draw_tool() != "select":
            return None
        candidate = self._selected_canonical_object()
        return candidate if isinstance(candidate, dict) and candidate else None

    def _active_draw_style(self) -> dict[str, object]:
        target = self._context_target_object()
        if target is None:
            return dict(self._context_draw_style)
        style = target.get("style")
        if not isinstance(style, dict):
            style = {}
        return {**self._context_draw_style, **style}

    def _sync_context_style_bar(self) -> None:
        bar = getattr(self, "_context_style_bar", None)
        if bar is None:
            return
        tool = self._current_draw_tool()
        target = self._context_target_object()
        object_type = str(target.get("type", "") or "") if target else ""
        is_text = object_type == "text" or tool == "text"
        is_line = object_type in {"line", "arrow", "curve", "rectangle"} or tool in {
            "line",
            "arrow",
            "curve",
            "rectangle",
        }
        if not (is_text or is_line):
            self._context_tool_hint.clear()
            self._context_color.setVisible(False)
            self._context_line_width.setVisible(False)
            self._context_line_style.setVisible(False)
            self._context_font_size.setVisible(False)
            self._context_advanced.setVisible(False)
            bar.show()
            return

        style = self._active_draw_style()
        with QSignalBlocker(self._context_line_width), QSignalBlocker(
            self._context_line_style
        ), QSignalBlocker(self._context_font_size):
            self._context_line_width.setCurrentIndex(
                self._line_width_index(float(style.get("line_width", 2.0) or 2.0))
            )
            self._context_line_style.setCurrentText(
                self._line_style_label(str(style.get("line_style", "-") or "-"))
            )
            self._context_font_size.setValue(int(float(style.get("font_size", 12) or 12)))
        color = str(style.get("color", "#D55E00") or "#D55E00")
        self._context_color.setIcon(self._color_icon(color))
        self._context_color.setAccessibleName(f"{tr('EDITOR_CONTEXT_COLOR')}: {color}")
        self._context_color.setVisible(True)
        self._context_line_width.setVisible(is_line)
        self._context_line_style.setVisible(is_line)
        self._context_font_size.setVisible(is_text)
        self._context_advanced.setVisible(target is not None)
        self._context_tool_hint.setText(self._context_hint(tool, object_type))
        bar.show()

    def _context_hint(self, tool: str, object_type: str) -> str:
        if tool == "text":
            return tr("EDITOR_DRAW_TEXT_HINT")
        if tool == "curve":
            return tr("EDITOR_DRAW_CURVE_HINT")
        if tool in {"line", "arrow", "rectangle"}:
            return tr("EDITOR_DRAW_OBJECT_HINT")
        if object_type:
            return tr("EDITOR_CONTEXT_SELECTED")
        return ""

    @staticmethod
    def _line_style_label(value: str) -> str:
        return next((label for label, style in _LINE_STYLE_VALUES.items() if style == value), "Solid")

    def _line_width_index(self, value: float) -> int:
        return min(
            range(self._context_line_width.count()),
            key=lambda index: abs(float(self._context_line_width.itemData(index)) - value),
        )

    def _on_context_line_width_changed(self, index: int) -> None:
        value = self._context_line_width.itemData(index)
        if value is not None:
            self._apply_context_line_width(float(value))

    def _apply_context_color(self, color: str) -> bool:
        return self._apply_context_style({"color": str(color)})

    def _apply_context_line_width(self, value: float) -> bool:
        return self._apply_context_style({"line_width": float(value)})

    def _apply_context_line_style(self, label: str) -> bool:
        return self._apply_context_style({"line_style": _LINE_STYLE_VALUES.get(str(label), "-")})

    def _apply_context_font_size(self, value: int) -> bool:
        return self._apply_context_style({"font_size": float(value)})

    def _apply_context_style(self, updates: dict[str, object]) -> bool:
        target = self._context_target_object()
        if target is None:
            self._context_draw_style.update(updates)
            self._sync_context_style_bar()
            return True
        object_id = str(target.get("id", "") or "")
        if not object_id:
            return False
        session = self._edit_session_for_adapter()
        if session is not None:
            result = self._execute_edit(UpdateStyleCommand(object_id, updates))
            if result is None or not result.changed:
                return False
            self._sync_context_style_bar()
            return True
        canvas = getattr(self, "_annotation_canvas", None)
        if canvas is None:
            return False
        changed = canvas.update_selected_properties(
            color=updates.get("color"),
            line_width=updates.get("line_width"),
            line_style=updates.get("line_style"),
            font_size=updates.get("font_size"),
        )
        if changed:
            self._sync_context_style_bar()
        return bool(changed)

    def retranslate_context_style_bar(self) -> None:
        if not hasattr(self, "_context_style_bar"):
            return
        self._context_color.setToolTip(tr("EDITOR_CONTEXT_COLOR"))
        self._context_line_width.setToolTip(tr("EDITOR_CONTEXT_LINE_WIDTH"))
        self._context_line_style.setToolTip(tr("EDITOR_CONTEXT_LINE_STYLE"))
        self._context_font_size.setToolTip(tr("EDITOR_CONTEXT_FONT_SIZE"))
        self._context_advanced.setText(tr("EDITOR_CONTEXT_ADVANCED"))
        self._context_advanced.setToolTip(tr("EDITOR_CONTEXT_ADVANCED"))
        self._sync_context_style_bar()


__all__ = ["ChartEditorContextStyleMixin"]
