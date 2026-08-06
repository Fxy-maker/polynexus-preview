from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_strain import analyze_strain_series


def _gaussian(q: np.ndarray, center: float, amplitude: float, width: float = 0.018) -> np.ndarray:
    return amplitude * np.exp(-0.5 * ((q - center) / width) ** 2)


def test_strain_orientation_uses_authoritative_total_profile_peak() -> None:
    q = np.linspace(0.20, 1.20, 600)
    total = 0.02 + _gaussian(q, 0.72, 12.0) + _gaussian(q, 0.45, 1.5)
    sector_radial = 0.02 + _gaussian(q, 0.45, 12.0) + _gaussian(q, 0.72, 1.5)
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    angular = 1.0 + 1.8 * np.cos(chi) ** 2
    sector_map = np.outer(angular, sector_radial)
    sector = {
        "I_2d": sector_map,
        "q_2d": q,
        "chi_rad": chi,
        "I_full": sector_radial,
        "I_merid": sector_radial,
        "I_equat": sector_radial,
        "support_count": np.ones_like(sector_map),
        "frame_source_index": 0,
    }

    result = analyze_strain_series(
        strains=[0.0],
        q_list=[q],
        I_list=[total],
        sector_data_list=[sector],
        frame_source_indices=[0],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.20,
            q_bragg_min=0.30,
            q_bragg_max=1.00,
            tensile_axis_deg=0.0,
        ),
    )

    point = result.strain_points[0]
    assert point.analysis_result is not None
    assert point.q_peak_total_nm1 == pytest.approx(0.72, abs=0.015)
    assert point.analysis_result.long_period.q_peak_nm1 == pytest.approx(
        point.q_peak_total_nm1
    )
    assert point.orientation_evidence["fit_evidence"]["q_star_candidate"] == pytest.approx(
        point.q_peak_total_nm1
    )
    assert point.orientation_evidence["fit_evidence"]["feature_kind"] == (
        "tracked_lamellar_peak"
    )


def test_strain_peak_tracking_follows_feature_and_fails_closed_when_it_disappears() -> None:
    q = np.linspace(0.20, 1.20, 600)
    first = 0.02 + _gaussian(q, 0.72, 12.0) + _gaussian(q, 0.45, 1.0)
    competing = 0.02 + _gaussian(q, 0.735, 3.0) + _gaussian(q, 0.45, 20.0)
    missing = 0.02 + _gaussian(q, 0.45, 20.0)

    result = analyze_strain_series(
        strains=[0.0, 20.0, 40.0],
        q_list=[q, q, q],
        I_list=[first, competing, missing],
        frame_source_indices=[0, 1, 2],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.20,
            q_bragg_min=0.30,
            q_bragg_max=1.00,
        ),
    )

    seeded, tracked, lost = result.strain_points
    assert seeded.feature_tracking_status == "seeded"
    assert seeded.q_peak_total_nm1 == pytest.approx(0.72, abs=0.015)
    assert tracked.feature_tracking_status == "tracked"
    assert tracked.q_peak_total_nm1 == pytest.approx(0.735, abs=0.015)
    assert tracked.L_nm == pytest.approx(2 * np.pi / tracked.q_peak_total_nm1)
    assert lost.feature_tracking_status == "tracking_lost"
    assert np.isnan(lost.q_peak_total_nm1)
    assert np.isnan(lost.L_nm)
    assert "tracked_feature_unavailable" in lost.feature_tracking_reason_codes


