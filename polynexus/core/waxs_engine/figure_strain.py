"""In-situ tensile WAXS publication figure recipes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import numpy as np

from polynexus.plotting.sci_style import AXIS_LABELS

from ..figures.contracts import AxisDefinition, DataColumnDefinition, FigureDataSourceDefinition, FigureDefinition, FigureLayoutDefinition, PanelDefinition
from .figure_common import WAXSScanView, classify_waxs_scan_eligibility, scan_views_from_engine
from .figure_static import _finite_profile


EVOLUTION_ID = "waxs.strain.evolution"
RESPONSE_ID = "waxs.strain.response"
SERIES_SI_ID = "waxs.strain.full-series.si"
DIAGNOSTIC_ID = "waxs.strain.sequence.diagnostic"
_COLORS = ("#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")


def _source(source_id: str, columns: Sequence[tuple[str, str, str]], values: Mapping[str, Sequence[Any]], *, role: str = "plot_data") -> FigureDataSourceDefinition:
    return FigureDataSourceDefinition(source_id, tuple(DataColumnDefinition(name, unit, dtype) for name, unit, dtype in columns), {name: tuple(items) for name, items in values.items()}, role=role)


def _panel(panel_id: str, *, x_label: str, y_label: str, x_unit: str = "", y_unit: str = "", legend: bool = False) -> PanelDefinition:
    return PanelDefinition(panel_id, 0, 0, AxisDefinition(f"{panel_id}-x", x_label, x_unit), AxisDefinition(f"{panel_id}-y", y_label, y_unit), show_legend=legend)


def _plot(object_id: str, panel_id: str, source_id: str, x_column: str, y_column: str, *, name: str, color: str, marker: str = "", chart_kind: str = "line") -> dict[str, Any]:
    style: dict[str, Any] = {"color": color, "line_width": 1.1}
    if marker:
        style.update({"marker": marker, "marker_size": 4.0})
    return {"id": object_id, "type": "plot_series", "panel_id": panel_id, "data_ref": source_id, "x_column": x_column, "y_column": y_column, "chart_kind": chart_kind, "name": name, "style": style}


def _definition(*, figure_id: str, role: str, title: str, panels: Sequence[PanelDefinition], sources: Sequence[FigureDataSourceDefinition], objects: Sequence[Mapping[str, Any]], category: str = "series_overview", order: int = 0, parameters: Mapping[str, Any] | None = None) -> FigureDefinition:
    labelled = tuple(replace(panel, column=index, panel_label=f"({chr(ord('a') + index)})") for index, panel in enumerate(panels))
    return FigureDefinition(
        figure_id=figure_id,
        technique="waxs",
        scope="series",
        category=category,
        publication_role=role,
        title=title,
        layout=FigureLayoutDefinition(7.0, 3.8, 1, len(labelled), labelled),
        data_sources=tuple(sources),
        objects=tuple(dict(item) for item in objects),
        recipe={"module": "polynexus.core.waxs_engine.figure_strain", "function": "build_strain_waxs_figure_definitions", "inputs": {"source": "completed_analysis"}, "parameters": {"source": "completed_analysis", "display_order": order, **dict(parameters or {})}, "v2_adapter": "waxs"},
            style_profile="sci_default",
        )


def _point_views(points: Sequence[Any]) -> tuple[WAXSScanView, ...]:
    results = [getattr(point, "waxs_result", None) for point in points]
    return scan_views_from_engine(SimpleNamespace(_results=tuple(result for result in results if result is not None)))


def _eligible_indices(points: Sequence[Any], views: Sequence[WAXSScanView]) -> tuple[int, ...]:
    return tuple(index for index, view in enumerate(views) if index < len(points) and classify_waxs_scan_eligibility(view).highest_role == "main" and np.isfinite(getattr(points[index], "strain_pct", np.nan)))


def _selected_indices(indices: Sequence[int]) -> tuple[int, ...]:
    if not indices:
        return ()
    return tuple(sorted({indices[0], indices[len(indices) // 2], indices[-1]}))


def _image_grid_source(scans: Sequence[Any], indices: Sequence[int]) -> FigureDataSourceDefinition | None:
    images = [getattr(scans[index], "image", None) for index in indices if index < len(scans)]
    if not images or any(not isinstance(image, np.ndarray) or image.ndim != 2 or not np.all(np.isfinite(image)) for image in images):
        return None
    shape = images[0].shape
    if any(image.shape != shape for image in images):
        return None
    grid_column: list[int] = []
    grid_row: list[int] = []
    pixel_x: list[float] = []
    pixel_y: list[float] = []
    intensity: list[float] = []
    for cell, image in enumerate(images):
        row, column = divmod(cell, 3)
        for y in range(shape[0]):
            for x in range(shape[1]):
                grid_column.append(column)
                grid_row.append(row)
                pixel_x.append(float(x))
                pixel_y.append(float(y))
                intensity.append(float(image[y, x]))
    return _source(
        "waxs-strain-image-grid",
        (("grid_column", "", "int64"), ("grid_row", "", "int64"), ("pixel_x", "px", "float64"), ("pixel_y", "px", "float64"), ("intensity", "a.u.", "float64")),
        {"grid_column": grid_column, "grid_row": grid_row, "pixel_x": pixel_x, "pixel_y": pixel_y, "intensity": intensity},
        role="image_data",
    )


def _profile_definition(points: Sequence[Any], views: Sequence[WAXSScanView], indices: Sequence[int], scans: Sequence[Any]) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for position, index in enumerate(indices):
        if index >= len(views):
            continue
        two_theta, intensity = _finite_profile(views[index])
        if len(two_theta) < 2:
            continue
        source_id = f"waxs-strain-profile-{index:03d}"
        sources.append(_source(source_id, (("two_theta_deg", "deg", "float64"), ("intensity", "a.u.", "float64")), {"two_theta_deg": two_theta, "intensity": intensity}))
        strain = float(getattr(points[index], "strain_pct", index))
        objects.append(_plot(f"profile-{index:03d}", "profile", source_id, "two_theta_deg", "intensity", name=f"{strain:g}%", color=_COLORS[position % len(_COLORS)]))
    if not sources:
        return None
    panels = [_panel("profile", x_label=AXIS_LABELS["two_theta"], y_label=AXIS_LABELS["I_waxs"], legend=True)]
    image_source = _image_grid_source(scans, indices)
    if image_source is not None:
        sources.append(image_source)
        panels.append(_panel("patterns", x_label="Pixel x", y_label="Pixel y"))
        objects.append({"id": "pattern-grid", "type": "image_grid", "panel_id": "patterns", "data_ref": image_source.source_id, "grid_column": "grid_column", "grid_row": "grid_row", "x_column": "pixel_x", "y_column": "pixel_y", "z_column": "intensity", "style": {"cmap": "viridis", "origin": "upper"}})
    return _definition(
        figure_id=EVOLUTION_ID,
        role="main",
        title="WAXS tensile structural evolution",
        panels=panels,
        sources=sources,
        objects=objects,
        parameters={"selected_strain_indices": list(indices), "image_grid": image_source is not None},
    )


def _response_choice(points: Sequence[Any], indices: Sequence[int], *, has_images: bool) -> tuple[str, str, str, list[tuple[float, float]]] | None:
    candidates = [
        ("orientation", AXIS_LABELS["f_herman"], lambda point: getattr(point, "f_Herman_avg", np.nan), has_images),
        ("lattice_strain", AXIS_LABELS["epsilon_micro"], lambda point: next(iter(getattr(point, "lattice_strain_per_peak", {}).values()), np.nan), True),
        ("microstrain", AXIS_LABELS["epsilon_micro"], lambda point: getattr(point, "epsilon_WH_pct", np.nan), True),
        ("crystallinity", AXIS_LABELS["phi_c_waxs"], lambda point: getattr(point, "Xc_pct", np.nan), True),
        ("size", AXIS_LABELS["D_scherrer"], lambda point: getattr(point, "D_Scherrer_nm", np.nan), True),
    ]
    for key, label, getter, allowed in candidates:
        if not allowed:
            continue
        rows = []
        for index in indices:
            value = getter(points[index])
            strain = getattr(points[index], "strain_pct", np.nan)
            if np.isfinite(value) and np.isfinite(strain):
                rows.append((float(strain), float(value)))
        if len(rows) >= 3:
            return key, label, "", rows
    return None


def build_strain_waxs_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    series = getattr(engine, "_strain_result", None)
    if series is None:
        return (_definition(
            figure_id=DIAGNOSTIC_ID,
            role="diagnostic",
            title="WAXS strain diagnostics",
            panels=(_panel("diagnostic", x_label=AXIS_LABELS["strain"], y_label=AXIS_LABELS["I_waxs"]),),
            sources=(),
            objects=(),
            category="diagnostic",
            order=100,
            parameters={"no_publication_ready_figure": True, "reason": "missing_strain_result"},
        ),)
    points = tuple(getattr(series, "point_results", ()) or ())
    views = _point_views(points)
    scans = tuple(getattr(getattr(engine, "_dataset", None), "scans", ()) or ())
    eligible = _eligible_indices(points, views)
    selected = _selected_indices(eligible)
    definitions: list[FigureDefinition] = []
    if selected:
        evolution = _profile_definition(points, views, selected, scans)
        if evolution is not None:
            definitions.append(evolution)
        has_images = _image_grid_source(scans, selected) is not None
        response = _response_choice(points, eligible, has_images=has_images)
        if response is not None:
            key, label, unit, rows = response
            source = _source("waxs-strain-response", (("strain_pct", "%", "float64"), ("response", unit, "float64")), {"strain_pct": tuple(row[0] for row in rows), "response": tuple(row[1] for row in rows)}, role="quantitative_parameters")
            definitions.append(_definition(
                figure_id=RESPONSE_ID,
                role="main",
                title="WAXS structural response under strain",
                panels=(_panel("response", x_label=AXIS_LABELS["strain"], y_label=label),),
                sources=(source,),
                objects=(_plot("strain-response", "response", source.source_id, "strain_pct", "response", name=key, color="#0072B2", marker="o", chart_kind="scatter"),),
                order=1,
                parameters={"metric": key, "point_count": len(rows)},
            ))
    if points:
        all_indices = tuple(range(min(len(points), len(views))))
        si = _profile_definition(points, views, all_indices, scans)
        if si is not None:
            si_recipe = dict(si.recipe)
            si_parameters = dict(si_recipe.get("parameters", {}))
            si_parameters["display_order"] = 20
            si_recipe["function"] = "build_strain_waxs_figure_definitions"
            si_recipe["parameters"] = si_parameters
            definitions.append(
                replace(
                    si,
                    figure_id=SERIES_SI_ID,
                    publication_role="si",
                    title="WAXS full strain sequence",
                    recipe=si_recipe,
                )
            )
    if not definitions:
        definitions.append(_definition(
            figure_id=DIAGNOSTIC_ID,
            role="diagnostic",
            title="WAXS strain diagnostics",
            panels=(_panel("diagnostic", x_label=AXIS_LABELS["strain"], y_label=AXIS_LABELS["I_waxs"]),),
            sources=(),
            objects=(),
            category="diagnostic",
            order=100,
            parameters={"no_publication_ready_figure": True, "reason": "no_reliable_strain_evidence"},
        ))
    return tuple(definitions)


__all__ = ["build_strain_waxs_figure_definitions"]
