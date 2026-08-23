"""Contract tests for the direct-run compute DTOs."""

import json
from pathlib import Path
from types import MappingProxyType

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
    assert payload["dataset"]["template_id"] == "raw-file-envelope.v1"
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


def test_failed_compute_run_retains_pre_provider_provenance(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    artifact = RawArtifact.from_path(source, technique="ir")
    dataset = CanonicalDataset.direct_envelope(artifact)
    plan = AnalysisPlan.direct(dataset, output_dir=tmp_path / "out")

    failed = ComputeRun(
        status="failed",
        artifact=artifact,
        dataset=dataset,
        plan=plan,
        reasons=("provider_failure",),
    )

    payload = failed.to_dict()

    assert payload["status"] == "failed"
    assert payload["artifact"]["artifact_id"] == artifact.artifact_id
    assert payload["dataset"]["source_artifact_id"] == artifact.artifact_id
    assert payload["plan"]["dataset_id"] == dataset.dataset_id
    assert payload["result"] is None
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload

    failed_before_conversion = ComputeRun(status="failed", artifact=artifact)
    assert failed_before_conversion.to_dict()["dataset"] is None
    assert failed_before_conversion.to_dict()["plan"] is None

    with pytest.raises(ValueError, match="both dataset and plan"):
        ComputeRun(status="failed", artifact=artifact, dataset=dataset)
    with pytest.raises(ValueError, match="cannot include a result"):
        ComputeRun(
            status="failed",
            artifact=artifact,
            dataset=dataset,
            plan=plan,
            result=ComputeResult(),
        )


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


def test_legacy_projection_scrubs_nested_paper_and_review_fields(tmp_path: Path) -> None:
    class FakeResult:
        parameters = {
            "peak_cm-1": 1630.0,
            "analysis_evidence": {"hidden": True},
            "nested": {
                "writing_eligibility": "blocked",
                "values": [{"manuscript_role": "results", "intensity": 4.2}],
            },
        }
        figures = {"spectrum": "spectrum.svg", "review_required": "internal.svg"}
        metadata = {
            "review_required": True,
            "evidence": {"hidden": True},
            "nested": {"manuscript_candidate": True, "provider": "legacy"},
        }
        validation_warnings = ()
        quality_flags = {}
        validation_summary = "All checks passed"

        @property
        def analysis_evidence(self) -> object:
            raise AssertionError("ComputeResult must not read analysis evidence")

    artifact = RawArtifact(
        artifact_id="artifact",
        path="curve.csv",
        technique="ir",
        format="csv",
        sha256="digest",
    )
    dataset = CanonicalDataset.direct_envelope(artifact)
    plan = AnalysisPlan.direct(dataset, output_dir=tmp_path / "out")
    run = ComputeRun.completed(
        artifact=artifact,
        dataset=dataset,
        plan=plan,
        result=ComputeResult.from_legacy_result(FakeResult()),
    )

    payload = run.to_dict()
    payload_text = json.dumps(payload, sort_keys=True)

    assert payload["result"]["metrics"]["peak_cm-1"] == 1630.0
    assert payload["result"]["metrics"]["nested"]["values"] == [{"intensity": 4.2}]
    assert payload["result"]["figures"] == {"spectrum": "spectrum.svg"}
    assert payload["result"]["metadata"]["nested"] == {"provider": "legacy"}
    for forbidden_key in (
        "analysis_evidence",
        "writing_eligibility",
        "manuscript_role",
        "manuscript_candidate",
        "review_required",
        "evidence",
    ):
        assert f'"{forbidden_key}"' not in payload_text


def test_contracts_reject_nonfinite_floats(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="non-finite"):
        RawArtifact.from_path(source, technique="ir", observed_facts={"signal": float("nan")})


def test_public_contracts_reject_non_json_values_at_construction() -> None:
    with pytest.raises(TypeError, match="artifact_id must be a string or path"):
        RawArtifact(
            artifact_id=object(),
            path="curve.csv",
            technique="ir",
            format="csv",
            sha256="digest",
        )

    with pytest.raises(TypeError, match="Unsupported compute contract value"):
        RawArtifact(
            artifact_id="artifact",
            path="curve.csv",
            technique="ir",
            format="csv",
            sha256="digest",
            observed_facts={"opaque": object()},
        )


def test_public_contracts_freeze_json_values_at_construction() -> None:
    artifact = RawArtifact(
        artifact_id="artifact",
        path=Path("curve.csv"),
        technique="ir",
        format="csv",
        sha256="digest",
        observed_facts={"rows": [2]},
    )
    dataset = CanonicalDataset(
        dataset_id="dataset",
        source_artifact_id=artifact.artifact_id,
        technique="ir",
        template_id="template.v1",
        payload={"channels": ["wavenumber", "absorbance"]},
        warnings=["canonicalized"],
    )
    plan = AnalysisPlan(
        plan_id="plan",
        dataset_id=dataset.dataset_id,
        technique="ir",
        output_dir=Path("out"),
        pipeline_options={"baseline": "auto"},
        parameter_sources={"baseline": "user"},
    )
    result = ComputeResult(
        metrics={"peak_cm-1": 1630.0},
        figures={"spectrum": Path("spectrum.svg")},
        metadata={"provider": "legacy"},
        warnings=["review"],
    )
    run = ComputeRun(
        status="ready",
        artifact=artifact,
        dataset=dataset,
        plan=plan,
        reasons=["awaiting_provider"],
    )

    assert artifact.path == "curve.csv"
    assert plan.output_dir == "out"
    assert result.figures["spectrum"] == "spectrum.svg"
    assert all(
        isinstance(value, MappingProxyType)
        for value in (
            artifact.observed_facts,
            dataset.payload,
            plan.pipeline_options,
            plan.parameter_sources,
            result.metrics,
            result.figures,
            result.metadata,
        )
    )
    assert dataset.warnings == ("canonicalized",)
    assert result.warnings == ("review",)
    assert run.reasons == ("awaiting_provider",)
    assert json.loads(json.dumps(run.to_dict(), sort_keys=True)) == run.to_dict()