def test_strain_reports_detector_coordinate_sector_peaks_for_tracked_feature() -> None:
    q = np.linspace(0.20, 1.20, 600)
    total = 0.02 + _gaussian(q, 0.72, 12.0)
    meridional = 0.02 + _gaussian(q, 0.68, 10.0) + _gaussian(q, 0.40, 15.0)
    equatorial = 0.02 + _gaussian(q, 0.78, 10.0) + _gaussian(q, 0.42, 15.0)
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    sector_map = np.outer(1.0 + np.cos(chi) ** 2, total)
    sector = {
        "q": q,
        "I_2d": sector_map,
        "q_2d": q,
        "chi_rad": chi,
        "I_full": total,
        "I_merid": meridional,
        "I_equat": equatorial,
        "support_count": np.ones_like(sector_map),
        "frame_source_index": 0,
    }

    result = analyze_strain_series(
        strains=[0.0],
        q_list=[q],
        I_list=[total],
        sector_data_list=[sector],
        frame_source_indices=[0],
        cfg=SAXSConfig(
            smooth_method="none",
            q_min=0.20,
            q_bragg_min=0.30,
            q_bragg_max=1.00,
        ),
    )

    point = result.strain_points[0]
    assert point.q_peak_meridional_nm1 == pytest.approx(0.68, abs=0.015)
    assert point.L_meridional_nm == pytest.approx(
        2 * np.pi / point.q_peak_meridional_nm1
    )
    assert point.q_peak_equatorial_nm1 == pytest.approx(0.78, abs=0.015)
    assert point.L_equatorial_nm == pytest.approx(
        2 * np.pi / point.q_peak_equatorial_nm1
    )


