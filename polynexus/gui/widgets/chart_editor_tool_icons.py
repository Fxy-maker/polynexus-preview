"""Deterministic vector icons for the compact chart-editor toolbar."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


_SUPPORTED_ACTIONS = frozenset(
    {"select", "text", "line", "arrow", "rectangle", "undo", "redo", "export"}
)


def editor_tool_icon(action_id: str, size: int = 18) -> QIcon:
    action = str(action_id or "").strip().lower()
    if action not in _SUPPORTED_ACTIONS or size <= 0:
        return QIcon()
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#D7E3F4"), max(1.0, size / 12.0))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    margin = size * 0.18
    end = size - margin
    center = size / 2
    if action == "select":
        painter.setBrush(QBrush(QColor("#D7E3F4")))
        painter.drawPolygon(
            [QPointF(margin, margin), QPointF(margin, end), QPointF(center, center * 1.15)]
        )
    elif action == "text":
        painter.drawLine(QPointF(margin, margin * 1.2), QPointF(end, margin * 1.2))
        painter.drawLine(QPointF(center, margin * 1.2), QPointF(center, end))
    elif action in {"line", "arrow"}:
        painter.drawLine(QPointF(margin, end), QPointF(end, margin))
        if action == "arrow":
            painter.drawLine(QPointF(end, margin), QPointF(end - size * 0.28, margin))
            painter.drawLine(QPointF(end, margin), QPointF(end, margin + size * 0.28))
    elif action == "rectangle":
        painter.drawRect(QRectF(margin, margin, size - 2 * margin, size - 2 * margin))
    elif action in {"undo", "redo"}:
        path = QPainterPath()
        if action == "undo":
            path.moveTo(end, margin * 1.4)
            path.cubicTo(margin, margin * 1.4, margin, end, end, end)
            painter.drawLine(QPointF(margin, margin * 1.4), QPointF(margin + size * 0.22, margin))
        else:
            path.moveTo(margin, margin * 1.4)
            path.cubicTo(end, margin * 1.4, end, end, margin, end)
            painter.drawLine(QPointF(end, margin * 1.4), QPointF(end - size * 0.22, margin))
        painter.drawPath(path)
    else:
        painter.drawLine(QPointF(center, margin), QPointF(center, end - size * 0.2))
        painter.drawLine(QPointF(margin * 1.4, end - size * 0.22), QPointF(end - margin * 1.4, end - size * 0.22))
        painter.drawLine(QPointF(margin * 1.4, end - size * 0.22), QPointF(margin * 1.4, end - size * 0.42))
        painter.drawLine(QPointF(end - margin * 1.4, end - size * 0.22), QPointF(end - margin * 1.4, end - size * 0.42))
    painter.end()
    return QIcon(pixmap)


__all__ = ["editor_tool_icon"]
