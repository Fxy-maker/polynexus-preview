"""Scientific FigureDefinition providers for SAXS workflows."""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

import numpy as np

from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureEligibilityDecision,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)

from .saxs_temperature import TempSeriesResult
from .figure_common import SAXSFrameView, frame_views_from_engine
from .figure_eligibility import classify_frame_eligibility
from .figure_selection import resolve_saxs_figure_mode


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


def build_saxs_figure_definitions(engine_state) -> tuple[FigureDefinition, ...]:
    """Build portable SAXS definitions for the engine's active analysis state."""

    mode = resolve_saxs_figure_mode(engine_state)
    if mode.mode in {"unsupported", "incomplete"}:
        return ()

    temperature_result = getattr(engine_state, "_temperature_result", None)
    if mode.mode == "temperature" and temperature_result is not None:
        evidence_frames = frame_views_from_engine(engine_state)
        definitions = build_saxs_temperature_definitions(
            temperature_result,
            tuple(getattr(engine_state, "_q_list", ())),
            tuple(getattr(engine_state, "_I_list", ())),
            evidence_frames=evidence_frames,
        )
        return _apply_publication_roles(
            engine_state,
            definitions,
            evidence_frames=evidence_frames,
        )

    series_kind = "strain" if mode.mode == "strain" else "static"
    frames = _non_temperature_frames(engine_state, series_kind)
    definitions = [
        _build_scattering_frame(
            index=index,
            series_kind=series_kind,
            label=label,
            q=q,
            intensity=intensity,
        )
        for index, (q, intensity, label) in enumerate(frames, start=1)
    ]
    if len(frames) > 1:
        definitions.append(_build_series_waterfall(series_kind, frames))
    return _apply_publication_roles(engine_state, tuple(definitions))


def _apply_publication_roles(
    engine_state,
    definitions: Sequence[FigureDefinition],
    *,
    evidence_frames: Sequence[SAXSFrameView] | None = None,
) -> tuple[FigureDefinition, ...]:
    """Carry emitted frame evidence into definition metadata without reanalysis."""

    views = tuple(
        frame_views_from_engine(engine_state)
        if evidence_frames is None
        else evidence_frames
    )
    if not views:
        return tuple(definitions)
    decisions = {
        view.index: classify_frame_eligibility(view)
        for view in views
    }
    frame_roles = {
        index: decision.highest_role
        for index, decision in decisions.items()
    }
    aggregate_role = _aggregate_publication_role(frame_roles.values())
    frame_reasons = {
        index: "|".join(decision.reasons)
        for index, decision in decisions.items()
    }
    annotated: list[FigureDefinition] = []
    for definition in definitions:
        role = (
            definition.publication_role
            if definition.scope != "frame" and definition.publication_role != "si"
            else aggregate_role
        )
        evidence = dict(definition.recipe.get("evidence", {}))
        if definition.scope == "frame":
            suffix = definition.figure_id.rsplit(".", 1)[-1]
            if suffix.isdigit():
                frame_index = int(suffix) - 1
                role = frame_roles.get(frame_index, aggregate_role)
                evidence.update(
                    {
                        "frame_indices": [frame_index],
                        "roles": {frame_index: role},
                        "reasons": {
                            frame_index: frame_reasons.get(
                                frame_index, "evidence_missing"
                            )
                        },
                    }
                )
        else:
            evidence.setdefault("included_frame_indices", list(frame_roles))
            evidence.setdefault("omitted_frame_indices", [])
            evidence.update(
                {
                    "frame_indices": list(frame_roles),
                    "roles": dict(frame_roles),
                    "reasons": dict(frame_reasons),
                }
            )
        recipe = dict(definition.recipe)
        recipe["evidence"] = evidence
        annotated.append(
            replace(definition, publication_role=role, recipe=recipe)
        )
    return tuple(annotated)


def _aggregate_publication_role(roles: Sequence[str]) -> str:
    roles = tuple(roles)
    if roles and all(role == "main" for role in roles):
        return "main"
    if "si" in roles or not roles:
        return "si"
    return "diagnostic"


