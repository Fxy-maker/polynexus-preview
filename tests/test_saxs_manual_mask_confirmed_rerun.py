"""TDD coverage for the SAXS manual-mask candidate boundary."""

import json

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.preprocess import preprocess_pipeline
from polynexus.core.saxs_engine.saxs_mask_edit import (
    MaskEditValidationError,
    apply_confirmed_mask_edit,
    build_mask_edit_candidate,
    confirm_mask_edit_candidate,
)


def _mask_pair() -> tuple[np.ndarray, np.ndarray]:
    base = np.zeros((4, 5), dtype=bool)
    edited = base.copy()
    edited[1, 2] = True
    edited[3, 4] = True
    return base, edited


def _config() -> SAXSConfig:
    return SAXSConfig(
        is_isotropic=True,
        analysis_priority="isotropic",
        use_pyfai_integration=False,
        dummy_val=np.nan,
        q_min=0.01,
        q_max=5.0,
        n_pt=12,
        smooth_method="none",
        sample_thickness_m=1.0,
        transmission_sample=1.0,
    )


def test_mask_candidate_is_detached_json_safe_and_explicit() -> None:
    base, edited = _mask_pair()

    candidate = build_mask_edit_candidate(
        base,
        edited,
        source_path="sample.edf",
        frame_index=3,
    )

    json.dumps(candidate)
    assert candidate["schema_version"] == 1
    assert candidate["confirmed"] is False
    assert candidate["shape"] == [4, 5]
    assert candidate["source_path"] == "sample.edf"
    assert candidate["frame_index"] == 3
    assert candidate["operations"] == [[1, 2, True], [3, 4, True]]
    assert "base_mask" not in candidate
    assert "edited_mask" not in candidate


def test_pending_mask_candidate_is_noop_and_visible_in_provenance() -> None:
    image = np.arange(16, dtype=float).reshape(4, 4) + 1.0
    base = np.zeros_like(image, dtype=bool)
    edited = base.copy()
    edited[1, 1] = True
    candidate = build_mask_edit_candidate(base, edited, source_path="sample.edf")

    result = preprocess_pipeline(image, _config(), mask_edit_candidate=candidate)

    assert result["detector_quality_report"]["masked_pixel_count"] == 0
    assert result["detector_quality_report"]["mask_provenance"]["edit_status"] == "candidate_only"
    assert np.array_equal(image, np.arange(16, dtype=float).reshape(4, 4) + 1.0)


def test_mask_candidate_digest_mismatch_fails_closed_without_applying() -> None:
    base, edited = _mask_pair()
    candidate = build_mask_edit_candidate(base, edited)
    changed_base = base.copy()
    changed_base[0, 0] = True

    with pytest.raises(MaskEditValidationError):
        confirm_mask_edit_candidate(candidate, changed_base)
    with pytest.raises(MaskEditValidationError):
        apply_confirmed_mask_edit(base, candidate)


def test_confirmed_mask_candidate_reaches_existing_preprocessing_quality_report() -> None:
    image = np.arange(16, dtype=float).reshape(4, 4) + 1.0
    base = np.zeros_like(image, dtype=bool)
    edited = base.copy()
    edited[1, 1] = True
    candidate = build_mask_edit_candidate(base, edited, source_path="sample.edf")
    confirmed = confirm_mask_edit_candidate(candidate, base)

    applied = apply_confirmed_mask_edit(base, confirmed)
    result = preprocess_pipeline(image, _config(), mask_edit_candidate=confirmed)

    assert bool(applied[1, 1]) is True
    assert not base.any()
    report = result["detector_quality_report"]
    assert report["masked_pixel_count"] == 1
    assert report["mask_provenance"]["edit_status"] == "confirmed"
    assert report["mask_provenance"]["changed_pixel_count"] == 1


def test_confirmed_mask_candidate_reaches_sector_and_azimuthal_paths() -> None:
    image = np.arange(64, dtype=float).reshape(8, 8) + 1.0
    base = np.zeros_like(image, dtype=bool)
    edited = base.copy()
    edited[2, 3] = True
    candidate = build_mask_edit_candidate(base, edited, source_path="sample.edf")
    confirmed = confirm_mask_edit_candidate(candidate, base)
    cfg = _config()
    cfg.is_isotropic = False
    cfg.analysis_priority = "anisotropic"
    cfg.n_chi_sectors = 16

    result = preprocess_pipeline(image, cfg, mask_edit_candidate=confirmed)

    assert result["detector_quality_report"]["masked_pixel_count"] == 1
    assert result["sector_data"]["I_2d"].shape[0] == 16
    assert result["sector_data"]["I_2d"].shape[1] == len(result["sector_data"]["q_2d"])
