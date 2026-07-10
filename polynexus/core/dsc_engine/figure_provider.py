"""Scientific FigureDefinition providers for DSC results."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)

from .core import DSCResult


def build_dsc_figure_definitions(
    results: Sequence[DSCResult],
) -> tuple[FigureDefinition, ...]:
    definitions: list[FigureDefinition] = []
    for index, result in enumerate(results, start=1):
        if len(result.T) == 0 or len(result.HF) != len(result.T):
            continue
        definitions.append(_build_thermogram(result, index))
        if math.isfinite(float(result.Tg_C)):
            definitions.append(_build_tg_view(result, index))
        components = _melting_component_curves(result)
        if len(components) >= 2:
            definitions.append(_build_deconvolution(result, index, components))
    overview = _build_crystallinity(results)
    if overview is not None:
        definitions.append(overview)
    return tuple(definitions)


def _build_thermogram(result: DSCResult, index: int) -> FigureDefinition:
    source_id = "thermogram-data"
    has_fit = len(result.HF_fit) == len(result.T)
    columns = [
        DataColumnDefinition("temperature_C", "C"),
        DataColumnDefinition("heat_flow_W_g", "W/g"),
    ]
    values: dict[str, tuple[float, ...]] = {
        "temperature_C": _float_values(result.T),
        "heat_flow_W_g": _float_values(result.HF),
    }
    objects: list[dict[str, object]] = [
        _series("series-heat-flow", source_id, "heat_flow_W_g", "Heat flow", "#222222")
    ]
    if has_fit:
        columns.append(DataColumnDefinition("heat_flow_fit_W_g", "W/g"))
        values["heat_flow_fit_W_g"] = _float_values(result.HF_fit)
        objects.append(
            _series("series-fit", source_id, "heat_flow_fit_W_g", "Fit", "#0072B2")
        )
    event_values = (
        ("tg", "Tg", result.Tg_C, "#009E73"),
        ("tm", "Tm", result.Tm_peak_C, "#D55E00"),
        ("tc", "Tc", result.Tc_peak_C, "#0072B2"),
        ("tcc", "Tcc", result.Tcc_peak_C, "#CC79A7"),
    )
    y_anchor = float(np.nanmax(np.asarray(result.HF, dtype=float)))
    for event_id, label, value, color in event_values:
        if not math.isfinite(float(value)):
            continue
        objects.extend(
            [
                {
                    "id": f"line-{event_id}",
                    "type": "line",
                    "panel_id": "main",
                    "orientation": "vertical",
                    "x": float(value),
                    "style": {"color": color, "line_width": 0.6, "line_style": ":"},
                },
                {
                    "id": f"text-{event_id}",
                    "type": "text",
                    "panel_id": "main",
                    "text": f"{label} {float(value):.1f} C",
                    "x": float(value),
                    "y": y_anchor,
                    "rotation": 90.0,
                    "style": {"color": color, "font_size": 6},
                },
            ]
        )
    return FigureDefinition(
        figure_id=f"dsc.frame.thermogram.{index:03d}",
        technique="dsc",
        scope="frame",
        category="per_frame",
        title=f"DSC Thermogram - {result.label}",
        layout=_thermogram_layout(show_legend=has_fit),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=tuple(columns),
                values=values,
            ),
        ),
        objects=tuple(objects),
        recipe=_recipe(result.label, index, "thermogram"),
        style_profile="sci_default",
    )


def _build_tg_view(result: DSCResult, index: int) -> FigureDefinition:
    temperature = np.asarray(result.T, dtype=float)
    heat_flow = np.asarray(result.HF, dtype=float)
    width = float(result.DTg_C) if math.isfinite(float(result.DTg_C)) else 20.0
    width = max(abs(width), 20.0)
    mask = np.abs(temperature - float(result.Tg_C)) <= width
    if np.count_nonzero(mask) < 2:
        mask = np.ones(len(temperature), dtype=bool)
    source_id = "tg-data"
    return FigureDefinition(
        figure_id=f"dsc.frame.tg.{index:03d}",
        technique="dsc",
        scope="frame",
        category="diagnostic",
        title=f"DSC Glass Transition - {result.label}",
        layout=_thermogram_layout(show_legend=False),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("temperature_C", "C"),
                    DataColumnDefinition("heat_flow_W_g", "W/g"),
                ),
                values={
                    "temperature_C": _float_values(temperature[mask]),
                    "heat_flow_W_g": _float_values(heat_flow[mask]),
                },
            ),
        ),
        objects=(
            _series("series-tg", source_id, "heat_flow_W_g", "Heat flow", "#222222"),
            {
                "id": "line-tg",
                "type": "line",
                "panel_id": "main",
                "orientation": "vertical",
                "x": float(result.Tg_C),
                "style": {"color": "#009E73", "line_width": 0.8, "line_style": "--"},
            },
        ),
        recipe=_recipe(result.label, index, "tg"),
        style_profile="sci_default",
    )


def _build_deconvolution(
    result: DSCResult,
    index: int,
    components: Sequence[tuple[str, np.ndarray]],
) -> FigureDefinition:
    source_id = "deconvolution-data"
    columns = [
        DataColumnDefinition("temperature_C", "C"),
        DataColumnDefinition("heat_flow_W_g", "W/g"),
    ]
    values: dict[str, tuple[float, ...]] = {
        "temperature_C": _float_values(result.T),
        "heat_flow_W_g": _float_values(result.HF),
    }
    objects: list[dict[str, object]] = [
        _series("series-experimental", source_id, "heat_flow_W_g", "Experimental", "#222222")
    ]
    colors = ("#0072B2", "#E69F00", "#009E73", "#CC79A7")
    for component_index, (column_name, curve) in enumerate(components, start=1):
        columns.append(DataColumnDefinition(column_name, "W/g"))
        values[column_name] = _float_values(curve)
        objects.append(
            _series(
                f"series-component-{component_index}",
                source_id,
                column_name,
                f"Component {component_index}",
                colors[(component_index - 1) % len(colors)],
            )
        )
    return FigureDefinition(
        figure_id=f"dsc.frame.deconvolution.{index:03d}",
        technique="dsc",
        scope="frame",
        category="supplementary",
        title=f"DSC Peak Deconvolution - {result.label}",
        layout=_thermogram_layout(show_legend=True),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=tuple(columns),
                values=values,
            ),
        ),
        objects=tuple(objects),
        recipe=_recipe(result.label, index, "deconvolution"),
        style_profile="sci_default",
    )


def _melting_component_curves(
    result: DSCResult,
) -> tuple[tuple[str, np.ndarray], ...]:
    temperature = np.asarray(result.T, dtype=float)
    minimum = float(np.nanmin(temperature))
    maximum = float(np.nanmax(temperature))
    curves: list[tuple[str, np.ndarray]] = []
    for component in result.peak_components:
        if str(component.get("type") or "") not in {"melting", "deconv_melting"}:
            continue
        center = float(component.get("mu_C", component.get("peak_C", np.nan)))
        if not math.isfinite(center) or not minimum <= center <= maximum:
            continue
        fraction = float(component.get("fraction", 1.0) or 0.0)
        if fraction < 0.01:
            continue
        sigma = max(float(component.get("sigma_C", 4.0) or 4.0), 1e-6)
        amplitude = float(component.get("amp", 1.0) or 0.0)
        curve = amplitude * np.exp(-0.5 * ((temperature - center) / sigma) ** 2)
        curves.append((f"component_{len(curves) + 1}", curve))
    return tuple(curves)


def _build_crystallinity(
    results: Sequence[DSCResult],
) -> FigureDefinition | None:
    rows = [
        (str(result.label), float(result.Xc_pct))
        for result in results
        if math.isfinite(float(result.Xc_pct))
    ]
    if not rows:
        return None
    source_id = "crystallinity-data"
    return FigureDefinition(
        figure_id="dsc.series.crystallinity",
        technique="dsc",
        scope="series",
        category="series_overview",
        title="DSC Crystallinity Overview",
        layout=_category_bar_layout(),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("label", "", dtype="str"),
                    DataColumnDefinition("crystallinity_pct", "%"),
                ),
                values={
                    "label": tuple(label for label, _value in rows),
                    "crystallinity_pct": tuple(value for _label, value in rows),
                },
            ),
        ),
        objects=(
            {
                "id": "bars-crystallinity",
                "type": "plot_series",
                "chart_kind": "bar",
                "panel_id": "main",
                "data_ref": source_id,
                "x_column": "label",
                "y_column": "crystallinity_pct",
                "style": {"color": "#D55E00"},
            },
        ),
        recipe={
            "module": "polynexus.core.dsc_engine.figure_provider",
            "function": "build_dsc_figure_definitions",
            "inputs": {"result_labels": [label for label, _value in rows]},
            "parameters": {"figure_kind": "crystallinity"},
        },
        style_profile="sci_default",
    )


def _series(
    object_id: str,
    source_id: str,
    y_column: str,
    name: str,
    color: str,
) -> dict[str, object]:
    return {
        "id": object_id,
        "type": "plot_series",
        "panel_id": "main",
        "name": name,
        "data_ref": source_id,
        "x_column": "temperature_C",
        "y_column": y_column,
        "style": {"color": color, "line_width": 0.9},
    }


def _thermogram_layout(*, show_legend: bool) -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=7.0,
        height_in=4.2,
        rows=1,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisDefinition(axis_id="x", label="Temperature", unit="C"),
                y_axis=AxisDefinition(axis_id="y", label="Heat flow", unit="W/g"),
                show_legend=show_legend,
            ),
        ),
    )


def _category_bar_layout() -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=7.0,
        height_in=4.0,
        rows=1,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisDefinition(axis_id="x", label="Sample"),
                y_axis=AxisDefinition(axis_id="y", label="Crystallinity", unit="%"),
            ),
        ),
    )


def _recipe(label: str, index: int, figure_kind: str) -> dict[str, object]:
    return {
        "module": "polynexus.core.dsc_engine.figure_provider",
        "function": "build_dsc_figure_definitions",
        "inputs": {"result_label": label},
        "parameters": {"frame_index": index, "figure_kind": figure_kind},
    }


def _float_values(values) -> tuple[float, ...]:
    return tuple(float(value) for value in values)
