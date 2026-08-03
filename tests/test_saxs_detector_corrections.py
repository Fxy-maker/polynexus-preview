from __future__ import annotations

import json

import numpy as np


def _reviewed_request(policy_id: str = "test.backend"):
    from polynexus.core.saxs_engine.saxs_detector_correction import (
        DetectorCalibrationFrame,
        DetectorCorrectionRequest,
    )

    frame = DetectorCalibrationFrame.from_array(
        role="dark",
        source_id="dark-1",
        image=np.ones((2, 2), dtype=float),
        metadata={
            "detector_model": "test-detector",
            "detector_serial_number": "serial-1",
            "exposure_time_s": 1.0,
            "geometry_digest": "geo-1",
        },
    )
    return DetectorCorrectionRequest(
        mode="reviewed",
        sample_source_id="sample-1",
        policy_id=policy_id,
        review_record_digest="review-1",
        frames=(frame,),
        explicit_scalars={
            "sample_exposure_s": 1.0,
            "transmission_sample": 1.0,
            "sample_thickness_m": 1.0,
        },
        geometry_digest="geo-1",
    )


def test_disabled_request_is_identity_and_strict_json_safe() -> None:
    from polynexus.core.saxs_engine.saxs_detector_correction import (
        DetectorCorrectionRequest,
        evaluate_detector_correction,
    )

    image = np.arange(16, dtype=float).reshape(4, 4)
    mask = np.zeros_like(image, dtype=bool)
    result = evaluate_detector_correction(
        image,
        mask,
        DetectorCorrectionRequest.disabled(sample_source_id="sample-1"),
    )

    np.testing.assert_array_equal(result.effective_image, image)
    np.testing.assert_array_equal(result.effective_mask, mask)
    assert result.applicable is False
    assert result.level == "Diagnostic"
    json.dumps(result.to_evidence_dict(), allow_nan=False)


def test_default_registry_has_no_production_backend() -> None:
    from polynexus.core.saxs_engine.saxs_detector_correction import (
        default_detector_correction_registry,
    )

    assert default_detector_correction_registry().policy_ids == ()


def test_reviewed_backend_commits_one_transaction_without_clipping_negative_pixels() -> None:
    from polynexus.core.saxs_engine.saxs_detector_correction import (
        DetectorCorrectionRegistry,
        evaluate_detector_correction,
    )
    from polynexus.core.saxs_engine.saxs_orientation_reliability import (
        CorrectionLedgerEntry,
    )

    class Backend:
        policy_id = "test.backend"
        operation_order = ("dark_correction",)

        def apply_validated(self, sample, mask, request):
            corrected = sample.copy()
            corrected[0, 0] = -3.0
            return (
                corrected,
                mask.copy(),
                (
                    CorrectionLedgerEntry(
                        operation="dark_correction",
                        status="applied",
                        source="test-backend",
                    ),
                ),
            )

    image = np.ones((2, 2), dtype=float)
    mask = np.zeros_like(image, dtype=bool)
    result = evaluate_detector_correction(
        image,
        mask,
        _reviewed_request(),
        registry=DetectorCorrectionRegistry({"test.backend": Backend()}),
    )

    assert result.applicable is True
    assert result.effective_image[0, 0] == -3.0
    assert result.effective_mask is not mask
    assert result.correction_ledger[0].status == "applied"
    np.testing.assert_array_equal(image, np.ones((2, 2), dtype=float))


def test_candidate_backend_never_promotes_candidate_pixels() -> None:
    from dataclasses import replace

    from polynexus.core.saxs_engine.saxs_detector_correction import (
        DetectorCorrectionRegistry,
        evaluate_detector_correction,
    )

    class Backend:
        policy_id = "test.backend"
        operation_order = ("dark_correction",)

        def apply_validated(self, sample, mask, request):
            return sample + 10.0, mask, ()

    image = np.ones((2, 2), dtype=float)
    result = evaluate_detector_correction(
        image,
        np.zeros_like(image, dtype=bool),
        replace(_reviewed_request(), mode="candidate"),
        registry=DetectorCorrectionRegistry({"test.backend": Backend()}),
    )

    np.testing.assert_array_equal(result.effective_image, image)
    assert result.applicable is False
    assert "detector_correction_candidate_only" in result.reason_codes
