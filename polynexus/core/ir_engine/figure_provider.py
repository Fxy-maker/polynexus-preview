"""Scientific FigureDefinition provider for IR spectra."""

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

from .core import IRResult
from .ir_mapping import IRMappingResult, build_ir_mapping_figure_definitions
from .ir_temperature import IRTemp2DResult


_CORRELATION_RENDER_MAX_POINTS = 420


def build_ir_figure_definitions(
    results: Sequence[IRResult],
    *,
    temperature_2d_result: IRTemp2DResult | None = None,
    mapping_result: IRMappingResult | None = None,
) -> tuple[FigureDefinition, ...]:
    """Build the complete set of available semantic IR figures."""

    definitions: list[FigureDefinition] = []
    temperature_definitions = (
        build_ir_temperature_2d_figure_definitions(temperature_2d_result)
        if temperature_2d_result is not None
        else ()
    )
    # Temperature-2D already exposes the sequence through one heatmap, band
    # series, and correlation figures.  Re-publishing every frame's generic
    # spectrum and peak-fit documents creates a large duplicate gallery and
    # makes a full sequence publication unnecessarily expensive.  If the
    # temperature payload is incomplete, keep the generic frame figures as a
    # safe publication fallback instead of publishing an empty set.
    frame_results = () if temperature_definitions else tuple(results)
    spectrum_by_index = {
        int(item.recipe["parameters"]["frame_index"]): item
        for item in build_ir_spectrum_definitions(frame_results)
    }
    for index, result in enumerate(frame_results, start=1):
        spectrum = spectrum_by_index.get(index)
        if spectrum is not None:
            definitions.append(spectrum)
        if (
            len(result.wavenumber) > 0
            and len(result.absorbance) == len(result.wavenumber)
            and len(result.absorbance_fit) == len(result.wavenumber)
        ):
            definitions.append(_build_peak_fit_definition(result, index))
        simulated = result.simulated_spectrum
        if (
            len(result.wavenumber) > 0
            and len(result.absorbance) == len(result.wavenumber)
            and simulated is not None
            and len(simulated.wavenumber) > 0
            and len(simulated.absorbance) == len(simulated.wavenumber)
        ):
            definitions.append(_build_comparison_definition(result, index))
    crystallinity = _build_crystallinity_definition(results)
    if crystallinity is not None:
        definitions.append(crystallinity)
    definitions.extend(temperature_definitions)
    if mapping_result is not None:
        definitions.extend(build_ir_mapping_figure_definitions(mapping_result))
    return tuple(definitions)


def build_ir_temperature_2d_figure_definitions(
    result: IRTemp2DResult,
) -> tuple[FigureDefinition, ...]:
    """Describe IR temperature-series figures through the shared contract."""

    matrix = _finite_matrix(result.absorbance_matrix)
    wavenumber = _finite_values(result.wavenumber)
    if matrix.ndim != 2 or not wavenumber.size or matrix.shape[1] != len(wavenumber):
        return ()
    frame_count = matrix.shape[0]
    if frame_count == 0 or len(result.frames) != frame_count:
        return ()

    frame_metadata = _temperature_2d_frame_metadata(result.frames)
    frame_indices = np.repeat(np.arange(frame_count), len(wavenumber))

    heatmap_source = FigureDataSourceDefinition(
        source_id="ir-temperature-2d-matrix",
        columns=(
            DataColumnDefinition("wavenumber_cm1", "cm^-1"),
            DataColumnDefinition("frame_index", ""),
            DataColumnDefinition("temperature_C", "C"),
            DataColumnDefinition("time_min", "min"),
            DataColumnDefinition("absorbance", "a.u."),
        ),
        values={
            "wavenumber_cm1": tuple(
                float(value) for value in np.tile(wavenumber, frame_count)
            ),
            "frame_index": tuple(float(index) for index in frame_indices),
            "temperature_C": tuple(
                _temperature_2d_source_value(frame_metadata[int(index)], "temperature_C")
                for index in frame_indices
            ),
            "time_min": tuple(
                _temperature_2d_source_value(frame_metadata[int(index)], "time_min")
                for index in frame_indices
            ),
            "absorbance": tuple(float(value) for value in matrix.reshape(-1)),
        },
    )
    definitions: list[FigureDefinition] = [
        FigureDefinition(
            figure_id="ir.temperature_2d.heatmap",
            technique="ir",
            scope="series",
            category="series_overview",
            publication_role="main",
            title="IR Temperature-Series Spectral Evolution",
            layout=_ir_temperature_2d_layout(
                x_label="Wavenumber",
                x_unit="cm^-1",
                y_label="Sequence frame",
                y_unit="",
                x_reversed=True,
            ),
            data_sources=(heatmap_source,),
            objects=(
                {
                    "id": "temperature-2d-heatmap",
                    "type": "heatmap",
                    "panel_id": "main",
                    "data_ref": heatmap_source.source_id,
                    "x_column": "wavenumber_cm1",
                    "y_column": "frame_index",
                    "z_column": "absorbance",
                    "style": {
                        "cmap": "viridis",
                        "colorbar_label": "Absorbance (a.u.)",
                    },
                },
            ),
            recipe=_temperature_2d_recipe(result, "heatmap"),
            style_profile="sci_default",
            display_order=10,
        )
    ]

    tracking = _temperature_2d_series_definition(
        result,
        result.band_intensity_vs_frame,
        figure_id="ir.temperature_2d.band-tracking",
        title="IR Temperature-Series Band Tracking",
        y_label="Band height",
        y_unit="a.u.",
        category="supplementary",
        display_order=20,
        recipe_kind="band_tracking",
    )
    if tracking is not None:
        definitions.append(tracking)

    indices = _temperature_2d_series_definition(
        result,
        result.band_indices_vs_frame,
        figure_id="ir.temperature_2d.band-indices",
        title="IR Temperature-Series Band Indices",
        y_label="Band index",
        y_unit="",
        category="supplementary",
        display_order=30,
        recipe_kind="band_indices",
    )
    if indices is not None:
        definitions.append(indices)

    for kind, correlation, order in (
        ("synchronous", result.sync_corr, 40),
        ("asynchronous", result.async_corr, 50),
    ):
        correlation_definition = _temperature_2d_correlation_definition(
            result,
            correlation,
            kind=kind,
            display_order=order,
        )
        if correlation_definition is not None:
            definitions.append(correlation_definition)
    return tuple(definitions)


