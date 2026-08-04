from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_common import (
    SAXSFrameView,
    kratky_curve_from_frame,
)
from polynexus.core.saxs_engine.figure_static import (
    build_static_saxs_figure_definitions,
)
from polynexus.core.saxs_engine.figure_strain import build_strain_figure_definitions
from polynexus.core.saxs_engine.figure_provider import build_saxs_figure_definitions
from polynexus.core.saxs_engine.figure_temperature import (
    build_temperature_figure_definitions,
)
from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult


def _analysis(index: int) -> SimpleNamespace:
    q = np.asarray([0.1, 0.2, 0.3], dtype=float)
    intensity_q2 = np.asarray([0.01, 0.08, 0.18], dtype=float) * (index + 1)
    return SimpleNamespace(
        label=f"frame-{index}",
        condition_value=float(index),
        q=q,
        I=q * 0 + 1.0,
        I_smooth=q * 0 + 1.0,
        quality_flag="OK",
        final_parameters={
            "quality_flag": "OK",
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": True,
            "L_nm": 15.0,
            "lc_nm": 6.0,
            "la_nm": 9.0,
            "Xc": 0.4,
            "Q_star_valid": True,
        },
        metric_evidence={
            "kratky": {"level": "Trend", "value": float(np.max(intensity_q2))},
        },
        kratky={"q": q, "kratky": intensity_q2},
        correlation={"r": np.asarray([0.0, 1.0]), "gamma": np.asarray([1.0, 0.1])},
        idf={"r_idf": np.asarray([0.0, 1.0]), "idf": np.asarray([0.1, 0.2])},
    )


def _engine(mode: str) -> SimpleNamespace:
    analyses = [_analysis(index) for index in range(3)]
    rows = [dict(analysis.final_parameters) for analysis in analyses]
    result = TempSeriesResult(
        temperatures=np.asarray([30.0, 80.0, 120.0]),
        temp_points=[SimpleNamespace(metric_evidence=analysis.metric_evidence, source_index=index) for index, analysis in enumerate(analyses)],
    )
    return SimpleNamespace(
        _batch_results=analyses,
        _batch_params=rows,
        _q_list=[analysis.q for analysis in analyses],
        _I_list=[analysis.I for analysis in analyses],
        _conditions=np.asarray([0.0, 5.0, 60.0]),
        _file_list=[f"frame-{index}.dat" for index in range(3)],
        _analysis=None,
        _results=list(analyses) if mode == "temperature" else [],
        _temperature_result=result if mode == "temperature" else None,
        _strain_result=SimpleNamespace(strains=np.asarray([0.0, 5.0, 60.0])) if mode == "strain" else None,
        _condition_type=mode,
        _I_equat_list=[None, None, None],
        cfg=SimpleNamespace(
            experiment_type=mode,
            condition_label="Temperature" if mode == "temperature" else "Strain",
            condition_unit="C" if mode == "temperature" else "%",
        ),
    )


def test_kratky_projection_uses_emitted_curve_and_filters_invalid_pairs() -> None:
    analysis = _analysis(0)
    analysis.kratky = {
        "q": np.asarray([0.3, np.nan, 0.1]),
        "kratky": np.asarray([3.0, 99.0, 1.0]),
    }
    frame = SAXSFrameView(
        index=0,
        label="frame-0",
        condition=0.0,
        q=np.asarray([0.1, 0.2]),
        intensity=np.asarray([1.0, 1.0]),
        analysis=analysis,
        parameters={},
    )

    curve = kratky_curve_from_frame(frame)

    assert curve is not None
    q, iq2, quality = curve
    assert q.tolist() == [0.1, 0.3]
    assert iq2.tolist() == [1.0, 3.0]
    assert quality["nonfinite_pair_count"] == 1


def test_static_definition_exposes_complete_iq2_trace() -> None:
    engine = _engine("static")

    definitions = build_static_saxs_figure_definitions(engine)
    definition = next(item for item in definitions if item.figure_id == "saxs.static.comparison")

    source = next(source for source in definition.data_sources if source.source_id == "static-frame-000-profile")
    assert {column.name for column in source.columns} >= {"q_nm_inv", "intensity_q2"}
    assert any(obj["panel_id"] == "lorentz" and obj["y_column"] == "intensity_q2" for obj in definition.objects)


def test_temperature_definitions_expose_selected_and_full_series_iq2() -> None:
    definitions = build_temperature_figure_definitions(_engine("temperature"))
    for definition in definitions:
        validate_figure_definition(definition)

    selected = next(item for item in definitions if item.figure_id.startswith("saxs.temperature.evidence."))
    assert "kratky" in {panel.panel_id for panel in selected.layout.panels}
    waterfall = next(item for item in definitions if item.figure_id == "saxs.temperature.kratky")
    assert len(waterfall.objects) == 3
    assert all(obj["y_column"] == "intensity_q2" for obj in waterfall.objects)