def test_strain_engine_reuses_series_analysis_and_supplies_source_indices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from polynexus.core import saxs as saxs_module
    from polynexus.core.saxs_engine.core import LongPeriodResult, SAXSResult, StructureParams
    from polynexus.core.saxs_engine.saxs_strain import (
        StrainPhase,
        StrainPointResult,
        StrainSeriesResult,
    )

    q = np.linspace(0.20, 1.20, 120)
    intensity = 0.1 + _gaussian(q, 0.65, 2.0, width=0.03)
    analyses = [
        SAXSResult(
            long_period=LongPeriodResult(
                L_best=9.1,
                L_bragg=10.0,
                q_peak_nm1=2 * np.pi / 10.0,
            ),
            structure=StructureParams(
                L=9.1,
                lc=3.0,
                la=6.1,
                phi_c=0.33,
                Q_invariant=5.0,
            ),
            porod={"slope": -4.0},
        ),
        SAXSResult(
            long_period=LongPeriodResult(
                L_best=10.4,
                L_bragg=12.0,
                q_peak_nm1=2 * np.pi / 12.0,
            ),
            structure=StructureParams(
                L=10.4,
                lc=3.2,
                la=7.2,
                phi_c=0.31,
                Q_invariant=4.5,
            ),
            porod={"slope": -4.0},
        ),
    ]
    points = [
        StrainPointResult(
            strain_pct=0.0,
            phase=StrainPhase.ELASTIC,
            L_nm=10.0,
            q_peak_total_nm1=2 * np.pi / 10.0,
            q_peak_meridional_nm1=0.60,
            L_meridional_nm=2 * np.pi / 0.60,
            q_peak_equatorial_nm1=0.66,
            L_equatorial_nm=2 * np.pi / 0.66,
            feature_tracking_status="seeded",
            invariant_Q=5.0,
            invariant_Q_rel=1.0,
            analysis_result=analyses[0],
        ),
        StrainPointResult(
            strain_pct=20.0,
            phase=StrainPhase.ELASTIC,
            L_nm=12.0,
            q_peak_total_nm1=2 * np.pi / 12.0,
            q_peak_meridional_nm1=0.50,
            L_meridional_nm=2 * np.pi / 0.50,
            q_peak_equatorial_nm1=0.55,
            L_equatorial_nm=2 * np.pi / 0.55,
            feature_tracking_status="tracked",
            invariant_Q=4.5,
            invariant_Q_rel=0.9,
            analysis_result=analyses[1],
        ),
    ]
    captured: dict[str, object] = {}

    def fake_series(*, frame_source_indices=None, **_kwargs):
        captured["frame_source_indices"] = frame_source_indices
        return StrainSeriesResult(
            strain_points=points,
            strains=np.asarray([0.0, 20.0]),
            L_array=np.asarray([10.0, 12.0]),
            lc_array=np.asarray([3.0, 3.2]),
            la_array=np.asarray([7.0, 8.8]),
            invariant_Q_array=np.asarray([5.0, 4.5]),
            invariant_Q_rel_array=np.asarray([1.0, 0.9]),
            f_herman_array=np.asarray([np.nan, np.nan]),
            phi_void_array=np.asarray([np.nan, np.nan]),
        )

    def forbidden_single(*_args, **_kwargs):
        raise AssertionError("strain engine reran analyze_single")

    monkeypatch.setattr(saxs_module, "analyze_strain_series", fake_series)
    monkeypatch.setattr(saxs_module, "analyze_single", forbidden_single)

    engine = saxs_module.SAXSEngine(
        config=saxs_module.SAXSConfig(experiment_type="strain")
    )
    engine._q_list = [q, q]  # type: ignore[attr-defined]
    engine._I_list = [intensity, intensity]  # type: ignore[attr-defined]
    engine._I_merid_list = [None, None]  # type: ignore[attr-defined]
    engine._I_equat_list = [None, None]  # type: ignore[attr-defined]
    engine._q_pyfai_list = [np.array([]), np.array([])]  # type: ignore[attr-defined]
    engine._I_pyfai_list = [np.array([]), np.array([])]  # type: ignore[attr-defined]
    engine._conditions = [0.0, 20.0]  # type: ignore[attr-defined]
    engine._condition_confidences = [1.0, 1.0]  # type: ignore[attr-defined]
    engine._file_list = ["frame-000-S_.edf", "frame-020-S_.edf"]  # type: ignore[attr-defined]
    engine._sector_data_list = [None, None]  # type: ignore[attr-defined]
    monkeypatch.setattr(
        engine,
        "_try_sasmodels_lc",
        lambda *_args, **_kwargs: (np.nan, np.nan, np.nan, "raw", "", np.nan),
    )

    assert engine._run_strain_pipeline() is True  # type: ignore[attr-defined]
    assert captured["frame_source_indices"] == [0, 1]
    assert [row["L_nm"] for row in engine._batch_params] == [10.0, 12.0]  # type: ignore[attr-defined]
    assert engine._batch_results == analyses  # type: ignore[attr-defined]
    first_row = engine._batch_params[0]  # type: ignore[attr-defined]
    assert first_row["q_peak_total_nm1"] == pytest.approx(2 * np.pi / 10.0)
    assert first_row["q_peak_meridional_nm1"] == pytest.approx(0.60)
    assert first_row["L_meridional_nm"] == pytest.approx(2 * np.pi / 0.60)
    assert first_row["q_peak_equatorial_nm1"] == pytest.approx(0.66)
    assert first_row["L_equatorial_nm"] == pytest.approx(2 * np.pi / 0.66)
    assert first_row["feature_tracking_status"] == "seeded"
    assert first_row["invariant_Q"] == pytest.approx(5.0)
    assert first_row["invariant_Q_rel"] == pytest.approx(1.0)
    assert "Q_star_abs" not in first_row
    assert "Q_star" not in first_row
    assert not any(key.startswith("Q_star") for key in first_row)


