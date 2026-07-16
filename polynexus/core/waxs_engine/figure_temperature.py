"""Temperature/time-resolved WAXS publication figure recipes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

import numpy as np

from polynexus.plotting.sci_style import AXIS_LABELS

from ..figures.contracts import AxisDefinition, DataColumnDefinition, FigureDataSourceDefinition, FigureDefinition, FigureLayoutDefinition, PanelDefinition
from .figure_common import WAXSScanView, classify_waxs_scan_eligibility, finite_parameter, scan_views_from_engine
from .figure_static import _finite_profile, _peak_position


EVOLUTION_ID = "waxs.temperature.evolution"
TREND_ID = "waxs.temperature.trend"
SERIES_SI_ID = "waxs.temperature.full-series.si"
DIAGNOSTIC_ID = "waxs.temperature.sequence.diagnostic"
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
    labelled = tuple(replace(panel, panel_label=f"({chr(ord('a') + index)})") for index, panel in enumerate(panels))
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
        recipe={"module": "polynexus.core.waxs_engine.figure_temperature", "function": "build_temperature_waxs_figure_definitions", "inputs": {"source": "completed_analysis"}, "parameters": {"source": "completed_analysis", "display_order": order, **dict(parameters or {})}, "v2_adapter": "waxs"},
            style_profile="sci_default",
        )


def _axis_ready(temperature_result: Any) -> bool:
    parameters = getattr(temperature_result, "parameters", {})
    if isinstance(parameters, Mapping) and "temperature_axis_ready" in parameters:
        return bool(parameters["temperature_axis_ready"])
    temperatures = np.asarray(getattr(temperature_result, "temperatures", ()), dtype=float).reshape(-1)
    return temperatures.size >= 1 and bool(np.all(np.isfinite(temperatures))) and bool(np.all(np.diff(temperatures) >= 0))


def _temperature_views(temperature_result: Any) -> tuple[WAXSScanView, ...]:
    return scan_views_from_engine(type("Projection", (), {"_results": tuple(getattr(temperature_result, "results", ()) or ())})())


def _selected_indices(views: Sequence[WAXSScanView], temperatures: Sequence[Any]) -> tuple[int, ...]:
    eligible = [index for index, view in enumerate(views) if classify_waxs_scan_eligibility(view).highest_role == "main"]
    if not eligible:
        return ()
    selected = {eligible[0], eligible[-1], eligible[len(eligible) // 2]}
    transitions = []
    for item in getattr(getattr(temperatures, "temperature_result", None), "transitions", ()) or ():
        if isinstance(item, Mapping):
            value = item.get("temperature_C", item.get("temperature", np.nan))
            if np.isfinite(float(value)):
                transitions.append(float(value))
    temperature_values = np.asarray(temperatures, dtype=float)
    for transition in transitions:
        candidates = [index for index in eligible if index < temperature_values.size]
        if candidates:
            selected.add(min(candidates, key=lambda index: abs(temperature_values[index] - transition)))
    return tuple(sorted(selected))


def _profile_definition(views: Sequence[WAXSScanView], indices: Sequence[int], *, role: str, figure_id: str, title: str, temperatures: Sequence[float], order: int = 0) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for position, index in enumerate(indices):
        view = views[index]
        two_theta, intensity = _finite_profile(view)
        if len(two_theta) < 2:
            continue
        source_id = f"waxs-temperature-profile-{index:03d}"
        sources.append(_source(source_id, (("two_theta_deg", "deg", "float64"), ("intensity", "a.u.", "float64")), {"two_theta_deg": two_theta, "intensity": intensity}))
        temperature = temperatures[index] if index < len(temperatures) else index
        objects.append(_plot(f"profile-{index:03d}", "evolution", source_id, "two_theta_deg", "intensity", name=f"{temperature:g} C", color=_COLORS[position % len(_COLORS)]))
    if not sources:
        return None
    return _definition(
        figure_id=figure_id,
        role=role,
        title=title,
        panels=(_panel("evolution", x_label=AXIS_LABELS["two_theta"], y_label=AXIS_LABELS["I_waxs"], legend=True),),
        sources=sources,
        objects=objects,
        order=order,
        parameters={"selected_frame_indices": list(indices), "temperatures_C": [float(value) for value in temperatures]},
    )


def _trend_choice(views: Sequence[WAXSScanView], temperatures: Sequence[float], result: Any) -> tuple[str, str, str, list[tuple[float, float]]] | None:
    metrics = (
        ("peak_position_deg", AXIS_LABELS["two_theta"], lambda view: _peak_position(view)),
        ("Xc_pct", AXIS_LABELS["phi_c_waxs"], lambda view: finite_parameter(view, "Xc_pct")),
        ("D_Scherrer_nm", AXIS_LABELS["D_scherrer"], lambda view: finite_parameter(view, "D_Scherrer_nm")),
    )
    eligible = {index for index, view in enumerate(views) if classify_waxs_scan_eligibility(view).highest_role == "main"}
    for key, label, getter in metrics:
        rows = []
        for index in sorted(eligible):
            value = getter(views[index])
            if index < len(temperatures) and np.isfinite(value) and np.isfinite(temperatures[index]):
                rows.append((float(temperatures[index]), float(value)))
        if len(rows) >= 3:
            return key, label, "", rows
    return None


def build_temperature_waxs_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    temperature_result = getattr(engine, "_temperature_result", None)
    if temperature_result is None:
        return (_definition(
            figure_id=DIAGNOSTIC_ID,
            role="diagnostic",
            title="WAXS temperature-sequence diagnostics",
            panels=(_panel("diagnostic", x_label=AXIS_LABELS["T"], y_label=AXIS_LABELS["I_waxs"]),),
            sources=(_source("waxs-temperature-empty", (("temperature_C", "degC", "float64"), ("metric", "", "float64")), {"temperature_C": (), "metric": ()}, role="diagnostic_evidence"),),
            objects=(),
            category="diagnostic",
            order=100,
            parameters={"reason": "missing_temperature_result"},
        ),)
    temperatures = tuple(float(value) for value in getattr(temperature_result, "temperatures", ()) or ())
    views = _temperature_views(temperature_result)
    axis_ready = _axis_ready(temperature_result)
    definitions: list[FigureDefinition] = []
    main_views = tuple(view for view in views if classify_waxs_scan_eligibility(view).highest_role == "main")
    if axis_ready and main_views:
        indices = _selected_indices(views, temperatures)
        evolution = _profile_definition(views, indices, role="main", figure_id=EVOLUTION_ID, title="WAXS structural evolution", temperatures=temperatures)
        if evolution is not None:
            definitions.append(evolution)
        trend = _trend_choice(views, temperatures, temperature_result)
        if trend is not None:
            key, label, unit, rows = trend
            source = _source("waxs-temperature-trend", (("temperature_C", "degC", "float64"), ("metric", unit, "float64")), {"temperature_C": tuple(row[0] for row in rows), "metric": tuple(row[1] for row in rows)}, role="quantitative_parameters")
            definitions.append(_definition(
                figure_id=TREND_ID,
                role="main",
                title="WAXS structural trend",
                panels=(_panel("trend", x_label=AXIS_LABELS["T"], y_label=label, legend=False),),
                sources=(source,),
                objects=(_plot("trend-metric", "trend", source.source_id, "temperature_C", "metric", name=key, color="#0072B2", marker="o", chart_kind="scatter"),),
                order=1,
                parameters={"metric": key, "point_count": len(rows)},
            ))
    if views:
        all_indices = tuple(range(len(views)))
        si = _profile_definition(views, all_indices, role="si", figure_id=SERIES_SI_ID, title="WAXS full temperature sequence", temperatures=temperatures, order=20)
        if si is not None:
            definitions.append(si)
    if not axis_ready or not definitions:
        definitions.append(_definition(
            figure_id=DIAGNOSTIC_ID,
            role="diagnostic",
            title="WAXS temperature-sequence diagnostics",
            panels=(_panel("diagnostic", x_label=AXIS_LABELS["T"], y_label=AXIS_LABELS["I_waxs"], legend=True),),
            sources=(),
            objects=(),
            category="diagnostic",
            order=100,
            parameters={"no_publication_ready_figure": True, "axis_ready": axis_ready, "frame_count": len(views), "reason": "axis_not_ready" if not axis_ready else "no_main_evidence"},
        ))
    return tuple(definitions)


__all__ = ["build_temperature_waxs_figure_definitions"]