def _evidence_plan(
    evidence_frames: Sequence[SAXSFrameView],
    frame_count: int,
) -> tuple[dict[int, FigureEligibilityDecision], tuple[int, ...], dict[int, str]]:
    decisions = {
        frame.index: classify_frame_eligibility(frame)
        for frame in evidence_frames
        if 0 <= frame.index < frame_count
    }
    main_indices = tuple(
        index
        for index in range(frame_count)
        if decisions.get(index, FigureEligibilityDecision("si", ("evidence_missing",))).highest_role
        == "main"
    )
    reasons = {
        index: "|".join(
            decisions[index].reasons
            if index in decisions
            else ("evidence_missing",)
        )
        for index in range(frame_count)
        if decisions.get(index, FigureEligibilityDecision("si", ("evidence_missing",))).highest_role
        != "main"
    }
    return decisions, main_indices, reasons


def build_saxs_temperature_definitions(
    result: TempSeriesResult,
    q_values: Sequence[np.ndarray],
    intensities: Sequence[np.ndarray],
    *,
    evidence_frames: Sequence[SAXSFrameView] = (),
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
        frame_count = len(cleaned_frames)
        _decisions, main_indices, omission_reasons = _evidence_plan(
            evidence_frames,
            frame_count,
        )
        selected_indices = main_indices or tuple(range(frame_count))
        evidence = {
            "included_frame_indices": list(selected_indices),
            "omitted_frame_indices": [
                index for index in range(frame_count) if index not in selected_indices
            ],
            "omission_reasons": omission_reasons,
        }
        all_roles = tuple(
            _decisions[index].highest_role
            if index in _decisions
            else "si"
            for index in range(frame_count)
        )
        waterfall_role = _aggregate_publication_role(all_roles)
        summary_role = "main" if main_indices else waterfall_role
        definitions.append(
            _build_temperature_waterfall(
                temperatures,
                cleaned_frames,
                publication_role=waterfall_role,
                evidence=evidence,
            )
        )
        definitions.extend(
            _build_temperature_summary_definitions(
                result,
                cleaned_frames,
                included_indices=selected_indices,
                publication_role=summary_role,
                evidence=evidence,
            )
        )
    return tuple(definitions)


def _non_temperature_frames(
    engine_state,
    series_kind: str,
) -> tuple[tuple[np.ndarray, np.ndarray, str], ...]:
    if series_kind == "static":
        analyzed = tuple(getattr(engine_state, "_batch_results", ()) or ())
        if not analyzed:
            single = getattr(engine_state, "_analysis", None)
            analyzed = (single,) if single is not None else ()
        frames = _frames_from_analyzed_results(analyzed)
        if frames:
            return frames

    q_values = tuple(getattr(engine_state, "_q_list", ()) or ())
    intensities = tuple(getattr(engine_state, "_I_list", ()) or ())
    if len(q_values) != len(intensities):
        raise ValueError("SAXS frame counts differ")
    condition_values = _frame_condition_values(
        engine_state,
        series_kind,
        len(q_values),
    )
    frames: list[tuple[np.ndarray, np.ndarray, str]] = []
    for index, (q, intensity) in enumerate(zip(q_values, intensities), start=1):
        clean_q, clean_intensity = _clean_frame(q, intensity, index)
        frames.append(
            (
                clean_q,
                clean_intensity,
                _frame_label(series_kind, condition_values[index - 1], index),
            )
        )
    return tuple(frames)


def _frames_from_analyzed_results(
    results: Sequence[object],
) -> tuple[tuple[np.ndarray, np.ndarray, str], ...]:
    frames: list[tuple[np.ndarray, np.ndarray, str]] = []
    for index, result in enumerate(results, start=1):
        q = getattr(result, "q", None)
        intensity = getattr(result, "I_smooth", None)
        if intensity is None or np.asarray(intensity).size != np.asarray(q).size:
            intensity = getattr(result, "I", None)
        if q is None or intensity is None:
            continue
        clean_q, clean_intensity = _clean_frame(q, intensity, index)
        label = str(getattr(result, "label", "") or "").strip()
        if not label:
            label = _frame_label(
                "static",
                getattr(result, "condition_value", np.nan),
                index,
            )
        frames.append((clean_q, clean_intensity, label))
    return tuple(frames)


def _frame_condition_values(
    engine_state,
    series_kind: str,
    frame_count: int,
) -> tuple[float, ...]:
    values = None
    if series_kind == "strain":
        strain_result = getattr(engine_state, "_strain_result", None)
        values = getattr(strain_result, "strains", None)
    if values is None or np.asarray(values).size != frame_count:
        values = getattr(engine_state, "_conditions", ())
    array = np.ravel(np.asarray(values, dtype=float))
    if len(array) != frame_count:
        return tuple(float("nan") for _index in range(frame_count))
    return tuple(float(value) for value in array)


def _frame_label(series_kind: str, condition_value: float, index: int) -> str:
    try:
        value = float(condition_value)
    except (TypeError, ValueError):
        value = np.nan
    if np.isfinite(value):
        if series_kind == "strain":
            return f"{value:g}% strain"
        return f"Condition {value:g}"
    return f"Frame {index}"


def _build_scattering_frame(
    *,
    index: int,
    series_kind: str,
    label: str,
    q: np.ndarray,
    intensity: np.ndarray,
) -> FigureDefinition:
    source_id = "scattering-data"
    return FigureDefinition(
        figure_id=f"saxs.frame.{series_kind}.scattering.{index:03d}",
        technique="saxs",
        scope="frame",
        category="per_frame",
        title=f"SAXS Scattering - {label}",
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
                "name": label,
                "data_ref": source_id,
                "x_column": "q_nm1",
                "y_column": "intensity_au",
                "style": {"color": "#222222", "line_width": 0.8},
            },
        ),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_provider",
            "function": "build_saxs_figure_definitions",
            "inputs": {"frame_label": label},
            "parameters": {
                "frame_index": index,
                "series_kind": series_kind,
                "figure_kind": "scattering",
            },
            "v2_adapter": "saxs_strain" if series_kind == "strain" else "saxs_static",
        },
        style_profile="sci_default",
    )


