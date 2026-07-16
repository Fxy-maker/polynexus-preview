"""Renderer-independent plotting primitives used by the figure runtime Spike."""

from .spike import (
    AxisGeometry,
    ErrorBarGeometry,
    LegendGeometry,
    LineGeometry,
    MatplotlibSceneRenderer,
    Point,
    QtSceneRenderer,
    RasterComparison,
    Rect,
    RenderComparison,
    RenderScene,
    RenderTrace,
    compare_raster_images,
)
from .matplotlib_renderer import (
    MatplotlibPublicationRenderer,
    PublicationAuditResult,
    PublicationProfile,
    PublicationResult,
)
from .qt_renderer import QtSceneRenderer as QtGraphicsSceneRenderer
from .scene import (
    RenderScene as ResolvedRenderScene,
    SceneDiagnostic,
    SceneDiff,
    SceneNode,
    SceneTrace,
    SceneTraceComparison,
)

__all__ = [
    "AxisGeometry",
    "ErrorBarGeometry",
    "LegendGeometry",
    "LineGeometry",
    "MatplotlibSceneRenderer",
    "Point",
    "QtSceneRenderer",
    "RasterComparison",
    "Rect",
    "RenderComparison",
    "RenderScene",
    "RenderTrace",
    "compare_raster_images",
    "MatplotlibPublicationRenderer",
    "PublicationAuditResult",
    "PublicationProfile",
    "PublicationResult",
    "QtGraphicsSceneRenderer",
    "ResolvedRenderScene",
    "SceneDiagnostic",
    "SceneDiff",
    "SceneNode",
    "SceneTrace",
    "SceneTraceComparison",
]
