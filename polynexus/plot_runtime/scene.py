"""Immutable, renderer-independent resolved scene geometry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import freeze_json, thaw_json


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

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height


@dataclass(frozen=True)
class Segment:
    start: Point
    end: Point


@dataclass(frozen=True)
class HeatmapCell:
    rect: Rect
    value: float


@dataclass(frozen=True)
class TickMark:
    value: float
    label: str
    position: float


@dataclass(frozen=True)
class PanelScene:
    panel_id: str
    axis_rect: Rect
    x_ticks: tuple[TickMark, ...]
    y_ticks: tuple[TickMark, ...]
    x_label: str
    y_label: str
    title: str = ""
    x_scale: str = "linear"
    y_scale: str = "linear"
    x_reversed: bool = False
    y_reversed: bool = False
    x_categories: tuple[str, ...] = ()
    y_categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class SceneDiagnostic:
    reason_code: str
    message: str
    object_id: str = ""
    revision_id: str = ""


@dataclass(frozen=True)
class SceneNode:
    node_id: str
    node_type: str
    panel_id: str
    z_index: int = 0
    visible: bool = True
    points: tuple[Point, ...] = ()
    segments: tuple[Segment, ...] = ()
    rectangles: tuple[HeatmapCell, ...] = ()
    bounds: Rect | None = None
    text_anchor: Point | None = None
    text: str = ""
    style: Any = ()
    metadata: Any = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "style", freeze_json(self.style if self.style else {}))
        object.__setattr__(self, "metadata", freeze_json(self.metadata if self.metadata else {}))

    @property
    def style_map(self) -> dict[str, Any]:
        return thaw_json(self.style)


@dataclass(frozen=True)
class SceneTraceComparison:
    passed: bool
    messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class SceneTrace:
    """Backend-independent geometry trace for renderer acceptance tests."""

    backend: str
    canvas_size: tuple[int, int]
    panels: tuple[tuple[str, Rect], ...]
    nodes: tuple[SceneNode, ...]

    @classmethod
    def from_scene(cls, scene: "RenderScene", backend: str) -> "SceneTrace":
        return cls(
            backend=backend,
            canvas_size=(scene.width_px, scene.height_px),
            panels=tuple((panel.panel_id, panel.axis_rect) for panel in scene.panels),
            nodes=scene.nodes,
        )

    def compare_geometry(
        self,
        other: "SceneTrace",
        *,
        pixel_tolerance: float = 1.0,
    ) -> SceneTraceComparison:
        messages: list[str] = []
        if self.canvas_size != other.canvas_size:
            messages.append(f"canvas size differs: {self.canvas_size} != {other.canvas_size}")
        self_panels = dict(self.panels)
        other_panels = dict(other.panels)
        if tuple(self_panels) != tuple(other_panels):
            messages.append("panel IDs differ")
        for panel_id in self_panels.keys() & other_panels.keys():
            _compare_rectangles(panel_id, self_panels[panel_id], other_panels[panel_id], pixel_tolerance, messages)
        self_nodes = {node.node_id: node for node in self.nodes}
        other_nodes = {node.node_id: node for node in other.nodes}
        if tuple(self_nodes) != tuple(other_nodes):
            messages.append("node IDs differ")
        for node_id in self_nodes.keys() & other_nodes.keys():
            first = self_nodes[node_id]
            second = other_nodes[node_id]
            if first.node_type != second.node_type:
                messages.append(f"{node_id} node type differs")
                continue
            _compare_points(node_id, first.points, second.points, pixel_tolerance, messages)
            _compare_segments(node_id, first.segments, second.segments, pixel_tolerance, messages)
            if len(first.rectangles) != len(second.rectangles):
                messages.append(f"{node_id} rectangle count differs")
            else:
                for index, (left, right) in enumerate(zip(first.rectangles, second.rectangles)):
                    _compare_rectangles(f"{node_id}[{index}]", left.rect, right.rect, pixel_tolerance, messages)
            if first.bounds is not None and second.bounds is not None:
                _compare_rectangles(node_id + " bounds", first.bounds, second.bounds, pixel_tolerance, messages)
            elif first.bounds != second.bounds:
                messages.append(f"{node_id} bounds differ")
            if first.text_anchor is not None and second.text_anchor is not None:
                _compare_points(node_id + " text", (first.text_anchor,), (second.text_anchor,), pixel_tolerance, messages)
            elif first.text_anchor != second.text_anchor:
                messages.append(f"{node_id} text anchor differs")
        return SceneTraceComparison(not messages, tuple(messages))


@dataclass(frozen=True)
class RenderScene:
    revision_id: str
    width_px: int
    height_px: int
    dpi: int
    background: str
    panels: tuple[PanelScene, ...]
    nodes: tuple[SceneNode, ...]

    def __post_init__(self) -> None:
        node_ids = [node.node_id for node in self.nodes]
        panel_ids = [panel.panel_id for panel in self.panels]
        if len(set(panel_ids)) != len(panel_ids) or not panel_ids:
            raise ValueError("scene panels must have unique non-empty IDs")
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("scene nodes must have unique IDs")
        if any(node.panel_id not in panel_ids for node in self.nodes):
            raise ValueError("scene node references an unknown panel")

    def panel_by_id(self, panel_id: str) -> PanelScene:
        for panel in self.panels:
            if panel.panel_id == str(panel_id):
                return panel
        raise KeyError(f"unknown scene panel: {panel_id}")

    def node_by_id(self, node_id: str) -> SceneNode:
        for node in self.nodes:
            if node.node_id == str(node_id):
                return node
        raise KeyError(f"unknown scene node: {node_id}")


@dataclass(frozen=True)
class SceneDiff:
    added_ids: tuple[str, ...]
    updated_ids: tuple[str, ...]
    removed_ids: tuple[str, ...]
    unchanged_ids: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not (self.added_ids or self.updated_ids or self.removed_ids)

    @classmethod
    def between(cls, before: RenderScene | None, after: RenderScene) -> "SceneDiff":
        if before is None:
            return cls(
                added_ids=tuple(node.node_id for node in after.nodes),
                updated_ids=(),
                removed_ids=(),
                unchanged_ids=(),
            )
        before_map = {node.node_id: node for node in before.nodes}
        after_map = {node.node_id: node for node in after.nodes}
        added = tuple(node_id for node_id in after_map if node_id not in before_map)
        removed = tuple(node_id for node_id in before_map if node_id not in after_map)
        updated = tuple(
            node_id
            for node_id in after_map
            if node_id in before_map and after_map[node_id] != before_map[node_id]
        )
        unchanged = tuple(
            node_id
            for node_id in after_map
            if node_id in before_map and after_map[node_id] == before_map[node_id]
        )
        return cls(added, updated, removed, unchanged)

    @classmethod
    def empty(cls) -> "SceneDiff":
        return cls((), (), (), ())


def _compare_rectangles(
    name: str,
    first: Rect,
    second: Rect,
    tolerance: float,
    messages: list[str],
) -> None:
    for field in ("left", "top", "width", "height"):
        difference = abs(getattr(first, field) - getattr(second, field))
        if difference > tolerance:
            messages.append(f"{name} {field} differs by {difference:.3f}px")


def _compare_points(
    name: str,
    first: tuple[Point, ...],
    second: tuple[Point, ...],
    tolerance: float,
    messages: list[str],
) -> None:
    if len(first) != len(second):
        messages.append(f"{name} point count differs")
        return
    for index, (left, right) in enumerate(zip(first, second)):
        difference = max(abs(left.x - right.x), abs(left.y - right.y))
        if difference > tolerance:
            messages.append(f"{name} point {index} differs by {difference:.3f}px")


def _compare_segments(
    name: str,
    first: tuple[Segment, ...],
    second: tuple[Segment, ...],
    tolerance: float,
    messages: list[str],
) -> None:
    if len(first) != len(second):
        messages.append(f"{name} segment count differs")
        return
    for index, (left, right) in enumerate(zip(first, second)):
        _compare_points(f"{name} segment {index} start", (left.start,), (right.start,), tolerance, messages)
        _compare_points(f"{name} segment {index} end", (left.end,), (right.end,), tolerance, messages)
