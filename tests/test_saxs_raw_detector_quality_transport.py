from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np


def _config():
    from polynexus.core.saxs_engine.config import SAXSConfig

    return SAXSConfig(
        experiment_type="strain",
        is_isotropic=True,
        beam_center_x=1.0,
        beam_center_y=1.0,
        pixel_size_m=1.0e-4,
        sdd_m=0.45,
        n_pt=8,
        q_min=0.01,
        q_max=1.0,
        smooth_method="none",
        dummy_val=-1.5,
        ddummy=0.05,
    )


def test_preprocess_pipeline_publishes_explicit_raw_detector_report(monkeypatch):
    from polynexus.core.saxs_engine import preprocess as preprocess_module

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    image = np.asarray([[1.0, 2.0], [-1.5, 9.0]])

    processed = preprocess_module.preprocess_pipeline(
        image,
        _config(),
        detector_header={"Saturation": "9", "Center_1": "1", "Center_2": "1"},
    )

    report = processed["detector_quality_report"]
    assert report["source_kind"] == "raw_detector"
    assert report["saturation_detection_available"] is True
    assert report["saturated_pixel_count"] == 1
    assert report["masked_pixel_count"] == 1
    assert report["beam_center"] == [1.0, 1.0]
    json.dumps(report, allow_nan=False)


def test_preprocess_pipeline_does_not_guess_missing_detector_evidence(monkeypatch):
    from polynexus.core.saxs_engine import preprocess as preprocess_module

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    image = np.asarray([[1.0, 2.0], [3.0, 8.0]])

    processed = preprocess_module.preprocess_pipeline(image, _config(), detector_header={})

    report = processed["detector_quality_report"]
    assert report["source_kind"] == "raw_detector"
    assert report["saturation_detection_available"] is False
    assert report["saturated_pixel_count"] == 0
    assert "detector_saturation_unknown" in report["reason_codes"]
    assert "beam_center_missing" in report["reason_codes"]


def test_raw_report_transports_complete_geometry_and_mask_provenance(monkeypatch):
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.io import extract_geometry_from_header

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    header = {
        "WaveLength": "1.54e-10",
        "PixelSize": "75e-6",
        "SampleDistance": "0.45",
        "Center_1": "1",
        "Center_2": "1",
    }
    cfg = extract_geometry_from_header(header, _config())
    processed = preprocess_module.preprocess_pipeline(
        np.asarray([[1.0, 2.0], [-1.5, 9.0]]),
        cfg,
        detector_header=header,
    )

    report = processed["detector_quality_report"]
    geometry = report["geometry_provenance"]
    assert geometry["source"] == "header"
    assert set(geometry["field_sources"].values()) == {"header"}
    assert geometry["values"] == {
        "wavelength_m": 1.54e-10,
        "pixel_size_m": 75e-6,
        "sdd_m": 0.45,
        "beam_center_x": 1.0,
        "beam_center_y": 1.0,
    }
    assert geometry["validity"] == "metadata_complete"
    assert report["mask_provenance"] == {
        "source": "saxs_config.dummy_value",
        "configured": True,
        "shape": [2, 2],
        "validity": "configured_shape_match",
    }
    json.dumps(report, allow_nan=False)


def test_raw_report_distinguishes_mixed_and_invalid_geometry_without_gate_changes(
    monkeypatch,
):
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.io import extract_geometry_from_header

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    header = {"WaveLength": "1.54e-10", "PixelSize": "not-a-number"}
    cfg = extract_geometry_from_header(header, _config())
    processed = preprocess_module.preprocess_pipeline(
        np.asarray([[1.0, 2.0], [3.0, 8.0]]),
        cfg,
        detector_header=header,
    )

    report = processed["detector_quality_report"]
    geometry = report["geometry_provenance"]
    assert geometry["source"] == "invalid_header"
    assert geometry["field_sources"] == {
        "wavelength_m": "header",
        "pixel_size_m": "invalid_header",
        "sdd_m": "config_default",
        "beam_center_x": "config_default",
        "beam_center_y": "config_default",
    }
    assert geometry["validity"] == "invalid"
    assert report["level"] == "Diagnostic"
    assert "beam_center_missing" in report["reason_codes"]


