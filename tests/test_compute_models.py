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


_FORBIDDEN_RESULT_KEY_NAMES = frozenset(
    {
        "analysis_evidence",
        "evidence",
        "evidence_package",
        "writing_eligibility",
        "writing_status",
        "manuscript_role",
        "manuscript_candidate",
        "manuscript_status",
        "review_required",
        "review_notes",
    }
)


def _normalize_result_key(key: str) -> str:
    return "_".join(key.casefold().replace("-", "_").replace("_", " ").split())


def assert_no_forbidden_result_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            assert _normalize_result_key(key) not in _FORBIDDEN_RESULT_KEY_NAMES
            assert_no_forbidden_result_keys(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_forbidden_result_keys(item)


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


def _mismatched_compute_context(
    tmp_path: Path,
    mismatch: str,
) -> tuple[RawArtifact, CanonicalDataset, AnalysisPlan]:
    artifact = RawArtifact(
        artifact_id="artifact",
        path="curve.csv",
        technique="ir",
        format="csv",
        sha256="digest",
    )
    dataset = CanonicalDataset.direct_envelope(artifact)
    plan = AnalysisPlan.direct(dataset, output_dir=tmp_path / "out")

    if mismatch == "artifact_dataset":
        artifact = RawArtifact(
            artifact_id="other-artifact",
            path="other.csv",
            technique="ir",
            format="csv",
            sha256="other-digest",
        )
    elif mismatch == "plan_dataset":
        plan = AnalysisPlan(
            plan_id="other-plan",
            dataset_id="other-dataset",
            technique="ir",
            output_dir=tmp_path / "out",
            pipeline_options={},
            parameter_sources={},
        )
    elif mismatch == "plan_technique":
        plan = AnalysisPlan(
            plan_id="other-plan",
            dataset_id=dataset.dataset_id,
            technique="dsc",
            output_dir=tmp_path / "out",
            pipeline_options={},
            parameter_sources={},
        )
    elif mismatch == "artifact_technique":
        artifact = RawArtifact(
            artifact_id=artifact.artifact_id,
            path=artifact.path,
            technique="dsc",
            format=artifact.format,
            sha256=artifact.sha256,
        )
    else:
        raise AssertionError(f"Unexpected mismatch: {mismatch}")
    return artifact, dataset, plan


@pytest.mark.parametrize(
    "mismatch",
    ("artifact_dataset", "plan_dataset", "plan_technique", "artifact_technique"),
)
def test_completed_compute_run_rejects_provenance_linkage_mismatches(
    tmp_path: Path,
    mismatch: str,
) -> None:
    artifact, dataset, plan = _mismatched_compute_context(tmp_path, mismatch)

    with pytest.raises(ValueError, match="linkage mismatch"):
        ComputeRun.completed(
            artifact=artifact,
            dataset=dataset,
            plan=plan,
            result=ComputeResult(),
        )


@pytest.mark.parametrize(
    "mismatch",
    ("artifact_dataset", "plan_dataset", "plan_technique", "artifact_technique"),
)
def test_failed_compute_run_with_context_rejects_provenance_linkage_mismatches(
    tmp_path: Path,
    mismatch: str,
) -> None:
    artifact, dataset, plan = _mismatched_compute_context(tmp_path, mismatch)

    with pytest.raises(ValueError, match="linkage mismatch"):
        ComputeRun(status="failed", artifact=artifact, dataset=dataset, plan=plan)


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


def test_legacy_projection_scrubs_nested_forbidden_aliases(tmp_path: Path) -> None:
    class FakeResult:
        parameters = {
            "peak_cm-1": 1630.0,
            "Analysis-Evidence": {"hidden": True},
            "nested": {
                "writing_status": "blocked",
                "values": [{"manuscript_role": "results", "intensity": 4.2}],
            },
        }
        figures = {"spectrum": "spectrum.svg", "Review-Notes": "internal.svg"}
        metadata = {
            "review_required": True,
            "evidence_package": {"hidden": True},
            "nested": {"manuscript_status": True, "provider": "legacy"},
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
    assert_no_forbidden_result_keys(payload["result"])
    assert "analysis_evidence" not in payload_text


def test_direct_compute_result_scrubs_forbidden_aliases_from_public_projection(
    tmp_path: Path,
) -> None:
    artifact = RawArtifact(
        artifact_id="artifact",
        path="curve.csv",
        technique="ir",
        format="csv",
        sha256="digest",
        observed_facts={"review_notes": "raw scientific metadata"},
    )
    dataset = CanonicalDataset.direct_envelope(artifact)
    plan = AnalysisPlan.direct(dataset, output_dir=tmp_path / "out")
    result = ComputeResult(
        metrics={
            "nested": {
                "Review-Notes": "private",
                "writing_status": "private",
                "intensity": 4.2,
            }
        },
        figures={"evidence_package": "private.svg", "spectrum": "spectrum.svg"},
        metadata={"nested": [{"manuscript_status": "draft"}], "provider": "direct"},
        warnings=("retained_warning",),
    )

    payload = ComputeRun.completed(
        artifact=artifact,
        dataset=dataset,
        plan=plan,
        result=result,
    ).to_dict()

    assert payload["result"]["metrics"]["nested"] == {"intensity": 4.2}
    assert payload["result"]["figures"] == {"spectrum": "spectrum.svg"}
    assert payload["result"]["metadata"] == {"nested": [{}], "provider": "direct"}
    assert payload["result"]["warnings"] == ["retained_warning"]
    assert_no_forbidden_result_keys(payload["result"])
    assert payload["artifact"]["observed_facts"] == {"review_notes": "raw scientific metadata"}
    assert payload["dataset"]["payload"]["observed_facts"] == {
        "review_notes": "raw scientific metadata"
    }


def test_direct_compute_result_retains_preview_figures_and_removes_explicit_aliases() -> None:
    result = ComputeResult(
        figures={
            "preview": "preview.svg",
            "chart_preview": "chart-preview.svg",
            "review_notes": "private.svg",
            "evidence_package": "private-package.svg",
        }
    )

    assert dict(result.figures) == {
        "preview": "preview.svg",
        "chart_preview": "chart-preview.svg",
    }


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
