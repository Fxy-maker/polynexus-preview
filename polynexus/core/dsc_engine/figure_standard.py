"""Publication-ready standard DSC figure recipes.

The provider is deliberately a projection of completed ``DSCResult`` objects.  It
does not rerun baseline correction, peak finding, or integration; all gates are
based on the evidence emitted by the analysis layer.
"""

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
from .figure_common import (
    DSCScanView,
    classify_dsc_scan_eligibility,
    finite_parameter,
    scan_views_from_engine,
)


STANDARD_MAIN_ID = "dsc.standard.thermogram"
COMPARISON_MAIN_ID = "dsc.comparison.thermal-events"
INTEGRATION_DIAGNOSTIC_ID = "dsc.standard.integration.diagnostic"
SI_ID = "dsc.standard.integration.si"

_COLORS = ("#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")
_EVENTS = (("Tg_C", "Tg"), ("Tc_peak_C", "Tc"), ("Tcc_peak_C", "Tcc"), ("Tm_peak_C", "Tm"))
_PARAMETERS = (
    ("Tg_C", "Temperature", "degC"),
    ("Tc_peak_C", "Temperature", "degC"),
    ("Tcc_peak_C", "Temperature", "degC"),
    ("Tm_peak_C", "Temperature", "degC"),
    ("DHm_Jg", "Enthalpy", "J/g"),
    ("DHc_Jg", "Enthalpy", "J/g"),
    ("DHcc_Jg", "Enthalpy", "J/g"),
    ("Xc_pct", "Crystallinity", "%"),
)


