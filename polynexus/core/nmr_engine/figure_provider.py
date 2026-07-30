"""Scientific FigureDefinition providers for NMR results."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)

from .core import NMRResult
from polynexus.core.scientific_review import (
    review_decision_snapshot,
    review_record_from_payload,
)


_PEAK_LABEL_LANES = (0.96, 0.84, 0.72, 0.60, 0.48)
_PEAK_LABEL_LIMIT = 10


def build_nmr_figure_definitions(
    results: Sequence[NMRResult],
) -> tuple[FigureDefinition, ...]:
    definitions: list[FigureDefinition] = []
    for index, result in enumerate(results, start=1):
        scientific_review = _result_scientific_review(result)
        if len(result.ppm) > 0 and len(result.intensity) == len(result.ppm):
            definitions.append(_build_spectrum(result, index, scientific_review))
            if len(result.intensity_fit) == len(result.ppm):
                definitions.append(_build_deconvolution(result, index, scientific_review))
        if result.matches:
            comparison = _build_comparison(result, index, scientific_review)
            if comparison is not None:
                definitions.append(comparison)
        if result.region_integrals:
            definitions.append(_build_region_integrals(result, index, scientific_review))
    overview = _build_crystallinity(results, _results_scientific_review(results))
    if overview is not None:
        definitions.append(overview)
    return tuple(definitions)


def _build_spectrum(
    result: NMRResult,
    index: int,
    scientific_review: Mapping[str, Any],
) -> FigureDefinition:
    source_id = "spectrum-data"
    objects: list[dict[str, object]] = [
        _series("series-spectrum", source_id, "intensity", "Spectrum", "#222222")
    ]
    objects.extend(_peak_objects(result.peaks))
    objects.extend(_assignment_objects(result.peaks))
    return FigureDefinition(
        figure_id=f"nmr.frame.spectrum.{index:03d}",
        technique="nmr",
        scope="frame",
        category="per_frame",
        publication_role=("main" if scientific_review["allowed"] else "diagnostic"),
        title=f"NMR Spectrum - {result.label}",
        layout=_spectrum_layout(
            result.nucleus,
            show_legend=False,
            assignment_column=True,
        ),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("ppm", "ppm"),
                    DataColumnDefinition("intensity", "a.u."),
                ),
                values={
                    "ppm": _float_values(result.ppm),
                    "intensity": _float_values(result.intensity),
                },
            ),
        ),
        objects=tuple(objects),
        recipe=_recipe(result, index, "spectrum", scientific_review),
        style_profile="sci_default",
    )


def _build_deconvolution(
    result: NMRResult,
    index: int,
    scientific_review: Mapping[str, Any],
) -> FigureDefinition:
    source_id = "deconvolution-data"
    objects: list[dict[str, object]] = [
        _series("series-data", source_id, "intensity", "Data", "#222222"),
        _series("series-fit", source_id, "intensity_fit", "Fit", "#D55E00"),
    ]
    objects.extend(
        item for item in _peak_objects(result.peaks) if item["type"] == "line"
    )
    return FigureDefinition(
        figure_id=f"nmr.frame.deconvolution.{index:03d}",
        technique="nmr",
        scope="frame",
        category="diagnostic",
        publication_role="diagnostic",
        title=f"NMR Peak Deconvolution - {result.label}",
        layout=_spectrum_layout(result.nucleus, show_legend=True),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("ppm", "ppm"),
                    DataColumnDefinition("intensity", "a.u."),
                    DataColumnDefinition("intensity_fit", "a.u."),
                ),
                values={
                    "ppm": _float_values(result.ppm),
                    "intensity": _float_values(result.intensity),
                    "intensity_fit": _float_values(result.intensity_fit),
                },
            ),
        ),
        objects=tuple(objects),
        recipe=_recipe(result, index, "deconvolution", scientific_review),
        style_profile="sci_default",
    )


def _build_comparison(
    result: NMRResult,
    index: int,
    scientific_review: Mapping[str, Any],
) -> FigureDefinition | None:
    rows: list[tuple[float, float]] = []
    for match in result.matches:
        try:
            experimental = float(match["exp_ppm"])
            computed = float(match["calc_ppm"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(experimental) and math.isfinite(computed):
            rows.append((experimental, computed))
    if not rows:
        return None
    lower = min(min(row) for row in rows)
    upper = max(max(row) for row in rows)
    margin = max((upper - lower) * 0.05, 1.0)
    lower -= margin
    upper += margin
    source_id = "comparison-data"
    return FigureDefinition(
        figure_id=f"nmr.frame.comparison.{index:03d}",
        technique="nmr",
        scope="frame",
        category="diagnostic",
        title=f"NMR Experimental And Computed - {result.label}",
        layout=_comparison_layout(),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("experimental_ppm", "ppm"),
                    DataColumnDefinition("computed_ppm", "ppm"),
                ),
                values={
                    "experimental_ppm": tuple(row[0] for row in rows),
                    "computed_ppm": tuple(row[1] for row in rows),
                },
            ),
        ),
        objects=(
            {
                "id": "scatter-comparison",
                "type": "plot_series",
                "chart_kind": "scatter",
                "panel_id": "main",
                "data_ref": source_id,
                "x_column": "experimental_ppm",
                "y_column": "computed_ppm",
                "style": {"color": "#0072B2", "marker_size": 24.0},
            },
            {
                "id": "line-identity",
                "type": "line",
                "panel_id": "main",
                "x1": lower,
                "y1": lower,
                "x2": upper,
                "y2": upper,
                "style": {"color": "#666666", "line_width": 0.7, "line_style": "--"},
            },
        ),
        publication_role=("si" if scientific_review["allowed"] else "diagnostic"),
        recipe=_recipe(result, index, "comparison", scientific_review),
        style_profile="sci_default",
    )


def _build_region_integrals(
    result: NMRResult,
    index: int,
    scientific_review: Mapping[str, Any],
) -> FigureDefinition:
    rows = [
        (str(label).replace("_", " "), float(value))
        for label, value in result.region_integrals.items()
        if math.isfinite(float(value))
    ]
    source_id = "region-integrals-data"
    return FigureDefinition(
        figure_id=f"nmr.frame.region-integrals.{index:03d}",
        technique="nmr",
        scope="frame",
        category="supplementary",
        title=f"NMR Region Integrals - {result.label}",
        layout=_category_layout("Integral fraction", "%"),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("region", "", dtype="str"),
                    DataColumnDefinition("integral_pct", "%"),
                ),
                values={
                    "region": tuple(label for label, _value in rows),
                    "integral_pct": tuple(value for _label, value in rows),
                },
            ),
        ),
        objects=(
            {
                "id": "bars-regions",
                "type": "plot_series",
                "chart_kind": "bar",
                "panel_id": "main",
                "data_ref": source_id,
                "x_column": "region",
                "y_column": "integral_pct",
                "style": {"color": "#009E73"},
            },
        ),
        publication_role=("si" if scientific_review["allowed"] else "diagnostic"),
        recipe=_recipe(result, index, "region_integrals", scientific_review),
        style_profile="sci_default",
    )


def _build_crystallinity(
    results: Sequence[NMRResult],
    scientific_review: Mapping[str, Any],
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
        figure_id="nmr.series.crystallinity",
        technique="nmr",
        scope="series",
        category="series_overview",
        title="NMR Crystallinity Overview",
        layout=_category_layout("Crystallinity", "%"),
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
                "style": {"color": "#CC79A7"},
            },
        ),
        recipe={
            "module": "polynexus.core.nmr_engine.figure_provider",
            "function": "build_nmr_figure_definitions",
            "inputs": {"result_labels": [label for label, _value in rows]},
            "parameters": {"figure_kind": "crystallinity"},
            "scientific_review": dict(scientific_review),
            "v2_adapter": "nmr",
        },
        publication_role=("si" if scientific_review["allowed"] else "diagnostic"),
        style_profile="sci_default",
    )


def _peak_objects(peaks: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    ranked = _rank_peaks(peaks)
    objects: list[dict[str, object]] = []
    for peak_index, peak in enumerate(ranked, start=1):
        ppm = float(peak["ppm"])
        objects.append(
            {
                "id": f"line-peak-{peak_index}",
                "type": "line",
                "panel_id": "main",
                "orientation": "vertical",
                "x": ppm,
                "style": {"color": "#0072B2", "line_width": 0.5, "line_style": ":"},
            }
        )
        if peak_index <= _PEAK_LABEL_LIMIT:
            label_y = _PEAK_LABEL_LANES[(peak_index - 1) % len(_PEAK_LABEL_LANES)]
            objects.append(
                {
                    "id": f"text-peak-{peak_index}",
                    "type": "text",
                    "panel_id": "main",
                    "text": f"{ppm:.1f}",
                    "x": ppm,
                    "y": label_y,
                    "coordinate_space": "xdata_yaxes",
                    "rotation": 90.0,
                    "style": {"color": "#0072B2", "font_size": 6},
                }
            )
    return objects


def _assignment_objects(peaks: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    objects: list[dict[str, object]] = []
    row_index = 0
    for peak_index, peak in enumerate(_rank_peaks(peaks), start=1):
        assignment = str(peak.get("assignment") or "").strip()
        if not assignment:
            continue
        ppm = float(peak["ppm"])
        objects.append(
            {
                "id": f"text-peak-assignment-{peak_index}",
                "type": "text",
                "panel_id": "main",
                "text": f"{ppm:.1f} — {assignment}",
                "coordinate_space": "axes",
                "x": 1.02,
                "y": 0.98 - row_index * 0.055,
                "horizontal_alignment": "left",
                "vertical_alignment": "top",
                "style": {"color": "#0072B2", "font_size": 6},
            }
        )
        row_index += 1
    return objects


def _rank_peaks(peaks: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        peaks,
        key=lambda item: float(item.get("prominence", item.get("height", 0.0)) or 0.0),
        reverse=True,
    )[:16]


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
        "x_column": "ppm",
        "y_column": y_column,
        "style": {"color": color, "line_width": 0.9},
    }


def _spectrum_layout(
    nucleus: str,
    *,
    show_legend: bool,
    assignment_column: bool = False,
) -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=9.5 if assignment_column else 7.0,
        height_in=4.0,
        rows=1,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisDefinition(
                    axis_id="x",
                    label=f"{nucleus} Chemical shift",
                    unit="ppm",
                    reversed=True,
                ),
                y_axis=AxisDefinition(axis_id="y", label="Intensity", unit="a.u."),
                show_legend=show_legend,
            ),
        ),
    )


def _comparison_layout() -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=5.5,
        height_in=5.5,
        rows=1,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisDefinition(
                    axis_id="x",
                    label="Experimental shift",
                    unit="ppm",
                    reversed=True,
                ),
                y_axis=AxisDefinition(
                    axis_id="y",
                    label="Computed shift",
                    unit="ppm",
                    reversed=True,
                ),
            ),
        ),
    )


def _category_layout(label: str, unit: str) -> FigureLayoutDefinition:
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
                x_axis=AxisDefinition(axis_id="x", label="Category"),
                y_axis=AxisDefinition(axis_id="y", label=label, unit=unit),
            ),
        ),
    )


def _recipe(
    result: NMRResult,
    index: int,
    figure_kind: str,
    scientific_review: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    review = dict(scientific_review or _result_scientific_review(result))
    return {
        "module": "polynexus.core.nmr_engine.figure_provider",
        "function": "build_nmr_figure_definitions",
        "inputs": {"result_label": result.label},
        "parameters": {
            "frame_index": index,
            "figure_kind": figure_kind,
            **({"peak_label_limit": _PEAK_LABEL_LIMIT} if figure_kind in {"spectrum", "deconvolution"} else {}),
        },
        "scientific_review": review,
        "v2_adapter": "nmr",
    }


def _is_solid_c(result: NMRResult) -> bool:
    nucleus = str(result.nucleus or "").strip().upper().replace("¹", "1")
    return nucleus in {"13C", "C", "13 C"} and str(result.sample_state or "").strip().lower() == "solid"


def _result_scientific_review(result: NMRResult) -> dict[str, Any]:
    source_ref = str(
        result.metadata.get("source_id")
        or result.metadata.get("filename")
        or result.label
        or ""
    ).strip()
    if not _is_solid_c(result):
        return {
            "allowed": True,
            "reason": "not_applicable",
            "record_id": "",
            "scope": "nmr.solid_c",
            "source_ref": source_ref,
        }
    return review_decision_snapshot(
        review_record_from_payload(result.metadata.get("scientific_review")),
        expected_scope="nmr.solid_c",
        source_ref=source_ref,
    )


def _results_scientific_review(results: Sequence[NMRResult]) -> dict[str, Any]:
    relevant = [_result_scientific_review(result) for result in results if _is_solid_c(result)]
    if not relevant:
        return {
            "allowed": True,
            "reason": "not_applicable",
            "record_id": "",
            "scope": "nmr.solid_c",
            "source_ref": "",
        }
    return next((item for item in relevant if not item["allowed"]), relevant[0])


def _float_values(values) -> tuple[float, ...]:
    return tuple(float(value) for value in values)
