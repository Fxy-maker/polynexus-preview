"""Manifest-backed figures for the Joint analysis hub."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any

from ..figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)
from .dataset import JointBatchRow, build_joint_run_provenance


_XC_TECHNIQUES = ("dsc", "waxs", "saxs", "ir", "nmr")
_XC_COLORS = {
    "dsc": "#B2182B",
    "waxs": "#2166AC",
    "saxs": "#1B7837",
    "ir": "#E69F00",
    "nmr": "#762A83",
}


def build_joint_figure_definitions(
    rows: Sequence[JointBatchRow],
) -> tuple[FigureDefinition, ...]:
    """Build Joint figures from the existing validated hub rows."""

    definitions: list[FigureDefinition] = []
    crystallinity = _crystallinity_definition(rows)
    if crystallinity is not None:
        definitions.append(crystallinity)
    multiscale = _multiscale_definition(rows)
    if multiscale is not None:
        definitions.append(multiscale)
    coverage = _coverage_definition(rows)
    if coverage is not None:
        definitions.append(coverage)
    return tuple(definitions)


def _crystallinity_definition(
    rows: Sequence[JointBatchRow],
) -> FigureDefinition | None:
    labels = _labels(rows)
    values = {
        f"{technique}_Xc_pct": tuple(_xc_pct(row, technique) for row in rows)
        for technique in _XC_TECHNIQUES
    }
    if not any(_has_finite(items) for items in values.values()):
        return None
    source = FigureDataSourceDefinition(
        source_id="joint-crystallinity-data",
        columns=(
            DataColumnDefinition("sample", "", dtype="str"),
            *(DataColumnDefinition(f"{technique}_Xc_pct", "%") for technique in _XC_TECHNIQUES),
        ),
        values={"sample": tuple(labels), **values},
        role="joint_consistency_data",
    )
    objects = tuple(
        {
            "id": f"{technique}-crystallinity",
            "type": "plot_series",
            "panel_id": "main",
            "name": technique.upper(),
            "data_ref": source.source_id,
            "x_column": "sample",
            "y_column": f"{technique}_Xc_pct",
            "chart_kind": "bar",
            "style": {"color": _XC_COLORS[technique], "alpha": 0.85},
        }
        for technique in _XC_TECHNIQUES
        if _has_finite(values[f"{technique}_Xc_pct"])
    )
    return FigureDefinition(
        figure_id="joint.series.crystallinity",
        technique="joint",
        scope="series",
        category="series_overview",
        publication_role="main",
        title="Cross-Technique Crystallinity Comparison",
        layout=_layout(
            x_label="Sample / batch",
            y_label="Crystallinity",
            y_unit="%",
            show_legend=True,
        ),
        data_sources=(source,),
        objects=objects,
        recipe=_recipe("crystallinity", rows),
        style_profile="sci_default",
        display_order=10,
    )


def _multiscale_definition(
    rows: Sequence[JointBatchRow],
) -> FigureDefinition | None:
    selected = [
        (label, _value(row, "saxs", ("L_nm", "long_period_nm", "L_best")),
         _value(row, "waxs", ("D_Scherrer_nm", "D_nm", "crystallite_size_nm")))
        for row, label in zip(rows, _labels(rows))
    ]
    selected = [item for item in selected if math.isfinite(item[1]) and math.isfinite(item[2])]
    if not selected:
        return None
    source = FigureDataSourceDefinition(
        source_id="joint-multiscale-data",
        columns=(
            DataColumnDefinition("long_period_nm", "nm"),
            DataColumnDefinition("crystallite_size_nm", "nm"),
        ),
        values={
            "long_period_nm": tuple(item[1] for item in selected),
            "crystallite_size_nm": tuple(item[2] for item in selected),
        },
        role="multiscale_support_data",
    )
    return FigureDefinition(
        figure_id="joint.series.multiscale",
        technique="joint",
        scope="series",
        category="supplementary",
        publication_role="si",
        title="SAXS-WAXS Multi-Scale Correlation",
        layout=_layout(
            x_label="SAXS long period",
            x_unit="nm",
            y_label="WAXS crystallite size",
            y_unit="nm",
        ),
        data_sources=(source,),
        objects=(
            {
                "id": "multiscale-correlation",
                "type": "plot_series",
                "panel_id": "main",
                "name": "Batches",
                "data_ref": source.source_id,
                "x_column": "long_period_nm",
                "y_column": "crystallite_size_nm",
                "chart_kind": "scatter",
                "style": {"color": "#2166AC", "marker_size": 30.0},
            },
        ),
        recipe=_recipe("multiscale", rows),
        style_profile="sci_default",
        display_order=20,
    )


def _coverage_definition(rows: Sequence[JointBatchRow]) -> FigureDefinition | None:
    if not rows:
        return None
    labels = _labels(rows)
    source = FigureDataSourceDefinition(
        source_id="joint-coverage-data",
        columns=(
            DataColumnDefinition("sample", "", dtype="str"),
            DataColumnDefinition("technique_count", "count"),
        ),
        values={
            "sample": tuple(labels),
            "technique_count": tuple(float(row.technique_count) for row in rows),
        },
        role="evidence_coverage_data",
    )
    return FigureDefinition(
        figure_id="joint.series.coverage",
        technique="joint",
        scope="series",
        category="diagnostic",
        publication_role="diagnostic",
        title="Joint Evidence Coverage",
        layout=_layout(
            x_label="Sample / batch",
            y_label="Available techniques",
            y_unit="count",
        ),
        data_sources=(source,),
        objects=(
            {
                "id": "technique-coverage",
                "type": "plot_series",
                "panel_id": "main",
                "name": "Available techniques",
                "data_ref": source.source_id,
                "x_column": "sample",
                "y_column": "technique_count",
                "chart_kind": "bar",
                "style": {"color": "#666666", "alpha": 0.85},
            },
        ),
        recipe=_recipe("coverage", rows),
        style_profile="sci_default",
        display_order=30,
    )


def _layout(
    *,
    x_label: str,
    y_label: str,
    x_unit: str = "",
    y_unit: str = "",
    show_legend: bool = False,
) -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=7.0,
        height_in=4.4,
        rows=1,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisDefinition(axis_id="x", label=x_label, unit=x_unit),
                y_axis=AxisDefinition(axis_id="y", label=y_label, unit=y_unit),
                show_legend=show_legend,
            ),
        ),
    )


def _value(row: JointBatchRow, technique: str, keys: Iterable[str]) -> float:
    run = row.run(technique)
    if run is None:
        return math.nan
    return run.get_first_number(keys)


def _xc_pct(row: JointBatchRow, technique: str) -> float:
    value = _value(row, technique, ("Xc_pct", "Xc", "phi_c", "crystallinity", "crystallinity_pct"))
    if math.isfinite(value) and 0.0 <= value <= 1.5:
        return value * 100.0
    return value


def _labels(rows: Sequence[JointBatchRow]) -> tuple[str, ...]:
    return tuple(f"{row.sample_name} / {row.batch_label}" for row in rows)


def _has_finite(values: Sequence[float]) -> bool:
    return any(math.isfinite(float(value)) for value in values)


def _recipe(kind: str, rows: Sequence[JointBatchRow]) -> dict[str, Any]:
    return {
        "module": "polynexus.core.joint.figure_provider",
        "function": "build_joint_figure_definitions",
        "inputs": {"batch_ids": [row.batch_id for row in rows]},
        "parameters": {"figure_kind": kind},
        "run_provenance": [build_joint_run_provenance(row) for row in rows],
        "v2_adapter": "joint",
    }


__all__ = ["build_joint_figure_definitions"]
