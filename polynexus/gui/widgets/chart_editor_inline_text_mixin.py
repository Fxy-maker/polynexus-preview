from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QLineEdit, QWidget

class _InlineTextEdit(QLineEdit):
    def __init__(self, on_cancel, parent=None):
        super().__init__(parent)
        self._on_cancel = on_cancel

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._on_cancel()
            event.accept()
            return
        super().keyPressEvent(event)


class ChartEditorInlineTextMixin:
    """Own the transient input field used by direct canvas text creation."""

    def _build_inline_text_editor(self) -> QLineEdit:
        editor = _InlineTextEdit(self._cancel_active_draw, self)
        editor.setObjectName("editor_inline_text")
        editor.setFrame(False)
        editor.setPlaceholderText("")
        editor.setStyleSheet(
            "QLineEdit#editor_inline_text {"
            "background: transparent;"
            "border: 1px dashed rgba(47, 111, 191, 150);"
            "border-radius: 2px;"
            "padding: 0 4px;"
            "}"
        )
        editor.setMinimumHeight(24)
        editor.hide()
        editor.returnPressed.connect(self._commit_inline_text_entry)
        editor.editingFinished.connect(self._commit_inline_text_entry)
        self._inline_text_editor = editor
        self._pending_inline_text = None
        self._inline_text_commit_in_progress = False
        return editor

    def _begin_inline_text_entry(self, payload: dict, *, host: QWidget, rect: QRect) -> None:
        if not isinstance(payload, dict):
            return
        self._cancel_inline_text_entry()
        geometry = QRect(rect).normalized()
        top_left = host.mapTo(self, geometry.topLeft())
        initial_text = payload.get("initial_text")
        if initial_text is None:
            self._inline_text_editor.clear()
        else:
            self._inline_text_editor.setText(str(initial_text))
            self._inline_text_editor.selectAll()
        font_metrics = self._inline_text_editor.fontMetrics()
        available_width = max(1, host.width() - max(0, geometry.x()))
        width = min(
            available_width,
            max(
                96,
                geometry.width(),
                font_metrics.horizontalAdvance(self._inline_text_editor.text()) + 24,
            ),
        )
        height = max(24, font_metrics.height() + 8)
        self._pending_inline_text = dict(payload)
        self._inline_text_editor.setGeometry(top_left.x(), top_left.y(), width, height)
        self._inline_text_editor.show()
        self._inline_text_editor.raise_()
        self._inline_text_editor.setFocus()

    def _commit_inline_text_entry(self, text: str | None = None) -> bool:
        payload = self._pending_inline_text
        if (
            not isinstance(payload, dict)
            or getattr(self, "_inline_text_commit_in_progress", False)
        ):
            return False
        value = self._inline_text_editor.text() if text is None else text
        if not str(value or "").strip():
            self._cancel_inline_text_entry()
            return False
        self._inline_text_commit_in_progress = True
        try:
            committed = bool(
                self._commit_inline_text_payload(payload, str(value).strip())
            )
        finally:
            self._inline_text_commit_in_progress = False
        if not committed:
            return False
        self._pending_inline_text = None
        self._inline_text_editor.hide()
        return True

    def _cancel_inline_text_entry(self) -> bool:
        had_pending_text = isinstance(getattr(self, "_pending_inline_text", None), dict)
        self._pending_inline_text = None
        editor = getattr(self, "_inline_text_editor", None)
        if editor is not None:
            was_visible = not editor.isHidden()
            editor.hide()
            return had_pending_text or was_visible
        return had_pending_text

    def retranslate_inline_text_editor(self) -> None:
        # Canvas text entry intentionally has no placeholder: the caret and
        # dashed edit range are the visual affordance in every language.
        return None


__all__ = ["ChartEditorInlineTextMixin"]
