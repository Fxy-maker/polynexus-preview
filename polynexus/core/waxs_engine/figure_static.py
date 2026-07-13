"""Static and multi-sample WAXS publication figure recipes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

import numpy as np

from polynexus.plotting.sci_style import AXIS_LABELS

from ..figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)
from .figure_common import WAXSScanView, classify_waxs_scan_eligibility, finite_parameter, scan_views_from_engine


STATIC_PROFILE_ID = "waxs.static.profile"
PROFILE_COMPARISON_ID = "waxs.comparison.profiles"
PEAK_COMPARISON_ID = "waxs.comparison.peak-position"
CRYSTALLINITY_COMPARISON_ID = "waxs.comparison.crystallinity"
SIZE_COMPARISON_ID = "waxs.comparison.size"
FIT_SI_ID = "waxs.static.fit.si"
DIAGNOSTIC_ID = "waxs.static.fit.diagnostic"

_COLORS = ("#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")


def _source(source_id: str, columns: Sequence[tuple[str, str, str]], values: Mapping[str, Sequence[Any]], *, role: str = "plot_data") -> FigureDataSourceDefinition:
    return FigureDataSourceDefinition(
        source_id=source_id,
        columns=tuple(DataColumnDefinition(name, unit, dtype) for name, unit, dtype in columns),
        values={name: tuple(items) for name, items in values.items()},
        role=role,
    )


def _panel(panel_id: str, *, x_label: str, y_label: str, x_unit: str = "", y_unit: str = "", legend: bool = False) -> PanelDefinition:
    return PanelDefinition(
        panel_id=panel_id,
        row=0,
        column=0,
        x_axis=AxisDefinition(f"{panel_id}-x", x_label, x_unit),
        y_axis=AxisDefinition(f"{panel_id}-y", y_label, y_unit),
        show_legend=legend,
    )


def _plot(object_id: str, panel_id: str, source_id: str, x_column: str, y_column: str, *, name: str, color: str, marker: str = "", chart_kind: str = "line") -> dict[str, Any]:
    style: dict[str, Any] = {"color": color, "line_width": 1.1}
    if marker:
        style.update({"marker": marker, "marker_size": 4.0})
    return {
        "id": object_id,
        "type": "plot_series",
        "panel_id": panel_id,
        "data_ref": source_id,
        "x_column": x_column,
        "y_column": y_column,
        "chart_kind": chart_kind,
        "name": name,
        "style": style,
    }


def _line(object_id: str, panel_id: str, x: float) -> dict[str, Any]:
    return {
        "id": object_id,
        "type": "line",
        "panel_id": panel_id,
        "orientation": "vertical",
        "x": float(x),
        "style": {"color": "#D55E00", "line_width": 0.8, "line_style": "--", "alpha": 0.8},
    }


def _labelled_panels(panels: Sequence[PanelDefinition]) -> tuple[PanelDefinition, ...]:
    return tuple(replace(panel, panel_label=f"({chr(ord('a') + index)})") for index, panel in enumerate(panels))


def _definition(*, figure_id: str, role: str, title: str, panels: Sequence[PanelDefinition], sources: Sequence[FigureDataSourceDefinition], objects: Sequence[Mapping[str, Any]], category: str = "series_overview", order: int = 0, parameters: Mapping[str, Any] | None = None) -> FigureDefinition:
    return FigureDefinition(
        figure_id=figure_id,
        technique="waxs",
        scope="series",
        category=category,
        publication_role=role,
        title=title,
        layout=FigureLayoutDefinition(
            width_in=7.0,
            height_in=3.8,
            rows=1,
            columns=len(panels),
            panels=_labelled_panels(panels),
        ),
        data_sources=tuple(sources),
        objects=tuple(dict(item) for item in objects),
        recipe={
            "module": "polynexus.core.waxs_engine.figure_static",
            "function": "build_static_waxs_figure_definitions",
            "inputs": {"source": "completed_analysis"},
            "parameters": {
                "source": "completed_analysis",
                "display_order": order,
                **dict(parameters or {}),
            },
            },
            style_profile="sci_default",
        )


def _finite_profile(view: WAXSScanView) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if len(view.two_theta_deg) != len(view.intensity):
        return (), ()
    pairs = [
        (float(two_theta), float(intensity))
        for two_theta, intensity in zip(view.two_theta_deg, view.intensity)
        if np.isfinite(two_theta) and np.isfinite(intensity)
    ]
    return tuple(item[0] for item in pairs), tuple(item[1] for item in pairs)


def _peak_position(view: WAXSScanView) -> float:
    values = []
    for peak in view.peaks:
        if isinstance(peak, Mapping):
            value = peak.get("two_theta", peak.get("two_theta_deg", np.nan))
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = np.nan
            if np.isfinite(value):
                values.append(value)
    return float(values[0]) if values else np.nan


def metric_main_eligible(view: WAXSScanView, key: str) -> bool:
    if classify_waxs_scan_eligibility(view).highest_role != "main":
        return False
    if key == "peak_position_deg":
        return bool(np.isfinite(_peak_position(view)))
    value = finite_parameter(view, key)
    if not np.isfinite(value):
        return False
    if key == "D_Scherrer_nm":
        status = view.size_reliability_status.strip().lower()
        return value > 0 and status not in {"unreliable", "failed", "invalid", "low_confidence"}
    return True


def _comparison_metric(views: Sequence[WAXSScanView]) -> tuple[str, str, str, str] | None:
    for key, figure_id, label, unit in (
        ("peak_position_deg", PEAK_COMPARISON_ID, AXIS_LABELS["two_theta"], ""),
        ("Xc_pct", CRYSTALLINITY_COMPARISON_ID, AXIS_LABELS["phi_c_waxs"], ""),
        ("D_Scherrer_nm", SIZE_COMPARISON_ID, AXIS_LABELS["D_scherrer"], ""),
    ):
        if sum(metric_main_eligible(view, key) for view in views) >= 3:
            return key, figure_id, label, unit
    return None


def _profile_definition(views: Sequence[WAXSScanView], *, role: str, figure_id: str, title: str, order: int = 0) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for position, view in enumerate(views):
        two_theta, intensity = _finite_profile(view)
        if len(two_theta) < 2:
            continue
        source_id = f"waxs-static-profile-{view.index:03d}"
        sources.append(_source(source_id, (("two_theta_deg", "deg", "float64"), ("intensity", "a.u.", "float64")), {"two_theta_deg": two_theta, "intensity": intensity}))
        objects.append(_plot(f"profile-{view.index:03d}", "profile", source_id, "two_theta_deg", "intensity", name=view.label, color=_COLORS[position % len(_COLORS)]))
        for peak_index, peak in enumerate(view.peaks):
            if not isinstance(peak, Mapping):
                continue
            value = peak.get("two_theta", peak.get("two_theta_deg", np.nan))
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = np.nan
            if np.isfinite(value):
                objects.append(_line(f"peak-{view.index:03d}-{peak_index:03d}", "profile", value))
    if not sources:
        return None
    return _definition(
        figure_id=figure_id,
        role=role,
        title=title,
        panels=(_panel("profile", x_label=AXIS_LABELS["two_theta"], y_label=AXIS_LABELS["I_waxs"], legend=True),),
        sources=sources,
        objects=objects,
        order=order,
        parameters={"scan_indices": [view.index for view in views]},
    )


def _comparison_definition(views: Sequence[WAXSScanView], metric: tuple[str, str, str, str]) -> FigureDefinition:
    key, figure_id, label, unit = metric
    rows: list[tuple[float, float]] = []
    for index, view in enumerate(views):
        value = _peak_position(view) if key == "peak_position_deg" else finite_parameter(view, key)
        if metric_main_eligible(view, key):
            rows.append((float(index), float(value)))
    source = _source(
        f"waxs-comparison-{key}",
        (("sample_index", "", "float64"), ("metric", unit, "float64")),
        {"sample_index": tuple(row[0] for row in rows), "metric": tuple(row[1] for row in rows)},
        role="quantitative_parameters",
    )
    return _definition(
        figure_id=figure_id,
        role="main",
        title="WAXS quantitative comparison",
        panels=(_panel("comparison", x_label="Sample", y_label=label, legend=False),),
        sources=(source,),
        objects=(_plot("comparison-metric", "comparison", source.source_id, "sample_index", "metric", name=key, color="#0072B2", marker="o", chart_kind="scatter"),),
        parameters={"metric": key, "sample_count": len(rows)},
    )


def _fit_si_definition(views: Sequence[WAXSScanView]) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for position, view in enumerate(views):
        two_theta, intensity = _finite_profile(view)
        if len(two_theta) < 2:
            continue
        columns = [("two_theta_deg", "deg", "float64"), ("intensity", "a.u.", "float64")]
        values: dict[str, Sequence[Any]] = {"two_theta_deg": two_theta, "intensity": intensity}
        if len(view.fit) == len(view.two_theta_deg):
            fit = tuple(float(value) for value in view.fit if np.isfinite(value))
            if len(fit) == len(two_theta):
                columns.append(("fit", "a.u.", "float64"))
                values["fit"] = fit
        if len(view.background) == len(view.two_theta_deg):
            background = tuple(float(value) for value in view.background if np.isfinite(value))
            if len(background) == len(two_theta):
                columns.append(("background", "a.u.", "float64"))
                values["background"] = background
        source_id = f"waxs-static-fit-{view.index:03d}"
        sources.append(_source(source_id, columns, values, role="fit_evidence"))
        if "fit" in values:
            objects.append(_plot(f"fit-{view.index:03d}", "fit", source_id, "two_theta_deg", "fit", name=f"Fit: {view.label}", color="#D55E00"))
        if "background" in values:
            objects.append(_plot(f"background-{view.index:03d}", "fit", source_id, "two_theta_deg", "background", name=f"Background: {view.label}", color="#666666"))
    if not sources or not objects:
        return None
    return _definition(
        figure_id=FIT_SI_ID,
        role="si",
        title="WAXS fit and background evidence",
        panels=(_panel("fit", x_label=AXIS_LABELS["two_theta"], y_label=AXIS_LABELS["I_waxs"], legend=True),),
        sources=sources,
        objects=objects,
        category="supplementary",
        order=20,
    )


def _diagnostic_definition(views: Sequence[WAXSScanView], *, no_main: bool = False) -> FigureDefinition:
    profile = _profile_definition(views, role="diagnostic", figure_id=DIAGNOSTIC_ID, title="WAXS profile diagnostics", order=100)
    if profile is not None:
        return replace(
            profile,
            recipe={
                **dict(profile.recipe),
                "parameters": {
                    **dict(profile.recipe.get("parameters", {})),
                    "no_publication_ready_figure": no_main,
                    "reason": "no_reliable_main" if no_main else "supporting_diagnostics",
                },
            },
        )
    source = _source("waxs-static-diagnostic-empty", (("two_theta_deg", "deg", "float64"), ("intensity", "a.u.", "float64")), {"two_theta_deg": (), "intensity": ()}, role="diagnostic_evidence")
    return _definition(
        figure_id=DIAGNOSTIC_ID,
        role="diagnostic",
        title="WAXS profile diagnostics",
        panels=(_panel("profile", x_label=AXIS_LABELS["two_theta"], y_label=AXIS_LABELS["I_waxs"]),),
        sources=(source,),
        objects=(),
        category="diagnostic",
        order=100,
        parameters={"no_publication_ready_figure": no_main, "reason": "no_profile_evidence"},
    )


def build_static_waxs_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    views = scan_views_from_engine(engine)
    main_views = tuple(view for view in views if classify_waxs_scan_eligibility(view).highest_role == "main")
    si_views = tuple(view for view in views if classify_waxs_scan_eligibility(view).highest_role == "si")
    diagnostic_views = tuple(view for view in views if classify_waxs_scan_eligibility(view).highest_role == "diagnostic")
    definitions: list[FigureDefinition] = []
    if len(main_views) == 1:
        definition = _profile_definition(main_views, role="main", figure_id=STATIC_PROFILE_ID, title="WAXS diffraction profile")
        if definition is not None:
            definitions.append(definition)
    elif len(main_views) >= 2:
        definition = _profile_definition(main_views, role="main", figure_id=PROFILE_COMPARISON_ID, title="WAXS diffraction profile comparison")
        if definition is not None:
            definitions.append(definition)
        metric = _comparison_metric(main_views)
        if metric is not None:
            definitions.append(_comparison_definition(main_views, metric))
    si_definition = _fit_si_definition(si_views)
    if si_definition is not None:
        definitions.append(si_definition)
    if diagnostic_views or not definitions:
        definitions.append(_diagnostic_definition(diagnostic_views or views, no_main=not main_views))
    return tuple(definitions)


__all__ = [
    "build_static_waxs_figure_definitions",
    "metric_main_eligible",
]
