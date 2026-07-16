"""Minimal shared-scene double-renderer Spike.

The Spike deliberately receives resolved pixel geometry instead of data tables.
That makes it possible to test the architectural boundary before adding data
bindings, editor commands, or a long-lived Qt session.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Rect:
    left: float
    top: float
    width: float
    height: float


@dataclass(frozen=True)
class AxisGeometry:
    rect: Rect
    x_ticks: tuple[tuple[float, str], ...]
    y_ticks: tuple[tuple[float, str], ...]
    x_label: str
    y_label: str


@dataclass(frozen=True)
class LineGeometry:
    object_id: str
    points: tuple[Point, ...]
    color: str
    width_px: float
    label: str


@dataclass(frozen=True)
class ErrorBarGeometry:
    object_id: str
    points: tuple[tuple[Point, float], ...]
    color: str
    width_px: float


@dataclass(frozen=True)
class LegendGeometry:
    object_id: str
    anchor: Point
    label: str
    color: str


@dataclass(frozen=True)
class RenderScene:
    width_px: int
    height_px: int
    background: str
    axis: AxisGeometry
    lines: tuple[LineGeometry, ...]
    error_bars: tuple[ErrorBarGeometry, ...]
    legend: LegendGeometry
    title: str


@dataclass(frozen=True)
class RenderComparison:
    passed: bool
    messages: tuple[str, ...]


@dataclass(frozen=True)
class RasterComparison:
    mean_absolute_rgb_error: float
    max_rgb_error: int
    foreground_iou: float
    passed: bool


@dataclass(frozen=True)
class RenderTrace:
    backend: str
    canvas_size: tuple[int, int]
    axis_rect: Rect
    line_paths: tuple[tuple[str, tuple[Point, ...]], ...]
    error_bar_segments: tuple[
        tuple[str, tuple[tuple[Point, Point], ...]], ...
    ]
    legend_anchor: Point
    text_anchors: tuple[tuple[str, Point], ...]

    def compare_geometry(
        self,
        other: "RenderTrace",
        *,
        pixel_tolerance: float = 1.0,
        text_tolerance: float = 2.0,
    ) -> RenderComparison:
        messages: list[str] = []
        if self.canvas_size != other.canvas_size:
            messages.append(
                f"canvas size differs: {self.canvas_size} != {other.canvas_size}"
            )
        _compare_rect("axis", self.axis_rect, other.axis_rect, pixel_tolerance, messages)
        _compare_point(
            "legend",
            self.legend_anchor,
            other.legend_anchor,
            pixel_tolerance,
            messages,
        )
        _compare_named_points(
            "line",
            self.line_paths,
            other.line_paths,
            pixel_tolerance,
            messages,
        )
        _compare_named_segments(
            "error bar",
            self.error_bar_segments,
            other.error_bar_segments,
            pixel_tolerance,
            messages,
        )
        _compare_named_points(
            "text",
            self.text_anchors,
            other.text_anchors,
            text_tolerance,
            messages,
        )
        return RenderComparison(not messages, tuple(messages))


@dataclass(frozen=True)
class QtRenderResult:
    image: QImage
    trace: RenderTrace


@dataclass(frozen=True)
class MatplotlibRenderResult:
    figure: Any
    trace: RenderTrace


class QtSceneRenderer:
    """Draw the already-resolved scene into an offscreen Qt image."""

    def render(self, scene: RenderScene) -> QtRenderResult:
        image = QImage(
            scene.width_px,
            scene.height_px,
            QImage.Format.Format_ARGB32,
        )
        image.fill(QColor(scene.background))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(QFont("DejaVu Sans", 10))
        self._draw_axis(painter, scene.axis)
        for line in scene.lines:
            self._draw_line(painter, line)
        for error_bar in scene.error_bars:
            self._draw_error_bars(painter, error_bar)
        self._draw_legend(painter, scene.legend)
        painter.setPen(QPen(QColor("#222222")))
        title_width = painter.fontMetrics().horizontalAdvance(scene.title)
        painter.drawText(
            QPointF(scene.width_px / 2.0 - title_width / 2.0, 24.0),
            scene.title,
        )
        painter.end()
        return QtRenderResult(image=image, trace=_trace_for_scene(scene, "qt"))

    @staticmethod
    def _draw_axis(painter: QPainter, axis: AxisGeometry) -> None:
        rect = axis.rect
        painter.setPen(QPen(QColor("#222222"), 1.0))
        painter.drawRect(QRectF(rect.left, rect.top, rect.width, rect.height))
        for value, label in axis.x_ticks:
            x = rect.left + value * rect.width
            painter.drawLine(QPointF(x, rect.top + rect.height), QPointF(x, rect.top + rect.height + 6.0))
            painter.drawText(QPointF(x - 8.0, rect.top + rect.height + 22.0), label)
        for value, label in axis.y_ticks:
            y = rect.top + (1.0 - value) * rect.height
            painter.drawLine(QPointF(rect.left - 6.0, y), QPointF(rect.left, y))
            painter.drawText(QPointF(rect.left - 32.0, y + 4.0), label)
        x_label_width = painter.fontMetrics().horizontalAdvance(axis.x_label)
        painter.drawText(
            QPointF(
                rect.left + rect.width / 2.0 - x_label_width / 2.0,
                rect.top + rect.height + 42.0,
            ),
            axis.x_label,
        )
        painter.save()
        painter.translate(rect.left - 46.0, rect.top + rect.height / 2.0)
        painter.rotate(-90.0)
        y_label_width = painter.fontMetrics().horizontalAdvance(axis.y_label)
        painter.drawText(QPointF(-y_label_width / 2.0, 0.0), axis.y_label)
        painter.restore()

    @staticmethod
    def _draw_line(painter: QPainter, line: LineGeometry) -> None:
        painter.setPen(QPen(QColor(line.color), line.width_px))
        painter.drawPolyline(QPolygonF([QPointF(point.x, point.y) for point in line.points]))

    @staticmethod
    def _draw_error_bars(painter: QPainter, error_bar: ErrorBarGeometry) -> None:
        painter.setPen(QPen(QColor(error_bar.color), error_bar.width_px))
        for point, radius in error_bar.points:
            painter.drawLine(QPointF(point.x, point.y - radius), QPointF(point.x, point.y + radius))
            painter.drawLine(QPointF(point.x - 4.0, point.y - radius), QPointF(point.x + 4.0, point.y - radius))
            painter.drawLine(QPointF(point.x - 4.0, point.y + radius), QPointF(point.x + 4.0, point.y + radius))

    @staticmethod
    def _draw_legend(painter: QPainter, legend: LegendGeometry) -> None:
        painter.setPen(QPen(QColor(legend.color), 2.0))
        painter.drawLine(QPointF(legend.anchor.x, legend.anchor.y), QPointF(legend.anchor.x + 24.0, legend.anchor.y))
        painter.setPen(QPen(QColor("#222222")))
        painter.drawText(QPointF(legend.anchor.x + 30.0, legend.anchor.y + 4.0), legend.label)


class MatplotlibSceneRenderer:
    """Draw the same resolved geometry using Matplotlib figure artists."""

    def render(self, scene: RenderScene, *, dpi: int) -> MatplotlibRenderResult:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        figure = Figure(
            figsize=(scene.width_px / dpi, scene.height_px / dpi),
            dpi=dpi,
            facecolor=scene.background,
        )
        FigureCanvasAgg(figure)
        self._draw_axis(figure, scene.axis, scene.width_px, scene.height_px)
        for line in scene.lines:
            self._draw_line(figure, line, scene.width_px, scene.height_px)
        for error_bar in scene.error_bars:
            self._draw_error_bars(figure, error_bar, scene.width_px, scene.height_px)
        self._draw_legend(figure, scene.legend, scene.width_px, scene.height_px)
        figure.text(
            0.5,
            1.0 - 24.0 / scene.height_px,
            scene.title,
            transform=figure.transFigure,
            ha="center",
            va="top",
            fontsize=10,
            color="#222222",
        )
        figure.canvas.draw()
        return MatplotlibRenderResult(
            figure=figure,
            trace=_trace_for_scene(scene, "matplotlib"),
        )

    @staticmethod
    def _to_figure(point: Point, width: int, height: int) -> tuple[float, float]:
        return point.x / width, 1.0 - point.y / height

    @classmethod
    def _draw_axis(cls, figure: Any, axis: AxisGeometry, width: int, height: int) -> None:
        from matplotlib.patches import Rectangle

        rect = axis.rect
        left = rect.left / width
        bottom = 1.0 - (rect.top + rect.height) / height
        figure.add_artist(
            Rectangle(
                (left, bottom),
                rect.width / width,
                rect.height / height,
                transform=figure.transFigure,
                fill=False,
                edgecolor="#222222",
                linewidth=1.0,
            )
        )
        for value, label in axis.x_ticks:
            x = rect.left + value * rect.width
            cls._add_segment(figure, Point(x, rect.top + rect.height), Point(x, rect.top + rect.height + 6.0), width, height)
            figure.text(x / width, 1.0 - (rect.top + rect.height + 22.0) / height, label, ha="center", va="top", fontsize=10)
        for value, label in axis.y_ticks:
            y = rect.top + (1.0 - value) * rect.height
            cls._add_segment(figure, Point(rect.left - 6.0, y), Point(rect.left, y), width, height)
            figure.text((rect.left - 32.0) / width, 1.0 - (y + 4.0) / height, label, ha="right", va="center", fontsize=10)
        figure.text((rect.left + rect.width / 2.0) / width, 1.0 - (rect.top + rect.height + 42.0) / height, axis.x_label, ha="center", va="top", fontsize=10)
        figure.text((rect.left - 46.0) / width, 1.0 - (rect.top + rect.height / 2.0) / height, axis.y_label, ha="right", va="center", fontsize=10, rotation=90)

    @classmethod
    def _draw_line(cls, figure: Any, line: LineGeometry, width: int, height: int) -> None:
        from matplotlib.lines import Line2D

        xs, ys = zip(*(cls._to_figure(point, width, height) for point in line.points))
        figure.add_artist(
            Line2D(
                xs,
                ys,
                transform=figure.transFigure,
                color=line.color,
                linewidth=line.width_px * 72.0 / 100.0,
                label=line.label,
            )
        )

    @classmethod
    def _draw_error_bars(cls, figure: Any, error_bar: ErrorBarGeometry, width: int, height: int) -> None:
        for point, radius in error_bar.points:
            cls._add_segment(figure, Point(point.x, point.y - radius), Point(point.x, point.y + radius), width, height, color=error_bar.color, line_width=error_bar.width_px)
            cls._add_segment(figure, Point(point.x - 4.0, point.y - radius), Point(point.x + 4.0, point.y - radius), width, height, color=error_bar.color, line_width=error_bar.width_px)
            cls._add_segment(figure, Point(point.x - 4.0, point.y + radius), Point(point.x + 4.0, point.y + radius), width, height, color=error_bar.color, line_width=error_bar.width_px)

    @classmethod
    def _draw_legend(cls, figure: Any, legend: LegendGeometry, width: int, height: int) -> None:
        cls._add_segment(figure, legend.anchor, Point(legend.anchor.x + 24.0, legend.anchor.y), width, height, color=legend.color, line_width=2.0)
        figure.text(*cls._to_figure(Point(legend.anchor.x + 30.0, legend.anchor.y + 4.0), width, height), legend.label, ha="left", va="center", fontsize=10, color="#222222")

    @classmethod
    def _add_segment(
        cls,
        figure: Any,
        start: Point,
        end: Point,
        width: int,
        height: int,
        *,
        color: str = "#222222",
        line_width: float = 1.0,
    ) -> None:
        from matplotlib.lines import Line2D

        start_x, start_y = cls._to_figure(start, width, height)
        end_x, end_y = cls._to_figure(end, width, height)
        figure.add_artist(
            Line2D(
                [start_x, end_x],
                [start_y, end_y],
                transform=figure.transFigure,
                color=color,
                linewidth=line_width * 72.0 / 100.0,
            )
        )


def compare_raster_images(qt_image: QImage, matplotlib_figure: Any) -> RasterComparison:
    """Compare the actual offscreen outputs without requiring pixel identity."""

    import numpy as np

    qt_rgba = qt_image.convertToFormat(QImage.Format.Format_RGBA8888)
    qt_array = np.frombuffer(
        bytes(qt_rgba.constBits()),
        dtype=np.uint8,
    ).reshape((qt_rgba.height(), qt_rgba.width(), 4))
    matplotlib_array = np.asarray(matplotlib_figure.canvas.buffer_rgba()).copy()
    if qt_array.shape != matplotlib_array.shape:
        return RasterComparison(
            mean_absolute_rgb_error=float("inf"),
            max_rgb_error=255,
            foreground_iou=0.0,
            passed=False,
        )
    rgb_delta = np.abs(
        qt_array[:, :, :3].astype(np.int16)
        - matplotlib_array[:, :, :3].astype(np.int16)
    )
    qt_foreground = np.any(qt_array[:, :, :3] < 245, axis=2)
    matplotlib_foreground = np.any(matplotlib_array[:, :, :3] < 245, axis=2)
    union = np.logical_or(qt_foreground, matplotlib_foreground).sum()
    intersection = np.logical_and(qt_foreground, matplotlib_foreground).sum()
    foreground_iou = float(intersection / union) if union else 1.0
    mean_absolute_rgb_error = float(rgb_delta.mean())
    max_rgb_error = int(rgb_delta.max())
    return RasterComparison(
        mean_absolute_rgb_error=mean_absolute_rgb_error,
        max_rgb_error=max_rgb_error,
        foreground_iou=foreground_iou,
        passed=mean_absolute_rgb_error <= 6.0,
    )


def _trace_for_scene(scene: RenderScene, backend: str) -> RenderTrace:
    segments: list[tuple[str, tuple[tuple[Point, Point], ...]]] = []
    for error_bar in scene.error_bars:
        error_segments: list[tuple[Point, Point]] = []
        for point, radius in error_bar.points:
            error_segments.extend(
                (
                    (Point(point.x, point.y - radius), Point(point.x, point.y + radius)),
                    (Point(point.x - 4.0, point.y - radius), Point(point.x + 4.0, point.y - radius)),
                    (Point(point.x - 4.0, point.y + radius), Point(point.x + 4.0, point.y + radius)),
                )
            )
        segments.append((error_bar.object_id, tuple(error_segments)))
    return RenderTrace(
        backend=backend,
        canvas_size=(scene.width_px, scene.height_px),
        axis_rect=scene.axis.rect,
        line_paths=tuple((line.object_id, line.points) for line in scene.lines),
        error_bar_segments=tuple(segments),
        legend_anchor=scene.legend.anchor,
        text_anchors=(
            ("title", Point(scene.width_px / 2.0, 24.0)),
            ("x_label", Point(scene.axis.rect.left + scene.axis.rect.width / 2.0, scene.axis.rect.top + scene.axis.rect.height + 42.0)),
            ("y_label", Point(scene.axis.rect.left - 46.0, scene.axis.rect.top + scene.axis.rect.height / 2.0)),
        ),
    )


def _compare_rect(name: str, left: Rect, right: Rect, tolerance: float, messages: list[str]) -> None:
    values = (("left", left.left, right.left), ("top", left.top, right.top), ("width", left.width, right.width), ("height", left.height, right.height))
    for field, first, second in values:
        if abs(first - second) > tolerance:
            messages.append(f"{name} {field} differs by {abs(first - second):.3f}px")


def _compare_point(name: str, left: Point, right: Point, tolerance: float, messages: list[str]) -> None:
    distance = hypot(left.x - right.x, left.y - right.y)
    if distance > tolerance:
        messages.append(f"{name} differs by {distance:.3f}px")


def _compare_named_points(name: str, left, right, tolerance: float, messages: list[str]) -> None:
    if [item[0] for item in left] != [item[0] for item in right]:
        messages.append(f"{name} object IDs differ")
        return
    for (object_id, first_points), (_other_id, second_points) in zip(left, right):
        if isinstance(first_points, Point) and isinstance(second_points, Point):
            _compare_point(name + " " + object_id, first_points, second_points, tolerance, messages)
            continue
        if isinstance(first_points, Point) or isinstance(second_points, Point):
            messages.append(f"{name} {object_id} point shape differs")
            continue
        if len(first_points) != len(second_points):
            messages.append(f"{name} {object_id} point count differs")
            continue
        for index, (first, second) in enumerate(zip(first_points, second_points)):
            distance = hypot(first.x - second.x, first.y - second.y)
            if distance > tolerance:
                messages.append(f"{name} {object_id}[{index}] differs by {distance:.3f}px")


def _compare_named_segments(name: str, left, right, tolerance: float, messages: list[str]) -> None:
    if [item[0] for item in left] != [item[0] for item in right]:
        messages.append(f"{name} object IDs differ")
        return
    for (object_id, first_segments), (_other_id, second_segments) in zip(left, right):
        if len(first_segments) != len(second_segments):
            messages.append(f"{name} {object_id} segment count differs")
            continue
        for index, (first, second) in enumerate(zip(first_segments, second_segments)):
            _compare_point(f"{name} {object_id}[{index}] start", first[0], second[0], tolerance, messages)
            _compare_point(f"{name} {object_id}[{index}] end", first[1], second[1], tolerance, messages)
