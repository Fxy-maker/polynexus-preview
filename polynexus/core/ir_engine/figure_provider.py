"""Scientific FigureDefinition provider for IR spectra."""

from __future__ import annotations

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
        ranked_peaks = sorted(
            result.peaks,
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
                },
                style_profile="sci_default",
            )
        )
    return tuple(definitions)


def _ir_spectrum_layout() -> FigureLayoutDefinition:
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
            ),
        ),
    )
