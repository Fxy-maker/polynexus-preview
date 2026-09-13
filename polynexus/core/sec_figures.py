"""Shared FigureDefinition providers for SEC/GPC results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)


def _layout(x: AxisDefinition, y: AxisDefinition, *, title: str, legend: bool = False) -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=7.0,
        height_in=4.5,
        rows=1,
        columns=1,
        panels=(PanelDefinition("main", 0, 0, x, y, title=title, show_legend=legend),),
    )


def _series(object_id: str, source: str, x: str, y: str, name: str, color: str) -> dict[str, Any]:
    return {
        "id": object_id,
        "type": "plot_series",
        "chart_kind": "line",
        "panel_id": "main",
        "name": name,
        "data_ref": source,
        "x_column": x,
        "y_column": y,
        "style": {"color": color, "line_width": 0.9},
    }


def _public_value(value: Any) -> Any:
    """Return a JSON-safe copy for recipe metadata and bindings."""

    if isinstance(value, Mapping):
        return {str(key): _public_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_public_value(item) for item in value]
    return value


def build_sec_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    measurements = tuple(getattr(engine, "_measurements", ()) or ())
    metrics = getattr(engine, "_metrics", {})
    if not measurements or not isinstance(metrics, dict):
        return ()
    curves = tuple(metrics.get("curves", ()))
    if not curves:
        return ()
    first = curves[0]
    x_unit = str(first.get("x_unit", "unknown"))
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    colors = ("#222222", "#0072B2", "#D55E00", "#009E73", "#CC79A7")
    for index, measurement in enumerate(measurements):
        source_id = f"{measurement.measurement_id}-data"
        sources.append(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("coordinate", x_unit),
                    DataColumnDefinition("response", measurement.units.get("intensity", "unknown")),
                ),
                values={
                    "coordinate": tuple(float(value) for value in measurement.channels["x"]),
                    "response": tuple(float(value) for value in measurement.channels["intensity"]),
                },
            )
        )
        objects.append(_series(f"series-{index + 1:03d}", source_id, "coordinate", "response", measurement.measurement_id, colors[index % len(colors)]))

    definitions: list[FigureDefinition] = [
        FigureDefinition(
            figure_id="sec.frame.chromatogram.001",
            technique="sec",
            scope="frame",
            category="per_frame",
            title="SEC/GPC Chromatogram",
            layout=_layout(
                AxisDefinition("coordinate", "Retention/elution coordinate", x_unit),
                AxisDefinition("response", "Recorded detector response", str(metrics.get("signal_unit", "unknown"))),
                title="SEC/GPC Chromatogram",
                legend=len(measurements) > 1,
            ),
            data_sources=tuple(sources),
            objects=tuple(objects),
            recipe={"module": "polynexus.core.sec_figures", "function": "build_sec_figure_definitions", "parameters": {"figure_kind": "chromatogram"}, "v2_adapter": "sec"},
            style_profile="sci_default",
            publication_role="diagnostic",
        )
    ]

    groups = metrics.get("sec_groups", {})
    selected_group: tuple[str, Mapping[str, Any]] | None = next(
        (
            (str(group_id), item["molecular_weight_summary"])
            for group_id, item in groups.items()
            if isinstance(item, Mapping)
            and isinstance(item.get("molecular_weight_summary"), Mapping)
            and item["molecular_weight_summary"].get("status") == "computed"
        ),
        None,
    )
    if selected_group is None:
        return tuple(definitions)
    group_id, summary = selected_group
    distribution = summary.get("molar_mass_distribution", {})
    if not isinstance(distribution, Mapping):
        return tuple(definitions)
    mm = tuple(float(value) for value in distribution.get("molar_mass", ()))
    response = tuple(float(value) for value in distribution.get("response_normalized", ()))
    coordinate = tuple(float(value) for value in distribution.get("coordinate", ()))
    if not mm or len(mm) != len(response) or len(mm) != len(coordinate):
        return tuple(definitions)
    mode = str(summary.get("distribution_mode", "unknown"))
    molar_mass_unit = str(summary.get("molar_mass_unit", "unknown"))
    coordinate_unit = str(summary.get("calibration_coordinate_unit") or x_unit)
    provenance = {
        "calibration_id": summary.get("calibration_id", ""),
        "standard_source": summary.get("calibration_standard_source", ""),
        "standard_ids": tuple(summary.get("calibration_standard_ids", ())),
        "distribution_mode": mode,
        "group_id": group_id,
    }

    metric_names = ("Mn", "Mw", "Mz", "dispersity")
    metric_paths = tuple(
        f"sec_groups.{group_id}.molecular_weight_summary.{name}"
        for name in metric_names
    )
    result = getattr(engine, "result", None)
    result_metadata = getattr(result, "metadata", {})
    metadata_units = (
        result_metadata.get("units", {})
        if isinstance(result_metadata, Mapping)
        else {}
    )
    metadata_methods = (
        result_metadata.get("methods", {})
        if isinstance(result_metadata, Mapping)
        else {}
    )
    metadata_parameters = (
        result_metadata.get("parameters", {})
        if isinstance(result_metadata, Mapping)
        else {}
    )
    manifest_binding = {
        path: {
            "unit": str(metadata_units.get(path) or ("1" if name == "dispersity" else molar_mass_unit)),
            "method": str(metadata_methods.get(path) or ""),
            "parameters": _public_value(metadata_parameters.get(path, {})),
        }
        for name, path in zip(metric_names, metric_paths)
    }
    summary_values = tuple(float(summary[name]) for name in metric_names)
    summary_units = tuple(item["unit"] for item in manifest_binding.values())
    summary_methods = tuple(item["method"] for item in manifest_binding.values())
    sources.append(
        FigureDataSourceDefinition(
            "molecular-weight-distribution-data",
            (
                DataColumnDefinition("molar_mass", molar_mass_unit),
                DataColumnDefinition("normalized_response", "1"),
                DataColumnDefinition("coordinate", coordinate_unit),
            ),
            {
                "molar_mass": mm,
                "normalized_response": response,
                "coordinate": coordinate,
            },
        )
    )
    sources.append(
        FigureDataSourceDefinition(
            "molecular-weight-summary",
            (
                DataColumnDefinition("metric_path", "", "str"),
                DataColumnDefinition("metric", "", "str"),
                DataColumnDefinition("value", ""),
                DataColumnDefinition("unit", "", "str"),
                DataColumnDefinition("method", "", "str"),
            ),
            {
                "metric_path": metric_paths,
                "metric": metric_names,
                "value": summary_values,
                "unit": summary_units,
                "method": summary_methods,
            },
            role="metric_summary",
        )
    )
    distribution_recipe = {
        "module": "polynexus.core.sec_figures",
        "function": "build_sec_figure_definitions",
        "parameters": {
            "figure_kind": "molecular_weight_distribution",
            "distribution_mode": mode,
            "calibration_id": summary.get("calibration_id", ""),
        },
        "group_id": group_id,
        "metric_manifest_paths": metric_paths,
        "metric_manifest_binding": manifest_binding,
        "provenance": provenance,
        "v2_adapter": "sec",
    }
    definitions.append(
        FigureDefinition(
            "sec.frame.molecular-weight-distribution.001",
            "sec",
            "frame",
            "supplementary",
            "SEC/GPC Molecular-Weight Distribution",
            _layout(
                AxisDefinition("molar_mass", "Molar mass", molar_mass_unit, "log"),
                AxisDefinition(
                    "normalized_response",
                    f"Normalized {mode} distribution",
                    "1",
                ),
                title="SEC/GPC Molecular-Weight Distribution",
            ),
            tuple(sources[-2:]),
            (
                _series(
                    "series-molecular-weight",
                    "molecular-weight-distribution-data",
                    "molar_mass",
                    "normalized_response",
                    f"{mode} distribution",
                    "#0072B2",
                ),
            ),
            distribution_recipe,
            "sci_default",
            "diagnostic",
            1,
        )
    )
    coefficients = tuple(float(value) for value in summary.get("calibration_coefficients_log10_molar_mass", ()))
    # The original standard coordinates/masses are retained in the canonical analysis spec.
    spec = getattr(engine, "_template", None)
    spec_payload = spec.payload.get("sec_analysis", {}) if spec is not None else {}
    standard_coords = tuple(float(value) for value in spec_payload.get("calibration_coordinates", ()))
    standard_masses = tuple(float(value) for value in spec_payload.get("calibration_molar_masses", ()))
    standard_ids = tuple(str(value) for value in spec_payload.get("standard_ids", ()))
    if len(standard_coords) == len(standard_masses) == len(standard_ids) and coefficients:
        fit_x = standard_coords
        fit_m = tuple(10.0 ** sum(coefficient * (x ** (len(coefficients) - index - 1)) for index, coefficient in enumerate(coefficients)) for x in fit_x)
        sources_cal = (
            FigureDataSourceDefinition(
                "calibration-standards",
                (
                    DataColumnDefinition("coordinate", coordinate_unit),
                    DataColumnDefinition("molar_mass", molar_mass_unit),
                    DataColumnDefinition("standard_id", "", "str"),
                ),
                {
                    "coordinate": fit_x,
                    "molar_mass": standard_masses,
                    "standard_id": standard_ids,
                },
            ),
            FigureDataSourceDefinition(
                "calibration-fit",
                (
                    DataColumnDefinition("coordinate", coordinate_unit),
                    DataColumnDefinition("molar_mass", molar_mass_unit),
                ),
                {"coordinate": fit_x, "molar_mass": fit_m},
            ),
        )
        definitions.append(
            FigureDefinition(
                "sec.frame.calibration.001",
                "sec",
                "frame",
                "diagnostic",
                "SEC/GPC Calibration Curve",
                _layout(
                    AxisDefinition(
                        "coordinate",
                        "Retention/elution coordinate",
                        coordinate_unit,
                    ),
                    AxisDefinition("molar_mass", "Molar mass", molar_mass_unit, "log"),
                    title="SEC/GPC Calibration Curve",
                    legend=True,
                ),
                sources_cal,
                (
                    _series(
                        "series-standards",
                        "calibration-standards",
                        "coordinate",
                        "molar_mass",
                        "Standards",
                        "#222222",
                    ),
                    _series(
                        "series-fit",
                        "calibration-fit",
                        "coordinate",
                        "molar_mass",
                        "Fit",
                        "#D55E00",
                    ),
                ),
                {
                    "module": "polynexus.core.sec_figures",
                    "function": "build_sec_figure_definitions",
                    "parameters": {
                        "figure_kind": "calibration",
                        "calibration_id": summary.get("calibration_id", ""),
                    },
                    "group_id": group_id,
                    "metric_manifest_paths": metric_paths,
                    "provenance": provenance,
                    "v2_adapter": "sec",
                },
                "sci_default",
                "diagnostic",
                2,
            )
        )
    return tuple(definitions)


__all__ = ["build_sec_figure_definitions"]