def test_stability_and_history_normalize_legacy_invariant_inputs() -> None:
    from polynexus.gui.analysis_history_service import saxs_strain_evidence_snapshot
    from polynexus.orchestrator_stability import _frame_values

    point = SimpleNamespace(
        invariant_Q=4.5,
        invariant_Q_rel=0.9,
        Q_star=99.0,
        Q_star_rel=9.9,
        L_nm=12.0,
        phi_c=0.3,
    )
    values = _frame_values(
        SimpleNamespace(
            _temperature_result=None,
            _strain_result=SimpleNamespace(strain_points=[point]),
        ),
        {"invariant_Q": 4.5},
    )
    assert values["invariant_Q"] == [4.5]
    assert "Q_star" not in values

    canonical = saxs_strain_evidence_snapshot(
        {},
        {
            "feature_evidence": {
                "condition_evidence": {"condition_label": "strain"},
                "strain_structure_evidence": {
                    "invariant_Q_rel_mean": 0.95,
                    "invariant_Q_rel_span": 0.1,
                },
            }
        },
        symptom_names=[],
    )
    legacy = saxs_strain_evidence_snapshot(
        {},
        {
            "feature_evidence": {
                "condition_evidence": {"condition_label": "strain"},
                "strain_structure_evidence": {
                    "Q_star_rel_mean": 0.95,
                    "Q_star_rel_span": 0.1,
                },
            }
        },
        symptom_names=[],
    )
    assert canonical["invariant_Q_rel_mean"] == pytest.approx(0.95)
    assert canonical["invariant_Q_rel_span"] == pytest.approx(0.1)
    assert legacy["invariant_Q_rel_mean"] == pytest.approx(0.95)
    assert legacy["invariant_Q_rel_span"] == pytest.approx(0.1)
    assert not any(key.startswith("Q_star") for key in canonical)
    assert not any(key.startswith("Q_star") for key in legacy)


def _strain_figure_engine(*, detector: bool = False) -> SimpleNamespace:
    q = np.asarray([0.20, 0.45, 0.70], dtype=float)
    intensity = np.asarray([2.0, 5.0, 3.0], dtype=float)
    rows = [
        {
            "file": f"frame-{index}.{'edf' if detector else 'dat'}",
            "quality_flag": "OK",
            "L_nm": 10.0 + index,
            "L_meridional_nm": 9.0 + index,
            "L_equatorial_nm": 11.0 + index,
            "lc_nm": 4.0,
            "la_nm": 6.0 + index,
            "Xc_effective": 0.4,
            "Q_star_valid": True,
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": True,
        }
        for index in range(3)
    ]
    rows[0].update(
        invariant_Q=7.0,
        invariant_Q_rel=1.0,
        Q_star=70.0,
        Q_star_rel=10.0,
    )
    rows[1].update(Q_star_abs=5.0, Q_rel=0.8)
    rows[2].update(Q_star=4.0, Q_star_rel=0.6)
    analyses = [
        SimpleNamespace(
            label=f"frame-{index}",
            condition_value=float(index * 10),
            q=q,
            I=intensity,
            I_smooth=intensity,
            final_parameters=row,
            metric_evidence={},
            quality_flag="OK",
        )
        for index, row in enumerate(rows)
    ]
    return SimpleNamespace(
        _batch_results=analyses,
        _batch_params=rows,
        _q_list=[q.copy() for _ in rows],
        _I_list=[intensity.copy() for _ in rows],
        _conditions=[0.0, 10.0, 20.0],
        _file_list=[row["file"] for row in rows],
        _analysis=None,
        _temperature_result=None,
        _strain_result=SimpleNamespace(
            strains=np.asarray([0.0, 10.0, 20.0]),
            metric_evidence={},
            strain_points=[],
        ),
        _condition_type="strain",
        cfg=SimpleNamespace(experiment_type="strain"),
    )


def test_strain_figures_emit_invariant_names_and_read_legacy_aliases() -> None:
    from polynexus.core.saxs_engine.figure_strain import (
        build_strain_figure_definitions,
    )

    definitions = build_strain_figure_definitions(_strain_figure_engine())
    invariant = next(
        item for item in definitions if item.figure_id == "saxs.strain.invariant"
    )
    source = invariant.data_sources[0]

    assert source.values["invariant_Q"] == pytest.approx((7.0, 5.0, 4.0))
    assert source.values["invariant_Q_rel"] == pytest.approx((1.0, 0.8, 0.6))
    assert all("Q_star" not in column.name for column in source.columns)
    assert all("Q_star" not in str(item) for item in invariant.objects)
    assert "Q_star_valid_required" not in invariant.recipe["parameters"]