def test_raw_report_marks_unconfigured_mask_without_inference(monkeypatch):
    from polynexus.core.saxs_engine import preprocess as preprocess_module

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    cfg = _config()
    cfg.dummy_val = np.nan
    processed = preprocess_module.preprocess_pipeline(
        np.asarray([[1.0, 2.0], [3.0, 8.0]]), cfg, detector_header={}
    )

    assert processed["detector_quality_report"]["mask_provenance"] == {
        "source": "none",
        "configured": False,
        "shape": None,
        "validity": "not_assessed",
    }


def test_directory_load_retains_one_raw_report_per_image_frame(tmp_path, monkeypatch):
    from polynexus.core import saxs as saxs_module
    from polynexus.core.saxs_engine.config import ExperimentCondition

    first = str(tmp_path / "frame-000.edf")
    second = str(tmp_path / "frame-008.edf")
    monkeypatch.setattr(
        saxs_module,
        "scan_experiment_dir",
        lambda _path, _cfg: [
            ExperimentCondition(value=0.0, files=[first]),
            ExperimentCondition(value=8.0, files=[second]),
        ],
    )

    def fake_read_image(path):
        return np.ones((2, 2)), {"Saturation": "4", "Center_1": "1", "Center_2": "1"}

    def fake_preprocess(image, cfg, detector_header=None):
        del image, cfg
        return {
            "q": np.linspace(0.1, 0.5, 8),
            "Iq": np.ones(8),
            "Iq_smooth": np.ones(8),
            "sector_data": None,
            "detector_quality_report": {
                "source_kind": "raw_detector",
                "source_header_saturation": detector_header["Saturation"],
            },
        }

    monkeypatch.setattr(saxs_module, "read_image", fake_read_image)
    monkeypatch.setattr(saxs_module, "preprocess_pipeline", fake_preprocess)
    monkeypatch.setattr(
        saxs_module,
        "_integrate_pyfai_shadow",
        lambda _image, _cfg: (np.array([]), np.array([])),
    )

    engine = saxs_module.SAXSEngine(config=_config())

    assert engine.load(str(tmp_path)) is True
    assert engine._detector_quality_reports == [  # type: ignore[attr-defined]
        {"source_kind": "raw_detector", "source_header_saturation": "4"},
        {"source_kind": "raw_detector", "source_header_saturation": "4"},
    ]


def _fake_analysis():
    return SimpleNamespace(
        long_period=SimpleNamespace(L_best=10.0, L_confidence=0.8, method_used="bragg"),
        structure=SimpleNamespace(
            lc=3.0,
            la=7.0,
            phi_c=0.3,
            confidence_lc=0.8,
            lc_tangent_nm=np.nan,
            lc_idf_nm=np.nan,
            lc_gamma_min_nm=np.nan,
        ),
        data_quality_report={"level": "Trend"},
        guinier_evidence=None,
        metric_evidence={},
        detector_quality_report=None,
        orientation_evidence=None,
    )


