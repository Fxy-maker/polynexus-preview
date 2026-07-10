"""Scientific FigureDefinition providers for WAXS results."""

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

from .core import WAXSResult


def build_waxs_figure_definitions(
    results: Sequence[WAXSResult],
) -> tuple[FigureDefinition, ...]:
    definitions: list[FigureDefinition] = []
    for index, result in enumerate(results, start=1):
        if len(result.two_theta) == 0 or len(result.I) != len(result.two_theta):
            continue
        definitions.append(_build_profile(result, index))
        if (
            len(result.I_amorphous) == len(result.two_theta)
            and len(result.I_crystalline) == len(result.two_theta)
        ):
            definitions.append(_build_decomposition(result, index))
    overview = _build_crystallinity(results)
    if overview is not None:
        definitions.append(overview)
    return tuple(definitions)


def _build_profile(result: WAXSResult, index: int) -> FigureDefinition:
    source_id = "profile-data"
    has_fit = len(result.I_fit) == len(result.two_theta)
    residual = (
        np.asarray(result.I, dtype=float) - np.asarray(result.I_fit, dtype=float)
        if has_fit
        else np.zeros(len(result.two_theta), dtype=float)
    )
    columns = [
        DataColumnDefinition("two_theta_deg", "deg"),
        DataColumnDefinition("intensity", "a.u."),
        DataColumnDefinition("residual", "a.u."),
    ]
    values: dict[str, tuple[float, ...]] = {
        "two_theta_deg": _float_values(result.two_theta),
        "intensity": _float_values(result.I),
        "residual": _float_values(residual),
    }
    if has_fit:
        columns.append(DataColumnDefinition("intensity_fit", "a.u."))
        values["intensity_fit"] = _float_values(result.I_fit)
    objects: list[dict[str, object]] = [
        _series("series-measured", "profile", source_id, "intensity", "Measured", "#222222"),
        _series("series-residual", "residual", source_id, "residual", "Residual", "#666666"),
    ]
    if has_fit:
        objects.insert(
            1,
            _series("series-fit", "profile", source_id, "intensity_fit", "Fit", "#D55E00"),
        )
    objects.extend(_peak_objects(result.peaks))
    return FigureDefinition(
        figure_id=f"waxs.frame.profile.{index:03d}",
        technique="waxs",
        scope="frame",
        category="per_frame",
        title=f"WAXS Profile - {result.label}",
        layout=_profile_layout(show_legend=has_fit),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=tuple(columns),
                values=values,
            ),
        ),
        objects=tuple(objects),
        recipe=_recipe(result.label, index, "profile"),
        style_profile="sci_default",
    )


def _build_decomposition(result: WAXSResult, index: int) -> FigureDefinition:
    source_id = "decomposition-data"
    return FigureDefinition(
        figure_id=f"waxs.frame.decomposition.{index:03d}",
        technique="waxs",
        scope="frame",
        category="diagnostic",
        title=f"WAXS Phase Decomposition - {result.label}",
        layout=_single_panel_layout(show_legend=True),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("two_theta_deg", "deg"),
                    DataColumnDefinition("total", "a.u."),
                    DataColumnDefinition("amorphous", "a.u."),
                    DataColumnDefinition("crystalline", "a.u."),
                ),
                values={
                    "two_theta_deg": _float_values(result.two_theta),
                    "total": _float_values(result.I),
                    "amorphous": _float_values(result.I_amorphous),
                    "crystalline": _float_values(result.I_crystalline),
                },
            ),
        ),
        objects=(
            _series("series-total", "main", source_id, "total", "Total", "#222222"),
            _series(
                "series-amorphous",
                "main",
                source_id,
                "amorphous",
                "Amorphous",
                "#E69F00",
            ),
            _series(
                "series-crystalline",
                "main",
                source_id,
                "crystalline",
                "Crystalline",
                "#0072B2",
            ),
        ),
        recipe=_recipe(result.label, index, "decomposition"),
        style_profile="sci_default",
    )


