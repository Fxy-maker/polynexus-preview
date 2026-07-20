from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF


_TOOL_ACTION_IDS = frozenset(
    {
        "select",
        "text",
        "line",
        "arrow",
        "curve",
        "rectangle",
        "undo",
        "redo",
        "export",
    }
)


def editor_tool_icon(action_id: str, size: int = 18) -> QIcon:
    """Return a compact vector-painted icon for an editor toolbox action."""
    if action_id not in _TOOL_ACTION_IDS:
        return QIcon()

    icon_size = max(1, int(size))
    pixmap = QPixmap(icon_size, icon_size)
    pixmap.fill(Qt.transparent)

    scale = icon_size / 18.0

    def point(x: float, y: float) -> QPointF:
        return QPointF(x * scale, y * scale)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#334155"))
    pen.setWidthF(max(1.25, 1.7 * scale))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)

    if action_id == "select":
        pointer = QPolygonF(
            [point(3, 2), point(4, 14), point(7.5, 10.5), point(10.5, 16), point(13, 14.5), point(10, 9)]
        )
        painter.setBrush(QColor("#e2e8f0"))
        painter.drawPolygon(pointer)
    elif action_id == "text":
        painter.drawLine(point(3, 3), point(15, 3))
        painter.drawLine(point(9, 3), point(9, 15))
    elif action_id == "line":
        painter.drawLine(point(3, 15), point(15, 3))
        painter.setBrush(QColor("#334155"))
        painter.drawEllipse(point(2, 14), 1, 1)
        painter.drawEllipse(point(14, 2), 1, 1)
    elif action_id == "arrow":
        painter.drawLine(point(3, 14), point(13, 4))
        painter.setBrush(QColor("#334155"))
        painter.drawPolygon(QPolygonF([point(10, 4), point(15, 3), point(14, 8)]))
    elif action_id == "curve":
        path = QPainterPath(point(2, 14))
        path.cubicTo(point(5, 2), point(11, 16), point(16, 4))
        painter.drawPath(path)
    elif action_id == "rectangle":
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(point(3, 4), point(12, 10)))
    elif action_id in {"undo", "redo"}:
        direction = -1 if action_id == "undo" else 1
        path = QPainterPath(point(14 if direction < 0 else 4, 5))
        path.cubicTo(
            point(8 if direction < 0 else 10, 2),
            point(3 if direction < 0 else 15, 7),
            point(6 if direction < 0 else 12, 14),
        )
        painter.drawPath(path)
        painter.setBrush(QColor("#334155"))
        head_x = 3 if direction < 0 else 15
        painter.drawPolygon(
            QPolygonF(
                [
                    point(head_x, 5),
                    point(head_x + (4 * direction), 2),
                    point(head_x + (4 * direction), 8),
                ]
            )
        )
    elif action_id == "export":
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(point(3, 10), point(12, 5)))
        painter.drawLine(point(9, 2), point(9, 12))
        painter.setBrush(QColor("#334155"))
        painter.drawPolygon(QPolygonF([point(6, 6), point(9, 10), point(12, 6)]))

    painter.end()
    return QIcon(pixmap)
