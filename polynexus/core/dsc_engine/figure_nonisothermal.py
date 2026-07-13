"""Evidence-gated non-isothermal DSC publication recipes."""

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


CONVERSION_ID = "dsc.nonisothermal.conversion"
METHOD_IDS = {
    "kissinger": "dsc.nonisothermal.kissinger",
    "ozawa": "dsc.nonisothermal.ozawa",
    "mo": "dsc.nonisothermal.mo",
    "friedman": "dsc.nonisothermal.friedman",
}
DIAGNOSTIC_ID = "dsc.nonisothermal.kinetics.diagnostic"
_METHOD_ORDER = ("kissinger", "ozawa", "mo", "friedman")
_COLORS = ("#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")


def _finite(value: Any) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return np.nan
    return value if np.isfinite(value) else np.nan


def _attr(owner: Any, key: str, default: Any = np.nan) -> Any:
    if isinstance(owner, Mapping):
        return owner.get(key, default)
    return getattr(owner, key, default)


def _array(owner: Any, *keys: str) -> np.ndarray:
    for key in keys:
        value = _attr(owner, key, None)
        if value is None:
            continue
        try:
            return np.asarray(value, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            continue
    return np.asarray([], dtype=float)


def _source(source_id: str, columns: Sequence[tuple[str, str, str]], values: Mapping[str, Sequence[Any]], *, role: str = "plot_data") -> FigureDataSourceDefinition:
    return FigureDataSourceDefinition(
        source_id=source_id,
        columns=tuple(DataColumnDefinition(name, unit, dtype) for name, unit, dtype in columns),
        values={name: tuple(items) for name, items in values.items()},
        role=role,
    )


def _panel(panel_id: str, *, x_label: str, x_unit: str, y_label: str, y_unit: str, legend: bool = False) -> PanelDefinition:
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
    return {"id": object_id, "type": "plot_series", "panel_id": panel_id, "data_ref": source_id, "x_column": x_column, "y_column": y_column, "chart_kind": chart_kind, "name": name, "style": style}


def _definition(*, figure_id: str, role: str, title: str, panel: PanelDefinition, source: Sequence[FigureDataSourceDefinition], objects: Sequence[Mapping[str, Any]], category: str = "series_overview", order: int = 0, parameters: Mapping[str, Any] | None = None) -> FigureDefinition:
    panel = replace(panel, panel_label="(a)")
    return FigureDefinition(
        figure_id=figure_id,
        technique="dsc",
        scope="series",
        category=category,
        publication_role=role,
        title=title,
        layout=FigureLayoutDefinition(width_in=6.8, height_in=3.7, rows=1, columns=1, panels=(panel,)),
        data_sources=tuple(source),
        objects=tuple(dict(item) for item in objects),
        recipe={
            "module": "polynexus.core.dsc_engine.figure_nonisothermal",
            "function": "build_nonisothermal_dsc_figure_definitions",
            "inputs": {"source": "completed_analysis"},
            "parameters": {"source": "completed_analysis", "display_order": order, **dict(parameters or {})},
        },
        style_profile="sci_default",
    )


def _curves(series: Any) -> list[Any]:
    values = _attr(series, "curves", ())
    return list(values or ())


def _curve_pairs(curve: Any) -> tuple[tuple[float, ...], tuple[float, ...]]:
    temperature = _array(curve, "T_xt_C", "T_C")
    conversion = _array(curve, "Xt")
    size = min(temperature.size, conversion.size)
    if size == 0:
        return (), ()
    temperature, conversion = temperature[:size], conversion[:size]
    finite = np.isfinite(temperature) & np.isfinite(conversion)
    return tuple(float(v) for v in temperature[finite]), tuple(float(v) for v in conversion[finite])


def _conversion_definition(curves: Sequence[Any], *, role: str) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for index, curve in enumerate(curves):
        temperature, conversion = _curve_pairs(curve)
        if len(temperature) < 2:
            continue
        source_id = f"dsc-nonisothermal-curve-{index:03d}"
        sources.append(_source(source_id, (("temperature_C", "degC", "float64"), ("relative_crystallinity", "", "float64")), {"temperature_C": temperature, "relative_crystallinity": conversion}))
        objects.append(_plot(f"curve-{index:03d}", "conversion", source_id, "temperature_C", "relative_crystallinity", name=str(_attr(curve, "label", "") or f"Rate {index + 1}"), color=_COLORS[index % len(_COLORS)]))
    if not sources:
        return None
    return _definition(
        figure_id=CONVERSION_ID,
        role=role,
        title="Non-isothermal crystallisation conversion",
        panel=_panel("conversion", x_label=AXIS_LABELS["T"], x_unit="", y_label=AXIS_LABELS["relative_crystallinity"], y_unit="", legend=True),
        source=sources,
        objects=objects,
        parameters={"curve_count": len(sources)},
    )


def _method_parameters(name: str, result: Any) -> tuple[float, ...]:
    if name == "kissinger":
        return (_finite(_attr(result, "kissinger_Ea_kJmol")),)
    if name == "ozawa":
        return (_finite(_attr(result, "ozawa_n")), _finite(_attr(result, "ozawa_K_T")))
    if name == "mo":
        return (_finite(_attr(result, "mo_F_T")), _finite(_attr(result, "mo_a")))
    friedman = _attr(result, "friedman_Ea", {})
    if isinstance(friedman, Mapping):
        return tuple(_finite(value) for value in friedman.values())
    return ()


def _method_points(result: Any) -> tuple[tuple[float, ...], tuple[float, ...]]:
    x = _array(result, "x", "x_data", "rates", "rate_K_per_min")
    y = _array(result, "y", "y_data", "Ea", "activation_energy")
    size = min(x.size, y.size)
    if size < 2:
        return (), ()
    x, y = x[:size], y[:size]
    finite = np.isfinite(x) & np.isfinite(y)
    return tuple(float(value) for value in x[finite]), tuple(float(value) for value in y[finite])


def _method_gate(name: str, result: Any) -> tuple[bool, str]:
    flags = tuple(str(flag).strip().lower() for flag in (_attr(result, "quality_flags", ()) or ()))
    if flags:
        return False, "quality_flags"
    r_squared = _finite(_attr(result, "r_squared"))
    rates = _array(result, "rates", "heating_rates", "cooling_rates")
    if rates.size < 3:
        return False, "insufficient_independent_rates"
    if not np.isfinite(r_squared) or r_squared < 0.90:
        return False, "low_fit_quality"
    if not _method_parameters(name, result) or not all(np.isfinite(value) for value in _method_parameters(name, result)):
        return False, "invalid_parameters"
    return True, "qualified"


def _method_definition(name: str, result: Any, *, role: str, order: int, reason: str) -> FigureDefinition:
    x, y = _method_points(result)
    if not x:
        rates = _array(result, "rates", "heating_rates", "cooling_rates")
        x = tuple(float(value) for value in rates if np.isfinite(value))
        value = next((item for item in _method_parameters(name, result) if np.isfinite(item)), np.nan)
        y = tuple(float(value) for _ in x)
    source_id = f"dsc-nonisothermal-{name}-evidence"
    source = _source(source_id, (("rate", "K/min", "float64"), ("response", "", "float64")), {"rate": x, "response": y}, role="kinetics_evidence")
    return _definition(
        figure_id=METHOD_IDS[name],
        role=role,
        title=f"{name.title()} non-isothermal kinetics",
        panel=_panel("kinetics", x_label=AXIS_LABELS["rate"], x_unit="", y_label=AXIS_LABELS["kinetics_response"], y_unit="", legend=True),
        source=(source,),
        objects=(_plot(f"{name}-evidence", "kinetics", source_id, "rate", "response", name=name.title(), color="#0072B2", marker="o", chart_kind="scatter"),),
        category="supplementary" if role == "si" else "diagnostic",
        order=order,
        parameters={"method": name, "gate": reason, "r_squared": _finite(_attr(result, "r_squared"))},
    )


def build_nonisothermal_dsc_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    kinetics = getattr(engine, "_kinetics_data", {}) or {}
    series = kinetics.get("non_isothermal") if isinstance(kinetics, Mapping) else None
    if series is None:
        return (_definition(
            figure_id=DIAGNOSTIC_ID,
            role="diagnostic",
            title="Non-isothermal DSC diagnostics",
            panel=_panel("diagnostic", x_label=AXIS_LABELS["T"], x_unit="", y_label=AXIS_LABELS["relative_crystallinity"], y_unit=""),
            source=(_source("dsc-nonisothermal-empty", (("temperature_C", "degC", "float64"), ("relative_crystallinity", "", "float64")), {"temperature_C": (), "relative_crystallinity": ()}, role="diagnostic_evidence"),),
            objects=(), category="diagnostic", order=100, parameters={"reason": "missing_non_isothermal_series"},
        ),)
    curves = _curves(series)
    definitions: list[FigureDefinition] = []
    conversion = _conversion_definition(curves, role="main" if sum(len(_curve_pairs(curve)[0]) >= 2 for curve in curves) >= 2 else "si")
    if conversion is not None:
        definitions.append(conversion)
    methods: dict[str, Any] = {}
    for name in _METHOD_ORDER:
        result = kinetics.get(name) if isinstance(kinetics, Mapping) else None
        if result is None:
            result = _attr(series, name, None)
        if result is not None:
            methods[name] = result
    gates = {name: _method_gate(name, result) for name, result in methods.items()}
    selected = next((name for name in _METHOD_ORDER if name in gates and gates[name][0]), None)
    for order, name in enumerate(_METHOD_ORDER, start=10):
        if name not in methods:
            continue
        passed, reason = gates[name]
        role = "main" if name == selected else ("si" if passed or reason == "low_fit_quality" else "diagnostic")
        definitions.append(_method_definition(name, methods[name], role=role, order=order, reason=reason))
    failed = {name: reason for name, (_passed, reason) in gates.items() if name != selected}
    if failed or not definitions:
        definitions.append(_definition(
            figure_id=DIAGNOSTIC_ID,
            role="diagnostic",
            title="Non-isothermal kinetics diagnostics",
            panel=_panel("diagnostic", x_label=AXIS_LABELS["method"], x_unit="", y_label=AXIS_LABELS["gate_status"], y_unit="", legend=False),
            source=(_source("dsc-nonisothermal-gates", (("method_index", "", "float64"), ("gate_value", "", "float64")), {"method_index": tuple(float(i) for i, _ in enumerate(failed)), "gate_value": tuple(0.0 for _ in failed)}, role="diagnostic_evidence"),),
            objects=(), category="diagnostic", order=100, parameters={"kinetics_gate": failed},
        ))
    return tuple(definitions)


__all__ = ["build_nonisothermal_dsc_figure_definitions"]
