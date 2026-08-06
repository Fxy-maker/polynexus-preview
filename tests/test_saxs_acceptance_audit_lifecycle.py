from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from polynexus.core import get_engine
from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult
from polynexus.core.saxs_engine.io import ExperimentCondition


def _temperature_engine_with_prevalidation_payload() -> SAXSEngine:
    engine = SAXSEngine(SAXSConfig(experiment_type="temperature"))
    engine.result.validation_passed = True
    engine._temperature_result = TempSeriesResult(  # type: ignore[attr-defined]
        temperatures=np.asarray([170.0, 180.0]),
        lc_array=np.asarray([3.0, 3.1]),
        lc_effective_array=np.asarray([3.0, 3.1]),
        raw_detector_quality_report={"level": "Trend", "reason_codes": []},
    )
    engine.result.parameters = engine.get_parameters()
    return engine


def test_saxs_audit_refreshes_to_final_validation_state() -> None:
    engine = _temperature_engine_with_prevalidation_payload()

    assert engine.result.parameters["scientific_acceptance_audit"][
        "automated_validation_passed"
    ] is True

    engine.add_quality_flag("temperature/validation", "ERROR")
    engine._validate_results()

    audit = engine.result.parameters["scientific_acceptance_audit"]
    assert engine.result.validation_passed is False
    assert audit["automated_validation_passed"] is False
    assert audit["status"] == "diagnostic_only"
    assert audit["publication_decision_changed"] is False
    json.dumps(audit, allow_nan=False)


def test_real_pa6_audit_matches_final_validation(tmp_path: Path) -> None:
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
    assert audit["automated_validation_passed"] is False
    assert audit["status"] == "diagnostic_only"
    assert audit["publication_decision_changed"] is False
    assert "guinier_sequence_no_valid_frames" in result.parameters[
        "guinier_sequence_evidence"
    ]["reason_codes"]
    json.dumps(audit, allow_nan=False)


def test_directory_with_discovered_but_zero_valid_frames_fails_closed(monkeypatch, tmp_path: Path) -> None:
    import polynexus.core.saxs as saxs_module

    source = tmp_path / "invalid.edf"
    source.write_bytes(b"not-an-edf")
    condition = ExperimentCondition(
        label="static",
        value=0.0,
        condition_key="static",
        files=[str(source)],
    )
    monkeypatch.setattr(saxs_module, "scan_experiment_dir", lambda *_args: [condition])
    monkeypatch.setattr(saxs_module, "read_image", lambda _path: (_ for _ in ()).throw(ValueError("bad frame")))

    engine = SAXSEngine(SAXSConfig())

    assert engine._load_directory(str(tmp_path)) is False
    assert engine.result.validation_passed is False
    assert engine.result.quality_flags["saxs"] == "ERROR"
    assert engine.result.metadata["sequence_qa"]["loaded_frame_count"] == 0
    assert "no_valid_frames" in engine.result.metadata["sequence_qa"]["reason_codes"]
