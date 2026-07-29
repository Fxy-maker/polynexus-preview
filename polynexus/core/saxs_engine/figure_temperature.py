"""Publication figure definitions for temperature and time-resolved SAXS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from polynexus.plotting.sci_style import AXIS_LABELS

from ..figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)
from .figure_common import (
    SAXSFrameView,
    _coerce_numeric_array,
    frame_views_from_engine,
)
from .figure_evidence import (
    attach_saxs_figure_evidence,
    configured_saxs_1d_review,
    existing_saxs_acceptance_audit,
)
from ..saxs_batch_helpers import copy_saxs_ai_rescue_evidence
from .figure_detector import build_detector_evidence, detector_capable
from .figure_eligibility import (
    classify_frame_eligibility,
    crystallinity_panel_eligible,
    invariant_panel_eligible,
    q_star_valid_for_invariant_panels,
    trend_panel_eligible,
)
from .figure_selection import (
    RepresentativeFrameSelection,
    select_representative_frames,
)


@dataclass(frozen=True)
class _ConditionAxis:
    kind: str
    column: str
    label: str
    unit: str


def _finite_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


def _first_final_value(frame: SAXSFrameView, *keys: str) -> Any:
    for key in keys:
        if key in frame.parameters and np.isfinite(_finite_float(frame.parameters[key])):
            return frame.parameters[key]
    return np.nan


def _condition_axis(engine: Any) -> _ConditionAxis:
    config = getattr(engine, "cfg", None)
    configured_label = str(getattr(config, "condition_label", "") or "").strip()
    configured_unit = str(getattr(config, "condition_unit", "") or "").strip()
    label_key = configured_label.lower()
    unit_key = configured_unit.lower().replace(" ", "")
    time_units = {
        "s",
        "sec",
        "second",
        "seconds",
        "min",
        "minute",
        "minutes",
        "h",
        "hr",
        "hour",
        "hours",
    }
    if "time" in label_key or unit_key in time_units:
        return _ConditionAxis(
            kind="time",
            column="time_s",
            label="Time",
            unit=configured_unit or "s",
        )
    return _ConditionAxis(
        kind="temperature",
        column="temperature_C",
        label="Temperature",
        unit=configured_unit or "C",
    )


def _sci_axis(axis_id: str, label_key: str, *, scale: str = "linear") -> AxisDefinition:
    return AxisDefinition(axis_id, AXIS_LABELS[label_key], scale=scale)


def _condition_sci_axis(axis_id: str, axis: _ConditionAxis) -> AxisDefinition:
    return _sci_axis(axis_id, "time" if axis.kind == "time" else "T")


def _condition_value(frame: SAXSFrameView) -> float:
    return _finite_float(frame.condition)


def _is_main_metric_frame(frame: SAXSFrameView) -> bool:
    if classify_frame_eligibility(frame).highest_role != "main":
        return False
    reliability = str(frame.parameters.get("lc_reliability_status") or "").strip().lower()
    return reliability not in {"low_confidence", "diagnostic_only", "no_path"}


def _column(name: str, unit: str, dtype: str = "float64") -> DataColumnDefinition:
    return DataColumnDefinition(name=name, unit=unit, dtype=dtype)


def _source(
    source_id: str,
    columns: Sequence[DataColumnDefinition],
    values: Mapping[str, Sequence[Any]],
    *,
    role: str = "plot_data",
) -> FigureDataSourceDefinition:
    return FigureDataSourceDefinition(
        source_id=source_id,
        columns=tuple(columns),
        values={name: tuple(items) for name, items in values.items()},
        role=role,
    )


def _selection_recipe(
    selection: RepresentativeFrameSelection,
    axis: _ConditionAxis,
) -> dict[str, Any]:
    return {
        "representative_indices": list(selection.indices),
        "representative_reasons": dict(selection.reasons),
        "representative_selection_source": selection.source,
        "condition_axis": axis.column,
        "condition_label": axis.label,
        "condition_unit": axis.unit,
        "manual_override": selection.source == "manual_override",
    }


def _positive_curve(frame: SAXSFrameView) -> tuple[np.ndarray, np.ndarray] | None:
    try:
        q = _coerce_numeric_array(frame.q)
        intensity = _coerce_numeric_array(frame.intensity)
    except (TypeError, ValueError):
        return None
    count = min(q.size, intensity.size)
    q = q[:count]
    intensity = intensity[:count]
    valid = np.isfinite(q) & np.isfinite(intensity) & (intensity > 0.0)
    q = q[valid]
    intensity = intensity[valid]
    if q.size < 2:
        return None
    order = np.argsort(q, kind="stable")
    q = q[order]
    intensity = intensity[order]
    q, unique_indices = np.unique(q, return_index=True)
    intensity = intensity[unique_indices]
    if q.size < 2:
        return None
    return q, intensity


def _profile_projection_quality(frame: SAXSFrameView) -> dict[str, Any] | None:
    try:
        q = _coerce_numeric_array(frame.q)
        intensity = _coerce_numeric_array(frame.intensity)
    except (TypeError, ValueError):
        return None
    count = min(q.size, intensity.size)
    q = q[:count]
    intensity = intensity[:count]
    finite = np.isfinite(q) & np.isfinite(intensity)
    retained = finite & (intensity > 0.0)
    finite_count = int(np.count_nonzero(finite))
    retained_count = int(np.count_nonzero(retained))
    nonfinite_count = int(count - finite_count)
    nonpositive_intensity_count = int(finite_count - retained_count)
    return {
        "input_pair_count": int(count),
        "retained_pair_count": retained_count,
        "nonfinite_pair_count": nonfinite_count,
        "nonpositive_intensity_pair_count": nonpositive_intensity_count,
        "status": (
            "complete"
            if nonfinite_count == 0 and nonpositive_intensity_count == 0
            else "partial_invalid"
        ),
    }


def _trace_projection_quality(
    payload: Any,
    x_key: str,
    y_key: str,
) -> dict[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None
    try:
        x_values = _coerce_numeric_array(payload.get(x_key, ()))
        y_values = _coerce_numeric_array(payload.get(y_key, ()))
    except (TypeError, ValueError):
        return None
    count = min(x_values.size, y_values.size)
    finite = np.isfinite(x_values[:count]) & np.isfinite(y_values[:count])
    retained_count = int(np.count_nonzero(finite))
    nonfinite_count = int(count - retained_count)
    return {
        "input_pair_count": int(count),
        "retained_pair_count": retained_count,
        "nonfinite_pair_count": nonfinite_count,
        "status": "complete" if nonfinite_count == 0 else "partial_nonfinite",
    }


def _regular_heatmap_source(
    frames: Sequence[SAXSFrameView],
    axis: _ConditionAxis,
) -> FigureDataSourceDefinition | None:
    curves: list[tuple[SAXSFrameView, np.ndarray, np.ndarray]] = []
    for frame in frames:
        curve = _positive_curve(frame)
        if curve is None or not np.isfinite(_condition_value(frame)):
            continue
        curves.append((frame, curve[0], curve[1]))
    if len(curves) < 2:
        return None
    q_min = max(float(q[0]) for _, q, _ in curves)
    q_max = min(float(q[-1]) for _, q, _ in curves)
    if not np.isfinite(q_min) or not np.isfinite(q_max) or q_max <= q_min:
        return None
    grid_size = min(160, max(2, min(q.size for _, q, _ in curves)))
    q_grid = np.linspace(q_min, q_max, grid_size)
    q_values: list[float] = []
    condition_values: list[float] = []
    log_intensity_values: list[float] = []
    for frame, q, intensity in curves:
        interpolated = np.interp(q_grid, q, intensity)
        if not np.all(np.isfinite(interpolated)) or np.any(interpolated <= 0.0):
            return None
        q_values.extend(q_grid.tolist())
        condition_values.extend([_condition_value(frame)] * grid_size)
        log_intensity_values.extend(np.log10(interpolated).tolist())
    return _source(
        "saxs-temperature-heatmap",
        (
            _column("q_nm1", "nm^-1"),
            _column(axis.column, axis.unit),
            _column("log10_intensity", "log10(a.u.)"),
        ),
        {
            "q_nm1": q_values,
            axis.column: condition_values,
            "log10_intensity": log_intensity_values,
        },
        role="heatmap_data",
    )


def _q_star_source(
    frames: Sequence[SAXSFrameView],
    axis: _ConditionAxis,
) -> FigureDataSourceDefinition | None:
    conditions: list[float] = []
    q_star_values: list[Any] = []
    for frame in frames:
        condition = _condition_value(frame)
        q_star = _first_final_value(
            frame,
            "q_star_nm1",
            "q_peak_nm1",
            "q_star_nm_inv",
        )
        if not np.isfinite(condition) or not np.isfinite(_finite_float(q_star)):
            continue
        conditions.append(condition)
        q_star_values.append(q_star)
    if len(conditions) < 2:
        return None
    return _source(
        "saxs-temperature-q-star",
        (
            _column(axis.column, axis.unit),
            _column("q_star_nm1", "nm^-1"),
        ),
        {axis.column: conditions, "q_star_nm1": q_star_values},
        role="trajectory_data",
    )


def _representative_profile_content(
    frames_by_index: Mapping[int, SAXSFrameView],
    selection: RepresentativeFrameSelection,
) -> tuple[
    list[FigureDataSourceDefinition],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    projection_quality: dict[str, dict[str, Any]] = {}
    colors = ("#0072B2", "#D55E00", "#009E73", "#E69F00", "#56B4E9", "#CC79A7")
    for order, index in enumerate(selection.indices):
        frame = frames_by_index[index]
        curve = _positive_curve(frame)
        if curve is None:
            continue
        quality = _profile_projection_quality(frame)
        if quality is not None:
            projection_quality[str(frame.index)] = quality
        source_id = f"saxs-temperature-profile-{index:03d}"
        sources.append(
            _source(
                source_id,
                (_column("q_nm1", "nm^-1"), _column("intensity", "a.u.")),
                {
                    "q_nm1": curve[0].tolist(),
                    "intensity": curve[1].tolist(),
                },
                role="representative_profile",
            )
        )
        objects.append(
            {
                "id": f"temperature-profile-{index:03d}",
                "type": "plot_series",
                "name": frame.label,
                "panel_id": "representative_profiles",
                "data_ref": source_id,
                "x_column": "q_nm1",
                "y_column": "intensity",
                "chart_kind": "line",
                "style": {
                    "color": colors[order % len(colors)],
                    "line_width": 0.9,
                },
            }
        )
    return sources, objects, projection_quality


def _lamellar_metrics_content(
    frames: Sequence[SAXSFrameView],
    axis: _ConditionAxis,
) -> tuple[FigureDataSourceDefinition | None, list[dict[str, Any]], dict[str, Any]]:
    metric_frames = [
        frame
        for frame in frames
        if _is_main_metric_frame(frame) and np.isfinite(_condition_value(frame))
    ]
    metrics = {
        "L_nm": [
            _first_final_value(frame, "L_nm", "L_nm_effective", "L_nm_measured")
            for frame in metric_frames
        ],
        "lc_nm": [
            _first_final_value(frame, "lc_nm_effective", "lc_effective_nm", "lc_nm")
            for frame in metric_frames
        ],
        "la_nm": [
            _first_final_value(frame, "la_nm_effective", "la_effective_nm", "la_nm")
            for frame in metric_frames
        ],
    }
    eligible = {name: trend_panel_eligible(values) for name, values in metrics.items()}
    if not any(eligible.values()):
        return (
            None,
            [],
            {
                "eligible": False,
                "reason": "fewer_than_three_valid_final_lamellar_points",
            },
        )
    included_frames = [
        (frame, position)
        for position, frame in enumerate(metric_frames)
        if all(
            not eligible[name] or np.isfinite(_finite_float(values[position]))
            for name, values in metrics.items()
        )
    ]
    if len(included_frames) < 3:
        return (
            None,
            [],
            {
                "eligible": False,
                "reason": "fewer_than_three_joint_final_lamellar_points",
            },
        )
    positions = [position for _, position in included_frames]
    source = _source(
        "saxs-temperature-lamellar-metrics",
        (
            _column(axis.column, axis.unit),
            _column("L_nm", "nm"),
            _column("lc_nm", "nm"),
            _column("la_nm", "nm"),
        ),
        {
            axis.column: [_condition_value(frame) for frame, _ in included_frames],
            **{
                name: [values[position] for position in positions]
                for name, values in metrics.items()
            },
        },
        role="final_parameter_trends",
    )
    styles = {
        "L_nm": ("Long period L", "#0072B2", "o"),
        "lc_nm": ("Effective crystalline thickness", "#D55E00", "s"),
        "la_nm": ("Effective amorphous thickness", "#009E73", "^"),
    }
    objects = [
        {
            "id": f"temperature-{name.replace('_', '-')}",
            "type": "plot_series",
            "name": styles[name][0],
            "panel_id": "lamellar_metrics",
            "data_ref": source.source_id,
            "x_column": axis.column,
            "y_column": name,
            "chart_kind": "line",
            "style": {
                "color": styles[name][1],
                "marker": styles[name][2],
                "marker_size": 3.5,
                "line_width": 0.9,
            },
        }
        for name in ("L_nm", "lc_nm", "la_nm")
        if eligible[name]
    ]
    return (
        source,
        objects,
        {
            "eligible": True,
            "reason": "at_least_three_valid_final_lamellar_points",
            "metrics": [name for name in ("L_nm", "lc_nm", "la_nm") if eligible[name]],
        },
    )


def _invariant_content(
    frames: Sequence[SAXSFrameView],
    axis: _ConditionAxis,
) -> tuple[FigureDataSourceDefinition | None, list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    invariant_values = [_first_final_value(frame, "Q_star") for frame in frames]
    crystallinity_values = [_first_final_value(frame, "Xc_effective", "Xc") for frame in frames]
    invariant_eligible = invariant_panel_eligible(frames, invariant_values)
    crystallinity_eligible = crystallinity_panel_eligible(frames, crystallinity_values)
    invariant_gate = {
        "eligible": invariant_eligible,
        "reason": (
            "emitted_q_star_valid_with_three_finite_points"
            if invariant_eligible
            else "requires_emitted_q_star_valid_and_three_finite_points"
        ),
    }
    crystallinity_gate = {
        "eligible": crystallinity_eligible,
        "reason": (
            "emitted_q_star_valid_with_three_finite_points"
            if crystallinity_eligible
            else "requires_emitted_q_star_valid_and_three_finite_points"
        ),
    }
    if not invariant_eligible and not crystallinity_eligible:
        return None, [], invariant_gate, crystallinity_gate
    included = [
        (index, frame)
        for index, frame in enumerate(frames)
        if q_star_valid_for_invariant_panels(frame)
        and np.isfinite(_condition_value(frame))
        and (
            (invariant_eligible and np.isfinite(_finite_float(invariant_values[index])))
            or (crystallinity_eligible and np.isfinite(_finite_float(crystallinity_values[index])))
        )
    ]
    source = _source(
        "saxs-temperature-invariant-metrics",
        (
            _column(axis.column, axis.unit),
            _column("Q_star", "a.u."),
            _column("Xc", "fraction"),
        ),
        {
            axis.column: [_condition_value(frame) for _, frame in included],
            "Q_star": [invariant_values[index] for index, _ in included],
            "Xc": [crystallinity_values[index] for index, _ in included],
        },
        role="gated_invariant_trends",
    )
    objects: list[dict[str, Any]] = []
    if invariant_eligible:
        objects.append(
            {
                "id": "temperature-invariant",
                "type": "plot_series",
                "name": "Invariant Q*",
                "panel_id": "invariant_metrics",
                "data_ref": source.source_id,
                "x_column": axis.column,
                "y_column": "Q_star",
                "chart_kind": "line",
                "style": {"color": "#CC79A7", "marker": "o", "line_width": 0.9},
            }
        )
    if crystallinity_eligible:
        objects.append(
            {
                "id": "temperature-crystallinity",
                "type": "plot_series",
                "name": "Crystallinity",
                "panel_id": "crystallinity_metrics",
                "data_ref": source.source_id,
                "x_column": axis.column,
                "y_column": "Xc",
                "chart_kind": "line",
                "style": {"color": "#56B4E9", "marker": "s", "line_width": 0.9},
            }
        )
    return source, objects, invariant_gate, crystallinity_gate


def _avrami_gate(engine: Any, axis: _ConditionAxis) -> tuple[dict[str, Any], Mapping[str, Any]]:
    result = getattr(engine, "_temperature_result", None)
    avrami = getattr(result, "avrami", {})
    if not isinstance(avrami, Mapping):
        avrami = {}
    if axis.kind != "time":
        return {"eligible": False, "reason": "time_axis_required"}, avrami
    if avrami.get("valid") is not True:
        return {"eligible": False, "reason": "avrami_valid_gate_not_emitted"}, avrami
    if not all(np.isfinite(_finite_float(avrami.get(key))) for key in ("n", "k_sn", "t_half_s")):
        return {"eligible": False, "reason": "nonfinite_avrami_parameters"}, avrami
    return {"eligible": True, "reason": "valid_time_axis_avrami_parameters"}, avrami


def _build_evolution(
    engine: Any,
    frames: Sequence[SAXSFrameView],
    selection: RepresentativeFrameSelection,
    axis: _ConditionAxis,
    avrami_gate: Mapping[str, Any],
) -> FigureDefinition | None:
    heatmap = _regular_heatmap_source(frames, axis)
    q_star = _q_star_source(frames, axis)
    frames_by_index = {frame.index: frame for frame in frames}
    profile_sources, profile_objects, profile_projection_quality = _representative_profile_content(
        frames_by_index,
        selection,
    )
    lamellar_source, lamellar_objects, lamellar_gate = _lamellar_metrics_content(
        frames,
        axis,
    )
    invariant_source, invariant_objects, invariant_gate, crystallinity_gate = _invariant_content(
        frames,
        axis,
    )
    if (
        heatmap is None
        or q_star is None
        or not profile_objects
        or lamellar_source is None
        or not lamellar_objects
    ):
        return None

    panels = [
        PanelDefinition(
            panel_id="heatmap",
            row=0,
            column=0,
            x_axis=_sci_axis("heatmap-q", "q"),
            y_axis=_condition_sci_axis("heatmap-condition", axis),
            panel_label="(a)",
        ),
        PanelDefinition(
            panel_id="representative_profiles",
            row=0,
            column=1,
            x_axis=_sci_axis("profile-q", "q"),
            y_axis=_sci_axis("profile-intensity", "I_saxs", scale="log"),
            show_legend=True,
            panel_label="(b)",
        ),
    ]
    invariant_panel_ids = {str(item.get("panel_id") or "") for item in invariant_objects}
    has_invariant_panel = "invariant_metrics" in invariant_panel_ids
    has_crystallinity_panel = "crystallinity_metrics" in invariant_panel_ids
    has_optional_panel = has_invariant_panel or has_crystallinity_panel
    panels.append(
        PanelDefinition(
            panel_id="lamellar_metrics",
            row=1,
            column=0,
            column_span=2,
            x_axis=_condition_sci_axis("lamellar-condition", axis),
            y_axis=_sci_axis("lamellar-length", "L"),
            show_legend=True,
            panel_label="(c)",
        )
    )
    if has_invariant_panel:
        panels.append(
            PanelDefinition(
                panel_id="invariant_metrics",
                row=2,
                column=0,
                column_span=1 if has_crystallinity_panel else 2,
                x_axis=_condition_sci_axis("invariant-condition", axis),
                y_axis=_sci_axis("invariant-value", "Q_star"),
                show_legend=True,
                panel_label="(d)",
            )
        )
    if has_crystallinity_panel:
        panels.append(
            PanelDefinition(
                panel_id="crystallinity_metrics",
                row=2,
                column=1 if has_invariant_panel else 0,
                column_span=1 if has_invariant_panel else 2,
                x_axis=_condition_sci_axis("crystallinity-condition", axis),
                y_axis=_sci_axis("crystallinity-value", "phi_c_saxs"),
                show_legend=True,
                panel_label="(e)" if has_invariant_panel else "(d)",
            )
        )

    sources = [heatmap, q_star, *profile_sources, lamellar_source]
    if has_optional_panel and invariant_source is not None:
        sources.append(invariant_source)
    objects: list[dict[str, Any]] = [
        {
            "id": "temperature-evolution-heatmap",
            "type": "heatmap",
            "name": "log10 I(q)",
            "panel_id": "heatmap",
            "data_ref": heatmap.source_id,
            "x_column": "q_nm1",
            "y_column": axis.column,
            "z_column": "log10_intensity",
            "style": {"cmap": "viridis", "colorbar_label": "log10 I(q)"},
        },
        {
            "id": "temperature-q-star-trajectory",
            "type": "plot_series",
            "name": "q*",
            "panel_id": "heatmap",
            "data_ref": q_star.source_id,
            "x_column": "q_star_nm1",
            "y_column": axis.column,
            "chart_kind": "line",
            "style": {
                "color": "#F0E442",
                "marker": "o",
                "marker_size": 3.0,
                "line_width": 1.0,
            },
        },
        *profile_objects,
        *lamellar_objects,
        *invariant_objects,
    ]
    recipe = {
        "module": "polynexus.core.saxs_engine.figure_temperature",
        "function": "build_temperature_figure_definitions",
        **_selection_recipe(selection, axis),
        "column_width": "double",
        "gates": {
            "lamellar_metrics": lamellar_gate,
            "invariant": invariant_gate,
            "crystallinity": crystallinity_gate,
            "avrami": dict(avrami_gate),
        },
        "parameters": {
            "profile_projection_quality": dict(profile_projection_quality),
        },
        "v2_adapter": "temperature_saxs",
    }
    return FigureDefinition(
        figure_id="saxs.temperature.evolution",
        technique="saxs",
        scope="series",
        category="series_overview",
        publication_role="main",
        title="Temperature/time-resolved SAXS evolution",
        layout=FigureLayoutDefinition(
            width_in=7.2,
            height_in=8.0 if has_optional_panel else 6.2,
            rows=3 if has_optional_panel else 2,
            columns=2,
            panels=tuple(panels),
            horizontal_spacing=0.24,
            vertical_spacing=0.28,
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe=recipe,
        style_profile="sci_default",
        display_order=10,
    )


def _build_avrami(
    frames: Sequence[SAXSFrameView],
    axis: _ConditionAxis,
    avrami: Mapping[str, Any],
    selection: RepresentativeFrameSelection,
) -> FigureDefinition:
    conditions: list[float] = []
    crystallinity: list[Any] = []
    retained_pair_count = 0
    for frame in frames:
        condition = _condition_value(frame)
        value = _first_final_value(frame, "Xc_effective", "Xc")
        if np.isfinite(condition) and np.isfinite(_finite_float(value)):
            retained_pair_count += 1
            conditions.append(condition)
            crystallinity.append(value)
    input_pair_count = len(frames)
    nonfinite_pair_count = input_pair_count - retained_pair_count
    avrami_projection_quality = {
        "input_pair_count": int(input_pair_count),
        "retained_pair_count": int(retained_pair_count),
        "nonfinite_pair_count": int(nonfinite_pair_count),
        "status": (
            "complete" if nonfinite_pair_count == 0 else "partial_nonfinite"
        ),
    }
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    if len(conditions) >= 2:
        source = _source(
            "saxs-temperature-avrami",
            (_column(axis.column, axis.unit), _column("Xc", "fraction")),
            {axis.column: conditions, "Xc": crystallinity},
            role="avrami_support_data",
        )
        sources.append(source)
        objects.append(
            {
                "id": "temperature-avrami-crystallinity",
                "type": "plot_series",
                "name": "Crystallinity",
                "panel_id": "avrami",
                "data_ref": source.source_id,
                "x_column": axis.column,
                "y_column": "Xc",
                "chart_kind": "line",
                "style": {"color": "#0072B2", "marker": "o", "line_width": 0.9},
            }
        )
    objects.append(
        {
            "id": "temperature-avrami-half-time",
            "type": "line",
            "name": "Half-time",
            "panel_id": "avrami",
            "orientation": "vertical",
            "x": avrami["t_half_s"],
            "style": {"color": "#D55E00", "line_style": "--", "line_width": 0.9},
        }
    )
    recipe = {
        "module": "polynexus.core.saxs_engine.figure_temperature",
        "function": "build_temperature_figure_definitions",
        **_selection_recipe(selection, axis),
        "parameters": {
            "n": avrami["n"],
            "k_sn": avrami["k_sn"],
            "t_half_s": avrami["t_half_s"],
            "avrami_projection_quality": avrami_projection_quality,
        },
        "gate": {"eligible": True, "reason": "valid_time_axis_avrami_parameters"},
        "v2_adapter": "temperature_saxs",
    }
    return FigureDefinition(
        figure_id="saxs.temperature.avrami",
        technique="saxs",
        scope="series",
        category="series_overview",
        publication_role="main",
        title="Avrami kinetics",
        layout=FigureLayoutDefinition(
            width_in=3.5,
            height_in=3.0,
            rows=1,
            columns=1,
            panels=(
                PanelDefinition(
                    panel_id="avrami",
                    row=0,
                    column=0,
                    x_axis=_sci_axis("avrami-time", "time"),
                    y_axis=_sci_axis("avrami-xc", "phi_c_saxs"),
                    show_legend=True,
                    panel_label="(a)",
                ),
            ),
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe=recipe,
        style_profile="sci_default",
        display_order=20,
    )


def _build_waterfall(
    frames: Sequence[SAXSFrameView],
    selection: RepresentativeFrameSelection,
    axis: _ConditionAxis,
) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    projection_quality: dict[str, dict[str, Any]] = {}
    colors = ("#0072B2", "#56B4E9", "#009E73", "#E69F00", "#D55E00", "#CC79A7")
    ordered_frames = sorted(frames, key=lambda frame: (_condition_value(frame), frame.index))
    for order, frame in enumerate(ordered_frames):
        curve = _positive_curve(frame)
        if curve is None:
            continue
        quality = _profile_projection_quality(frame)
        if quality is not None:
            projection_quality[str(frame.index)] = quality
        source_id = f"saxs-temperature-waterfall-{frame.index:03d}"
        sources.append(
            _source(
                source_id,
                (
                    _column("q_nm1", "nm^-1"),
                    _column("intensity_offset", "a.u."),
                ),
                {
                    "q_nm1": curve[0].tolist(),
                    "intensity_offset": (curve[1] * (10.0**order)).tolist(),
                },
                role="full_series_profile",
            )
        )
        objects.append(
            {
                "id": f"temperature-waterfall-{frame.index:03d}",
                "type": "plot_series",
                "name": frame.label,
                "panel_id": "waterfall",
                "data_ref": source_id,
                "x_column": "q_nm1",
                "y_column": "intensity_offset",
                "chart_kind": "line",
                "style": {"color": colors[order % len(colors)], "line_width": 0.8},
            }
        )
    if not objects:
        return None
    return FigureDefinition(
        figure_id="saxs.temperature.waterfall",
        technique="saxs",
        scope="series",
        category="supplementary",
        publication_role="si",
        title="Full SAXS series waterfall",
        layout=FigureLayoutDefinition(
            width_in=7.2,
            height_in=4.2,
            rows=1,
            columns=1,
            panels=(
                PanelDefinition(
                    panel_id="waterfall",
                    row=0,
                    column=0,
                    x_axis=_sci_axis("waterfall-q", "q"),
                    y_axis=_sci_axis("waterfall-intensity", "I_saxs", scale="log"),
                    show_legend=False,
                    panel_label="(a)",
                ),
            ),
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_temperature",
            "function": "build_temperature_figure_definitions",
            **_selection_recipe(selection, axis),
            "includes_all_frames": True,
            "parameters": {
                "profile_projection_quality": dict(projection_quality),
            },
            "v2_adapter": "temperature_saxs",
        },
        style_profile="sci_default",
        display_order=100,
    )


def _build_detector_figure(
    frames: Sequence[SAXSFrameView],
    selection: RepresentativeFrameSelection,
    axis: _ConditionAxis,
) -> FigureDefinition | None:
    if not frames or not detector_capable(frames):
        return None
    frame_by_index = {frame.index: frame for frame in frames}
    selected_frames = tuple(frame_by_index[index] for index in selection.indices)
    evidence, failures = build_detector_evidence(selected_frames)
    if not evidence:
        return None

    panels: list[PanelDefinition] = []
    objects: list[dict[str, Any]] = []
    for ordinal, item in enumerate(evidence):
        panel_id = f"detector-{item.frame.index:03d}"
        condition = _condition_value(item.frame)
        title = (
            f"{condition:g} {axis.unit}"
            if np.isfinite(condition)
            else item.frame.label
        )
        panels.append(
            PanelDefinition(
                panel_id=panel_id,
                row=0,
                column=ordinal,
                x_axis=AxisDefinition(
                    f"{panel_id}-x",
                    AXIS_LABELS["detector_x"],
                    unit="pixel",
                ),
                y_axis=AxisDefinition(
                    f"{panel_id}-y",
                    AXIS_LABELS["detector_y"],
                    unit="pixel",
                    reversed=True,
                ),
                title=title,
                panel_label=f"({chr(97 + ordinal)})",
            )
        )
        objects.append(
            {
                "id": f"detector-pattern-{item.frame.index:03d}",
                "type": "heatmap",
                "panel_id": panel_id,
                "data_ref": item.source.source_id,
                "x_column": "pixel_x",
                "y_column": "pixel_y",
                "z_column": "log_intensity",
                "allow_partial_detector_grid": True,
                "style": {
                    "cmap": "magma",
                    "colorbar_label": "log10(counts)",
                },
            }
        )

    parameters = {
        "source_capability": "detector_2d",
        "included_frame_indices": [frame.index for frame in frames],
        "representative_indices": list(selection.indices),
        "representative_reasons": dict(selection.reasons),
        "representative_selection_source": selection.source,
        "source_path_by_frame": {
            str(frame.index): frame.source_path for frame in frames
        },
        "selected_detector_source_paths": {
            str(frame.index): frame.source_path for frame in selected_frames
        },
        "detector_failures": dict(failures),
        "detector_projection_quality": {
            str(item.frame.index): item.projection_quality for item in evidence
        },
    }
    return FigureDefinition(
        figure_id="saxs.temperature.detector.2d",
        technique="saxs",
        scope="series",
        category="diagnostic",
        publication_role="diagnostic",
        title="Temperature SAXS detector evidence",
        layout=FigureLayoutDefinition(
            width_in=max(4.2, 3.2 * len(panels)),
            height_in=3.2,
            rows=1,
            columns=len(panels),
            panels=tuple(panels),
        ),
        data_sources=tuple(item.source for item in evidence),
        objects=tuple(objects),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_temperature",
            "function": "build_temperature_figure_definitions",
            "inputs": {
                "source_paths": [frame.source_path for frame in frames],
            },
            **_selection_recipe(selection, axis),
            "parameters": parameters,
            "v2_adapter": "temperature_saxs",
        },
        style_profile="sci_default",
        display_order=30,
    )


def _mapping_curve(
    payload: Any,
    x_key: str,
    y_key: str,
) -> tuple[np.ndarray, np.ndarray] | None:
    if not isinstance(payload, Mapping):
        return None
    try:
        x = _coerce_numeric_array(payload.get(x_key, ()))
        y = _coerce_numeric_array(payload.get(y_key, ()))
    except (TypeError, ValueError):
        return None
    count = min(x.size, y.size)
    valid = np.isfinite(x[:count]) & np.isfinite(y[:count])
    x = x[:count][valid]
    y = y[:count][valid]
    if x.size < 2:
        return None
    return x, y


def _build_selected_evidence(
    frame: SAXSFrameView,
    selection: RepresentativeFrameSelection,
    axis: _ConditionAxis,
    display_order: int,
) -> FigureDefinition | None:
    correlation = _mapping_curve(getattr(frame.analysis, "correlation", None), "r", "gamma")
    idf = _mapping_curve(getattr(frame.analysis, "idf", None), "r_idf", "idf")
    if correlation is None and idf is None:
        return None
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    panels: list[PanelDefinition] = []
    trace_projection_quality: dict[str, dict[str, Any]] = {}
    if correlation is not None:
        quality = _trace_projection_quality(
            getattr(frame.analysis, "correlation", None), "r", "gamma"
        )
        if quality is not None:
            trace_projection_quality["correlation"] = quality
        source_id = f"saxs-temperature-correlation-{frame.index:03d}"
        sources.append(
            _source(
                source_id,
                (_column("r_nm", "nm"), _column("gamma", "normalized")),
                {"r_nm": correlation[0].tolist(), "gamma": correlation[1].tolist()},
                role="correlation_evidence",
            )
        )
        panels.append(
            PanelDefinition(
                panel_id="correlation",
                row=0,
                column=0,
                x_axis=_sci_axis("correlation-r", "r"),
                y_axis=_sci_axis("correlation-gamma", "gamma"),
                panel_label="(a)",
            )
        )
        objects.append(
            {
                "id": f"temperature-correlation-{frame.index:03d}",
                "type": "plot_series",
                "name": "gamma(r)",
                "panel_id": "correlation",
                "data_ref": source_id,
                "x_column": "r_nm",
                "y_column": "gamma",
                "chart_kind": "line",
                "style": {"color": "#0072B2", "line_width": 0.9},
            }
        )
    if idf is not None:
        quality = _trace_projection_quality(
            getattr(frame.analysis, "idf", None), "r_idf", "idf"
        )
        if quality is not None:
            trace_projection_quality["idf"] = quality
        column = len(panels)
        source_id = f"saxs-temperature-idf-{frame.index:03d}"
        sources.append(
            _source(
                source_id,
                (_column("r_nm", "nm"), _column("idf", "a.u.")),
                {"r_nm": idf[0].tolist(), "idf": idf[1].tolist()},
                role="idf_evidence",
            )
        )
        panels.append(
            PanelDefinition(
                panel_id="idf",
                row=0,
                column=column,
                x_axis=_sci_axis("idf-r", "r"),
                y_axis=_sci_axis("idf-value", "g1"),
                panel_label=f"({chr(ord('a') + column)})",
            )
        )
        objects.append(
            {
                "id": f"temperature-idf-{frame.index:03d}",
                "type": "plot_series",
                "name": "IDF",
                "panel_id": "idf",
                "data_ref": source_id,
                "x_column": "r_nm",
                "y_column": "idf",
                "chart_kind": "line",
                "style": {"color": "#D55E00", "line_width": 0.9},
            }
        )
    supported_parameters: list[str] = []
    if correlation is not None and np.isfinite(
        _finite_float(_first_final_value(frame, "L_nm", "L_nm_effective", "L_nm_measured"))
    ):
        supported_parameters.append("L_nm")
    if idf is not None and np.isfinite(
        _finite_float(_first_final_value(frame, "lc_nm_effective", "lc_effective_nm", "lc_nm"))
    ):
        supported_parameters.append("lc_nm")
    supports_main = (
        classify_frame_eligibility(frame).highest_role == "main"
        and _is_main_metric_frame(frame)
        and bool(supported_parameters)
    )
    role = "si" if supports_main else "diagnostic"
    return FigureDefinition(
        figure_id=f"saxs.temperature.evidence.{frame.index:03d}",
        technique="saxs",
        scope="frame",
        category="supplementary" if supports_main else "diagnostic",
        publication_role=role,
        title=f"Selected-frame correlation/IDF evidence: {frame.label}",
        layout=FigureLayoutDefinition(
            width_in=7.2 if len(panels) == 2 else 3.5,
            height_in=3.0,
            rows=1,
            columns=len(panels),
            panels=tuple(panels),
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_temperature",
            "function": "build_temperature_figure_definitions",
            **_selection_recipe(selection, axis),
            "source_frame_index": frame.index,
            "selection_reason": selection.reasons[frame.index],
            "supported_main_parameters": supported_parameters,
            "parameters": {
                "trace_projection_quality": trace_projection_quality,
            },
            "role_reason": (
                "supports_main_parameter" if supports_main else "does_not_support_main_parameter"
            ),
            "v2_adapter": "temperature_saxs",
        },
        style_profile="sci_default",
        display_order=display_order,
    )


def build_temperature_figure_definitions(
    engine: Any,
    *,
    representative_indices: Sequence[int] | None = None,
) -> tuple[FigureDefinition, ...]:
    """Build deterministic publication recipes from existing engine evidence."""

    frames = frame_views_from_engine(engine)
    if not frames:
        return ()
    selection = select_representative_frames(
        frames,
        override_indices=representative_indices,
    )
    axis = _condition_axis(engine)
    avrami_gate, avrami = _avrami_gate(engine, axis)
    definitions: list[FigureDefinition] = []
    detector = _build_detector_figure(frames, selection, axis)
    if detector is not None:
        definitions.append(detector)
    evolution = _build_evolution(
        engine,
        frames,
        selection,
        axis,
        avrami_gate,
    )
    if evolution is not None:
        definitions.append(evolution)
    if avrami_gate["eligible"]:
        definitions.append(_build_avrami(frames, axis, avrami, selection))
    waterfall = _build_waterfall(frames, selection, axis)
    if waterfall is not None:
        definitions.append(waterfall)
    frames_by_index = {frame.index: frame for frame in frames}
    for order, index in enumerate(selection.indices):
        evidence = _build_selected_evidence(
            frames_by_index[index],
            selection,
            axis,
            display_order=200 + order,
        )
        if evidence is not None:
            definitions.append(evidence)
    ordered = tuple(sorted(definitions, key=lambda item: (item.display_order, item.figure_id)))
    final_definitions = tuple(_ensure_display_order(item) for item in ordered)
    return attach_saxs_figure_evidence(
        final_definitions,
        frames,
        mode="temperature",
        series=getattr(engine, "_temperature_result", None),
        ai_rescue=copy_saxs_ai_rescue_evidence(
            engine,
            getattr(engine, "result", None),
        ),
        acceptance_audit=existing_saxs_acceptance_audit(engine),
        scientific_review=configured_saxs_1d_review(engine),
    )


def _ensure_display_order(definition: FigureDefinition) -> FigureDefinition:
    recipe = dict(definition.recipe)
    parameters = dict(recipe.get("parameters", {}))
    parameters.setdefault("display_order", int(definition.display_order))
    recipe["parameters"] = parameters
    return definition.__class__(**{**definition.__dict__, "recipe": recipe})


__all__ = ["build_temperature_figure_definitions"]
