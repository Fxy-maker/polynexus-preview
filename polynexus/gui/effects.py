"""Small UI effects used by the PolyNexus desktop shell.

The helpers stay deliberately lightweight: they use stock Qt animation and
painting APIs, so the GUI keeps working without extra runtime dependencies.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QSequentialAnimationGroup,
    Qt,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QWidget,
)

from .theme import ThemeEngine


def _ease():
    return QEasingCurve(QEasingCurve.OutCubic)


def fade_in(widget: QWidget, duration: int = 180, start: float = 0.0) -> None:
    """Fade *widget* into view using an opacity effect."""
    if widget is None:
        return
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    effect.setOpacity(start)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(1.0)
    anim.setEasingCurve(_ease())
    widget._pn_fade_anim = anim
    anim.start()


def animate_width(widget: QWidget, end_width: int, duration: int = 220) -> None:
    """Animate both min/max width so splitter children collapse smoothly."""
    if widget is None:
        return
    start_width = max(0, widget.width())
    group = QParallelAnimationGroup(widget)
    for prop in (b"minimumWidth", b"maximumWidth"):
        anim = QPropertyAnimation(widget, prop, group)
        anim.setDuration(duration)
        anim.setStartValue(start_width)
        anim.setEndValue(end_width)
        anim.setEasingCurve(_ease())
        group.addAnimation(anim)
    widget._pn_width_anim = group
    group.start()


def start_busy_pulse(widget: QWidget) -> None:
    """Apply a subtle repeating opacity pulse to a busy control."""
    if widget is None:
        return
    stop_busy_pulse(widget)
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(1.0)
    widget.setGraphicsEffect(effect)

    group = QSequentialAnimationGroup(widget)
    down = QPropertyAnimation(effect, b"opacity", group)
    down.setDuration(520)
    down.setStartValue(1.0)
    down.setEndValue(0.72)
    down.setEasingCurve(QEasingCurve(QEasingCurve.InOutSine))
    up = QPropertyAnimation(effect, b"opacity", group)
    up.setDuration(520)
    up.setStartValue(0.72)
    up.setEndValue(1.0)
    up.setEasingCurve(QEasingCurve(QEasingCurve.InOutSine))
    group.addAnimation(down)
    group.addAnimation(up)
    group.setLoopCount(-1)
    widget._pn_busy_pulse = group
    group.start()


def stop_busy_pulse(widget: QWidget) -> None:
    """Remove the busy pulse effect if it is active."""
    group = getattr(widget, "_pn_busy_pulse", None)
    if group is not None:
        group.stop()
        widget._pn_busy_pulse = None
    if isinstance(widget.graphicsEffect(), QGraphicsOpacityEffect):
        widget.setGraphicsEffect(None)


def start_progress_animation(progress_bar) -> None:
    """Animate a QProgressBar with a indeterminate-style looping animation.

    Uses QPropertyAnimation in a sequential group (0→100→0, looped) so the
    bar keeps moving under custom QSS without relying on the native style's
    indeterminate engine that QSS overrides break.
    """
    if progress_bar is None:
        return
    stop_progress_animation(progress_bar)
    progress_bar.setRange(0, 100)
    progress_bar.setValue(0)

    forward = QPropertyAnimation(progress_bar, b"value")
    forward.setDuration(700)
    forward.setStartValue(0)
    forward.setEndValue(100)
    forward.setEasingCurve(QEasingCurve(QEasingCurve.InOutSine))

    backward = QPropertyAnimation(progress_bar, b"value")
    backward.setDuration(700)
    backward.setStartValue(100)
    backward.setEndValue(0)
    backward.setEasingCurve(QEasingCurve(QEasingCurve.InOutSine))

    group = QSequentialAnimationGroup(progress_bar)
    group.addAnimation(forward)
    group.addAnimation(backward)
    group.setLoopCount(-1)
    group.start()
    progress_bar._pn_progress_anim = group


def stop_progress_animation(progress_bar) -> None:
    """Stop the indeterminate progress animation and reset the bar."""
    if progress_bar is None:
        return
    anim = getattr(progress_bar, "_pn_progress_anim", None)
    if anim is not None:
        anim.stop()
        anim.deleteLater()
        progress_bar._pn_progress_anim = None
    progress_bar.setValue(0)


def install_shadow(
    widget: QWidget,
    blur: float = 22.0,
    y: float = 8.0,
    alpha: int = 90,
) -> QGraphicsDropShadowEffect:
    """Attach a theme-aware soft shadow to *widget*."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(QPointF(0, y))
    color = QColor(0, 0, 0, alpha)
    if not ThemeEngine.instance().is_dark:
        color = QColor(40, 48, 62, max(28, alpha // 3))
    effect.setColor(color)
    widget.setGraphicsEffect(effect)
    return effect


def animate_shadow(effect: QGraphicsDropShadowEffect, active: bool) -> None:
    """Animate thumbnail shadows for hover and selection feedback."""
    if effect is None:
        return
    target_blur = 34.0 if active else 18.0
    target_offset = QPointF(0, 12 if active else 5)

    group = QParallelAnimationGroup(effect)
    blur = QPropertyAnimation(effect, b"blurRadius", group)
    blur.setDuration(160)
    blur.setEndValue(target_blur)
    blur.setEasingCurve(_ease())
    offset = QPropertyAnimation(effect, b"offset", group)
    offset.setDuration(160)
    offset.setEndValue(target_offset)
    offset.setEasingCurve(_ease())
    group.addAnimation(blur)
    group.addAnimation(offset)
    effect._pn_shadow_anim = group
    group.start()


class ScientificBackdrop(QWidget):
    """Quiet application backdrop with a barely perceptible vertical wash."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def paintEvent(self, event):
        t = ThemeEngine.instance().tokens
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(t.bg_deep))
        grad.setColorAt(0.7, QColor(t.bg_deep))
        grad.setColorAt(1.0, QColor(t.bg_deep))
        painter.fillRect(self.rect(), grad)

        super().paintEvent(event)
