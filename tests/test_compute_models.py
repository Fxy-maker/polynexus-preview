"""Contract tests for the direct-run compute DTOs."""

import json
from pathlib import Path

import pytest

from polynexus.core.compute.models import (
    AnalysisPlan,
    CanonicalDataset,
    ComputeResult,
    ComputeRun,
    RawArtifact,
)


def test_direct_contract_hashes_are_stable_json_safe_and_provenance_linked(
    tmp_path: Path,
) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")

    artifact = RawArtifact.from_path(source, technique="ir", observed_facts={"rows": 2})
    repeated_artifact = RawArtifact.from_path(source, technique="ir", observed_facts={"rows": 2})
    dataset = CanonicalDataset.direct_envelope(artifact)
    plan = AnalysisPlan.direct(
        dataset,
        output_dir=tmp_path / "out",
        pipeline_options={"baseline": "auto"},
    )
    repeated_plan = AnalysisPlan.direct(
        dataset,
        output_dir=tmp_path / "out",
        pipeline_options={"baseline": "auto"},
    )
    run = ComputeRun.completed(
        artifact=artifact,
        dataset=dataset,
        plan=plan,
        result=ComputeResult(metrics={"peak_cm-1": 1630.0}, warnings=("auto_baseline",)),
    )

    payload = run.to_dict()

    assert artifact.artifact_id == repeated_artifact.artifact_id
    assert plan.plan_id == repeated_plan.plan_id
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload
    assert payload["status"] == "completed"
    assert payload["artifact"]["sha256"] == artifact.sha256
    assert payload["dataset"]["source_artifact_id"] == artifact.artifact_id
    assert payload["dataset"]["payload"]["kind"] == "raw_file"
    assert payload["plan"]["dataset_id"] == dataset.dataset_id
    assert payload["result"]["metrics"] == {"peak_cm-1": 1630.0}
    assert "analysis_evidence" not in str(payload)
    assert "writing_eligibility" not in str(payload)


def test_compute_run_rejects_review_required_status(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    artifact = RawArtifact.from_path(source, technique="ir")

    with pytest.raises(ValueError, match="Unsupported compute status"):
        ComputeRun(status="review_required", artifact=artifact, reasons=("legacy",))


def test_missing_artifact_cannot_make_a_direct_envelope(tmp_path: Path) -> None:
    artifact = RawArtifact.missing(tmp_path / "missing.csv", technique="ir")

    assert artifact.sha256 == ""
    with pytest.raises(ValueError, match="content hash"):
        CanonicalDataset.direct_envelope(artifact)


def test_legacy_projection_collects_warnings_without_reading_analysis_evidence() -> None:
    class FakeResult:
        parameters = {"peak_cm-1": 1630.0}
        figures = {"spectrum": "spectrum.svg"}
        metadata = {"provider": "fake"}
        validation_warnings = ["auto_baseline"]
        quality_flags = {"fit": "WARN", "normalization": "OK"}
        validation_summary = "fit needs inspection"

        @property
        def analysis_evidence(self) -> object:
            raise AssertionError("ComputeResult must not read analysis evidence")

    result = ComputeResult.from_legacy_result(FakeResult())
    payload = ComputeRun(
        status="failed",
        artifact=RawArtifact.missing("missing.csv", technique="ir"),
        reasons=("legacy_failure",),
        legacy_result=FakeResult(),
    ).to_dict()

    assert dict(result.metrics) == {"peak_cm-1": 1630.0}
    assert dict(result.figures) == {"spectrum": "spectrum.svg"}
    assert dict(result.metadata) == {"provider": "fake"}
    assert result.warnings == ("auto_baseline", "quality_flag:fit:WARN", "fit needs inspection")
    assert "legacy_result" not in payload
    assert "analysis_evidence" not in str(payload)


def test_contracts_reject_nonfinite_floats(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="non-finite"):
        RawArtifact.from_path(source, technique="ir", observed_facts={"signal": float("nan")})