def _build_series_waterfall(
    series_kind: str,
    frames: Sequence[tuple[np.ndarray, np.ndarray, str]],
) -> FigureDefinition:
    selected_indices = _waterfall_indices(len(frames))
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, object]] = []
    for display_index, frame_index in enumerate(selected_indices):
        q, intensity, label = frames[frame_index]
        source_id = f"frame-{frame_index + 1:03d}-data"
        offset = np.log10(np.clip(intensity, np.finfo(float).tiny, None)) + display_index * 1.2
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
        objects.append(
            {
                "id": f"series-frame-{frame_index + 1:03d}",
                "type": "plot_series",
                "panel_id": "main",
                "name": label,
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
        figure_id=f"saxs.series.{series_kind}.waterfall",
        technique="saxs",
        scope="series",
        category="series_overview",
        title=f"SAXS {series_kind.title()} Waterfall",
        layout=_waterfall_layout(),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_provider",
            "function": "build_saxs_figure_definitions",
            "inputs": {"frame_count": len(frames)},
            "parameters": {
                "series_kind": series_kind,
                "figure_kind": "waterfall",
                "intensity_transform": "log10_offset",
                "selected_frame_indices": [index + 1 for index in selected_indices],
            },
            "v2_adapter": "saxs_strain" if series_kind == "strain" else "saxs_static",
        },
        style_profile="sci_default",
    )


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
            "v2_adapter": "temperature_saxs",
        },
        style_profile="sci_default",
    )


def _build_temperature_waterfall(
    temperatures: np.ndarray,
    frames: Sequence[tuple[np.ndarray, np.ndarray]],
    *,
    publication_role: str = "si",
    evidence: dict[str, object] | None = None,
) -> FigureDefinition:
    selected_indices = _waterfall_indices(len(frames))
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, object]] = []
    for display_index, frame_index in enumerate(selected_indices):
        q, intensity = frames[frame_index]
        source_id = f"frame-{frame_index + 1:03d}-data"
        offset = np.log10(np.clip(intensity, np.finfo(float).tiny, None)) + display_index * 1.2
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
            "v2_adapter": "temperature_saxs",
            **({"evidence": evidence} if evidence is not None else {}),
        },
        style_profile="sci_default",
        publication_role=publication_role,
    )


def _build_temperature_summary_definitions(
    result: TempSeriesResult,
    frames: Sequence[tuple[np.ndarray, np.ndarray]],
    *,
    included_indices: Sequence[int],
    publication_role: str,
    evidence: dict[str, object],
) -> tuple[FigureDefinition, ...]:
    return (
        _build_temperature_parameters(
            result,
            included_indices=included_indices,
            publication_role=publication_role,
            evidence=evidence,
        ),
        _build_temperature_heatmap(
            np.asarray(result.temperatures, dtype=float),
            frames,
            included_indices=included_indices,
            publication_role=publication_role,
            evidence=evidence,
        ),
    )