def _finite_pairs(view: DSCScanView) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return finite paired values while retaining analysis-time alignment."""

    if len(view.temperature_C) != len(view.heat_flow_W_g):
        return (), ()
    pairs = [
        (float(t), float(h))
        for t, h in zip(view.temperature_C, view.heat_flow_W_g)
        if np.isfinite(t) and np.isfinite(h)
    ]
    if not pairs:
        return (), ()
    return tuple(pair[0] for pair in pairs), tuple(pair[1] for pair in pairs)


def _source(
    source_id: str,
    columns: Sequence[tuple[str, str, str]],
    values: Mapping[str, Sequence[Any]],
    *,
    role: str = "plot_data",
) -> FigureDataSourceDefinition:
    return FigureDataSourceDefinition(
        source_id=source_id,
        columns=tuple(DataColumnDefinition(name, unit, dtype) for name, unit, dtype in columns),
        values={name: tuple(items) for name, items in values.items()},
        role=role,
    )


def _panel(
    panel_id: str,
    row: int,
    column: int,
    *,
    x_label: str,
    x_unit: str,
    y_label: str,
    y_unit: str,
    title: str = "",
    legend: bool = False,
) -> PanelDefinition:
    return PanelDefinition(
        panel_id=panel_id,
        row=row,
        column=column,
        title=title,
        show_legend=legend,
        x_axis=AxisDefinition(f"{panel_id}-x", x_label, x_unit),
        y_axis=AxisDefinition(f"{panel_id}-y", y_label, y_unit),
    )


def _plot(
    object_id: str,
    panel_id: str,
    source_id: str,
    x_column: str,
    y_column: str,
    *,
    name: str = "",
    color: str = "#000000",
    marker: str = "",
    chart_kind: str = "line",
) -> dict[str, Any]:
    style: dict[str, Any] = {"color": color, "line_width": 1.15}
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


def _line(object_id: str, panel_id: str, x: float, *, color: str = "#D55E00") -> dict[str, Any]:
    return {
        "id": object_id,
        "type": "line",
        "panel_id": panel_id,
        "orientation": "vertical",
        "x": float(x),
        "style": {"color": color, "line_width": 0.8, "line_style": "--", "alpha": 0.8},
    }


def _labelled_panels(panels: Sequence[PanelDefinition]) -> tuple[PanelDefinition, ...]:
    return tuple(replace(panel, panel_label=f"({chr(ord('a') + index)})") for index, panel in enumerate(panels))


def _definition(
    *,
    figure_id: str,
    role: str,
    title: str,
    panels: Sequence[PanelDefinition],
    sources: Sequence[FigureDataSourceDefinition],
    objects: Sequence[Mapping[str, Any]],
    category: str = "series_overview",
    scope: str = "series",
    rows: int = 1,
    columns: int = 1,
    width: float = 7.0,
    height: float = 3.8,
    display_order: int = 0,
    parameters: Mapping[str, Any] | None = None,
) -> FigureDefinition:
    return FigureDefinition(
        figure_id=figure_id,
        technique="dsc",
        scope=scope,
        category=category,
        publication_role=role,
        title=title,
        layout=FigureLayoutDefinition(
            width_in=width,
            height_in=height,
            rows=rows,
            columns=columns,
            panels=_labelled_panels(panels),
        ),
        data_sources=tuple(sources),
        objects=tuple(dict(item) for item in objects),
        recipe={
            "module": "polynexus.core.dsc_engine.figure_standard",
            "function": "build_standard_dsc_figure_definitions",
            "inputs": {"source": "completed_analysis"},
            "parameters": {
                "source": "completed_analysis",
                "display_order": display_order,
                **dict(parameters or {}),
            },
        },
        style_profile="sci_default",
    )


def _parameter_source(view: DSCScanView, source_id: str = "dsc-standard-parameters") -> FigureDataSourceDefinition:
    columns = [("metric_index", "", "float64")] + [(key, unit, "float64") for key, _label, unit in _PARAMETERS]
    values = {"metric_index": (0.0,)}
    values.update({key: (finite_parameter(view, key),) for key, _label, _unit in _PARAMETERS})
    return _source(source_id, columns, values, role="quantitative_parameters")


def _event_source(view: DSCScanView, source_id: str) -> tuple[FigureDataSourceDefinition, list[dict[str, Any]]]:
    events = [(name, finite_parameter(view, key)) for key, name in _EVENTS]
    finite = [(index, name, value) for index, (name, value) in enumerate(events) if np.isfinite(value)]
    source = _source(
        source_id,
        (("event_index", "", "float64"), ("event_temperature_C", "degC", "float64")),
        {
            "event_index": tuple(float(index) for index, _name, _value in finite),
            "event_temperature_C": tuple(float(value) for _index, _name, value in finite),
        },
        role="thermal_events",
    )
    return source, [
        _line(f"event-{name.lower()}", "thermogram", value)
        for _index, name, value in finite
    ]


def _thermogram_definition(view: DSCScanView, *, role: str, display_order: int = 0) -> FigureDefinition | None:
    temperature, heat_flow = _finite_pairs(view)
    if len(temperature) < 2:
        return None
    source_id = f"dsc-standard-scan-{view.index:03d}"
    source = _source(
        source_id,
        (("temperature_C", "degC", "float64"), ("heat_flow_W_g", "W/g", "float64")),
        {"temperature_C": temperature, "heat_flow_W_g": heat_flow},
    )
    parameter_source = _parameter_source(view)
    event_source, event_lines = _event_source(view, f"dsc-standard-events-{view.index:03d}")
    objects: list[dict[str, Any]] = [_plot("thermogram", "thermogram", source_id, "temperature_C", "heat_flow_W_g", name=view.label)]
    if event_source.values["event_temperature_C"]:
        objects.append(_plot("thermal-events", "quantitative", event_source.source_id, "event_index", "event_temperature_C", name="Events", color="#0072B2", marker="o", chart_kind="scatter"))
        objects.extend(event_lines)
    else:
        metric_key = next((key for key, _label, _unit in _PARAMETERS[4:] if np.isfinite(finite_parameter(view, key))), None)
        if metric_key:
            objects.append(_plot("quantitative-metric", "quantitative", parameter_source.source_id, "metric_index", metric_key, name=metric_key, color="#0072B2", marker="o", chart_kind="scatter"))
    metric_key = next((key for key, _label, _unit in _PARAMETERS[4:] if np.isfinite(finite_parameter(view, key))), None)
    quantitative_valid = any(np.isfinite(finite_parameter(view, key)) for key, _label, _unit in _PARAMETERS[4:])
    panels = [
        _panel("thermogram", 0, 0, x_label=AXIS_LABELS["T"], x_unit="", y_label=AXIS_LABELS["HF_Wg"], y_unit="", legend=True),
    ]
    if quantitative_valid or any(np.isfinite(finite_parameter(view, key)) for key, _name in _EVENTS):
        if event_source.values["event_temperature_C"]:
            metric_label, metric_unit = AXIS_LABELS["T"], ""
        elif metric_key and metric_key.startswith("Xc"):
            metric_label, metric_unit = AXIS_LABELS["crystallinity"], ""
        else:
            metric_label, metric_unit = AXIS_LABELS["enthalpy"], ""
        panels.append(_panel("quantitative", 0, 1, x_label=AXIS_LABELS["event"], x_unit="", y_label=metric_label, y_unit=metric_unit))
    if len(panels) == 1:
        objects = [objects[0]]
        sources = (source, parameter_source)
        layout_columns = 1
    else:
        sources = (source, event_source, parameter_source)
        layout_columns = 2
    return _definition(
        figure_id=STANDARD_MAIN_ID if role == "main" else SI_ID,
        role=role,
        title="DSC thermogram and thermal events",
        panels=(
            *panels,
        ),
        sources=sources,
        objects=objects,
        columns=layout_columns,
        width=7.2,
        height=3.6,
        display_order=display_order,
        parameters={"scan_index": view.index, "quality_flags": list(view.quality_flags)},
    )


def _si_definition(views: Sequence[DSCScanView]) -> FigureDefinition | None:
    """Preserve every low-confidence scan in one editable SI overlay."""

    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for order, view in enumerate(views):
        temperature, heat_flow = _finite_pairs(view)
        if len(temperature) < 2:
            continue
        source_id = f"dsc-si-scan-{view.index:03d}"
        sources.append(_source(source_id, (("temperature_C", "degC", "float64"), ("heat_flow_W_g", "W/g", "float64")), {"temperature_C": temperature, "heat_flow_W_g": heat_flow}, role="supplementary_evidence"))
        objects.append(_plot(f"si-scan-{view.index:03d}", "evidence", source_id, "temperature_C", "heat_flow_W_g", name=view.label, color=_COLORS[order % len(_COLORS)]))
    if not sources:
        return None
    return _definition(
        figure_id=SI_ID,
        role="si",
        title="DSC supplementary scan evidence",
        panels=(_panel("evidence", 0, 0, x_label=AXIS_LABELS["T"], x_unit="", y_label=AXIS_LABELS["HF_Wg"], y_unit="", legend=True),),
        sources=sources,
        objects=objects,
        columns=1,
        width=6.8,
        height=3.6,
        display_order=20,
        parameters={"scan_count": len(sources)},
    )


def _comparison_definition(views: Sequence[DSCScanView]) -> FigureDefinition:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    event_rows: list[tuple[float, ...]] = []
    for order, view in enumerate(views):
        temperature, heat_flow = _finite_pairs(view)
        source_id = f"dsc-comparison-scan-{view.index:03d}"
        sources.append(_source(source_id, (("temperature_C", "degC", "float64"), ("heat_flow_W_g", "W/g", "float64")), {"temperature_C": temperature, "heat_flow_W_g": heat_flow}))
        objects.append(_plot(f"scan-{view.index:03d}", "thermograms", source_id, "temperature_C", "heat_flow_W_g", name=view.label, color=_COLORS[order % len(_COLORS)]))
        event_rows.append((float(order), finite_parameter(view, "Tg_C"), finite_parameter(view, "Tc_peak_C"), finite_parameter(view, "Tm_peak_C"), finite_parameter(view, "DHm_Jg"), finite_parameter(view, "DHc_Jg"), finite_parameter(view, "DHcc_Jg"), finite_parameter(view, "Xc_pct")))
    event_source = _source(
        "dsc-comparison-events",
        (("sample_index", "", "float64"), ("Tg_C", "degC", "float64"), ("Tc_peak_C", "degC", "float64"), ("Tm_peak_C", "degC", "float64"), ("DHm_Jg", "J/g", "float64"), ("DHc_Jg", "J/g", "float64"), ("DHcc_Jg", "J/g", "float64"), ("Xc_pct", "%", "float64")),
        {"sample_index": tuple(row[0] for row in event_rows), "Tg_C": tuple(row[1] for row in event_rows), "Tc_peak_C": tuple(row[2] for row in event_rows), "Tm_peak_C": tuple(row[3] for row in event_rows), "DHm_Jg": tuple(row[4] for row in event_rows), "DHc_Jg": tuple(row[5] for row in event_rows), "DHcc_Jg": tuple(row[6] for row in event_rows), "Xc_pct": tuple(row[7] for row in event_rows)},
        role="quantitative_parameters",
    )
    sources.append(event_source)
    thermal_points = sum(any(np.isfinite(value) for value in row[1:4]) for row in event_rows)
    enthalpy_points = sum(any(np.isfinite(value) for value in row[4:7]) for row in event_rows)
    crystallinity_points = sum(np.isfinite(row[7]) for row in event_rows)
    comparison_kind = "thermal" if thermal_points >= 3 else "enthalpy" if enthalpy_points >= 3 else "crystallinity" if crystallinity_points >= 3 else "none"
    if comparison_kind == "thermal":
        for key, name, color in (("Tg_C", "Tg", "#009E73"), ("Tc_peak_C", "Tc", "#D55E00"), ("Tm_peak_C", "Tm", "#0072B2")):
            if any(np.isfinite(row[1 + ("Tg_C", "Tc_peak_C", "Tm_peak_C").index(key)]) for row in event_rows):
                objects.append(_plot(f"events-{name.lower()}", "events", event_source.source_id, "sample_index", key, name=name, color=color, marker="o"))
    elif comparison_kind == "enthalpy":
        for key, name, color in (("DHm_Jg", "DHm", "#0072B2"), ("DHc_Jg", "DHc", "#D55E00"), ("DHcc_Jg", "DHcc", "#009E73")):
            if any(np.isfinite(row[4 + ("DHm_Jg", "DHc_Jg", "DHcc_Jg").index(key)]) for row in event_rows):
                objects.append(_plot(f"events-{name.lower()}", "events", event_source.source_id, "sample_index", key, name=name, color=color, marker="o"))
    elif comparison_kind == "crystallinity":
        objects.append(_plot("events-xc", "events", event_source.source_id, "sample_index", "Xc_pct", name="Xc", color="#0072B2", marker="o"))
    panels = [_panel("thermograms", 0, 0, x_label=AXIS_LABELS["T"], x_unit="", y_label=AXIS_LABELS["HF_Wg"], y_unit="", legend=True)]
    columns = 1
    if comparison_kind != "none":
        if comparison_kind == "thermal":
            y_label = AXIS_LABELS["T"]
        elif comparison_kind == "enthalpy":
            y_label = AXIS_LABELS["enthalpy"]
        else:
            y_label = AXIS_LABELS["crystallinity"]
        panels.append(_panel("events", 0, 1, x_label=AXIS_LABELS["sample"], x_unit="", y_label=y_label, y_unit="", legend=True))
        columns = 2
    return _definition(
        figure_id=COMPARISON_MAIN_ID,
        role="main",
        title="DSC comparison of thermal events",
        panels=(
            *panels,
        ),
        sources=sources,
        objects=objects,
        columns=columns,
        width=7.4,
        height=3.6,
        display_order=0,
        parameters={"scan_count": len(views)},
    )


def _diagnostic_definition(views: Sequence[DSCScanView]) -> FigureDefinition:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    reasons: dict[str, list[str]] = {}
    for order, view in enumerate(views):
        temperature = tuple(view.temperature_C)
        heat_flow = tuple(view.heat_flow_W_g)
        if len(temperature) != len(heat_flow):
            size = min(len(temperature), len(heat_flow))
            temperature, heat_flow = temperature[:size], heat_flow[:size]
        source_id = f"dsc-diagnostic-scan-{view.index:03d}"
        sources.append(_source(source_id, (("temperature_C", "degC", "float64"), ("heat_flow_W_g", "W/g", "float64")), {"temperature_C": temperature, "heat_flow_W_g": heat_flow}, role="diagnostic_evidence"))
        if len(temperature) >= 2:
            objects.append(_plot(f"diagnostic-{view.index:03d}", "evidence", source_id, "temperature_C", "heat_flow_W_g", name=view.label, color=_COLORS[order % len(_COLORS)]))
        reason_list = list(classify_dsc_scan_eligibility(view).reasons)
        if "Xc_pct" in view.parameters and not np.isfinite(finite_parameter(view, "Xc_pct")):
            reason_list.append("invalid_Xc_pct")
        reasons[view.label] = reason_list
        parameter_source = _parameter_source(view, f"dsc-diagnostic-parameters-{view.index:03d}")
        sources.append(parameter_source)
    if not sources:
        sources.append(_source("dsc-diagnostic-empty", (("temperature_C", "degC", "float64"), ("heat_flow_W_g", "W/g", "float64")), {"temperature_C": (), "heat_flow_W_g": ()}, role="diagnostic_evidence"))
    return _definition(
        figure_id=INTEGRATION_DIAGNOSTIC_ID,
        role="diagnostic",
        title="DSC integration and quality diagnostics",
        category="diagnostic",
        panels=(_panel("evidence", 0, 0, x_label=AXIS_LABELS["T"], x_unit="", y_label=AXIS_LABELS["HF_Wg"], y_unit="", legend=True),),
        sources=sources,
        objects=objects,
        parameters={"eligibility": reasons},
        display_order=100,
    )


def build_standard_dsc_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    """Build standard DSC Main/SI/Diagnostics definitions from completed scans."""

    views = scan_views_from_engine(engine)
    main_views = tuple(view for view in views if classify_dsc_scan_eligibility(view).highest_role == "main")
    si_views = tuple(view for view in views if classify_dsc_scan_eligibility(view).highest_role == "si")
    diagnostic_views = tuple(view for view in views if classify_dsc_scan_eligibility(view).highest_role == "diagnostic")
    # Keep a traceable evidence view when a scan is otherwise usable but a
    # quantitative crystallinity result is missing/invalid.  The thermogram
    # may remain a Main figure, while the omitted quantitative result is still
    # visible in Diagnostics rather than silently disappearing.
    quantitative_evidence_views = tuple(
        view
        for view in main_views
        if "Xc_pct" in view.parameters and not np.isfinite(finite_parameter(view, "Xc_pct"))
    )
    definitions: list[FigureDefinition] = []
    if len(main_views) >= 2:
        definitions.append(_comparison_definition(main_views))
    elif main_views:
        definition = _thermogram_definition(main_views[0], role="main")
        if definition is not None:
            definitions.append(definition)
    if si_views:
        definition = _si_definition(si_views)
        if definition is not None:
            definitions.append(definition)
    diagnostic_evidence = diagnostic_views + quantitative_evidence_views
    if diagnostic_evidence or not definitions:
        definitions.append(_diagnostic_definition(diagnostic_evidence or views))
    return tuple(definitions)


__all__ = [
    "STANDARD_MAIN_ID",
    "COMPARISON_MAIN_ID",
    "INTEGRATION_DIAGNOSTIC_ID",
    "build_standard_dsc_figure_definitions",
]