def _temperature_2d_series_definition(
    result: IRTemp2DResult,
    series: dict[str, Sequence[float]],
    *,
    figure_id: str,
    title: str,
    y_label: str,
    y_unit: str,
    category: str,
    display_order: int,
    recipe_kind: str,
) -> FigureDefinition | None:
    objects: list[dict[str, object]] = []
    sources: list[FigureDataSourceDefinition] = []
    for index, (name, values) in enumerate(sorted(series.items())):
        finite = [
            (float(frame_index), float(value))
            for frame_index, value in enumerate(values)
            if np.isfinite(value)
        ]
        if len(finite) < 2:
            continue
        source = FigureDataSourceDefinition(
            source_id=f"ir-temperature-2d-{recipe_kind}-{index:03d}",
            columns=(
                DataColumnDefinition("frame_index", ""),
                DataColumnDefinition("temperature_C", "C"),
                DataColumnDefinition("time_min", "min"),
                DataColumnDefinition("value", y_unit),
            ),
            values={
                "frame_index": tuple(item[0] for item in finite),
                "temperature_C": tuple(
                    _temperature_2d_source_value(
                        _temperature_2d_frame_metadata(result.frames)[int(item[0])],
                        "temperature_C",
                    )
                    for item in finite
                ),
                "time_min": tuple(
                    _temperature_2d_source_value(
                        _temperature_2d_frame_metadata(result.frames)[int(item[0])],
                        "time_min",
                    )
                    for item in finite
                ),
                "value": tuple(item[1] for item in finite),
            },
        )
        sources.append(source)
        objects.append(
            {
                "id": f"{recipe_kind}-{index:03d}",
                "type": "plot_series",
                "panel_id": "main",
                "name": str(name),
                "data_ref": source.source_id,
                "x_column": "frame_index",
                "y_column": "value",
                "chart_kind": "line",
                "style": {"line_width": 0.9},
            }
        )
    if not sources:
        return None
    return FigureDefinition(
        figure_id=figure_id,
        technique="ir",
        scope="series",
        category=category,
        publication_role="si",
        title=title,
        layout=_ir_temperature_2d_layout(
            x_label="Sequence frame",
            x_unit="",
            y_label=y_label,
            y_unit=y_unit,
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe=_temperature_2d_recipe(result, recipe_kind),
        style_profile="sci_default",
        display_order=display_order,
    )


def _temperature_2d_correlation_definition(
    result: IRTemp2DResult,
    correlation: np.ndarray,
    *,
    kind: str,
    display_order: int,
) -> FigureDefinition | None:
    matrix = np.asarray(correlation, dtype=float)
    wavenumber = _finite_values(result.wavenumber)
    if matrix.shape != (len(wavenumber), len(wavenumber)) or not np.isfinite(matrix).all():
        return None
    render_wavenumber, render_matrix = _downsample_square(
        wavenumber,
        matrix,
        max_points=_CORRELATION_RENDER_MAX_POINTS,
    )
    source_id = f"ir-temperature-2d-{kind}-correlation"
    source = FigureDataSourceDefinition(
        source_id=source_id,
        columns=(
            DataColumnDefinition("wavenumber_x_cm1", "cm^-1"),
            DataColumnDefinition("wavenumber_y_cm1", "cm^-1"),
            DataColumnDefinition("correlation", "a.u."),
        ),
        values={
            "wavenumber_x_cm1": tuple(float(value) for value in np.tile(render_wavenumber, len(render_wavenumber))),
            "wavenumber_y_cm1": tuple(float(value) for value in np.repeat(render_wavenumber, len(render_wavenumber))),
            "correlation": tuple(float(value) for value in render_matrix.reshape(-1)),
        },
    )
    recipe = _temperature_2d_recipe(result, f"{kind}_correlation")
    recipe["parameters"] = {
        **dict(recipe.get("parameters", {})),
        "correlation_render_max_points": _CORRELATION_RENDER_MAX_POINTS,
        "correlation_render_points": len(render_wavenumber),
    }
    return FigureDefinition(
        figure_id=f"ir.temperature_2d.{kind}-correlation",
        technique="ir",
        scope="series",
        category="diagnostic",
        publication_role="diagnostic",
        title=f"IR {kind.title()} 2D Correlation",
        layout=_ir_temperature_2d_layout(
            x_label="Wavenumber",
            x_unit="cm^-1",
            y_label="Wavenumber",
            y_unit="cm^-1",
            x_reversed=True,
            y_reversed=True,
        ),
        data_sources=(source,),
        objects=(
            {
                "id": f"{kind}-correlation-heatmap",
                "type": "heatmap",
                "panel_id": "main",
                "data_ref": source_id,
                "x_column": "wavenumber_x_cm1",
                "y_column": "wavenumber_y_cm1",
                "z_column": "correlation",
                "style": {"cmap": "RdBu_r", "colorbar_label": "Correlation"},
            },
        ),
        recipe=recipe,
        style_profile="sci_default",
        display_order=display_order,
    )


def _ir_temperature_2d_layout(
    *,
    x_label: str,
    x_unit: str,
    y_label: str,
    y_unit: str,
    x_reversed: bool = False,
    y_reversed: bool = False,
) -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=7.0,
        height_in=4.6,
        rows=1,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisDefinition(
                    axis_id="x",
                    label=x_label,
                    unit=x_unit,
                    reversed=x_reversed,
                ),
                y_axis=AxisDefinition(
                    axis_id="y",
                    label=y_label,
                    unit=y_unit,
                    reversed=y_reversed,
                ),
                show_legend=True,
            ),
        ),
    )