def _build_temperature_parameters(
    result: TempSeriesResult,
    *,
    included_indices: Sequence[int] | None = None,
    publication_role: str = "si",
    evidence: dict[str, object] | None = None,
) -> FigureDefinition:
    all_temperatures = np.ravel(np.asarray(result.temperatures, dtype=float))
    count = len(all_temperatures)
    indices = tuple(range(count)) if included_indices is None else tuple(included_indices)
    temperatures = all_temperatures[list(indices)]
    long_period = _series_values(result.L_array, count, "L_array")[list(indices)]
    raw_lc = _series_values(result.lc_array, count, "lc_array")[list(indices)]
    effective_lc = _series_values(
        result.lc_effective_array,
        count,
        "lc_effective_array",
        missing_ok=True,
    )[list(indices)]
    lc_values = np.where(np.isfinite(effective_lc), effective_lc, raw_lc)
    amorphous_values = long_period - lc_values
    invariant = _series_values(result.Q_star_array, count, "Q_star_array")[list(indices)]
    crystallinity = _series_values(result.Xc_array, count, "Xc_array")[list(indices)]
    source_id = "temperature-parameters-data"
    return FigureDefinition(
        figure_id="saxs.series.temperature.parameters",
        technique="saxs",
        scope="series",
        category="series_overview",
        title="SAXS Temperature Parameters",
        layout=_temperature_parameters_layout(),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("temperature_C", "C"),
                    DataColumnDefinition("L_nm", "nm"),
                    DataColumnDefinition("lc_nm", "nm"),
                    DataColumnDefinition("la_nm", "nm"),
                    DataColumnDefinition("Q_star", "a.u."),
                    DataColumnDefinition("crystallinity_fraction", "1"),
                ),
                values={
                    "temperature_C": _float_values(temperatures),
                    "L_nm": _float_values(long_period),
                    "lc_nm": _float_values(lc_values),
                    "la_nm": _float_values(amorphous_values),
                    "Q_star": _float_values(invariant),
                    "crystallinity_fraction": _float_values(crystallinity),
                },
            ),
        ),
        objects=(
            _parameter_series(
                "series-long-period",
                "long-period",
                source_id,
                "L_nm",
                "Long period",
                "#0072B2",
            ),
            _parameter_series(
                "series-crystalline-thickness",
                "thickness",
                source_id,
                "lc_nm",
                "Crystalline",
                "#009E73",
            ),
            _parameter_series(
                "series-amorphous-thickness",
                "thickness",
                source_id,
                "la_nm",
                "Amorphous",
                "#E69F00",
            ),
            _parameter_series(
                "series-invariant",
                "invariant",
                source_id,
                "Q_star",
                "Invariant",
                "#CC79A7",
            ),
            _parameter_series(
                "series-crystallinity",
                "crystallinity",
                source_id,
                "crystallinity_fraction",
                "Crystallinity",
                "#D55E00",
            ),
        ),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_provider",
            "function": "build_saxs_temperature_definitions",
            "inputs": {"temperature_count": len(temperatures)},
            "parameters": {
                "figure_kind": "parameters",
                "lc_source": "effective_with_raw_fallback",
            },
            "v2_adapter": "temperature_saxs",
            **({"evidence": evidence} if evidence is not None else {}),
        },
        style_profile="sci_default",
        publication_role=publication_role,
    )


