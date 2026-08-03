from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from polynexus.core import get_engine
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    build_saxs_scientific_acceptance_audit,
)


def test_audit_surfaces_existing_guinier_sequence_level_and_reasons() -> None:
    parameters = {
        "paper_figure_candidate": False,
        "paper_conclusion_candidate": False,
        "paper_conclusion_ready": False,
        "guinier_sequence_evidence": {
            "level": "Unusable",
            "reason_codes": ["guinier_sequence_no_valid_frames"],
            "valid_frame_count": 0,
        },
    }
    before = copy.deepcopy(parameters)

    audit = build_saxs_scientific_acceptance_audit(True, parameters)

    assert audit["status"] == "diagnostic_only"
    assert audit["evidence_levels"]["guinier_sequence_evidence"] == ["Unusable"]
    assert "guinier_sequence_no_valid_frames" in audit["reason_codes"]
    assert parameters == before
    json.dumps(audit, allow_nan=False)


def test_real_pa6_audit_surfaces_guinier_sequence_reason(tmp_path: Path) -> None:
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

    audit = result.parameters["scientific_acceptance_audit"]
    assert audit["status"] == "diagnostic_only"
    assert audit["evidence_levels"]["guinier_sequence_evidence"] == ["Unusable"]
    assert "guinier_sequence_no_valid_frames" in audit["reason_codes"]
    json.dumps(audit, allow_nan=False)
