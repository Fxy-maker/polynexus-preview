"""Static SAXS publication figures assembled from completed analysis output."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
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
    frame_views_from_engine,
    polish_saxs_publication_definitions,
)
from .figure_evidence import attach_saxs_figure_evidence
from .figure_eligibility import (
    classify_frame_eligibility,
    crystallinity_panel_eligible,
    invariant_panel_eligible,
    trend_panel_eligible,
)


_COLORS = ("#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377")
_DIAGNOSTIC_METHODS = ("correlation", "idf", "porod", "guinier", "kratky")


def _finite_number(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _parameter(frame: SAXSFrameView, *keys: str) -> Any:
    """Return the first finite emitted value without deriving a replacement."""

    parameter_sources: list[Mapping[str, Any]] = [frame.parameters]
    analysis_parameters = getattr(frame.analysis, "final_parameters", {})
    if isinstance(analysis_parameters, Mapping):
        parameter_sources.append(analysis_parameters)
    for key in keys:
        for parameters in parameter_sources:
            value = parameters.get(key)
            if _finite_number(value):
                return value
        value = getattr(frame.analysis, key, None)
        if _finite_number(value):
            return value
    return np.nan


def _text_parameter(frame: SAXSFrameView, *keys: str) -> str:
    sources: list[Mapping[str, Any]] = [frame.parameters]
    analysis_parameters = getattr(frame.analysis, "final_parameters", {})
    if isinstance(analysis_parameters, Mapping):
        sources.append(analysis_parameters)
    for key in keys:
        for source in sources:
            value = str(source.get(key) or "").strip()
            if value:
                return value
        value = str(getattr(frame.analysis, key, "") or "").strip()
        if value:
            return value
    return ""


def _numeric_pairs(
    x_values: Any,
    y_values: Any,
    *,
    positive_x: bool = False,
    positive_y: bool = False,
    minimum: int = 2,
    require_all_finite: bool = True,
) -> tuple[tuple[float, ...], tuple[float, ...]] | None:
    try:
        x = np.asarray(x_values, dtype=float).reshape(-1)
        y = np.asarray(y_values, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return None
    if x.size != y.size or x.size < minimum:
        return None
    finite = np.isfinite(x) & np.isfinite(y)
    if require_all_finite and not bool(np.all(finite)):
        return None
    if positive_x:
        finite &= x > 0
    if positive_y:
        finite &= y > 0
    if int(np.count_nonzero(finite)) < minimum:
        return None
    return tuple(float(value) for value in x[finite]), tuple(
        float(value) for value in y[finite]
    )


def _mapping_pairs(
    value: Any,
    x_keys: Sequence[str],
    y_keys: Sequence[str],
) -> tuple[tuple[float, ...], tuple[float, ...]] | None:
    if not isinstance(value, Mapping):
        return None
    x_values = next((value[key] for key in x_keys if key in value), None)
    y_values = next((value[key] for key in y_keys if key in value), None)
    return _numeric_pairs(x_values, y_values)


def _profile_pairs(
    frame: SAXSFrameView,
) -> tuple[tuple[float, ...], tuple[float, ...]] | None:
    return _numeric_pairs(
        frame.q,
        frame.intensity,
        positive_x=True,
        positive_y=True,
        require_all_finite=False,
    )


def _q_star(frame: SAXSFrameView) -> Any:
    value = _parameter(frame, "q_star_nm1", "q_peak_nm1", "q_peak")
    if _finite_number(value) and float(value) > 0:
        return value
    fit_regions = getattr(frame.analysis, "fit_regions", ()) or ()
    for region in fit_regions:
        if not isinstance(region, Mapping):
            continue
        value = region.get("q_peak_fit")
        if str(region.get("kind") or "") == "bragg_peak" and _finite_number(value):
            return value
    return np.nan


def _source(
    source_id: str,
    columns: Sequence[tuple[str, str, str]],
    values: Mapping[str, Sequence[Any]],
) -> FigureDataSourceDefinition:
    return FigureDataSourceDefinition(
        source_id=source_id,
        columns=tuple(
            DataColumnDefinition(name=name, unit=unit, dtype=dtype)
            for name, unit, dtype in columns
        ),
        values={name: tuple(items) for name, items in values.items()},
    )


def _panel(
    panel_id: str,
    row: int,
    column: int,
    *,
    title: str,
    x_label: str,
    x_unit: str,
    y_label: str,
    y_unit: str,
    x_scale: str = "linear",
    y_scale: str = "linear",
    legend: bool = False,
) -> PanelDefinition:
    return PanelDefinition(
        panel_id=panel_id,
        row=row,
        column=column,
        title=title,
        show_legend=legend,
        x_axis=AxisDefinition(
            axis_id=f"{panel_id}-x",
            label=x_label,
            unit=x_unit,
            scale=x_scale,
        ),
        y_axis=AxisDefinition(
            axis_id=f"{panel_id}-y",
            label=y_label,
            unit=y_unit,
            scale=y_scale,
        ),
    )


def _plot_object(
    object_id: str,
    panel_id: str,
    source_id: str,
    x_column: str,
    y_column: str,
    *,
    name: str = "",
    color: str = "#4477AA",
    chart_kind: str = "line",
    marker: str = "",
) -> dict[str, Any]:
    style: dict[str, Any] = {"color": color, "line_width": 1.1}
    if marker:
        style.update({"marker": marker, "marker_size": 4.0})
    return {
        "id": object_id,
        "type": "plot_series",
        "panel_id": panel_id,
        "data_ref": source_id,
        "x_column": x_column,
        "y_column": y_column,
        "chart_kind": chart_kind,
        "name": name,
        "style": style,
    }


def _line_object(
    object_id: str,
    panel_id: str,
    x: Any,
    *,
    color: str = "#777777",
) -> dict[str, Any]:
    return {
        "id": object_id,
        "type": "line",
        "panel_id": panel_id,
        "orientation": "vertical",
        "x": float(x),
        "style": {
            "color": color,
            "line_width": 0.8,
            "line_style": "--",
            "alpha": 0.8,
        },
    }


def _definition(
    *,
    figure_id: str,
    scope: str,
    category: str,
    role: str,
    title: str,
    display_order: int,
    panels: Sequence[PanelDefinition],
    sources: Sequence[FigureDataSourceDefinition],
    objects: Sequence[Mapping[str, Any]],
    rows: int,
    columns: int,
    width: float,
    height: float,
    recipe_inputs: Mapping[str, Any],
) -> FigureDefinition:
    return FigureDefinition(
        figure_id=figure_id,
        technique="saxs",
        scope=scope,
        category=category,
        publication_role=role,
        title=title,
        display_order=display_order,
        layout=FigureLayoutDefinition(
            width_in=width,
            height_in=height,
            rows=rows,
            columns=columns,
            panels=tuple(panels),
        ),
        data_sources=tuple(sources),
        objects=tuple(dict(item) for item in objects),
        recipe={
            "module": "polynexus.core.saxs_engine.figure_static",
            "function": "build_static_saxs_figure_definitions",
            "inputs": dict(recipe_inputs),
            "parameters": {
                "source": "completed_analysis",
                "display_order": int(display_order),
            },
        },
        style_profile="sci_default",
    )


def _append_profile_objects(
    frames: Sequence[SAXSFrameView],
    *,
    profile_panel: str,
    lorentz_panel: str,
) -> tuple[list[FigureDataSourceDefinition], list[dict[str, Any]]]:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for order, frame in enumerate(frames):
        pairs = _profile_pairs(frame)
        if pairs is None:
            continue
        q, intensity = pairs
        source_id = f"static-frame-{frame.index:03d}-profile"
        color = _COLORS[order % len(_COLORS)]
        sources.append(
            _source(
                source_id,
                (
                    ("q_nm_inv", "nm^-1", "float64"),
                    ("intensity", "a.u.", "float64"),
                    ("intensity_q2", "a.u. nm^-2", "float64"),
                ),
                {
                    "q_nm_inv": q,
                    "intensity": intensity,
                    "intensity_q2": tuple(
                        intensity_value * q_value**2
                        for q_value, intensity_value in zip(q, intensity)
                    ),
                },
            )
        )
        objects.extend(
            (
                _plot_object(
                    f"profile-{frame.index:03d}",
                    profile_panel,
                    source_id,
                    "q_nm_inv",
                    "intensity",
                    name=frame.label,
                    color=color,
                ),
                _plot_object(
                    f"lorentz-{frame.index:03d}",
                    lorentz_panel,
                    source_id,
                    "q_nm_inv",
                    "intensity_q2",
                    name=frame.label,
                    color=color,
                ),
            )
        )
        q_star = _q_star(frame)
        if _finite_number(q_star) and float(q_star) > 0:
            objects.append(
                _line_object(
                    f"q-star-{frame.index:03d}",
                    lorentz_panel,
                    q_star,
                    color=color,
                )
            )
    return sources, objects


def _metric_values(frames: Sequence[SAXSFrameView]) -> dict[str, tuple[Any, ...]]:
    return {
        "sample": tuple(frame.label for frame in frames),
        "L_nm": tuple(_parameter(frame, "L_nm", "L_nm_effective", "L_nm_measured") for frame in frames),
        "lc_nm": tuple(_parameter(frame, "lc_nm", "lc_nm_effective", "lc_effective_nm") for frame in frames),
        "la_nm": tuple(_parameter(frame, "la_nm", "la_nm_effective") for frame in frames),
        "Xc": tuple(_parameter(frame, "Xc", "Xc_effective") for frame in frames),
        "Q_star_rel": tuple(_parameter(frame, "Q_star_rel", "Q_rel") for frame in frames),
    }


def _build_comparison(frames: Sequence[SAXSFrameView]) -> FigureDefinition | None:
    profile_frames = tuple(frame for frame in frames if _profile_pairs(frame) is not None)
    if len(profile_frames) < 2:
        return None
    sources, objects = _append_profile_objects(
        profile_frames,
        profile_panel="profiles",
        lorentz_panel="lorentz",
    )
    panels = [
        _panel(
            "profiles",
            0,
            0,
            title="Scattering profiles",
            x_label="Scattering vector",
            x_unit="nm^-1",
            y_label="Intensity",
            y_unit="a.u.",
            x_scale="log",
            y_scale="log",
            legend=True,
        ),
        _panel(
            "lorentz",
            0,
            1,
            title="Lorentz-corrected profiles",
            x_label="Scattering vector",
            x_unit="nm^-1",
            y_label="I(q) q^2",
            y_unit="a.u. nm^-2",
            legend=True,
        ),
    ]
    metrics = _metric_values(profile_frames)
    thickness_columns = tuple(
        name
        for name in ("L_nm", "lc_nm", "la_nm")
        if trend_panel_eligible(metrics[name])
    )
    relative_column = ""
    if crystallinity_panel_eligible(profile_frames, metrics["Xc"]):
        relative_column = "Xc"
    elif invariant_panel_eligible(profile_frames, metrics["Q_star_rel"]):
        relative_column = "Q_star_rel"

    if thickness_columns or relative_column:
        sources.append(
            _source(
                "static-metrics",
                (
                    ("sample", "", "string"),
                    ("L_nm", "nm", "float64"),
                    ("lc_nm", "nm", "float64"),
                    ("la_nm", "nm", "float64"),
                    ("Xc", "", "float64"),
                    ("Q_star_rel", "", "float64"),
                ),
                metrics,
            )
        )
    if thickness_columns:
        panels.append(
            _panel(
                "thickness",
                1,
                0,
                title="Lamellar dimensions",
                x_label="Sample",
                x_unit="",
                y_label="Length",
                y_unit="nm",
                legend=True,
            )
        )
        for index, name in enumerate(thickness_columns):
            objects.append(
                _plot_object(
                    f"thickness-{name.lower()}",
                    "thickness",
                    "static-metrics",
                    "sample",
                    name,
                    name=name.replace("_nm", ""),
                    color=_COLORS[index],
                    chart_kind="bar",
                )
            )
    if relative_column:
        relative_title = (
            "Linear crystallinity" if relative_column == "Xc" else "Relative invariant"
        )
        panels.append(
            _panel(
                "relative",
                1,
                1,
                title=relative_title,
                x_label="Sample",
                x_unit="",
                y_label=relative_title,
                y_unit="",
            )
        )
        objects.append(
            _plot_object(
                f"relative-{relative_column.lower()}",
                "relative",
                "static-metrics",
                "sample",
                relative_column,
                color="#AA3377",
                marker="o",
            )
        )
    return _definition(
        figure_id="saxs.static.comparison",
        scope="series",
        category="series_overview",
        role="main",
        title="Static SAXS sample comparison",
        display_order=10,
        panels=panels,
        sources=sources,
        objects=objects,
        rows=2,
        columns=2,
        width=7.2,
        height=6.0,
        recipe_inputs={"frame_indices": [frame.index for frame in profile_frames]},
    )


def _build_sample(frame: SAXSFrameView) -> FigureDefinition | None:
    pairs = _profile_pairs(frame)
    if pairs is None:
        return None
    sources, objects = _append_profile_objects(
        (frame,),
        profile_panel="profile",
        lorentz_panel="lorentz",
    )
    panels = [
        _panel(
            "profile",
            0,
            0,
            title="Scattering profile",
            x_label="Scattering vector",
            x_unit="nm^-1",
            y_label="Intensity",
            y_unit="a.u.",
            x_scale="log",
            y_scale="log",
        ),
        _panel(
            "lorentz",
            0,
            1,
            title="Lorentz-corrected profile",
            x_label="Scattering vector",
            x_unit="nm^-1",
            y_label="I(q) q^2",
            y_unit="a.u. nm^-2",
        ),
    ]
    metrics = _metric_values((frame,))
    available = tuple(
        name for name in ("L_nm", "lc_nm", "la_nm") if _finite_number(metrics[name][0])
    )
    if available:
        panels.append(
            _panel(
                "metrics",
                1,
                0,
                title="Final lamellar metrics",
                x_label="Metric",
                x_unit="",
                y_label="Length",
                y_unit="nm",
            )
        )
        metric_labels = tuple(name.replace("_nm", "") for name in available)
        metric_values = tuple(metrics[name][0] for name in available)
        sources.append(
            _source(
                "static-sample-metrics",
                (
                    ("metric", "", "string"),
                    ("value_nm", "nm", "float64"),
                ),
                {"metric": metric_labels, "value_nm": metric_values},
            )
        )
        objects.append(
            _plot_object(
                "sample-metrics",
                "metrics",
                "static-sample-metrics",
                "metric",
                "value_nm",
                color="#228833",
                chart_kind="bar",
            )
        )
        xc = metrics["Xc"][0]
        if _finite_number(xc):
            objects.append(
                {
                    "id": "sample-xc-text",
                    "type": "text",
                    "panel_id": "metrics",
                    "x": 0.98,
                    "y": 0.96,
                    "text": f"Xc = {float(xc):.3g}",
                    "horizontal_alignment": "right",
                    "vertical_alignment": "top",
                    "style": {"color": "#222222", "font_size": 8.0},
                }
            )
    return _definition(
        figure_id="saxs.static.sample",
        scope="frame",
        category="per_frame",
        role="main",
        title=f"Static SAXS: {frame.label}",
        display_order=10,
        panels=panels,
        sources=sources,
        objects=objects,
        rows=2,
        columns=2,
        width=7.2,
        height=5.5,
        recipe_inputs={"frame_index": frame.index},
    )


def _correlation_pairs(frame: SAXSFrameView):
    return _mapping_pairs(getattr(frame.analysis, "correlation", None), ("r",), ("gamma",))


def _idf_pairs(frame: SAXSFrameView):
    return _mapping_pairs(getattr(frame.analysis, "idf", None), ("r_idf", "r"), ("idf",))


def _supported_lc(frame: SAXSFrameView) -> Any:
    lc = _parameter(frame, "lc_nm_effective", "lc_nm", "lc_effective_nm")
    idf = getattr(frame.analysis, "idf", None)
    idf_lc = idf.get("lc_idf") if isinstance(idf, Mapping) else np.nan
    status = _text_parameter(frame, "lc_reliability_status").lower()
    rejected = status in {"low_confidence", "diagnostic_only", "unusable", "error"}
    if (
        _finite_number(lc)
        and float(lc) > 0
        and _finite_number(idf_lc)
        and float(idf_lc) > 0
        and not rejected
    ):
        return lc
    return np.nan


def _promotable(frame: SAXSFrameView) -> bool:
    if classify_frame_eligibility(frame).highest_role != "main":
        return False
    status = _text_parameter(
        frame,
        "lc_reliability_status",
        "lc_path_status",
        "lamellar_interpretation_mode",
    ).lower()
    return status not in {
        "low_confidence",
        "diagnostic_only",
        "unusable",
        "error",
        "no_path",
        "raw_low_confidence",
        "sequence_path_low_confidence",
        "sequence_path_diagnostic_only",
        "sequence_path_none",
    }


def _build_correlation_support(frames: Sequence[SAXSFrameView]) -> FigureDefinition | None:
    selected = next(
        (
            frame
            for frame in sorted(frames, key=lambda item: item.index)
            if classify_frame_eligibility(frame).highest_role != "diagnostic"
            and (_correlation_pairs(frame) is not None or _idf_pairs(frame) is not None)
        ),
        None,
    )
    if selected is None:
        return None
    correlation = _correlation_pairs(selected)
    idf = _idf_pairs(selected)
    sources = []
    objects = []
    panels = []
    if correlation is not None:
        sources.append(
            _source(
                "static-support-correlation",
                (("r_nm", "nm", "float64"), ("gamma", "", "float64")),
                {"r_nm": correlation[0], "gamma": correlation[1]},
            )
        )
        objects.append(
            _plot_object(
                "support-correlation-series",
                "correlation",
                "static-support-correlation",
                "r_nm",
                "gamma",
                color="#4477AA",
            )
        )
        panels.append(
            _panel(
                "correlation", 0, len(panels), title="Correlation function",
                x_label="Distance", x_unit="nm", y_label="Correlation", y_unit="",
            )
        )
    if idf is not None:
        sources.append(
            _source(
                "static-support-idf",
                (("r_nm", "nm", "float64"), ("idf", "nm^-2", "float64")),
                {"r_nm": idf[0], "idf": idf[1]},
            )
        )
        objects.append(
            _plot_object(
                "support-idf-series", "idf", "static-support-idf", "r_nm", "idf", color="#EE6677"
            )
        )
        panels.append(
            _panel(
                "idf", 0, len(panels), title="Interface distribution function",
                x_label="Distance", x_unit="nm", y_label="IDF", y_unit="nm^-2",
            )
        )
    lc = _supported_lc(selected)
    if _finite_number(lc):
        if correlation is not None:
            objects.append(_line_object("support-correlation-lc", "correlation", lc))
        if idf is not None:
            objects.append(_line_object("support-idf-lc", "idf", lc))
    return _definition(
        figure_id="saxs.static.correlation.support",
        scope="frame",
        category="supplementary",
        role="si",
        title=f"Correlation and IDF support: {selected.label}",
        display_order=20,
        panels=tuple(panels),
        sources=sources,
        objects=objects,
        rows=1,
        columns=len(panels),
        width=7.2,
        height=3.2,
        recipe_inputs={"frame_index": selected.index},
    )


def _diagnostic_pairs(
    frame: SAXSFrameView,
    method: str,
) -> tuple[tuple[float, ...], tuple[float, ...]] | None:
    if method == "correlation":
        return _correlation_pairs(frame)
    if method == "idf":
        return _idf_pairs(frame)
    if method == "porod":
        return _mapping_pairs(
            getattr(frame.analysis, "porod", None),
            ("q_porod", "q"),
            ("Iq4_porod", "Iq4", "iq4"),
        )
    if method == "guinier":
        guinier = getattr(frame.analysis, "guinier", None)
        if isinstance(guinier, Mapping):
            pairs = _mapping_pairs(
                guinier,
                ("q_guinier", "q"),
                ("lnI_guinier", "lnI", "ln_intensity"),
            )
            if pairs is not None:
                return pairs
        return _numeric_pairs(
            getattr(frame.analysis, "q_guinier", None),
            getattr(frame.analysis, "lnI_guinier", None),
        )
    if method == "kratky":
        return _mapping_pairs(
            getattr(frame.analysis, "kratky", None),
            ("q",),
            ("kratky", "iq2"),
        )
    return None


def _build_diagnostic(frame: SAXSFrameView, method: str) -> FigureDefinition | None:
    pairs = _diagnostic_pairs(frame, method)
    if pairs is None:
        return None
    x_values, y_values = pairs
    x_column = "r_nm" if method in {"correlation", "idf"} else "q_nm_inv"
    x_label = "Distance" if method in {"correlation", "idf"} else "Scattering vector"
    x_unit = "nm" if method in {"correlation", "idf"} else "nm^-1"
    y_config = {
        "correlation": ("gamma", "Correlation", ""),
        "idf": ("idf", "IDF", "nm^-2"),
        "porod": ("intensity_q4", "I(q) q^4", "a.u. nm^-4"),
        "guinier": ("ln_intensity", "ln I(q)", ""),
        "kratky": ("intensity_q2", "I(q) q^2", "a.u. nm^-2"),
    }
    y_column, y_label, y_unit = y_config[method]
    if method == "guinier":
        x_values = tuple(value**2 for value in x_values)
        x_column = "q2_nm_minus2"
        x_label = "Squared scattering vector"
        x_unit = "nm^-2"
    source_id = f"static-frame-{frame.index:03d}-{method}"
    return _definition(
        figure_id=f"saxs.static.frame.{frame.index:03d}.{method}",
        scope="frame",
        category="diagnostic",
        role="diagnostic",
        title=f"{method.capitalize()} diagnostic: {frame.label}",
        display_order=100 + frame.index * 10 + _DIAGNOSTIC_METHODS.index(method),
        panels=(
            _panel(
                method,
                0,
                0,
                title=method.capitalize(),
                x_label=x_label,
                x_unit=x_unit,
                y_label=y_label,
                y_unit=y_unit,
            ),
        ),
        sources=(
            _source(
                source_id,
                ((x_column, x_unit, "float64"), (y_column, y_unit, "float64")),
                {x_column: x_values, y_column: y_values},
            ),
        ),
        objects=(
            _plot_object(
                f"{method}-series-{frame.index:03d}",
                method,
                source_id,
                x_column,
                y_column,
                color="#4477AA",
            ),
        ),
        rows=1,
        columns=1,
        width=3.5,
        height=3.0,
        recipe_inputs={"frame_index": frame.index, "method": method},
    )


def build_static_saxs_figure_definitions(engine_state: Any) -> tuple[FigureDefinition, ...]:
    """Build deterministic static figures from immutable views of emitted data."""

    frames = frame_views_from_engine(engine_state)
    promoted = tuple(
        frame
        for frame in frames
        if _promotable(frame)
    )
    definitions: list[FigureDefinition] = []
    if len(promoted) >= 2:
        main = _build_comparison(promoted)
    elif len(promoted) == 1:
        main = _build_sample(promoted[0])
    else:
        main = None
    if main is not None:
        definitions.append(main)

    support = _build_correlation_support(frames)
    if support is not None:
        definitions.append(support)
    elif main is not None and promoted:
        # A missing correlation/IDF trace must not erase the SI tier.  Keep a
        # traceable profile snapshot as supplementary evidence and leave the
        # absent diagnostics out rather than synthesising them.
        profile = _build_sample(promoted[0])
        if profile is not None:
            definitions.append(
                replace(
                    profile,
                    figure_id="saxs.static.profile.si",
                    category="supplementary",
                    publication_role="si",
                    title=f"Static SAXS supplementary profile: {promoted[0].label}",
                    display_order=20,
                )
            )
    for frame in frames:
        for method in _DIAGNOSTIC_METHODS:
            diagnostic = _build_diagnostic(frame, method)
            if diagnostic is not None:
                definitions.append(diagnostic)

    role_rank = {"main": 0, "si": 1, "diagnostic": 2}
    ordered = tuple(
        sorted(
            definitions,
            key=lambda item: (
                role_rank[item.publication_role],
                item.display_order,
                item.figure_id,
            ),
        )
    )
    polished = polish_saxs_publication_definitions(
        tuple(_ensure_display_order(item) for item in ordered)
    )
    return attach_saxs_figure_evidence(
        polished,
        frames,
        mode="static",
    )


def _ensure_display_order(definition: FigureDefinition) -> FigureDefinition:
    recipe = dict(definition.recipe)
    parameters = dict(recipe.get("parameters", {}))
    parameters["display_order"] = int(definition.display_order)
    recipe["parameters"] = parameters
    return replace(definition, recipe=recipe)


# A concise compatibility name for provider callers.
build_static_figure_definitions = build_static_saxs_figure_definitions


__all__ = [
    "build_static_figure_definitions",
    "build_static_saxs_figure_definitions",
]
