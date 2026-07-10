"""Scientific FigureDefinition providers for SAXS workflows."""

from __future__ import annotations

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

from .saxs_temperature import TempSeriesResult


_SERIES_COLORS = (
    "#0072B2",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#E69F00",
    "#D55E00",
    "#CC79A7",
    "#332288",
    "#88CCEE",
    "#AA4499",
)


def build_saxs_temperature_definitions(
    result: TempSeriesResult,
    q_values: Sequence[np.ndarray],
    intensities: Sequence[np.ndarray],
) -> tuple[FigureDefinition, ...]:
    """Describe SAXS temperature figures without publishing artifacts."""

    temperatures = np.asarray(result.temperatures, dtype=float)
    if len(temperatures) != len(q_values) or len(q_values) != len(intensities):
        raise ValueError("temperature frame counts differ")
    definitions: list[FigureDefinition] = []
    cleaned_frames: list[tuple[np.ndarray, np.ndarray]] = []
    for index, (temperature, q, intensity) in enumerate(
        zip(temperatures, q_values, intensities),
        start=1,
    ):
        clean_q, clean_intensity = _clean_frame(q, intensity, index)
        cleaned_frames.append((clean_q, clean_intensity))
        definitions.append(
            _build_temperature_frame(
                index,
                float(temperature),
                clean_q,
                clean_intensity,
            )
        )
    if definitions:
        definitions.append(_build_temperature_waterfall(temperatures, cleaned_frames))
    return tuple(definitions)


def _build_temperature_frame(
    index: int,
    temperature: float,
    q: np.ndarray,
    intensity: np.ndarray,
) -> FigureDefinition:
    source_id = "scattering-data"
    return FigureDefinition(
        figure_id=f"saxs.frame.temperature.scattering.{index:03d}",
        technique="saxs",
        scope="frame",
        category="per_frame",
        title=f"SAXS Scattering At {temperature:g} C",
        layout=_scattering_layout(show_legend=False),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("q_nm1", "nm^-1"),
                    DataColumnDefinition("intensity_au", "a.u."),
                ),
                values={
                    "q_nm1": _float_values(q),
                    "intensity_au": _float_values(intensity),
                },
            ),
        ),
        objects=(
            {
                "id": "series-scattering",
                "type": "plot_series",
                "panel_id": "main",
                "data_ref": source_id,
                "x_column": "q_nm1",
                "y_column": "intensity_au",
                "style": {"color": "#222222", "line_width": 0.8},
            },
        ),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_provider",
            "function": "build_saxs_temperature_definitions",
            "inputs": {"temperature_C": temperature},
            "parameters": {"frame_index": index, "figure_kind": "scattering"},
        },
        style_profile="sci_default",
    )


def _build_temperature_waterfall(
    temperatures: np.ndarray,
    frames: Sequence[tuple[np.ndarray, np.ndarray]],
) -> FigureDefinition:
    selected_indices = _waterfall_indices(len(frames))
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, object]] = []
    for display_index, frame_index in enumerate(selected_indices):
        q, intensity = frames[frame_index]
        source_id = f"frame-{frame_index + 1:03d}-data"
        offset = np.log10(
            np.clip(intensity, np.finfo(float).tiny, None)
        ) + display_index * 1.2
        sources.append(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("q_nm1", "nm^-1"),
                    DataColumnDefinition("intensity_offset", "a.u."),
                ),
                values={
                    "q_nm1": _float_values(q),
                    "intensity_offset": _float_values(offset),
                },
            )
        )
        temperature = float(temperatures[frame_index])
        objects.append(
            {
                "id": f"series-frame-{frame_index + 1:03d}",
                "type": "plot_series",
                "panel_id": "main",
                "name": f"{temperature:g} C",
                "data_ref": source_id,
                "x_column": "q_nm1",
                "y_column": "intensity_offset",
                "style": {
                    "color": _SERIES_COLORS[display_index % len(_SERIES_COLORS)],
                    "line_width": 0.7,
                },
            }
        )
    return FigureDefinition(
        figure_id="saxs.series.temperature.waterfall",
        technique="saxs",
        scope="series",
        category="series_overview",
        title="SAXS Temperature Waterfall",
        layout=_waterfall_layout(),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_provider",
            "function": "build_saxs_temperature_definitions",
            "inputs": {"temperature_count": len(temperatures)},
            "parameters": {
                "figure_kind": "waterfall",
                "intensity_transform": "log10_offset",
                "selected_frame_indices": [index + 1 for index in selected_indices],
            },
        },
        style_profile="sci_default",
    )


def _scattering_layout(*, show_legend: bool) -> FigureLayoutDefinition:
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
                x_axis=AxisDefinition(
                    axis_id="x",
                    label="q",
                    unit="nm^-1",
                    scale="log",
                ),
                y_axis=AxisDefinition(
                    axis_id="y",
                    label="Intensity",
                    unit="a.u.",
                    scale="log",
                ),
                show_legend=show_legend,
            ),
        ),
    )


def _waterfall_layout() -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=7.5,
        height_in=5.0,
        rows=1,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisDefinition(
                    axis_id="x",
                    label="q",
                    unit="nm^-1",
                    scale="log",
                ),
                y_axis=AxisDefinition(
                    axis_id="y",
                    label="log10 Intensity + offset",
                    unit="a.u.",
                ),
                show_legend=True,
            ),
        ),
    )


def _clean_frame(
    q_values: np.ndarray,
    intensities: np.ndarray,
    frame_index: int,
) -> tuple[np.ndarray, np.ndarray]:
    q = np.ravel(np.asarray(q_values, dtype=float))
    intensity = np.ravel(np.asarray(intensities, dtype=float))
    if len(q) != len(intensity):
        raise ValueError(f"temperature frame data lengths differ: {frame_index}")
    mask = np.isfinite(q) & np.isfinite(intensity) & (q > 0) & (intensity > 0)
    if not np.any(mask):
        raise ValueError(f"temperature frame has no plottable data: {frame_index}")
    q = q[mask]
    intensity = intensity[mask]
    order = np.argsort(q)
    return q[order], intensity[order]


def _waterfall_indices(frame_count: int) -> tuple[int, ...]:
    if frame_count <= 10:
        return tuple(range(frame_count))
    return tuple(
        int(index)
        for index in np.unique(
            np.linspace(0, frame_count - 1, num=10, dtype=int)
        )
    )


def _float_values(values: np.ndarray) -> tuple[float, ...]:
    return tuple(float(value) for value in values)
