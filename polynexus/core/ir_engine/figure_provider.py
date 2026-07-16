"""Scientific FigureDefinition provider for IR spectra."""

from __future__ import annotations

import math
from typing import Sequence

from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)

from .core import IRResult


def build_ir_figure_definitions(
    results: Sequence[IRResult],
) -> tuple[FigureDefinition, ...]:
    """Build the complete set of available semantic IR figures."""

    definitions: list[FigureDefinition] = []
    spectrum_by_index = {
        int(item.recipe["parameters"]["frame_index"]): item
        for item in build_ir_spectrum_definitions(results)
    }
    for index, result in enumerate(results, start=1):
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
    return tuple(definitions)


def build_ir_spectrum_definitions(
    results: Sequence[IRResult],
) -> tuple[FigureDefinition, ...]:
    """Describe editable IR spectrum figures without choosing output behavior."""

    definitions: list[FigureDefinition] = []
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
            )
        )
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
