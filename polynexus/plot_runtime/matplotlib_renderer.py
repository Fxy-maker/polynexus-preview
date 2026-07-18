"""Matplotlib publication backend for resolved, renderer-independent scenes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .scene import PanelScene, Point, RenderScene, SceneDiagnostic, SceneNode, SceneTrace


@dataclass(frozen=True)
class PublicationProfile:
    dpi: int = 300
    font_family: str = "DejaVu Sans"
    embed_fonts: bool = True
    formats: tuple[str, ...] = ("svg", "pdf", "png", "tiff")


@dataclass(frozen=True)
class PublicationAuditResult:
    passed: bool
    issues: tuple[SceneDiagnostic, ...] = ()


@dataclass(frozen=True)
class PublicationResult:
    ok: bool
    scene_revision_id: str
    provenance: Mapping[str, str]
    paths: tuple[Path, ...] = ()
    diagnostics: tuple[SceneDiagnostic, ...] = ()
    audit: PublicationAuditResult | None = None


class MatplotlibPublicationRenderer:
    """Render a ``RenderScene`` for publication without consulting Qt state."""

    _SUPPORTED_NODE_TYPES = {
        "plot_series",
        "line",
        "heatmap",
        "image_grid",
        "legend",
        "text",
    }
    _SUPPORTED_FORMATS = {"svg", "pdf", "png", "tif", "tiff"}

    def render(self, scene: RenderScene, *, profile: PublicationProfile | None = None) -> Any:
        profile = profile or PublicationProfile(dpi=scene.dpi)
        diagnostics = self._validate(scene)
        if diagnostics:
            raise ValueError(diagnostics[0].message)
        import matplotlib
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        rc_params = {
            "font.family": [profile.font_family],
            "pdf.fonttype": 42 if profile.embed_fonts else 3,
            "svg.fonttype": "none" if profile.embed_fonts else "path",
        }
        with matplotlib.rc_context(rc_params):
            figure = Figure(
                figsize=(scene.width_px / profile.dpi, scene.height_px / profile.dpi),
                dpi=profile.dpi,
                facecolor=scene.background,
            )
            FigureCanvasAgg(figure)
            for panel in scene.panels:
                self._draw_panel(figure, panel, scene.width_px, scene.height_px)
            for node in sorted(scene.nodes, key=lambda item: item.z_index):
                self._draw_node(figure, node, scene.width_px, scene.height_px)
            figure.canvas.draw()
        return figure

    @staticmethod
    def trace(scene: RenderScene) -> SceneTrace:
        return SceneTrace.from_scene(scene, "matplotlib")

    def export(
        self,
        scene: RenderScene,
        destination: str | Path,
        *,
        profile: PublicationProfile | None = None,
        provenance: Mapping[str, str] | None = None,
    ) -> PublicationResult:
        profile = profile or PublicationProfile(dpi=scene.dpi)
        normalized_provenance = dict(provenance or {})
        normalized_provenance.setdefault("scene_revision_id", scene.revision_id)
        diagnostics = (*self._validate(scene), *self._validate_formats(profile))
        if diagnostics:
            return PublicationResult(
                ok=False,
                scene_revision_id=scene.revision_id,
                provenance=normalized_provenance,
                diagnostics=diagnostics,
                audit=PublicationAuditResult(False, diagnostics),
            )
        figure = self.render(scene, profile=profile)
        stem = Path(destination)
        if stem.suffix:
            stem = stem.with_suffix("")
        stem.parent.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        provenance_text = "; ".join(
            f"{key}={value}" for key, value in normalized_provenance.items()
        )
        for format_name in profile.formats:
            normalized_format = str(format_name).lower().lstrip(".")
            path = stem.with_suffix(f".{normalized_format}")
            figure.savefig(
                path,
                format=normalized_format,
                dpi=profile.dpi,
                metadata=self._metadata_for_format(normalized_format, provenance_text),
            )
            paths.append(path)
        audit = self.audit(
            scene,
            tuple(paths),
            profile=profile,
            provenance=normalized_provenance,
        )
        if not audit.passed:
            for path in paths:
                path.unlink(missing_ok=True)
            return PublicationResult(
                ok=False,
                scene_revision_id=scene.revision_id,
                provenance=normalized_provenance,
                diagnostics=audit.issues,
                audit=audit,
            )
        return PublicationResult(
            ok=True,
            scene_revision_id=scene.revision_id,
            provenance=normalized_provenance,
            paths=tuple(paths),
            audit=audit,
        )

    def audit(
        self,
        scene: RenderScene,
        paths: tuple[Path, ...],
        *,
        profile: PublicationProfile | None = None,
        provenance: Mapping[str, str] | None = None,
    ) -> PublicationAuditResult:
        profile = profile or PublicationProfile(dpi=scene.dpi)
        issues: list[SceneDiagnostic] = [
            *self._validate(scene),
            *self._validate_formats(profile),
        ]
        expected_formats = {
            str(format_name).lower().lstrip(".") for format_name in profile.formats
        }
        actual_formats = {path.suffix.lower().lstrip(".") for path in paths}
        if actual_formats != expected_formats:
            issues.append(
                SceneDiagnostic(
                    "asset_format_mismatch",
                    f"exported formats differ from profile: {sorted(actual_formats)} != {sorted(expected_formats)}",
                    revision_id=scene.revision_id,
                )
            )
        for path in paths:
            if not path.is_file() or path.stat().st_size <= 0:
                issues.append(
                    SceneDiagnostic(
                        "empty_publication_asset",
                        f"publication asset is missing or empty: {path}",
                        revision_id=scene.revision_id,
                    )
                )
        if not provenance or str(provenance.get("scene_revision_id") or "") != scene.revision_id:
            issues.append(
                SceneDiagnostic(
                    "missing_provenance",
                    "publication provenance must include the scene revision",
                    revision_id=scene.revision_id,
                )
            )
        return PublicationAuditResult(not issues, tuple(issues))

    @staticmethod
    def _metadata_for_format(format_name: str, provenance_text: str) -> dict[str, str] | None:
        if format_name == "svg":
            return {"Description": provenance_text}
        if format_name == "pdf":
            return {"Subject": provenance_text}
        if format_name == "png":
            return {"Software": f"PolyNexus; {provenance_text}"}
        return None

    @classmethod
    def _validate(cls, scene: RenderScene) -> tuple[SceneDiagnostic, ...]:
        diagnostics: list[SceneDiagnostic] = []
        for node in scene.nodes:
            if node.node_type not in cls._SUPPORTED_NODE_TYPES:
                diagnostics.append(
                    SceneDiagnostic(
                        "unsupported_object_type",
                        f"publication renderer does not support {node.node_type}",
                        object_id=node.node_id,
                        revision_id=scene.revision_id,
                    )
                )
        return tuple(diagnostics)

    @classmethod
    def _validate_formats(cls, profile: PublicationProfile) -> tuple[SceneDiagnostic, ...]:
        diagnostics: list[SceneDiagnostic] = []
        for format_name in profile.formats:
            normalized = str(format_name).lower().lstrip(".")
            if normalized not in cls._SUPPORTED_FORMATS:
                diagnostics.append(
                    SceneDiagnostic(
                        "unsupported_format",
                        f"publication format is not supported: {format_name}",
                    )
                )
        return tuple(diagnostics)

    @classmethod
    def _draw_panel(cls, figure: Any, panel: PanelScene, width: int, height: int) -> None:
        from matplotlib.patches import Rectangle

        rect = panel.axis_rect
        figure.add_artist(
            Rectangle(
                (rect.left / width, 1.0 - (rect.top + rect.height) / height),
                rect.width / width,
                rect.height / height,
                transform=figure.transFigure,
                fill=False,
                edgecolor="#333333",
                linewidth=1.0,
            )
        )
        for tick in panel.x_ticks:
            cls._add_segment(
                figure,
                Point(tick.position, rect.bottom),
                Point(tick.position, rect.bottom + 5.0),
                width,
                height,
            )
            figure.text(tick.position / width, cls._y(rect.bottom + 7.0, height), tick.label, ha="center", va="top", fontsize=8)
        for tick in panel.y_ticks:
            cls._add_segment(
                figure,
                Point(rect.left - 5.0, tick.position),
                Point(rect.left, tick.position),
                width,
                height,
            )
            figure.text(cls._x(rect.left - 8.0, width), cls._y(tick.position, height), tick.label, ha="right", va="center", fontsize=8)
        if panel.title:
            figure.text(cls._x(rect.left, width), cls._y(max(0.0, rect.top - 8.0), height), panel.title, ha="left", va="bottom", fontsize=10)
        if panel.x_label:
            figure.text(cls._x(rect.left + rect.width / 2.0, width), cls._y(rect.bottom + 25.0, height), panel.x_label, ha="center", va="top", fontsize=9)
        if panel.y_label:
            figure.text(cls._x(rect.left - 35.0, width), cls._y(rect.top + rect.height / 2.0, height), panel.y_label, ha="right", va="center", rotation=90, fontsize=9)

    @classmethod
    def _draw_node(cls, figure: Any, node: SceneNode, width: int, height: int) -> None:
        from matplotlib.lines import Line2D
        from matplotlib.patches import Rectangle

        style = node.style_map
        color = str(style.get("color", "#1f77b4"))
        line_width = float(style.get("line_width", 1.0))
        line_style = "--" if style.get("line_style") in {"dashed", "--"} else "-"
        if node.node_type in {"plot_series", "line"}:
            if node.points:
                xs, ys = zip(*(cls._to_figure(point, width, height) for point in node.points))
                figure.add_artist(Line2D(xs, ys, transform=figure.transFigure, color=color, linewidth=line_width * 72.0 / 100.0, linestyle=line_style))
            for segment in node.segments:
                cls._add_segment(figure, segment.start, segment.end, width, height, color=color, line_width=line_width, line_style=line_style)
            return
        if node.node_type == "heatmap":
            for cell in node.rectangles:
                rect = cell.rect
                figure.add_artist(
                    Rectangle(
                        (cls._x(rect.left, width), cls._y(rect.bottom, height)),
                        rect.width / width,
                        rect.height / height,
                        transform=figure.transFigure,
                        facecolor=color,
                        edgecolor=color,
                        linewidth=0.5,
                    )
                )
            return
        if node.node_type == "image_grid":
            import matplotlib
            from matplotlib.colors import Normalize

            values = [float(cell.value) for cell in node.rectangles]
            vmin = min(values) if values else 0.0
            vmax = max(values) if values else 1.0
            if vmax <= vmin:
                vmax = vmin + 1.0
            cmap_name = str(style.get("cmap", style.get("colormap", "viridis")) or "viridis")
            try:
                cmap = matplotlib.colormaps.get_cmap(cmap_name)
            except (AttributeError, ValueError):
                cmap = matplotlib.cm.get_cmap(cmap_name)
            normalize = Normalize(vmin=vmin, vmax=vmax)
            for cell in node.rectangles:
                rect = cell.rect
                color_value = cmap(normalize(float(cell.value)))
                figure.add_artist(
                    Rectangle(
                        (cls._x(rect.left, width), cls._y(rect.bottom, height)),
                        rect.width / width,
                        rect.height / height,
                        transform=figure.transFigure,
                        facecolor=color_value,
                        edgecolor=color_value,
                        linewidth=0.25,
                    )
                )
            return
        if node.node_type == "legend":
            if node.bounds is not None:
                bounds = node.bounds
                figure.add_artist(
                    Rectangle(
                        (cls._x(bounds.left, width), cls._y(bounds.bottom, height)),
                        bounds.width / width,
                        bounds.height / height,
                        transform=figure.transFigure,
                        facecolor="#FFFFFF",
                        edgecolor="#777777",
                        linewidth=1.0,
                        alpha=0.86,
                    )
                )
            if node.text_anchor is not None:
                figure.text(cls._x(node.text_anchor.x, width), cls._y(node.text_anchor.y, height), node.text, ha="left", va="center", fontsize=9)
            return
        if node.node_type == "text" and node.text_anchor is not None:
            figure.text(cls._x(node.text_anchor.x, width), cls._y(node.text_anchor.y, height), node.text, ha="left", va="top", fontsize=9, color=color)

    @staticmethod
    def _add_segment(
        figure: Any,
        start: Point,
        end: Point,
        width: int,
        height: int,
        *,
        color: str = "#333333",
        line_width: float = 1.0,
        line_style: str = "-",
    ) -> None:
        from matplotlib.lines import Line2D

        start_x, start_y = MatplotlibPublicationRenderer._to_figure(start, width, height)
        end_x, end_y = MatplotlibPublicationRenderer._to_figure(end, width, height)
        figure.add_artist(Line2D([start_x, end_x], [start_y, end_y], transform=figure.transFigure, color=color, linewidth=line_width * 72.0 / 100.0, linestyle=line_style))

    @staticmethod
    def _to_figure(point: Point, width: int, height: int) -> tuple[float, float]:
        return point.x / width, 1.0 - point.y / height

    @staticmethod
    def _x(value: float, width: int) -> float:
        return value / width

    @staticmethod
    def _y(value: float, height: int) -> float:
        return 1.0 - value / height
