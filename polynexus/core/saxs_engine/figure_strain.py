"""Editable publication definitions for in-situ strain SAXS series.

This provider is deliberately a projection layer: it selects and reshapes
already-emitted engine evidence but never runs a SAXS analysis routine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

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
from .figure_evidence import attach_saxs_figure_evidence, existing_saxs_acceptance_audit
from ..saxs_batch_helpers import copy_saxs_ai_rescue_evidence
from .figure_eligibility import (
    FigureEligibilityDecision,
    classify_frame_eligibility,
    crystallinity_panel_eligible,
    invariant_panel_eligible,
    q_star_valid_for_invariant_panels,
    trend_panel_eligible,
)
from .figure_selection import RepresentativeFrameSelection, select_representative_frames
from .io import SUPPORTED_2D_EXTENSIONS, read_image


_MODULE = "polynexus.core.saxs_engine.figure_strain"
_COLORS = ("#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2")
_STANDARD_AXIS_LABELS = {
    "Detector x": r"Detector $x$ (pixel)",
    "Detector y": r"Detector $y$ (pixel)",
    "q": r"$q$ (nm$^{-1}$)",
    "Intensity": r"$I$ (a.u.)",
    "Strain": r"Strain $\varepsilon$ (\%)",
    "Length": r"Long period $L$ (nm)",
    "Relative metric": "Relative metric (a.u.)",
    "Orientation metric": r"Herman orientation factor $f$",
    "r": r"$r$ (nm)",
    "Correlation": r"$\gamma(r)$",
    "IDF": r"$\mathrm{IDF}(r)$ (a.u.)",
    "Azimuth": r"Azimuth $\chi$ (rad)",
    "Phase": "Strain phase",
}


@dataclass(frozen=True)
class _DetectorEvidence:
    frame: SAXSFrameView
    source: FigureDataSourceDefinition
    sampled_pixel_count: int
    retained_pixel_count: int
    nonfinite_pixel_count: int

    @property
    def projection_quality(self) -> dict[str, Any]:
        return {
            "sampled_pixel_count": self.sampled_pixel_count,
            "retained_pixel_count": self.retained_pixel_count,
            "nonfinite_pixel_count": self.nonfinite_pixel_count,
            "status": (
                "partial_nonfinite"
                if self.nonfinite_pixel_count
                else "complete"
            ),
        }


@dataclass(frozen=True)
class _DetectorProjection:
    pixel_x: np.ndarray
    pixel_y: np.ndarray
    log_intensity: np.ndarray
    sampled_pixel_count: int
    retained_pixel_count: int
    nonfinite_pixel_count: int


def _finite_number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


def _first_finite(*values: Any) -> float:
    for value in values:
        number = _finite_number(value)
        if np.isfinite(number):
            return number
    return np.nan


def _analysis_parameters(frame: SAXSFrameView) -> Mapping[str, Any]:
    parameters = getattr(frame.analysis, "final_parameters", {})
    return parameters if isinstance(parameters, Mapping) else {}


def _emitted_parameter(frame: SAXSFrameView, *keys: str) -> float:
    analysis_parameters = _analysis_parameters(frame)
    for key in keys:
        if key in frame.parameters:
            number = _finite_number(frame.parameters[key])
            if np.isfinite(number):
                return number
        if key in analysis_parameters:
            number = _finite_number(analysis_parameters[key])
            if np.isfinite(number):
                return number
        if hasattr(frame.analysis, key):
            number = _finite_number(getattr(frame.analysis, key))
            if np.isfinite(number):
                return number
    return np.nan


def _series_point(engine: Any, frame: SAXSFrameView) -> Any:
    result = getattr(engine, "_strain_result", None)
    points = getattr(result, "strain_points", ()) or ()
    if frame.index < len(points):
        return points[frame.index]
    return None


def _point_value(engine: Any, frame: SAXSFrameView, *keys: str) -> float:
    point = _series_point(engine, frame)
    for key in keys:
        if point is not None and hasattr(point, key):
            number = _finite_number(getattr(point, key))
            if np.isfinite(number):
                return number
    return _emitted_parameter(frame, *keys)


def _data_source(
    source_id: str,
    columns: Sequence[tuple[str, str, str]],
    values: Mapping[str, Sequence[Any]],
    *,
    role: str,
) -> FigureDataSourceDefinition:
    return FigureDataSourceDefinition(
        source_id=source_id,
        columns=tuple(
            DataColumnDefinition(name=name, unit=unit, dtype=dtype) for name, unit, dtype in columns
        ),
        values={name: tuple(values[name]) for name, _, _ in columns},
        role=role,
    )


def _axis(
    axis_id: str,
    label: str,
    unit: str = "",
    *,
    scale: str = "linear",
    reversed: bool = False,
) -> AxisDefinition:
    return AxisDefinition(
        axis_id=axis_id,
        label=_STANDARD_AXIS_LABELS.get(label, label),
        unit="",
        scale=scale,
        reversed=reversed,
    )


def _panel(
    panel_id: str,
    row: int,
    column: int,
    x_axis: AxisDefinition,
    y_axis: AxisDefinition,
    *,
    title: str,
    row_span: int = 1,
    column_span: int = 1,
    show_legend: bool = False,
    panel_label: str = "",
) -> PanelDefinition:
    return PanelDefinition(
        panel_id=panel_id,
        row=row,
        column=column,
        x_axis=x_axis,
        y_axis=y_axis,
        # Descriptive text belongs in the FigureDefinition title/caption.
        title="",
        show_legend=show_legend,
        row_span=row_span,
        column_span=column_span,
        panel_label=panel_label,
    )


def _series_object(
    object_id: str,
    panel_id: str,
    data_ref: str,
    x_column: str,
    y_column: str,
    *,
    name: str = "",
    color: str = "#000000",
    marker: str = "",
    chart_kind: str = "line",
) -> dict[str, Any]:
    style: dict[str, Any] = {"color": color, "line_width": 0.9}
    if marker:
        style.update({"marker": marker, "marker_size": 3.2})
    return {
        "id": object_id,
        "type": "plot_series",
        "panel_id": panel_id,
        "data_ref": data_ref,
        "x_column": x_column,
        "y_column": y_column,
        "chart_kind": chart_kind,
        "name": name,
        "style": style,
    }


def _heatmap_object(
    object_id: str,
    panel_id: str,
    data_ref: str,
    x_column: str,
    y_column: str,
    z_column: str,
    *,
    cmap: str,
    colorbar_label: str,
) -> dict[str, Any]:
    return {
        "id": object_id,
        "type": "heatmap",
        "panel_id": panel_id,
        "data_ref": data_ref,
        "x_column": x_column,
        "y_column": y_column,
        "z_column": z_column,
        "style": {"cmap": cmap, "colorbar_label": colorbar_label},
    }


def _detector_capable(engine: Any) -> bool:
    paths = tuple(str(path or "") for path in (getattr(engine, "_file_list", ()) or ()))
    return any(Path(path).suffix.lower() in SUPPORTED_2D_EXTENSIONS for path in paths)


def _representative_override(engine: Any) -> Sequence[int] | None:
    config = getattr(engine, "cfg", None)
    candidates = (
        getattr(engine, "_figure_representative_indices", None),
        getattr(config, "figure_representative_indices", None),
        getattr(config, "representative_indices", None),
    )
    for candidate in candidates:
        if candidate is not None:
            return tuple(candidate)
    return None


def _select_representatives(
    engine: Any,
    frames: Sequence[SAXSFrameView],
    override_indices: Sequence[int] | None,
) -> RepresentativeFrameSelection:
    maximum = min(3, len(frames))
    if maximum == 0:
        return RepresentativeFrameSelection((), {}, "deterministic_transition")
    return select_representative_frames(
        frames,
        maximum=maximum,
        override_indices=(
            _representative_override(engine) if override_indices is None else override_indices
        ),
        minimum_separation=2,
    )


def _profile_values(
    frame: SAXSFrameView,
    intensity: Any | None = None,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    try:
        q = _coerce_numeric_array(frame.q)
        values = _coerce_numeric_array(
            frame.intensity if intensity is None else intensity,
        )
    except (TypeError, ValueError):
        return (), ()
    count = min(q.size, values.size)
    q = q[:count]
    values = values[:count]
    finite = np.isfinite(q) & np.isfinite(values) & (q > 0) & (values > 0)
    return tuple(q[finite].tolist()), tuple(values[finite].tolist())


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
    retained = finite & (q > 0.0) & (intensity > 0.0)
    finite_count = int(np.count_nonzero(finite))
    retained_count = int(np.count_nonzero(retained))
    nonfinite_count = int(count - finite_count)
    nonpositive_count = int(finite_count - retained_count)
    return {
        "input_pair_count": int(count),
        "retained_pair_count": retained_count,
        "nonfinite_pair_count": nonfinite_count,
        "nonpositive_pair_count": nonpositive_count,
        "status": (
            "complete"
            if nonfinite_count == 0 and nonpositive_count == 0
            else "partial_invalid"
        ),
    }


def _engine_channel(engine: Any, frame: SAXSFrameView, attribute: str) -> Any | None:
    values = getattr(engine, attribute, ()) or ()
    if frame.index < len(values):
        return values[frame.index]
    return None


def _profile_source(
    engine: Any,
    frame: SAXSFrameView,
    *,
    source_id: str,
    prefer_equatorial: bool,
    include_sectors: bool,
) -> FigureDataSourceDefinition | None:
    equatorial = _engine_channel(engine, frame, "_I_equat_list")
    meridional = _engine_channel(engine, frame, "_I_merid_list")
    selected = equatorial if prefer_equatorial and equatorial is not None else frame.intensity
    q_values, intensity_values = _profile_values(frame, selected)
    if not q_values:
        return None

    columns: list[tuple[str, str, str]] = [
        ("q_nm_inv", "nm^-1", "float64"),
        ("intensity", "a.u.", "float64"),
    ]
    values: dict[str, Sequence[Any]] = {
        "q_nm_inv": q_values,
        "intensity": intensity_values,
    }
    if include_sectors:
        for column, channel in (
            ("equatorial_intensity", equatorial),
            ("meridional_intensity", meridional),
        ):
            channel_q, channel_values = _profile_values(frame, channel)
            if channel is not None and channel_q == q_values:
                columns.append((column, "a.u.", "float64"))
                values[column] = channel_values
    return _data_source(source_id, columns, values, role="scattering_profile")


def _q_strain_source(
    frames: Sequence[SAXSFrameView],
) -> tuple[FigureDataSourceDefinition | None, str]:
    curves: list[tuple[SAXSFrameView, np.ndarray, np.ndarray]] = []
    for frame in frames:
        try:
            q = _coerce_numeric_array(frame.q)
            intensity = _coerce_numeric_array(frame.intensity)
        except (TypeError, ValueError):
            return None, "unavailable"
        count = min(q.size, intensity.size)
        finite = np.isfinite(q[:count]) & np.isfinite(intensity[:count])
        q = q[:count][finite]
        intensity = intensity[:count][finite]
        if q.size < 2:
            return None, "unavailable"
        order = np.argsort(q, kind="stable")
        q = q[order]
        intensity = intensity[order]
        q, unique_indices = np.unique(q, return_index=True)
        intensity = intensity[unique_indices]
        if q.size < 2:
            return None, "unavailable"
        curves.append((frame, q, intensity))

    first_q = curves[0][1]
    shared_grid = all(
        q.shape == first_q.shape and np.allclose(q, first_q, rtol=1e-7, atol=1e-12, equal_nan=False)
        for _frame, q, _intensity in curves[1:]
    )
    if shared_grid:
        q_grid = first_q
        transform = "none_shared_q_grid"
    else:
        q_min = max(float(q[0]) for _frame, q, _intensity in curves)
        q_max = min(float(q[-1]) for _frame, q, _intensity in curves)
        if not np.isfinite(q_min) or not np.isfinite(q_max) or q_max <= q_min:
            return None, "unavailable"
        grid_size = min(160, max(2, min(q.size for _frame, q, _intensity in curves)))
        q_grid = np.linspace(q_min, q_max, grid_size)
        transform = "linear_interpolation_common_q_overlap"

    q_values: list[float] = []
    strain_values: list[float] = []
    intensity_values: list[float] = []
    for frame, q, intensity in curves:
        if shared_grid:
            aligned = intensity
        else:
            aligned = np.interp(q_grid, q, intensity)
        if aligned.size != q_grid.size or not np.all(np.isfinite(aligned)):
            return None, "unavailable"
        strain = _finite_number(frame.condition)
        if not np.isfinite(strain):
            return None, "unavailable"
        positive = np.clip(aligned, np.finfo(float).tiny, None)
        q_values.extend(float(value) for value in q_grid)
        strain_values.extend([strain] * q_grid.size)
        intensity_values.extend(np.log10(positive).tolist())
    return (
        _data_source(
            "q-strain-heatmap",
            (
                ("q_nm_inv", "nm^-1", "float64"),
                ("strain_pct", "%", "float64"),
                ("log_intensity", "log10(a.u.)", "float64"),
            ),
            {
                "q_nm_inv": q_values,
                "strain_pct": strain_values,
                "log_intensity": intensity_values,
            },
            role="scattering_heatmap",
        ),
        transform,
    )


def _morphology_source(
    frames: Sequence[SAXSFrameView],
) -> FigureDataSourceDefinition:
    return _data_source(
        "strain-morphology",
        (
            ("strain_pct", "%", "float64"),
            ("L_nm", "nm", "float64"),
            ("lc_nm", "nm", "float64"),
            ("la_nm", "nm", "float64"),
        ),
        {
            "strain_pct": [_finite_number(frame.condition) for frame in frames],
            "L_nm": [
                _emitted_parameter(frame, "L_nm", "L_nm_effective", "L_nm_measured")
                for frame in frames
            ],
            "lc_nm": [_emitted_parameter(frame, "lc_nm_effective", "lc_nm") for frame in frames],
            "la_nm": [_emitted_parameter(frame, "la_nm_effective", "la_nm") for frame in frames],
        },
        role="morphology_trends",
    )


def _metric_values(
    engine: Any,
    frames: Sequence[SAXSFrameView],
) -> dict[str, list[float]]:
    values = {
        "strain_pct": [_finite_number(frame.condition) for frame in frames],
        "Q_star": [_emitted_parameter(frame, "Q_star", "Q_star_abs") for frame in frames],
        "Q_star_rel": [_emitted_parameter(frame, "Q_star_rel", "Q_rel") for frame in frames],
        "Xc": [_emitted_parameter(frame, "Xc_effective", "Xc", "phi_c") for frame in frames],
        "phi_void": [_point_value(engine, frame, "phi_void") for frame in frames],
        "void_ar": [_point_value(engine, frame, "void_ar") for frame in frames],
    }
    for index, frame in enumerate(frames):
        if q_star_valid_for_invariant_panels(frame):
            continue
        for key in ("Q_star", "Q_star_rel", "Xc"):
            values[key][index] = np.nan
    return values


def _metrics_source(
    engine: Any,
    frames: Sequence[SAXSFrameView],
) -> tuple[FigureDataSourceDefinition | None, tuple[str, ...]]:
    values = _metric_values(engine, frames)
    enabled: list[str] = []
    if invariant_panel_eligible(frames, values["Q_star"]):
        enabled.extend(("Q_star", "Q_star_rel"))
    if crystallinity_panel_eligible(frames, values["Xc"]):
        enabled.append("Xc")
    if trend_panel_eligible(values["phi_void"]):
        enabled.append("phi_void")
    if trend_panel_eligible(values["void_ar"]):
        enabled.append("void_ar")
    enabled = list(dict.fromkeys(enabled))
    if not enabled:
        return None, ()
    units = {
        "Q_star": "a.u.",
        "Q_star_rel": "1",
        "Xc": "1",
        "phi_void": "1",
        "void_ar": "1",
    }
    columns = [("strain_pct", "%", "float64")]
    columns.extend((name, units[name], "float64") for name in enabled)
    selected_values = {"strain_pct": values["strain_pct"]}
    selected_values.update({name: values[name] for name in enabled})
    return (
        _data_source(
            "strain-metrics",
            columns,
            selected_values,
            role="invariant_void_evidence",
        ),
        tuple(enabled),
    )


def _invariant_definition(
    engine: Any,
    frames: Sequence[SAXSFrameView],
    decisions: Mapping[int, FigureEligibilityDecision],
) -> FigureDefinition | None:
    values = _metric_values(engine, frames)
    enabled: list[str] = []
    if invariant_panel_eligible(frames, values["Q_star"]):
        enabled.extend(("Q_star", "Q_star_rel"))
    if crystallinity_panel_eligible(frames, values["Xc"]):
        enabled.append("Xc")
    if not enabled:
        return None
    units = {"Q_star": "a.u.", "Q_star_rel": "1", "Xc": "1"}
    columns = [("strain_pct", "%", "float64")]
    columns.extend((name, units[name], "float64") for name in enabled)
    selected_values = {"strain_pct": values["strain_pct"]}
    selected_values.update({name: values[name] for name in enabled})
    source = _data_source(
        "invariant-evidence",
        columns,
        selected_values,
        role="invariant_evidence",
    )
    role = (
        "diagnostic"
        if all(decisions[frame.index].highest_role == "diagnostic" for frame in frames)
        else "si"
    )
    return FigureDefinition(
        figure_id="saxs.strain.invariant",
        technique="saxs",
        scope="series",
        category="diagnostic" if role == "diagnostic" else "supplementary",
        publication_role=role,
        title="Strain SAXS invariant evidence",
        layout=FigureLayoutDefinition(
            width_in=6.6,
            height_in=4.2,
            rows=1,
            columns=1,
            panels=(
                _panel(
                    "invariant",
                    0,
                    0,
                    _axis("invariant-x", "Strain", "%"),
                    _axis("invariant-y", "Relative metric", "a.u."),
                    title="Invariant evidence",
                    show_legend=True,
                    panel_label="(a)",
                ),
            ),
        ),
        data_sources=(source,),
        objects=tuple(
            _series_object(
                f"invariant-{column}",
                "invariant",
                source.source_id,
                "strain_pct",
                column,
                name=column,
                color=_COLORS[index % len(_COLORS)],
                marker="o",
            )
            for index, column in enumerate(enabled)
        ),
        recipe={
            "module": _MODULE,
            "function": "build_strain_figure_definitions",
            "inputs": {},
            "parameters": {
                "included_frame_indices": [frame.index for frame in frames],
                "eligibility_reasons": _eligibility_payload(frames, decisions),
                "Q_star_valid_required": True,
            },
        },
        style_profile="sci_default",
        display_order=105,
    )


def _orientation_values(
    engine: Any,
    frames: Sequence[SAXSFrameView],
) -> dict[str, list[float]]:
    f_values: list[float] = []
    anisotropy_values: list[float] = []
    for frame in frames:
        point = _series_point(engine, frame)
        anisotropy = getattr(frame.analysis, "anisotropy", None)
        f_values.append(
            _first_finite(
                getattr(point, "f_herman", np.nan),
                getattr(anisotropy, "f_herman", np.nan),
                _emitted_parameter(frame, "f_herman", "f_Herman", "orientation_f"),
            )
        )
        anisotropy_values.append(
            _first_finite(
                getattr(anisotropy, "anisotropy_index", np.nan),
                _emitted_parameter(frame, "anisotropy_index"),
            )
        )
    return {
        "strain_pct": [_finite_number(frame.condition) for frame in frames],
        "f_herman": f_values,
        "anisotropy_index": anisotropy_values,
    }


def _orientation_source(
    engine: Any,
    frames: Sequence[SAXSFrameView],
) -> tuple[FigureDataSourceDefinition | None, tuple[str, ...]]:
    values = _orientation_values(engine, frames)
    enabled = tuple(
        key
        for key in ("f_herman", "anisotropy_index")
        if any(np.isfinite(_finite_number(value)) for value in values[key])
    )
    if not enabled:
        return None, ()
    columns = [("strain_pct", "%", "float64")]
    columns.extend((key, "1", "float64") for key in enabled)
    selected_values = {"strain_pct": values["strain_pct"]}
    selected_values.update({key: values[key] for key in enabled})
    return (
        _data_source(
            "orientation-trends",
            columns,
            selected_values,
            role="orientation_evidence",
        ),
        enabled,
    )


def _downsample_detector(image: Any) -> _DetectorProjection | None:
    try:
        array = np.asarray(image, dtype=float)
    except (TypeError, ValueError):
        return None
    if array.ndim != 2 or array.size == 0:
        return None
    row_count, column_count = array.shape
    row_indices = np.linspace(
        0,
        row_count - 1,
        min(row_count, 256),
        dtype=int,
    )
    column_indices = np.linspace(
        0,
        column_count - 1,
        min(column_count, 256),
        dtype=int,
    )
    sampled = array[np.ix_(row_indices, column_indices)]
    x_grid, y_grid = np.meshgrid(column_indices, row_indices)
    finite = np.isfinite(sampled).reshape(-1)
    sampled_pixel_count = int(finite.size)
    retained_pixel_count = int(np.count_nonzero(finite))
    nonfinite_pixel_count = sampled_pixel_count - retained_pixel_count
    if retained_pixel_count == 0:
        return None
    sampled_values = sampled.reshape(-1)[finite]
    positive = np.clip(sampled_values, np.finfo(float).tiny, None)
    return _DetectorProjection(
        pixel_x=x_grid.reshape(-1)[finite],
        pixel_y=y_grid.reshape(-1)[finite],
        log_intensity=np.log10(positive),
        sampled_pixel_count=sampled_pixel_count,
        retained_pixel_count=retained_pixel_count,
        nonfinite_pixel_count=nonfinite_pixel_count,
    )


def _detector_evidence(
    selected_frames: Sequence[SAXSFrameView],
) -> tuple[tuple[_DetectorEvidence, ...], dict[str, str]]:
    evidence: list[_DetectorEvidence] = []
    failures: dict[str, str] = {}
    for frame in selected_frames:
        source_path = str(frame.source_path or "")
        if Path(source_path).suffix.lower() not in SUPPORTED_2D_EXTENSIONS:
            failures[str(frame.index)] = "source is not a supported detector image"
            continue
        try:
            image, _header = read_image(source_path)
        except Exception as exc:
            failures[str(frame.index)] = str(exc) or type(exc).__name__
            continue
        sampled = _downsample_detector(image)
        if sampled is None:
            failures[str(frame.index)] = (
                "detector image is empty, non-finite, or not two-dimensional"
            )
            continue
        pixel_x = sampled.pixel_x
        pixel_y = sampled.pixel_y
        log_intensity = sampled.log_intensity
        source = _data_source(
            f"detector-image-{frame.index:03d}",
            (
                ("pixel_x", "pixel", "int64"),
                ("pixel_y", "pixel", "int64"),
                ("log_intensity", "log10(counts)", "float64"),
            ),
            {
                "pixel_x": pixel_x.tolist(),
                "pixel_y": pixel_y.tolist(),
                "log_intensity": log_intensity.tolist(),
            },
            role="detector_image",
        )
        evidence.append(
            _DetectorEvidence(
                frame=frame,
                source=source,
                sampled_pixel_count=sampled.sampled_pixel_count,
                retained_pixel_count=sampled.retained_pixel_count,
                nonfinite_pixel_count=sampled.nonfinite_pixel_count,
            )
        )
    return tuple(evidence), failures


def _eligibility_payload(
    frames: Sequence[SAXSFrameView],
    decisions: Mapping[int, FigureEligibilityDecision],
) -> dict[str, list[str]]:
    return {str(frame.index): list(decisions[frame.index].reasons) for frame in frames}


def _main_recipe(
    frames: Sequence[SAXSFrameView],
    decisions: Mapping[int, FigureEligibilityDecision],
    selection: RepresentativeFrameSelection,
    detector_failures: Mapping[str, str],
    detector_projection_quality: Mapping[str, Mapping[str, Any]],
    profile_projection_quality: Mapping[str, Mapping[str, Any]],
    *,
    detector_capable: bool,
    heatmap_render_transform: str,
) -> dict[str, Any]:
    frame_by_index = {frame.index: frame for frame in frames}
    recipe = {
        "module": _MODULE,
        "function": "build_strain_figure_definitions",
        "condition_axis": "strain_pct",
        "condition_label": "Strain",
        "condition_unit": "%",
        "representative_indices": list(selection.indices),
        "representative_reasons": dict(selection.reasons),
        "representative_selection_source": selection.source,
        "manual_override": selection.source == "manual_override",
        "source_capability": "detector_2d" if detector_capable else "profile_1d",
        "source_path_by_frame": {str(frame.index): frame.source_path for frame in frames},
        "inputs": {
            "source_paths": [frame.source_path for frame in frames],
        },
        "parameters": {
            "condition_axis": "strain_pct",
            "included_frame_indices": [frame.index for frame in frames],
            "representative_indices": list(selection.indices),
            "representative_reasons": {
                str(index): reason for index, reason in selection.reasons.items()
            },
            "representative_source": selection.source,
            "eligibility_reasons": _eligibility_payload(frames, decisions),
            "heatmap_render_transform": heatmap_render_transform,
        },
    }
    if not detector_capable:
        recipe["parameters"]["profile_projection_quality"] = {
            str(index): dict(quality)
            for index, quality in profile_projection_quality.items()
        }
    if detector_capable:
        recipe["selected_detector_source_paths"] = {
            str(index): frame_by_index[index].source_path
            for index in selection.indices
        }
        recipe["parameters"]["detector_failures"] = dict(detector_failures)
        recipe["parameters"]["detector_projection_quality"] = {
            str(index): dict(quality)
            for index, quality in detector_projection_quality.items()
        }
    return recipe


def _main_definition(
    engine: Any,
    frames: Sequence[SAXSFrameView],
    decisions: Mapping[int, FigureEligibilityDecision],
    *,
    publication_role: str,
    detector_capable: bool,
    representative_indices: Sequence[int] | None,
) -> FigureDefinition:
    selection = _select_representatives(engine, frames, representative_indices)
    frame_by_index = {frame.index: frame for frame in frames}
    selected_frames = tuple(frame_by_index[index] for index in selection.indices)
    detector_evidence: tuple[_DetectorEvidence, ...] = ()
    detector_failures: dict[str, str] = {}
    if detector_capable:
        detector_evidence, detector_failures = _detector_evidence(selected_frames)
    detector_projection_quality = {
        str(item.frame.index): item.projection_quality for item in detector_evidence
    }

    sources: list[FigureDataSourceDefinition] = []
    panels: list[PanelDefinition] = []
    objects: list[dict[str, Any]] = []
    auxiliary: list[tuple[PanelDefinition, tuple[dict[str, Any], ...]]] = []
    profile_projection_quality: dict[str, dict[str, Any]] = {}

    if detector_capable:
        for ordinal, item in enumerate(detector_evidence):
            panel_id = f"detector-{item.frame.index:03d}"
            sources.append(item.source)
            panels.append(
                _panel(
                    panel_id,
                    0,
                    ordinal * 2,
                    _axis(f"{panel_id}-x", "Detector x", "pixel"),
                    _axis(f"{panel_id}-y", "Detector y", "pixel", reversed=True),
                    title=f"{_finite_number(item.frame.condition):g}% strain",
                    column_span=2,
                )
            )
            objects.append(
                _heatmap_object(
                    f"detector-pattern-{item.frame.index:03d}",
                    panel_id,
                    item.source.source_id,
                    "pixel_x",
                    "pixel_y",
                    "log_intensity",
                    cmap="magma",
                    colorbar_label="log10(counts)",
                )
            )
    else:
        profile_objects: list[dict[str, Any]] = []
        for ordinal, frame in enumerate(selected_frames):
            source = _profile_source(
                engine,
                frame,
                source_id=f"representative-profile-{frame.index:03d}",
                prefer_equatorial=True,
                include_sectors=False,
            )
            if source is None:
                continue
            quality = _profile_projection_quality(frame)
            if quality is not None:
                profile_projection_quality[str(frame.index)] = quality
            sources.append(source)
            profile_objects.append(
                _series_object(
                    f"representative-profile-{frame.index:03d}",
                    "profiles",
                    source.source_id,
                    "q_nm_inv",
                    "intensity",
                    name=f"{_finite_number(frame.condition):g}%",
                    color=_COLORS[ordinal % len(_COLORS)],
                )
            )
        if profile_objects:
            panels.append(
                _panel(
                    "profiles",
                    0,
                    0,
                    _axis("profiles-x", "q", "nm^-1", scale="log"),
                    _axis("profiles-y", "Intensity", "a.u.", scale="log"),
                    title="Representative 1D/equatorial profiles",
                    column_span=2,
                    show_legend=True,
                )
            )
            objects.extend(profile_objects)

    q_strain, heatmap_render_transform = _q_strain_source(frames)
    if q_strain is not None:
        sources.append(q_strain)
        auxiliary.append(
            (
                _panel(
                    "q-strain",
                    0,
                    0,
                    _axis("q-strain-x", "q", "nm^-1"),
                    _axis("q-strain-y", "Strain", "%"),
                    title="Scattering evolution",
                ),
                (
                    _heatmap_object(
                        "q-strain-map",
                        "q-strain",
                        q_strain.source_id,
                        "q_nm_inv",
                        "strain_pct",
                        "log_intensity",
                        cmap="viridis",
                        colorbar_label="log10(Intensity)",
                    ),
                ),
            )
        )

    morphology = _morphology_source(frames)
    morphology_objects = tuple(
        _series_object(
            f"morphology-{column}",
            "morphology",
            morphology.source_id,
            "strain_pct",
            column,
            name=label,
            color=color,
            marker="o",
        )
        for column, label, color in (
            ("L_nm", "L", _COLORS[0]),
            ("lc_nm", "lc", _COLORS[1]),
            ("la_nm", "la", _COLORS[2]),
        )
        if trend_panel_eligible(morphology.values[column])
    )
    if morphology_objects:
        sources.append(morphology)
        auxiliary.append(
            (
                _panel(
                    "morphology",
                    0,
                    0,
                    _axis("morphology-x", "Strain", "%"),
                    _axis("morphology-y", "Length", "nm"),
                    title="Lamellar morphology",
                    show_legend=True,
                ),
                morphology_objects,
            )
        )

    metrics, metric_columns = _metrics_source(engine, frames)
    if metrics is not None:
        sources.append(metrics)
        metric_objects = tuple(
            _series_object(
                f"metric-{column}",
                "metrics",
                metrics.source_id,
                "strain_pct",
                column,
                name=column,
                color=_COLORS[index % len(_COLORS)],
                marker="o",
            )
            for index, column in enumerate(metric_columns)
        )
        auxiliary.append(
            (
                _panel(
                    "metrics",
                    0,
                    0,
                    _axis("metrics-x", "Strain", "%"),
                    _axis("metrics-y", "Relative metric", "a.u."),
                    title="Invariant and void evidence",
                    show_legend=True,
                ),
                metric_objects,
            )
        )

    if detector_capable:
        orientation, orientation_columns = _orientation_source(engine, frames)
        if orientation is not None:
            sources.append(orientation)
            orientation_objects = tuple(
                _series_object(
                    f"orientation-{column}",
                    "orientation",
                    orientation.source_id,
                    "strain_pct",
                    column,
                    name=column,
                    color=_COLORS[index % len(_COLORS)],
                    marker="o",
                )
                for index, column in enumerate(orientation_columns)
            )
            auxiliary.append(
                (
                    _panel(
                        "orientation",
                        0,
                        0,
                        _axis("orientation-x", "Strain", "%"),
                        _axis("orientation-y", "Orientation metric", "1"),
                        title="Existing anisotropy evidence",
                        show_legend=True,
                    ),
                    orientation_objects,
                )
            )

    if detector_capable:
        base_row = 1 if detector_evidence else 0
        if len(auxiliary) <= 3:
            span = 6 // max(1, len(auxiliary))
            for index, (panel, panel_objects) in enumerate(auxiliary):
                panels.append(
                    PanelDefinition(
                        **{
                            **panel.__dict__,
                            "row": base_row,
                            "column": index * span,
                            "column_span": span,
                        }
                    )
                )
                objects.extend(panel_objects)
            rows = base_row + (1 if auxiliary else 0)
        else:
            for index, (panel, panel_objects) in enumerate(auxiliary):
                panels.append(
                    PanelDefinition(
                        **{
                            **panel.__dict__,
                            "row": base_row + index // 2,
                            "column": (index % 2) * 3,
                            "column_span": 3,
                        }
                    )
                )
                objects.extend(panel_objects)
            rows = base_row + 2
        columns = 6
        width, height = 10.0, max(5.4, rows * 2.6)
        figure_id = "saxs.strain.evolution.2d"
        title = "Strain SAXS evolution (2D detector series)"
    else:
        base_row = 1 if panels else 0
        for index, (panel, panel_objects) in enumerate(auxiliary[:2]):
            panels.append(
                PanelDefinition(
                    **{
                        **panel.__dict__,
                        "row": base_row,
                        "column": index,
                    }
                )
            )
            objects.extend(panel_objects)
        for offset, (panel, panel_objects) in enumerate(auxiliary[2:]):
            panels.append(
                PanelDefinition(
                    **{
                        **panel.__dict__,
                        "row": base_row + 1 + offset,
                        "column": 0,
                        "column_span": 2,
                    }
                )
            )
            objects.extend(panel_objects)
        rows = base_row + (1 if auxiliary[:2] else 0) + max(0, len(auxiliary) - 2)
        columns = 2
        width, height = 7.2, max(5.2, rows * 2.35)
        figure_id = "saxs.strain.evolution.1d"
        title = "Strain SAXS evolution (1D/equatorial series)"

    labelled_panels = tuple(
        PanelDefinition(
            **{
                **panel.__dict__,
                "panel_label": f"({chr(97 + index)})",
            }
        )
        for index, panel in enumerate(panels)
    )
    return FigureDefinition(
        figure_id=figure_id,
        technique="saxs",
        scope="series",
        category={
            "main": "series_overview",
            "si": "supplementary",
            "diagnostic": "diagnostic",
        }[publication_role],
        publication_role=publication_role,
        title=title,
        layout=FigureLayoutDefinition(
            width_in=width,
            height_in=height,
            rows=max(1, rows),
            columns=columns,
            panels=labelled_panels,
            horizontal_spacing=0.3,
            vertical_spacing=0.35,
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe=_main_recipe(
            frames,
            decisions,
            selection,
            detector_failures,
            detector_projection_quality,
            profile_projection_quality,
            detector_capable=detector_capable,
            heatmap_render_transform=heatmap_render_transform,
        ),
        style_profile="sci_default",
        display_order=10,
    )


def _sequence_definition(
    engine: Any,
    frames: Sequence[SAXSFrameView],
    decisions: Mapping[int, FigureEligibilityDecision],
    *,
    detector_capable: bool,
    diagnostic: bool,
) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    profile_projection_quality: dict[str, dict[str, Any]] = {}
    for ordinal, frame in enumerate(frames):
        source = _profile_source(
            engine,
            frame,
            source_id=f"sequence-profile-{frame.index:03d}",
            prefer_equatorial=detector_capable,
            include_sectors=detector_capable,
        )
        if source is None:
            continue
        quality = _profile_projection_quality(frame)
        if quality is not None:
            profile_projection_quality[str(frame.index)] = quality
        sources.append(source)
        objects.append(
            _series_object(
                f"sequence-profile-{frame.index:03d}",
                "sequence",
                source.source_id,
                "q_nm_inv",
                "intensity",
                name=f"{_finite_number(frame.condition):g}%",
                color=_COLORS[ordinal % len(_COLORS)],
            )
        )
        source_columns = {column.name for column in source.columns}
        for suffix, column, line_style_color in (
            ("equatorial", "equatorial_intensity", _COLORS[3]),
            ("meridional", "meridional_intensity", _COLORS[5]),
        ):
            if column in source_columns:
                objects.append(
                    _series_object(
                        f"sequence-{suffix}-{frame.index:03d}",
                        "sequence",
                        source.source_id,
                        "q_nm_inv",
                        column,
                        name=f"{frame.index}: {suffix}",
                        color=line_style_color,
                    )
                )
    if not sources:
        return None
    publication_role = "diagnostic" if diagnostic else "si"
    figure_id = (
        "saxs.strain.sequence.diagnostic"
        if diagnostic
        else f"saxs.strain.sequence.{'2d' if detector_capable else '1d'}"
    )
    parameters: dict[str, Any] = {
        "included_frame_indices": [frame.index for frame in frames],
        "eligibility_reasons": _eligibility_payload(frames, decisions),
        **({"detector_images_loaded": False} if detector_capable else {}),
    }
    if not detector_capable:
        parameters["profile_projection_quality"] = {
            str(index): dict(quality)
            for index, quality in profile_projection_quality.items()
        }
    return FigureDefinition(
        figure_id=figure_id,
        technique="saxs",
        scope="series",
        category="diagnostic" if diagnostic else "supplementary",
        publication_role=publication_role,
        title=(
            "Strain SAXS excluded-frame diagnostics"
            if diagnostic
            else "Full strain SAXS profile sequence"
        ),
        layout=FigureLayoutDefinition(
            width_in=7.2,
            height_in=4.8,
            rows=1,
            columns=1,
            panels=(
                _panel(
                    "sequence",
                    0,
                    0,
                    _axis("sequence-x", "q", "nm^-1", scale="log"),
                    _axis("sequence-y", "Intensity", "a.u.", scale="log"),
                    title="Full sequence" if not diagnostic else "Excluded frames",
                    show_legend=True,
                    panel_label="(a)",
                ),
            ),
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe={
            "module": _MODULE,
            "function": "build_strain_figure_definitions",
            "inputs": {"source_paths": [frame.source_path for frame in frames]},
            "parameters": parameters,
        },
        style_profile="sci_default",
        display_order=200 if diagnostic else 100,
    )


def _analysis_trace(
    frame: SAXSFrameView,
    attribute: str,
    x_key: str,
    y_key: str,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    payload = getattr(frame.analysis, attribute, None)
    if not isinstance(payload, Mapping):
        return (), ()
    try:
        x_values = _coerce_numeric_array(payload.get(x_key, ()))
        y_values = _coerce_numeric_array(payload.get(y_key, ()))
    except (TypeError, ValueError):
        return (), ()
    count = min(x_values.size, y_values.size)
    finite = np.isfinite(x_values[:count]) & np.isfinite(y_values[:count])
    return tuple(x_values[:count][finite]), tuple(y_values[:count][finite])


def _trace_definition(
    frames: Sequence[SAXSFrameView],
    decisions: Mapping[int, FigureEligibilityDecision],
    *,
    figure_id: str,
    attribute: str,
    x_key: str,
    y_key: str,
    x_label: str,
    x_unit: str,
    y_label: str,
    display_order: int,
) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for ordinal, frame in enumerate(frames):
        x_values, y_values = _analysis_trace(frame, attribute, x_key, y_key)
        if not x_values:
            continue
        source_id = f"{attribute}-trace-{frame.index:03d}"
        sources.append(
            _data_source(
                source_id,
                (("x", x_unit, "float64"), ("y", "a.u.", "float64")),
                {"x": x_values, "y": y_values},
                role=f"{attribute}_evidence",
            )
        )
        objects.append(
            _series_object(
                source_id,
                "trace",
                source_id,
                "x",
                "y",
                name=f"{_finite_number(frame.condition):g}%",
                color=_COLORS[ordinal % len(_COLORS)],
            )
        )
    if not sources:
        return None
    role = (
        "diagnostic"
        if all(decisions[frame.index].highest_role == "diagnostic" for frame in frames)
        else "si"
    )
    return FigureDefinition(
        figure_id=figure_id,
        technique="saxs",
        scope="series",
        category="diagnostic" if role == "diagnostic" else "supplementary",
        publication_role=role,
        title=f"Strain SAXS {attribute} evidence",
        layout=FigureLayoutDefinition(
            width_in=6.6,
            height_in=4.2,
            rows=1,
            columns=1,
            panels=(
                _panel(
                    "trace",
                    0,
                    0,
                    _axis("trace-x", x_label, x_unit),
                    _axis("trace-y", y_label, "a.u."),
                    title=f"{attribute.capitalize()} traces",
                    show_legend=True,
                    panel_label="(a)",
                ),
            ),
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe={
            "module": _MODULE,
            "function": "build_strain_figure_definitions",
            "inputs": {},
            "parameters": {
                "included_frame_indices": [
                    int(source.source_id.rsplit("-", 1)[1]) for source in sources
                ],
                "eligibility_reasons": _eligibility_payload(frames, decisions),
            },
        },
        style_profile="sci_default",
        display_order=display_order,
    )


def _azimuthal_definition(
    frames: Sequence[SAXSFrameView],
    decisions: Mapping[int, FigureEligibilityDecision],
) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    azimuthal_projection_quality: dict[str, dict[str, Any]] = {}
    for ordinal, frame in enumerate(frames):
        anisotropy = getattr(frame.analysis, "anisotropy", None)
        try:
            chi = np.asarray(getattr(anisotropy, "azimuthal_chi", ()), dtype=float).reshape(-1)
            intensity = np.asarray(
                getattr(anisotropy, "azimuthal_I", ()),
                dtype=float,
            ).reshape(-1)
        except (TypeError, ValueError):
            continue
        count = min(chi.size, intensity.size)
        finite = np.isfinite(chi[:count]) & np.isfinite(intensity[:count])
        if not np.any(finite):
            continue
        retained_count = int(np.count_nonzero(finite))
        nonfinite_count = count - retained_count
        azimuthal_projection_quality[str(frame.index)] = {
            "input_pair_count": int(count),
            "retained_pair_count": retained_count,
            "nonfinite_pair_count": int(nonfinite_count),
            "status": "partial_nonfinite" if nonfinite_count else "complete",
        }
        source_id = f"azimuthal-trace-{frame.index:03d}"
        sources.append(
            _data_source(
                source_id,
                (("chi_rad", "rad", "float64"), ("intensity", "a.u.", "float64")),
                {"chi_rad": chi[:count][finite], "intensity": intensity[:count][finite]},
                role="azimuthal_evidence",
            )
        )
        objects.append(
            _series_object(
                source_id,
                "azimuthal",
                source_id,
                "chi_rad",
                "intensity",
                name=f"{_finite_number(frame.condition):g}%",
                color=_COLORS[ordinal % len(_COLORS)],
            )
        )
    if not sources:
        return None
    role = (
        "diagnostic"
        if all(decisions[frame.index].highest_role == "diagnostic" for frame in frames)
        else "si"
    )
    return FigureDefinition(
        figure_id="saxs.strain.azimuthal",
        technique="saxs",
        scope="series",
        category="diagnostic" if role == "diagnostic" else "supplementary",
        publication_role=role,
        title="Strain SAXS azimuthal traces",
        layout=FigureLayoutDefinition(
            width_in=6.6,
            height_in=4.2,
            rows=1,
            columns=1,
            panels=(
                _panel(
                    "azimuthal",
                    0,
                    0,
                    _axis("azimuthal-x", "Azimuth", "rad"),
                    _axis("azimuthal-y", "Intensity", "a.u."),
                    title="Existing azimuthal evidence",
                    show_legend=True,
                    panel_label="(a)",
                ),
            ),
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe={
            "module": _MODULE,
            "function": "build_strain_figure_definitions",
            "inputs": {},
            "parameters": {
                "included_frame_indices": [
                    int(source.source_id.rsplit("-", 1)[1]) for source in sources
                ],
                "eligibility_reasons": _eligibility_payload(frames, decisions),
                "azimuthal_projection_quality": dict(azimuthal_projection_quality),
            },
        },
        style_profile="sci_default",
        display_order=130,
    )


def _phase_definition(
    engine: Any,
    frames: Sequence[SAXSFrameView],
    decisions: Mapping[int, FigureEligibilityDecision],
) -> FigureDefinition | None:
    strain_values: list[float] = []
    phase_values: list[str] = []
    confidence_values: list[float] = []
    for frame in frames:
        point = _series_point(engine, frame)
        phase = getattr(point, "phase", None)
        phase_name = str(getattr(phase, "name", "") or frame.parameters.get("phase_name", ""))
        if not phase_name:
            continue
        strain_values.append(_finite_number(frame.condition))
        phase_values.append(phase_name.lower())
        confidence_values.append(
            _first_finite(
                getattr(point, "confidence", np.nan),
                frame.parameters.get("phase_support_score", np.nan),
            )
        )
    if not strain_values:
        return None
    source = _data_source(
        "phase-evidence",
        (
            ("strain_pct", "%", "float64"),
            ("phase", "", "string"),
            ("confidence", "1", "float64"),
        ),
        {
            "strain_pct": strain_values,
            "phase": phase_values,
            "confidence": confidence_values,
        },
        role="phase_evidence",
    )
    role = (
        "diagnostic"
        if all(decisions[frame.index].highest_role == "diagnostic" for frame in frames)
        else "si"
    )
    return FigureDefinition(
        figure_id="saxs.strain.phase-evidence",
        technique="saxs",
        scope="series",
        category="diagnostic" if role == "diagnostic" else "supplementary",
        publication_role=role,
        title="Strain phase evidence",
        layout=FigureLayoutDefinition(
            width_in=6.6,
            height_in=3.8,
            rows=1,
            columns=1,
            panels=(
                _panel(
                    "phase",
                    0,
                    0,
                    _axis("phase-x", "Strain", "%"),
                    _axis("phase-y", "Phase", ""),
                    title="Emitted phase classification",
                    panel_label="(a)",
                ),
            ),
        ),
        data_sources=(source,),
        objects=(
            _series_object(
                "phase-points",
                "phase",
                source.source_id,
                "strain_pct",
                "phase",
                color=_COLORS[0],
                marker="o",
                chart_kind="scatter",
            ),
        ),
        recipe={
            "module": _MODULE,
            "function": "build_strain_figure_definitions",
            "inputs": {},
            "parameters": {
                "included_frame_indices": [frame.index for frame in frames],
                "eligibility_reasons": _eligibility_payload(frames, decisions),
            },
        },
        style_profile="sci_default",
        display_order=140,
    )


def _low_q_definition(
    frames: Sequence[SAXSFrameView],
    decisions: Mapping[int, FigureEligibilityDecision],
) -> FigureDefinition | None:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for ordinal, frame in enumerate(frames):
        q_values, intensity_values = _profile_values(frame)
        if len(q_values) < 3:
            continue
        q_array = np.asarray(q_values)
        intensity_array = np.asarray(intensity_values)
        count = max(3, int(np.ceil(q_array.size * 0.25)))
        source_id = f"low-q-profile-{frame.index:03d}"
        sources.append(
            _data_source(
                source_id,
                (("q_nm_inv", "nm^-1", "float64"), ("intensity", "a.u.", "float64")),
                {"q_nm_inv": q_array[:count], "intensity": intensity_array[:count]},
                role="low_q_evidence",
            )
        )
        objects.append(
            _series_object(
                source_id,
                "low-q",
                source_id,
                "q_nm_inv",
                "intensity",
                name=f"{_finite_number(frame.condition):g}%",
                color=_COLORS[ordinal % len(_COLORS)],
            )
        )
    if not sources:
        return None
    return FigureDefinition(
        figure_id="saxs.strain.low-q.diagnostic",
        technique="saxs",
        scope="series",
        category="diagnostic",
        publication_role="diagnostic",
        title="Strain SAXS low-q diagnostics",
        layout=FigureLayoutDefinition(
            width_in=6.6,
            height_in=4.2,
            rows=1,
            columns=1,
            panels=(
                _panel(
                    "low-q",
                    0,
                    0,
                    _axis("low-q-x", "q", "nm^-1", scale="log"),
                    _axis("low-q-y", "Intensity", "a.u.", scale="log"),
                    title="Measured low-q region",
                    show_legend=True,
                    panel_label="(a)",
                ),
            ),
        ),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe={
            "module": _MODULE,
            "function": "build_strain_figure_definitions",
            "inputs": {},
            "parameters": {
                "included_frame_indices": [
                    int(source.source_id.rsplit("-", 1)[1]) for source in sources
                ],
                "eligibility_reasons": _eligibility_payload(frames, decisions),
            },
        },
        style_profile="sci_default",
        display_order=220,
    )


def build_strain_figure_definitions(
    engine: Any,
    *,
    representative_indices: Sequence[int] | None = None,
) -> tuple[FigureDefinition, ...]:
    """Build deterministic strain publication/SI/diagnostic definitions."""

    frames = frame_views_from_engine(engine)
    if not frames:
        return ()
    decisions = {frame.index: classify_frame_eligibility(frame) for frame in frames}
    main_frames = tuple(frame for frame in frames if decisions[frame.index].highest_role == "main")
    si_frames = tuple(frame for frame in frames if decisions[frame.index].highest_role == "si")
    diagnostic_frames = tuple(
        frame for frame in frames if decisions[frame.index].highest_role == "diagnostic"
    )
    if main_frames:
        pack_frames = main_frames
        pack_role = "main"
    elif si_frames:
        pack_frames = si_frames
        pack_role = "si"
    else:
        pack_frames = diagnostic_frames
        pack_role = "diagnostic"

    detector_capable = _detector_capable(engine)
    definitions: list[FigureDefinition] = [
        _main_definition(
            engine,
            pack_frames,
            decisions,
            publication_role=pack_role,
            detector_capable=detector_capable,
            representative_indices=representative_indices,
        )
    ]

    non_diagnostic_frames = tuple(
        frame for frame in frames if decisions[frame.index].highest_role != "diagnostic"
    )
    sequence = _sequence_definition(
        engine,
        non_diagnostic_frames,
        decisions,
        detector_capable=detector_capable,
        diagnostic=False,
    )
    if sequence is not None:
        definitions.append(sequence)
    diagnostic = _sequence_definition(
        engine,
        diagnostic_frames,
        decisions,
        detector_capable=detector_capable,
        diagnostic=True,
    )
    if diagnostic is not None:
        definitions.append(diagnostic)

    evidence_frames = non_diagnostic_frames or diagnostic_frames
    for definition in (
        _invariant_definition(engine, evidence_frames, decisions),
        _trace_definition(
            evidence_frames,
            decisions,
            figure_id="saxs.strain.correlation",
            attribute="correlation",
            x_key="r",
            y_key="gamma",
            x_label="r",
            x_unit="nm",
            y_label="Correlation",
            display_order=110,
        ),
        _trace_definition(
            evidence_frames,
            decisions,
            figure_id="saxs.strain.idf",
            attribute="idf",
            x_key="r_idf",
            y_key="idf",
            x_label="r",
            x_unit="nm",
            y_label="IDF",
            display_order=120,
        ),
        _azimuthal_definition(evidence_frames, decisions) if detector_capable else None,
        _phase_definition(engine, evidence_frames, decisions),
        _low_q_definition(evidence_frames, decisions),
    ):
        if definition is not None:
            definitions.append(definition)

    ordered = tuple(sorted(definitions, key=lambda item: (item.display_order, item.figure_id)))
    final_definitions = tuple(_ensure_display_order(item) for item in ordered)
    return attach_saxs_figure_evidence(
        final_definitions,
        frames,
        mode="strain",
        series=getattr(engine, "_strain_result", None),
        ai_rescue=copy_saxs_ai_rescue_evidence(
            engine,
            getattr(engine, "result", None),
        ),
        acceptance_audit=existing_saxs_acceptance_audit(engine),
    )


def _ensure_display_order(definition: FigureDefinition) -> FigureDefinition:
    recipe = dict(definition.recipe)
    parameters = dict(recipe.get("parameters", {}))
    parameters.setdefault("display_order", int(definition.display_order))
    recipe["parameters"] = parameters
    return definition.__class__(**{**definition.__dict__, "recipe": recipe})


build_strain_saxs_figure_definitions = build_strain_figure_definitions


__all__ = [
    "build_strain_figure_definitions",
    "build_strain_saxs_figure_definitions",
]
