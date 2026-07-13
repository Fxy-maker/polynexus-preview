"""Evidence-gated isothermal DSC/Avrami publication figure recipes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

import numpy as np
from polynexus.plotting.sci_style import AXIS_LABELS

from ..figures.contracts import AxisDefinition, DataColumnDefinition, FigureDataSourceDefinition, FigureDefinition, FigureLayoutDefinition, PanelDefinition


AVRAMI_ID = "dsc.isothermal.avrami"
SERIES_ID = "dsc.isothermal.series"
DIAGNOSTIC_ID = "dsc.isothermal.fit.diagnostic"
_COLORS = ("#000000", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")


def _attr(owner: Any, key: str, default: Any = np.nan) -> Any:
    if isinstance(owner, Mapping):
        return owner.get(key, default)
    return getattr(owner, key, default)


def _array(owner: Any, key: str) -> np.ndarray:
    try:
        return np.asarray(_attr(owner, key, ()), dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return np.asarray([], dtype=float)


def _finite(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


def _source(source_id: str, columns: Sequence[tuple[str, str, str]], values: Mapping[str, Sequence[Any]], *, role: str = "plot_data") -> FigureDataSourceDefinition:
    return FigureDataSourceDefinition(source_id, tuple(DataColumnDefinition(name, unit, dtype) for name, unit, dtype in columns), {name: tuple(items) for name, items in values.items()}, role=role)


def _panel(panel_id: str, *, x_label: str, x_unit: str, y_label: str, y_unit: str, legend: bool = False) -> PanelDefinition:
    return PanelDefinition(panel_id, 0, 0, AxisDefinition(f"{panel_id}-x", x_label, x_unit), AxisDefinition(f"{panel_id}-y", y_label, y_unit), show_legend=legend)


def _plot(object_id: str, panel_id: str, source_id: str, x_column: str, y_column: str, *, name: str, color: str, marker: str = "", chart_kind: str = "line") -> dict[str, Any]:
    style: dict[str, Any] = {"color": color, "line_width": 1.1}
    if marker:
        style.update({"marker": marker, "marker_size": 4.0})
    return {"id": object_id, "type": "plot_series", "panel_id": panel_id, "data_ref": source_id, "x_column": x_column, "y_column": y_column, "chart_kind": chart_kind, "name": name, "style": style}


def _definition(*, figure_id: str, role: str, title: str, panel: PanelDefinition, sources: Sequence[FigureDataSourceDefinition], objects: Sequence[Mapping[str, Any]], category: str = "series_overview", order: int = 0, parameters: Mapping[str, Any] | None = None) -> FigureDefinition:
    return FigureDefinition(
        figure_id=figure_id,
        technique="dsc",
        scope="series",
        category=category,
        publication_role=role,
        title=title,
        layout=FigureLayoutDefinition(6.8, 3.8, 1, 1, (replace(panel, panel_label="(a)"),)),
        data_sources=tuple(sources),
        objects=tuple(dict(item) for item in objects),
        recipe={"module": "polynexus.core.dsc_engine.figure_isothermal", "function": "build_isothermal_dsc_figure_definitions", "inputs": {"source": "completed_analysis"}, "parameters": {"source": "completed_analysis", "display_order": order, **dict(parameters or {})}},
        style_profile="sci_default",
    )


def _fit_gate(avrami: Any) -> tuple[bool, str]:
    t = _array(avrami, "t_data")
    x = _array(avrami, "Xt_data")
    fit = _array(avrami, "Xt_fit")
    if t.size < 5 or x.size != t.size or fit.size != t.size:
        return False, "misaligned_or_insufficient_fit_arrays"
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(x)) and np.all(np.isfinite(fit))):
        return False, "non_finite_fit_values"
    if int(np.count_nonzero((x > 0.0) & (x < 1.0))) < 3:
        return False, "insufficient_conversion_window"
    if any(not np.isfinite(_finite(_attr(avrami, key))) for key in ("n", "k", "t_half_min", "r_squared")):
        return False, "invalid_avrami_parameters"
    if _finite(_attr(avrami, "r_squared")) < 0.90:
        return False, "low_fit_quality"
    if tuple(_attr(avrami, "quality_flags", ()) or ()):
        return False, "quality_flags"
    return True, "qualified"


def _avrami_source(avrami: Any, source_id: str, *, include_fit: bool = True) -> FigureDataSourceDefinition:
    t = _array(avrami, "t_data")
    x = _array(avrami, "Xt_data")
    fit = _array(avrami, "Xt_fit")
    size = min(t.size, x.size, fit.size if include_fit else t.size)
    t, x = t[:size], x[:size]
    values: dict[str, Sequence[Any]] = {"time_min": tuple(float(v) for v in t), "relative_crystallinity": tuple(float(v) for v in x)}
    columns: list[tuple[str, str, str]] = [("time_min", "min", "float64"), ("relative_crystallinity", "", "float64")]
    if include_fit:
        columns.append(("relative_crystallinity_fit", "", "float64"))
        fit = fit[:size]
        values["relative_crystallinity_fit"] = tuple(float(v) for v in fit)
    return _source(source_id, columns, values, role="avrami_fit" if include_fit else "isothermal_evidence")


def _best_avrami(kinetics: Mapping[str, Any]) -> Any:
    best = kinetics.get("avrami")
    if best is not None:
        return best
    series = kinetics.get("avrami_series", ()) or ()
    return series[0] if series else None


def build_isothermal_dsc_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    kinetics = getattr(engine, "_kinetics_data", {}) or {}
    if not isinstance(kinetics, Mapping):
        kinetics = {}
    best = _best_avrami(kinetics)
    fits = list(kinetics.get("avrami_series", ()) or ())
    if best is not None and not any(best is item for item in fits):
        fits.insert(0, best)
    definitions: list[FigureDefinition] = []
    gate, reason = _fit_gate(best) if best is not None else (False, "missing_avrami_fit")
    if gate:
        source = _avrami_source(best, "dsc-isothermal-avrami")
        definitions.append(_definition(
            figure_id=AVRAMI_ID,
            role="main",
            title="Isothermal crystallisation and Avrami fit",
            panel=_panel("avrami", x_label=AXIS_LABELS["time_min"], x_unit="", y_label=AXIS_LABELS["relative_crystallinity"], y_unit="", legend=True),
            sources=(source,),
            objects=(
                _plot("avrami-data", "avrami", source.source_id, "time_min", "relative_crystallinity", name=str(_attr(best, "label", "Data") or "Data"), color="#000000", marker="o", chart_kind="scatter"),
                _plot("avrami-fit", "avrami", source.source_id, "time_min", "relative_crystallinity_fit", name="Avrami fit", color="#D55E00"),
            ),
            parameters={"n": _finite(_attr(best, "n")), "k": _finite(_attr(best, "k")), "t_half_min": _finite(_attr(best, "t_half_min")), "r_squared": _finite(_attr(best, "r_squared"))},
        ))
    valid_series: list[Any] = []
    series_sources: list[FigureDataSourceDefinition] = []
    series_objects: list[dict[str, Any]] = []
    for index, avrami in enumerate(fits):
        t, x = _array(avrami, "t_data"), _array(avrami, "Xt_data")
        size = min(t.size, x.size)
        if size < 2:
            continue
        source = _avrami_source(avrami, f"dsc-isothermal-series-{index:03d}", include_fit=False)
        series_sources.append(source)
        series_objects.append(_plot(f"series-{index:03d}", "series", source.source_id, "time_min", "relative_crystallinity", name=str(_attr(avrami, "label", "") or f"Segment {index + 1}"), color=_COLORS[index % len(_COLORS)], marker="o", chart_kind="scatter"))
        valid_series.append(avrami)
    if valid_series:
        definitions.append(_definition(
            figure_id=SERIES_ID,
            role="si",
            title="Isothermal crystallisation series",
            panel=_panel("series", x_label=AXIS_LABELS["time_min"], x_unit="", y_label=AXIS_LABELS["relative_crystallinity"], y_unit="", legend=True),
            sources=series_sources,
            objects=series_objects,
            category="supplementary",
            order=20,
            parameters={"segment_count": len(valid_series)},
        ))
    if best is not None and not gate:
        source = _avrami_source(best, "dsc-isothermal-fit-diagnostic", include_fit=False)
        definitions.append(_definition(
            figure_id=DIAGNOSTIC_ID,
            role="diagnostic",
            title="Avrami fit diagnostics",
            panel=_panel("diagnostic", x_label=AXIS_LABELS["time_min"], x_unit="", y_label=AXIS_LABELS["relative_crystallinity"], y_unit="", legend=True),
            sources=(source,),
            objects=(_plot("fit-diagnostic", "diagnostic", source.source_id, "time_min", "relative_crystallinity", name="Rejected fit", color="#D55E00", marker="o", chart_kind="scatter"),),
            category="diagnostic",
            order=100,
            parameters={"gate": reason},
        ))
    if not definitions:
        definitions.append(_definition(
            figure_id=DIAGNOSTIC_ID,
            role="diagnostic",
            title="Avrami fit diagnostics",
            panel=_panel("diagnostic", x_label=AXIS_LABELS["time_min"], x_unit="", y_label=AXIS_LABELS["relative_crystallinity"], y_unit="", legend=False),
            sources=(_source("dsc-isothermal-empty", (("time_min", "min", "float64"), ("relative_crystallinity", "", "float64")), {"time_min": (), "relative_crystallinity": ()}, role="diagnostic_evidence"),),
            objects=(), category="diagnostic", order=100, parameters={"gate": reason},
        ))
    return tuple(definitions)


__all__ = ["build_isothermal_dsc_figure_definitions"]