def test_invalid_emitted_kratky_frame_is_omitted_with_quality_evidence() -> None:
    engine = _engine("temperature")
    engine._batch_results[1].kratky = {
        "q": np.asarray([np.nan, np.nan]),
        "kratky": np.asarray([np.nan, np.nan]),
    }

    definitions = build_temperature_figure_definitions(engine)
    waterfall = next(item for item in definitions if item.figure_id == "saxs.temperature.kratky")

    assert len(waterfall.objects) == 2
    quality = waterfall.recipe["parameters"]["projection_quality"]["1"]
    assert quality["status"] == "partial_nonfinite"
    assert quality["retained_pair_count"] == 0


def test_strain_definitions_expose_full_series_iq2() -> None:
    definitions = build_strain_figure_definitions(_engine("strain"))
    for definition in definitions:
        validate_figure_definition(definition)

    waterfall = next(item for item in definitions if item.figure_id == "saxs.strain.kratky")
    assert len(waterfall.objects) == 3
    assert all(obj["y_column"] == "intensity_q2" for obj in waterfall.objects)


def test_public_strain_route_preserves_iq2_axis_and_values() -> None:
    definitions = build_saxs_figure_definitions(_engine("strain"))

    waterfall = next(item for item in definitions if item.figure_id == "saxs.strain.kratky")
    y_axis = waterfall.layout.panels[0].y_axis
    assert "q" in y_axis.label.lower()
    assert "I" in y_axis.label
    assert y_axis.label != r"$I$ (a.u.)"

    source = waterfall.data_sources[0]
    assert source.values["intensity_q2"] == (0.01, 0.08, 0.18)
    assert source.values["intensity_q2"] != (1.0, 1.0, 1.0)


def test_public_static_and_temperature_routes_preserve_iq2_axis() -> None:
    for mode in ("static", "temperature"):
        definitions = build_saxs_figure_definitions(_engine(mode))
        waterfall = next(item for item in definitions if item.figure_id.endswith(".kratky"))
        y_label = waterfall.layout.panels[0].y_axis.label
        assert "q" in y_label.lower()
        assert "q^2" in y_label.lower()


def test_fourier_definition_uses_distance_axis() -> None:
    definitions = build_temperature_figure_definitions(_engine("temperature"))

    selected = next(item for item in definitions if item.figure_id.startswith("saxs.temperature.evidence."))
    correlation = next(panel for panel in selected.layout.panels if panel.panel_id == "correlation")
    assert correlation.x_axis.unit == ""
    assert "r" in correlation.x_axis.label.lower()
    assert "q" not in correlation.x_axis.label.lower()


def test_public_strain_correlation_and_idf_keep_distance_space_labels() -> None:
    definitions = build_saxs_figure_definitions(_engine("strain"))

    correlation = next(
        item for item in definitions if item.figure_id == "saxs.strain.correlation"
    )
    idf = next(item for item in definitions if item.figure_id == "saxs.strain.idf")

    correlation_panel = correlation.layout.panels[0]
    idf_panel = idf.layout.panels[0]
    assert "r" in correlation_panel.x_axis.label.lower()
    assert "q" not in correlation_panel.x_axis.label.lower()
    assert "gamma" in correlation_panel.y_axis.label.lower()
    assert "r" in idf_panel.x_axis.label.lower()
    assert "q" not in idf_panel.x_axis.label.lower()
    assert "idf" in idf_panel.y_axis.label.lower() or "g_1" in idf_panel.y_axis.label.lower()
    assert idf_panel.y_axis.label != r"$I$ (a.u.)"


def test_public_static_and_temperature_fourier_idf_labels_stay_distance_space() -> None:
    static_definitions = build_saxs_figure_definitions(_engine("static"))
    static_idf = next(
        item for item in static_definitions if item.figure_id == "saxs.static.frame.000.idf"
    )
    assert "r" in static_idf.layout.panels[0].x_axis.label.lower()
    assert "q" not in static_idf.layout.panels[0].x_axis.label.lower()
    assert "idf" in static_idf.layout.panels[0].y_axis.label.lower()

    temperature_definitions = build_saxs_figure_definitions(_engine("temperature"))
    selected = next(
        item
        for item in temperature_definitions
        if item.figure_id == "saxs.temperature.evidence.000"
    )
    panels = {panel.panel_id: panel for panel in selected.layout.panels}
    assert "r" in panels["correlation"].x_axis.label.lower()
    assert "q" not in panels["correlation"].x_axis.label.lower()
    assert "r" in panels["idf"].x_axis.label.lower()
    assert "q" not in panels["idf"].x_axis.label.lower()
    assert "idf" in panels["idf"].y_axis.label.lower()