def test_strain_morphology_includes_detector_coordinate_long_period_curves() -> None:
    from polynexus.core.saxs_engine.figure_strain import (
        build_strain_figure_definitions,
    )

    evolution = next(
        item
        for item in build_strain_figure_definitions(_strain_figure_engine())
        if item.figure_id == "saxs.strain.evolution.1d"
    )
    source = next(
        item for item in evolution.data_sources if item.source_id == "strain-morphology"
    )
    morphology_objects = tuple(
        item for item in evolution.objects if item["panel_id"] == "morphology"
    )

    assert source.values["L_meridional_nm"] == pytest.approx((9.0, 10.0, 11.0))
    assert source.values["L_equatorial_nm"] == pytest.approx((11.0, 12.0, 13.0))
    assert {item["y_column"] for item in morphology_objects} >= {
        "L_meridional_nm",
        "L_equatorial_nm",
    }


def test_detector_preview_excludes_floor_sentinels_without_dropping_valid_negative_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from matplotlib.figure import Figure

    from polynexus.core.figures.renderer import MatplotlibFigureRenderer
    from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
    import polynexus.core.saxs_engine.figure_strain as figure_strain_module

    image = np.asarray(
        [
            [np.nan, 0.0, -2.0, 0.01, 0.1],
            [1.0, 10.0, 100.0, 1000.0, 1_000_000.0],
        ],
        dtype=float,
    )
    monkeypatch.setattr(
        figure_strain_module,
        "read_image",
        lambda _path: (image.copy(), {}),
    )

    evolution = next(
        item
        for item in figure_strain_module.build_strain_figure_definitions(
            _strain_figure_engine(detector=True)
        )
        if item.figure_id == "saxs.strain.evolution.2d"
    )
    detector = next(
        item for item in evolution.data_sources if item.source_id == "detector-image-000"
    )
    heatmap = next(
        item for item in evolution.objects if item["id"] == "detector-pattern-000"
    )
    evidence_before = np.asarray(detector.values["log_intensity"], dtype=float).copy()
    display_values = np.asarray(
        detector.values["display_log_intensity"],
        dtype=float,
    )
    eligible = np.log10(image[np.isfinite(image) & (image > 0.0)])
    expected_bounds = np.percentile(eligible, [2.0, 98.0])
    v2_artifact = build_v2_definition_artifact(evolution)

    figure = Figure(figsize=(4.0, 3.0), dpi=100)
    axis = figure.add_subplot(111)
    artist = MatplotlibFigureRenderer()._render_heatmap(
        figure,
        axis,
        SimpleNamespace(data_tables={detector.source_id: detector.values}),
        heatmap,
    )[0]

    assert heatmap["z_column"] == "display_log_intensity"
    assert heatmap["allow_partial_detector_grid"] is True
    assert np.all(np.isfinite(display_values))
    assert v2_artifact.capability["v2_runtime"] == "ready"
    assert artist.get_clim() == pytest.approx(tuple(expected_bounds))
    assert np.array_equal(
        np.asarray(detector.values["log_intensity"], dtype=float),
        evidence_before,
    )
    assert np.any(np.isclose(evidence_before, -2.0))
    assert np.any(np.isclose(evidence_before, -1.0))
    assert np.any(np.isclose(evidence_before, 0.0))


def test_detector_display_bounds_remain_finite_for_constant_negative_log_values() -> None:
    import polynexus.core.saxs_engine.figure_strain as figure_strain_module

    evidence = np.asarray([-307.0, -1.0, -1.0], dtype=float)
    evidence_before = evidence.copy()

    display = figure_strain_module._detector_display_values(
        evidence,
        np.asarray([False, True, True]),
    )

    assert np.all(np.isfinite(display))
    assert (float(np.min(display)), float(np.max(display))) == pytest.approx(
        (-1.01, -0.99)
    )
    assert np.array_equal(evidence, evidence_before)