def _build_crystallinity(
    results: Sequence[WAXSResult],
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
        figure_id="waxs.series.crystallinity",
        technique="waxs",
        scope="series",
        category="series_overview",
        title="WAXS Crystallinity Overview",
        layout=_category_bar_layout("Crystallinity", "%"),
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
                "style": {"color": "#0072B2"},
            },
        ),
        recipe={
            "module": "polynexus.core.waxs_engine.figure_provider",
            "function": "build_waxs_figure_definitions",
            "inputs": {"result_labels": [label for label, _value in rows]},
            "parameters": {"figure_kind": "crystallinity"},
        },
        style_profile="sci_default",
    )


def _peak_objects(peaks: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    ranked = sorted(
        peaks,
        key=lambda item: float(item.get("prominence", item.get("height", 0.0)) or 0.0),
        reverse=True,
    )[:16]
    objects: list[dict[str, object]] = []
    for peak_index, peak in enumerate(ranked, start=1):
        position = float(peak["two_theta"])
        height = float(peak.get("height", 0.0) or 0.0)
        hkl = str(peak.get("hkl") or "")
        objects.extend(
            [
                {
                    "id": f"line-peak-{peak_index}",
                    "type": "line",
                    "panel_id": "profile",
                    "orientation": "vertical",
                    "x": position,
                    "style": {"color": "#009E73", "line_width": 0.5, "line_style": ":"},
                },
                {
                    "id": f"text-peak-{peak_index}",
                    "type": "text",
                    "panel_id": "profile",
                    "text": f"{position:.1f}" + (f"\n{hkl}" if hkl else ""),
                    "x": position,
                    "y": height,
                    "style": {"color": "#009E73", "font_size": 6},
                },
            ]
        )
    return objects


def _series(
    object_id: str,
    panel_id: str,
    source_id: str,
    y_column: str,
    name: str,
    color: str,
) -> dict[str, object]:
    return {
        "id": object_id,
        "type": "plot_series",
        "panel_id": panel_id,
        "name": name,
        "data_ref": source_id,
        "x_column": "two_theta_deg",
        "y_column": y_column,
        "style": {"color": color, "line_width": 0.9},
    }


def _profile_layout(*, show_legend: bool) -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=7.0,
        height_in=5.5,
        rows=2,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="profile",
                row=0,
                column=0,
                x_axis=AxisDefinition(axis_id="x-profile", label="2 theta", unit="deg"),
                y_axis=AxisDefinition(axis_id="y-profile", label="Intensity", unit="a.u."),
                title="Measured And Fitted Profile",
                show_legend=show_legend,
            ),
            PanelDefinition(
                panel_id="residual",
                row=1,
                column=0,
                x_axis=AxisDefinition(axis_id="x-residual", label="2 theta", unit="deg"),
                y_axis=AxisDefinition(axis_id="y-residual", label="Residual", unit="a.u."),
            ),
        ),
    )


def _single_panel_layout(*, show_legend: bool) -> FigureLayoutDefinition:
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
                x_axis=AxisDefinition(axis_id="x", label="2 theta", unit="deg"),
                y_axis=AxisDefinition(axis_id="y", label="Intensity", unit="a.u."),
                show_legend=show_legend,
            ),
        ),
    )


def _category_bar_layout(label: str, unit: str) -> FigureLayoutDefinition:
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
                y_axis=AxisDefinition(axis_id="y", label=label, unit=unit),
            ),
        ),
    )


def _recipe(label: str, index: int, figure_kind: str) -> dict[str, object]:
    return {
        "module": "polynexus.core.waxs_engine.figure_provider",
        "function": "build_waxs_figure_definitions",
        "inputs": {"result_label": label},
        "parameters": {"frame_index": index, "figure_kind": figure_kind},
    }


def _float_values(values) -> tuple[float, ...]:
    return tuple(float(value) for value in values)
