from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from polynexus.core import get_engine
from polynexus.core.saxs_engine.core import SAXSResult, StructureParams


def test_static_single_parameters_expose_existing_acceptance_audit() -> None:
    engine = get_engine("saxs", submodule_id="saxs.static")
    result = SAXSResult(
        structure=StructureParams(L=12.0, lc=4.0, la=8.0),
        data_quality_report={"level": "Diagnostic"},
        metric_evidence={
            "porod": {
                "level": "Diagnostic",
                "reason_codes": ["porod_applicability_unresolved"],
            }
        },
    )
    engine._analysis = result  # type: ignore[attr-defined]

    params = engine.get_parameters()

    audit = params["scientific_acceptance_audit"]
    assert audit["status"] == "diagnostic_only"
    assert audit["existing_publication_gate"] == {
        "paper_figure_candidate": None,
        "paper_conclusion_candidate": None,
        "paper_conclusion_ready": None,
    }
    assert audit["publication_decision_changed"] is False
    assert "porod_applicability_unresolved" in audit["reason_codes"]
    json.dumps(audit, allow_nan=False)


def test_static_batch_parameters_keep_alignment_and_expose_audit() -> None:
    engine = get_engine("saxs", submodule_id="saxs.static")
    first = SAXSResult(
        structure=StructureParams(L=12.0),
        metric_evidence={"porod": {"level": "Trend", "value": 1.0}},
    )
    third = SAXSResult(
        structure=StructureParams(L=13.0),
        metric_evidence={"porod": {"level": "Diagnostic", "value": 0.5}},
    )
    engine._batch_results = [first, None, third]  # type: ignore[attr-defined]
    engine._batch_params = [  # type: ignore[attr-defined]
        {"file": "frame_001.dat", "L_nm": 12.0},
        {"file": "frame_002.dat", "L_nm": None},
        {"file": "frame_003.dat", "L_nm": 13.0},
    ]
    before = copy.deepcopy(engine._batch_params)  # type: ignore[attr-defined]

    params = engine.get_parameters()

    assert params["scientific_acceptance_audit"]["status"] == "diagnostic_only"
    assert [row["file"] for row in params["_batch_data"]] == [
        "frame_001.dat",
        "frame_002.dat",
        "frame_003.dat",
    ]
    assert params["metric_evidence"]["porod"]["missing_frame_count"] == 1
    assert engine._batch_params == before  # type: ignore[attr-defined]
    json.dumps(params["scientific_acceptance_audit"], allow_nan=False)


def test_real_static_directory_exposes_acceptance_audit(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    source = project_root / "测试数据" / "saxs" / "普通小角"
    if not source.exists():
        pytest.skip(f"real Static SAXS fixture unavailable: {source}")

    engine = get_engine(
        "saxs",
        config={"fig_format": "png"},
        submodule_id="saxs.static",
    )
    result = engine.run_pipeline(str(source), str(tmp_path / "output"))

    audit = result.parameters["scientific_acceptance_audit"]
    assert audit["audit_scope"] == "existing_gates_only"
    assert audit["publication_decision_changed"] is False
    json.dumps(audit, allow_nan=False)