def test_temperature_raw_reports_follow_source_index_after_sort(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = np.ones_like(q)
    monkeypatch.setattr(module, "analyze_single", lambda *_args, **_kwargs: _fake_analysis())
    monkeypatch.setattr(module, "scattering_invariant", lambda *_args, **_kwargs: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda *_args, **_kwargs: (10.0, 0.628, {}))

    reports = [
        {"source_kind": "raw_detector", "source_id": "original-180"},
        {"source_kind": "raw_detector", "source_id": "original-170"},
    ]
    result = module.analyze_temperature_series(
        [180.0, 170.0],
        [q, q],
        [intensity, intensity],
        cfg=_config(),
        detector_quality_reports=reports,
    )

    assert [point.source_index for point in result.temp_points] == [1, 0]
    assert [point.raw_detector_quality_report["source_id"] for point in result.temp_points] == [
        "original-170",
        "original-180",
    ]
    assert result.raw_detector_quality_report["source_kinds"] == ["raw_detector"]


def test_strain_keeps_raw_detector_and_sector_map_reports_separate(monkeypatch):
    import polynexus.core.saxs_engine.saxs_strain as module

    q = np.linspace(0.02, 0.6, 24)
    chi = np.linspace(-np.pi, np.pi, 36, endpoint=False)
    I_2d = (1.0 + 0.4 * np.cos(2.0 * chi))[:, None] * np.ones((1, q.size))
    sector_data = {
        "I_2d": I_2d,
        "q_2d": q,
        "chi_rad": chi,
        "q": q,
        "I_full": np.mean(I_2d, axis=0),
    }
    intensity = np.ones_like(q)
    monkeypatch.setattr(module, "analyze_single", lambda *_args, **_kwargs: _fake_analysis())
    monkeypatch.setattr(module, "scattering_invariant", lambda *_args, **_kwargs: 1.0)

    result = module.analyze_strain_series(
        [0.0, 10.0],
        [q, q],
        [intensity, intensity],
        sector_data_list=[sector_data, sector_data],
        cfg=_config(),
        detector_quality_reports=[
            {"source_kind": "raw_detector", "source_id": "raw-0"},
            {"source_kind": "raw_detector", "source_id": "raw-1"},
        ],
    )

    assert result.strain_points[0].detector_quality_report["source_kind"] == "sector_map"
    assert result.strain_points[0].raw_detector_quality_report["source_id"] == "raw-0"
    assert result.detector_quality_report["source_kinds"] == ["sector_map"]
    assert result.raw_detector_quality_report["source_kinds"] == ["raw_detector"]
    json.dumps(result.raw_detector_quality_report, allow_nan=False)


def test_raw_report_survives_existing_figure_and_export_evidence_boundaries():
    from polynexus.core.saxs_engine.figure_common import SAXSFrameView
    from polynexus.core.saxs_engine.figure_evidence import build_saxs_figure_evidence
    from polynexus.core.saxs_export_bundle import _quality_object_payload

    report = {
        "source_kind": "raw_detector",
        "level": "Diagnostic",
        "reason_codes": ["detector_saturation_unknown"],
        "coverage_fraction": 0.75,
        "geometry_provenance": {
            "source": "mixed",
            "field_sources": {"sdd_m": "config_default"},
            "values": {"sdd_m": 0.45},
            "validity": "not_assessed",
        },
        "mask_provenance": {
            "source": "none",
            "configured": False,
            "shape": None,
            "validity": "not_assessed",
        },
    }
    analysis = SimpleNamespace(raw_detector_quality_report=report)
    frame = SAXSFrameView(
        index=0,
        label="frame-0",
        condition=0.0,
        q=np.asarray([0.1, 0.2]),
        intensity=np.asarray([1.0, 2.0]),
        analysis=analysis,
        parameters={},
    )

    export_payload = _quality_object_payload(analysis)
    figure_payload = build_saxs_figure_evidence(
        [frame],
        mode="static",
        series=SimpleNamespace(raw_detector_quality_report=report),
    )

    assert export_payload["raw_detector_quality_report"]["source_kind"] == "raw_detector"
    assert (
        figure_payload["frame_records"][0]["raw_detector_quality_report"]["source_kind"]
        == "raw_detector"
    )
    assert (
        figure_payload["series_record"]["raw_detector_quality_report"]["source_kind"]
        == "raw_detector"
    )
    assert (
        figure_payload["frame_records"][0]["raw_detector_quality_report"][
            "geometry_provenance"
        ]["source"]
        == "mixed"
    )
    assert (
        figure_payload["series_record"]["raw_detector_quality_report"][
            "mask_provenance"
        ]["source"]
        == "none"
    )

    sector_report = {
        "source_kind": "sector_map",
        "level": "Diagnostic",
        "geometry_provenance": {"source": "should-not-be-present"},
        "mask_provenance": {"source": "should-not-be-present"},
    }
    sector_frame = SAXSFrameView(
        index=1,
        label="sector-frame",
        condition=0.0,
        q=np.asarray([0.1, 0.2]),
        intensity=np.asarray([1.0, 2.0]),
        analysis=SimpleNamespace(detector_quality_report=sector_report),
        parameters={},
    )
    sector_payload = build_saxs_figure_evidence([sector_frame], mode="static")
    projected_sector = sector_payload["frame_records"][0]["detector_quality_report"]
    assert "geometry_provenance" not in projected_sector
    assert "mask_provenance" not in projected_sector
    json.dumps(figure_payload, allow_nan=False)
