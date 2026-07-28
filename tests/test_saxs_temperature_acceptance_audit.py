from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from polynexus.core import get_engine
from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult


def test_temperature_parameters_attach_existing_acceptance_audit() -> None:
    engine = SAXSEngine(SAXSConfig(experiment_type="temperature"))
    engine.result.validation_passed = False
    sequence = {
        "level": "Unusable",
        "reason_codes": ["guinier_sequence_no_valid_frames"],
        "valid_frame_count": 0,
    }
    engine._temperature_result = TempSeriesResult(  # type: ignore[attr-defined]
        temperatures=np.asarray([170.0, 180.0]),
        lc_array=np.asarray([np.nan, np.nan]),
        lc_effective_array=np.asarray([np.nan, np.nan]),
        guinier_sequence_evidence=sequence,
        raw_detector_quality_report={
            "level": "Unusable",
            "reason_codes": ["nonpositive_pixels"],
        },
    )

    params = engine.get_parameters()

    audit = params["scientific_acceptance_audit"]
    assert audit["status"] == "diagnostic_only"
    assert audit["automated_validation_passed"] is False
    assert audit["publication_decision_changed"] is False
    assert params["guinier_sequence_evidence"] == sequence
    assert "guinier_sequence_no_valid_frames" in sequence["reason_codes"]
    json.dumps(audit, allow_nan=False)


def test_real_pa6_temperature_exposes_existing_diagnostic_boundary(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    source = project_root / "测试数据" / "saxs" / "pa6变温"
    if not source.exists():
        pytest.skip(f"real PA6 temperature fixture unavailable: {source}")

    engine = get_engine(
        "saxs",
        config={"fig_format": "png"},
        submodule_id="saxs.temperature",
    )
    result = engine.run_pipeline(str(source), str(tmp_path / "output"))

    assert result.validation_passed is False
    audit = result.parameters["scientific_acceptance_audit"]
    assert audit["status"] == "diagnostic_only"
    assert audit["publication_decision_changed"] is False
    sequence = result.parameters["guinier_sequence_evidence"]
    assert sequence["level"] == "Unusable"
    assert "guinier_sequence_no_valid_frames" in sequence["reason_codes"]
    json.dumps(audit, allow_nan=False)