def _temperature_2d_recipe(result: IRTemp2DResult, figure_kind: str) -> dict[str, object]:
    return {
        "module": "polynexus.core.ir_engine.figure_provider",
        "function": "build_ir_temperature_2d_figure_definitions",
        "inputs": {"series_label": result.label},
        "parameters": {"figure_kind": figure_kind, "frame_count": len(result.frames)},
        "frame_metadata": _temperature_2d_frame_metadata(result.frames),
        "v2_adapter": "ir",
    }


def _temperature_2d_frame_metadata(frames: Sequence[object]) -> list[dict[str, object]]:
    metadata: list[dict[str, object]] = []
    for index, frame in enumerate(frames):
        metadata.append(
            {
                "frame_index": index,
                "label": str(getattr(frame, "label", "") or ""),
                "stage": str(getattr(frame, "stage", "") or ""),
                "temperature_C": _finite_or_none(getattr(frame, "temperature_C", np.nan)),
                "time_min": _finite_or_none(getattr(frame, "time_min", np.nan)),
                "time_estimated": bool(getattr(frame, "time_estimated", False)),
                "sequence_order_source": str(
                    getattr(frame, "sequence_order_source", "") or ""
                ),
            }
        )
    return metadata


def _finite_or_none(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if np.isfinite(numeric) else None


def _temperature_2d_source_value(
    metadata: dict[str, object],
    key: str,
) -> float:
    value = metadata.get(key)
    return float(value) if value is not None else float("nan")


def _finite_matrix(values: object) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        return np.empty((0, 0), dtype=float)
    return matrix


def _finite_values(values: object) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or not np.isfinite(array).all():
        return np.array([], dtype=float)
    return array


def _downsample_square(
    wavenumber: np.ndarray,
    matrix: np.ndarray,
    *,
    max_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Bound a square publication snapshot while retaining full analysis data."""

    if matrix.shape[0] <= max_points:
        return wavenumber, matrix
    indices = np.linspace(0, len(wavenumber) - 1, max_points, dtype=int)
    return wavenumber[indices], matrix[np.ix_(indices, indices)]


def build_ir_spectrum_definitions(
    results: Sequence[IRResult],
) -> tuple[FigureDefinition, ...]:
    """Describe editable IR spectrum figures without choosing output behavior."""

    definitions: list[FigureDefinition] = []
    main_spectrum_emitted = False
    for index, result in enumerate(results, start=1):
        if len(result.wavenumber) == 0 or len(result.absorbance) == 0:
            continue
        figure_id = f"ir.frame.spectrum.{index:03d}"
        source_id = "spectrum-data"
        objects: list[dict[str, object]] = [
            {
                "id": "series-spectrum",
                "type": "plot_series",
                "panel_id": "main",
                "name": "Absorbance",
                "data_ref": source_id,
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "style": {"color": "#222222", "line_width": 0.8},
            }
        ]
        objects.extend(_peak_annotation_objects(result.peaks))
        definitions.append(
            FigureDefinition(
                figure_id=figure_id,
                technique="ir",
                scope="frame",
                category="per_frame",
                title=f"IR Spectrum - {result.label}",
                layout=_ir_spectrum_layout(),
                data_sources=(
                    FigureDataSourceDefinition(
                        source_id=source_id,
                        columns=(
                            DataColumnDefinition("wavenumber_cm1", "cm^-1"),
                            DataColumnDefinition("absorbance", "a.u."),
                        ),
                        values={
                            "wavenumber_cm1": tuple(
                                float(value) for value in result.wavenumber
                            ),
                            "absorbance": tuple(
                                float(value) for value in result.absorbance
                            ),
                        },
                    ),
                ),
                objects=tuple(objects),
                recipe={
                    "module": "polynexus.core.ir_engine.figure_provider",
                    "function": "build_ir_spectrum_definitions",
                    "inputs": {"result_label": result.label},
                    "parameters": {"frame_index": index},
                    "v2_adapter": "ir",
                },
                style_profile="sci_default",
                publication_role="main" if not main_spectrum_emitted else "si",
            )
        )
        main_spectrum_emitted = True
    return tuple(definitions)


def _build_peak_fit_definition(result: IRResult, index: int) -> FigureDefinition:
    source_id = "peak-fit-data"
    objects: list[dict[str, object]] = [
        {
            "id": "series-absorbance",
            "type": "plot_series",
            "panel_id": "main",
            "name": "Absorbance",
            "data_ref": source_id,
            "x_column": "wavenumber_cm1",
            "y_column": "absorbance",
            "style": {"color": "#222222", "line_width": 0.8},
        },
        {
            "id": "series-fit",
            "type": "plot_series",
            "panel_id": "main",
            "name": "Peak fit",
            "data_ref": source_id,
            "x_column": "wavenumber_cm1",
            "y_column": "absorbance_fit",
            "style": {"color": "#0072B2", "line_width": 0.9},
        },
    ]
    objects.extend(_peak_annotation_objects(result.peaks))
    return FigureDefinition(
        figure_id=f"ir.frame.peak-fit.{index:03d}",
        technique="ir",
        scope="frame",
        category="per_frame",
        publication_role="si",
        title=f"IR Peak Fit - {result.label}",
        layout=_ir_spectrum_layout(show_legend=True),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("wavenumber_cm1", "cm^-1"),
                    DataColumnDefinition("absorbance", "a.u."),
                    DataColumnDefinition("absorbance_fit", "a.u."),
                ),
                values={
                    "wavenumber_cm1": _float_values(result.wavenumber),
                    "absorbance": _float_values(result.absorbance),
                    "absorbance_fit": _float_values(result.absorbance_fit),
                },
            ),
        ),
        objects=tuple(objects),
        recipe={
            "module": "polynexus.core.ir_engine.figure_provider",
            "function": "build_ir_figure_definitions",
            "inputs": {"result_label": result.label},
            "parameters": {"frame_index": index, "figure_kind": "peak_fit"},
            "v2_adapter": "ir",
        },
        style_profile="sci_default",
    )


def _build_comparison_definition(result: IRResult, index: int) -> FigureDefinition:
    simulated = result.simulated_spectrum
    if simulated is None:
        raise ValueError("computed IR spectrum is missing")
    return FigureDefinition(
        figure_id=f"ir.frame.comparison.{index:03d}",
        technique="ir",
        scope="frame",
        category="per_frame",
        publication_role="diagnostic",
        title=f"IR Experimental And Computed - {result.label}",
        layout=_ir_spectrum_layout(show_legend=True),
        data_sources=(
            FigureDataSourceDefinition(
                source_id="experimental-data",
                columns=(
                    DataColumnDefinition("wavenumber_cm1", "cm^-1"),
                    DataColumnDefinition("absorbance", "a.u."),
                ),
                values={
                    "wavenumber_cm1": _float_values(result.wavenumber),
                    "absorbance": _float_values(result.absorbance),
                },
            ),
            FigureDataSourceDefinition(
                source_id="computed-data",
                columns=(
                    DataColumnDefinition("wavenumber_cm1", "cm^-1"),
                    DataColumnDefinition("absorbance", "a.u."),
                ),
                values={
                    "wavenumber_cm1": _float_values(simulated.wavenumber),
                    "absorbance": _float_values(simulated.absorbance),
                },
            ),
        ),
        objects=(
            {
                "id": "series-experimental",
                "type": "plot_series",
                "panel_id": "main",
                "name": "Experimental",
                "data_ref": "experimental-data",
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "style": {"color": "#222222", "line_width": 0.8},
            },
            {
                "id": "series-computed",
                "type": "plot_series",
                "panel_id": "main",
                "name": "Computed",
                "data_ref": "computed-data",
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "style": {"color": "#D55E00", "line_width": 0.8},
            },
        ),
        recipe={
            "module": "polynexus.core.ir_engine.figure_provider",
            "function": "build_ir_figure_definitions",
            "inputs": {"result_label": result.label},
            "parameters": {"frame_index": index, "figure_kind": "comparison"},
            "v2_adapter": "ir",
        },
        style_profile="sci_default",
    )


def _build_crystallinity_definition(
    results: Sequence[IRResult],
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
        figure_id="ir.series.crystallinity",
        technique="ir",
        scope="series",
        category="series_overview",
        publication_role="main",
        title="IR Crystallinity Overview",
        layout=FigureLayoutDefinition(
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
                    y_axis=AxisDefinition(
                        axis_id="y",
                        label="Crystallinity",
                        unit="%",
                    ),
                ),
            ),
        ),
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
                "style": {"color": "#009E73"},
            },
        ),
        recipe={
            "module": "polynexus.core.ir_engine.figure_provider",
            "function": "build_ir_figure_definitions",
            "inputs": {"result_labels": [label for label, _value in rows]},
            "parameters": {"figure_kind": "crystallinity"},
            "v2_adapter": "ir",
        },
        style_profile="sci_default",
    )


def _peak_annotation_objects(
    peaks: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    objects: list[dict[str, object]] = []
    ranked_peaks = sorted(
        peaks,
        key=lambda item: float(
            item.get("prominence", item.get("height", 0.0)) or 0.0
        ),
        reverse=True,
    )[:16]
    for peak_index, peak in enumerate(ranked_peaks, start=1):
        wavenumber = float(peak["wavenumber"])
        height = float(peak["height"])
        assignment = str(peak.get("assignment") or "")
        label = f"{wavenumber:.0f}"
        if assignment and assignment != "unknown":
            label = f"{label}\n{assignment[:15]}"
        objects.extend(
            [
                {
                    "id": f"line-peak-{peak_index}",
                    "type": "line",
                    "panel_id": "main",
                    "orientation": "vertical",
                    "x": wavenumber,
                    "style": {
                        "color": "#D55E00",
                        "line_width": 0.5,
                        "line_style": ":",
                        "alpha": 0.5,
                    },
                },
                {
                    "id": f"text-peak-{peak_index}",
                    "type": "text",
                    "panel_id": "main",
                    "text": label,
                    "x": wavenumber,
                    "y": height,
                    "rotation": 90.0,
                    "style": {"color": "#D55E00", "font_size": 5},
                },
            ]
        )
    return objects


def _float_values(values) -> tuple[float, ...]:
    return tuple(float(value) for value in values)


def _ir_spectrum_layout(*, show_legend: bool = False) -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=7.5,
        height_in=3.8,
        rows=1,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisDefinition(
                    axis_id="x",
                    label="Wavenumber",
                    unit="cm^-1",
                    reversed=True,
                ),
                y_axis=AxisDefinition(
                    axis_id="y",
                    label="Absorbance",
                    unit="a.u.",
                ),
                show_legend=show_legend,
            ),
        ),
    )
