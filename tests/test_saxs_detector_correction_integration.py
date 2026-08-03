from __future__ import annotations

import copy
from dataclasses import replace

import numpy as np


def test_preprocess_default_correction_is_numerical_identity(monkeypatch) -> None:
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.config import SAXSConfig
    from polynexus.core.saxs_engine.saxs_detector_correction import (
        DetectorCorrectionRequest,
    )

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    cfg = SAXSConfig(
        is_isotropic=True,
        beam_center_x=2.0,
        beam_center_y=2.0,
        pixel_size_m=1.0e-4,
        n_pt=8,
        q_min=0.01,
        q_max=1.0,
        smooth_method="none",
    )
    image = np.arange(25, dtype=float).reshape(5, 5) + 1.0
    header = {"Center_1": "2", "Center_2": "2"}
    baseline = preprocess_module.preprocess_pipeline(
        image, copy.deepcopy(cfg), detector_header=header,
    )
    plugin = preprocess_module.preprocess_pipeline(
        image,
        copy.deepcopy(cfg),
        detector_header=header,
        detector_correction_request=DetectorCorrectionRequest.disabled("sample"),
    )

    np.testing.assert_array_equal(plugin["q"], baseline["q"])
    np.testing.assert_array_equal(plugin["Iq"], baseline["Iq"])
    assert plugin["detector_correction_evidence"]["applicable"] is False
    assert plugin["detector_quality_report"]["detector_correction_evidence"]["applicable"] is False


def test_one_effective_image_and_mask_feed_all_integrations(monkeypatch) -> None:
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.config import SAXSConfig
    from polynexus.core.saxs_engine.saxs_detector_correction import DetectorCorrectionRegistry
    from polynexus.core.saxs_engine.saxs_detector_correction import DetectorCalibrationFrame
    from polynexus.core.saxs_engine.saxs_orientation_reliability import CorrectionLedgerEntry
    from tests.test_saxs_detector_corrections import _reviewed_request

    captured = []

    def fake_sectors(_ai, detector_image, _cfg, mask=None):
        captured.append((detector_image.copy(), mask.copy()))
        q = np.linspace(0.1, 0.8, 4)
        values = np.ones(4, dtype=float)
        return q, values, values.copy(), values.copy()

    def fake_chi(_ai, detector_image, _cfg, mask=None):
        captured.append((detector_image.copy(), mask.copy()))
        return preprocess_module.SectorMapResult(
            np.linspace(0.1, 0.8, 4),
            np.ones((8, 4), dtype=float),
            np.linspace(-np.pi, np.pi, 8, endpoint=False),
            np.ones((8, 4), dtype=float),
            "test",
        )

    class Backend:
        policy_id = "test.backend"
        operation_order = ("dark_correction",)

        def apply_validated(self, sample, mask, request):
            corrected = sample.copy()
            corrected += 2.0
            return corrected, mask.copy(), (
                CorrectionLedgerEntry(
                    operation="dark_correction",
                    status="applied",
                    source="test-backend",
                ),
            )

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    monkeypatch.setattr(preprocess_module, "integrate_sectors", fake_sectors)
    monkeypatch.setattr(preprocess_module, "integrate_chi_sectors", fake_chi)
    cfg = SAXSConfig(
        experiment_type="strain",
        beam_center_x=2.0,
        beam_center_y=2.0,
        pixel_size_m=1.0e-4,
        n_pt=4,
        n_chi_sectors=8,
        q_min=0.01,
        q_max=1.0,
        smooth_method="none",
    )
    image = np.ones((5, 5), dtype=float)
    request = _reviewed_request()
    request = replace(
        request,
        frames=tuple(
            DetectorCalibrationFrame.from_array(
                role=frame.role,
                source_id=frame.source_id,
                image=np.ones((5, 5), dtype=float),
                metadata=frame.metadata,
            )
            for frame in request.frames
        ),
    )
    processed = preprocess_module.preprocess_pipeline(
        image,
        cfg,
        detector_correction_request=request,
        detector_correction_registry=DetectorCorrectionRegistry({"test.backend": Backend()}),
    )

    assert len(captured) == 2
    np.testing.assert_array_equal(captured[0][0], captured[1][0])
    np.testing.assert_array_equal(captured[0][1], captured[1][1])
    assert processed["integration_input_digest"] == processed["sector_map_input_digest"]
    assert processed["detector_correction_evidence"]["applicable"] is True