def _build_temperature_heatmap(
    temperatures: np.ndarray,
    frames: Sequence[tuple[np.ndarray, np.ndarray]],
    *,
    included_indices: Sequence[int] | None = None,
    publication_role: str = "si",
    evidence: dict[str, object] | None = None,
) -> FigureDefinition:
    indices = (
        tuple(range(len(frames)))
        if included_indices is None
        else tuple(included_indices)
    )
    selected_temperatures = temperatures[list(indices)]
    selected_frames = tuple(frames[index] for index in indices)
    q_min = max(float(np.nanmin(q)) for q, _intensity in selected_frames)
    q_max = min(float(np.nanmax(q)) for q, _intensity in selected_frames)
    if not q_min < q_max:
        raise ValueError("temperature q ranges do not overlap")
    point_count = max(2, min(512, max(len(q) for q, _intensity in selected_frames)))
    common_q = np.linspace(q_min, q_max, point_count)
    q_column: list[float] = []
    temperature_column: list[float] = []
    intensity_column: list[float] = []
    for temperature, (q, intensity) in zip(selected_temperatures, selected_frames):
        interpolated = np.interp(common_q, q, intensity)
        q_column.extend(float(value) for value in common_q)
        temperature_column.extend(float(temperature) for _value in common_q)
        intensity_column.extend(float(value) for value in interpolated)
    source_id = "temperature-heatmap-data"
    return FigureDefinition(
        figure_id="saxs.series.temperature.heatmap",
        technique="saxs",
        scope="series",
        category="series_overview",
        title="SAXS Temperature Heatmap",
        layout=_temperature_heatmap_layout(),
        data_sources=(
            FigureDataSourceDefinition(
                source_id=source_id,
                columns=(
                    DataColumnDefinition("q_nm1", "nm^-1"),
                    DataColumnDefinition("temperature_C", "C"),
                    DataColumnDefinition("intensity", "a.u."),
                ),
                values={
                    "q_nm1": tuple(q_column),
                    "temperature_C": tuple(temperature_column),
                    "intensity": tuple(intensity_column),
                },
            ),
        ),
        objects=(
            {
                "id": "heatmap-intensity",
                "type": "heatmap",
                "panel_id": "main",
                "data_ref": source_id,
                "x_column": "q_nm1",
                "y_column": "temperature_C",
                "z_column": "intensity",
                "style": {"cmap": "viridis", "colorbar_label": "I(q)"},
            },
        ),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_provider",
            "function": "build_saxs_temperature_definitions",
            "inputs": {"temperature_count": len(selected_temperatures)},
            "parameters": {
                "figure_kind": "heatmap",
                "common_q_point_count": point_count,
                "common_q_range_nm1": [q_min, q_max],
            },
            "v2_adapter": "temperature_saxs",
            **({"evidence": evidence} if evidence is not None else {}),
        },
        style_profile="sci_default",
        publication_role=publication_role,
    )


def _parameter_series(
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
        "x_column": "temperature_C",
        "y_column": y_column,
        "style": {"color": color, "line_width": 0.9, "marker": "o"},
    }


def _temperature_parameters_layout() -> FigureLayoutDefinition:
    def x_axis(panel_id: str) -> AxisDefinition:
        return AxisDefinition(
            axis_id=f"x-{panel_id}",
            label="Temperature",
            unit="C",
        )

    return FigureLayoutDefinition(
        width_in=8.0,
        height_in=6.5,
        rows=2,
        columns=2,
        panels=(
            PanelDefinition(
                panel_id="long-period",
                row=0,
                column=0,
                x_axis=x_axis("long-period"),
                y_axis=AxisDefinition(
                    axis_id="y-long-period",
                    label="Long period",
                    unit="nm",
                ),
                title="Long Period",
            ),
            PanelDefinition(
                panel_id="thickness",
                row=0,
                column=1,
                x_axis=x_axis("thickness"),
                y_axis=AxisDefinition(
                    axis_id="y-thickness",
                    label="Thickness",
                    unit="nm",
                ),
                title="Phase Thickness",
                show_legend=True,
            ),
            PanelDefinition(
                panel_id="invariant",
                row=1,
                column=0,
                x_axis=x_axis("invariant"),
                y_axis=AxisDefinition(
                    axis_id="y-invariant",
                    label="Invariant",
                    unit="a.u.",
                ),
                title="Scattering Invariant",
            ),
            PanelDefinition(
                panel_id="crystallinity",
                row=1,
                column=1,
                x_axis=x_axis("crystallinity"),
                y_axis=AxisDefinition(
                    axis_id="y-crystallinity",
                    label="Relative crystallinity",
                    unit="1",
                ),
                title="Relative Crystallinity",
            ),
        ),
    )


def _temperature_heatmap_layout() -> FigureLayoutDefinition:
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
                ),
                y_axis=AxisDefinition(
                    axis_id="y",
                    label="Temperature",
                    unit="C",
                ),
            ),
        ),
    )


def _series_values(
    values,
    count: int,
    name: str,
    *,
    missing_ok: bool = False,
) -> np.ndarray:
    if values is None:
        if missing_ok:
            return np.full(count, np.nan, dtype=float)
        raise ValueError(f"temperature result array is missing: {name}")
    array = np.ravel(np.asarray(values, dtype=float))
    if len(array) != count:
        raise ValueError(f"temperature result array length differs: {name}")
    return array


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
        int(index) for index in np.unique(np.linspace(0, frame_count - 1, num=10, dtype=int))
    )


def _float_values(values: np.ndarray) -> tuple[float, ...]:
    return tuple(float(value) for value in values)
