from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from polynexus.core.ai_platform import ComputationState
from polynexus.core.ai_platform.capabilities import CapabilityDescriptor
from polynexus.core.ai_platform.planner import CapabilityPlanItem
from polynexus.core.canonical_experiments.nd_adapters import adapt_nmr_fid
from polynexus.core.compute.models import ComputeResult
from polynexus.core.compute.models import AnalysisPlan, CanonicalDataset, ComputeRun, RawArtifact
from polynexus.core.agent_workflow.models import WorkflowStepResult


def _descriptor(*, input_contract):
    return CapabilityDescriptor.create(
        capability_id="test.contract.v1",
        techniques=("nmr",),
        input_contract=input_contract,
        output_schema={"value": {"type": "scalar"}},
    )


def test_capability_descriptor_rejects_unknown_input_contract_keys() -> None:
    with pytest.raises(ValueError, match="unknown.*input_contract"):
        _descriptor(input_contract={"kind": "complex", "invented_gate": True})


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("kinds", 42),
        ("required_dims", {"dim": "time"}),
        ("axis_requirements", ("time",)),
        ("axis_requirements", {"time": {"quantitative": "yes"}}),
        ("required_calibrations", {"scope": "nmr"}),
        ("required_any_inputs", ("dwell_time", "spectral_width")),
        ("required_any_inputs", ((),)),
        ("required_any_inputs", (("dwell_time", 42),)),
        ("metric_paths", 42),
    ),
)
def test_capability_descriptor_rejects_malformed_input_contract_values(
    key: str, value: object
) -> None:
    with pytest.raises((TypeError, ValueError), match=key):
        _descriptor(input_contract={key: value})


def test_capability_descriptor_rejects_conflicting_compatibility_aliases() -> None:
    with pytest.raises(ValueError, match="kind.*kinds"):
        _descriptor(input_contract={"kind": "complex", "kinds": ("series",)})


def test_capability_descriptor_accepts_typed_alternative_input_groups() -> None:
    descriptor = _descriptor(
        input_contract={
            "kind": "complex",
            "required_any_inputs": (
                ("dwell_time", "sampling_interval", "spectral_width"),
                ("nucleus", "chemical_shift_calibration"),
            ),
        }
    )

    assert descriptor.input_contract["required_any_inputs"] == (
        ("dwell_time", "sampling_interval", "spectral_width"),
        ("nucleus", "chemical_shift_calibration"),
    )


@pytest.mark.parametrize(
    "precondition",
    (
        {},
        {"kind": ""},
        {"kind": "invented", "axis": "time"},
        {"kind": "axis"},
        {"kind": "axis", "axis": "time", "accepted_sources": 42},
        {"kind": "axis", "axis": "time", "invented_gate": True},
        {"kind": "calibration"},
        {"kind": "calibration", "scope": "time", "invented_gate": True},
    ),
)
def test_capability_descriptor_rejects_unknown_or_malformed_preconditions(
    precondition: object,
) -> None:
    with pytest.raises((TypeError, ValueError), match="precondition"):
        CapabilityDescriptor.create(
            capability_id="test.precondition.v1",
            techniques=("nmr",),
            input_contract={"kind": "complex"},
            output_schema={},
            preconditions=(precondition,),
        )


def test_capability_descriptor_accepts_only_supported_typed_preconditions() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="test.precondition.v1",
        techniques=("nmr",),
        input_contract={"kind": "complex"},
        output_schema={},
        preconditions=(
            {
                "kind": "axis_provenance",
                "axis": "time",
                "accepted_sources": ("observed", "user_confirmed"),
            },
            {"type": "calibration", "scope": "nmr.time_axis"},
        ),
    )

    assert CapabilityDescriptor.from_dict(descriptor.to_dict()) == descriptor


def test_capability_descriptor_accepts_calibration_id_precondition_alias() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="test.calibration-id.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={},
        preconditions=({"kind": "calibration", "id": "geometry"},),
    )

    assert descriptor.preconditions[0]["id"] == "geometry"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("techniques", "nmr"),
        ("dependencies", "curve.summary.v1"),
        ("alternatives", "nmr.other.v1"),
        ("aliases", "fid_fft"),
        ("failure_reason_codes", "missing_fid"),
        ("preconditions", "axis"),
        ("missing_input_actions", "provide_fid"),
    ),
)
def test_capability_descriptor_factory_rejects_scalar_sequence_fields(
    field: str, value: object
) -> None:
    kwargs = {
        "capability_id": "test.sequence.v1",
        "techniques": ("nmr",),
        "input_contract": {"kind": "complex"},
        "output_schema": {},
        field: value,
    }
    with pytest.raises(TypeError, match=field):
        CapabilityDescriptor.create(**kwargs)


@pytest.mark.parametrize(
    ("field", "override"),
    (
        ("representation", "real_spectrum"),
        ("components", ("real",)),
        ("source_path", "other/fid"),
    ),
)
def test_nmr_adapter_rejects_metadata_that_would_override_canonical_fields(
    tmp_path: Path, field: str, override: object
) -> None:
    fid_path = tmp_path / "fid"
    fid_path.write_bytes(b"\x00\x00\x00\x01\x00\x00\x00\x02")

    with pytest.raises(ValueError, match=rf"reserved.*{field}"):
        adapt_nmr_fid(
            fid_path,
            source_artifact_id="nmr-artifact",
            metadata={field: override},
        )


def test_nmr_adapter_keeps_canonical_fields_when_extension_metadata_is_supplied(
    tmp_path: Path,
) -> None:
    fid_path = tmp_path / "fid"
    fid_path.write_bytes(b"\x00\x00\x00\x01\x00\x00\x00\x02")

    adapted = adapt_nmr_fid(
        fid_path,
        source_artifact_id="nmr-artifact",
        metadata={"sample_state": "solid", "operator_note": "kept"},
    )

    assert adapted.data_block is not None
    assert adapted.data_block.metadata["representation"] == "complex_fid"
    assert adapted.data_block.metadata["components"] == ("real", "imaginary")
    assert adapted.data_block.metadata["sample_state"] == "solid"
    assert adapted.data_block.metadata["operator_note"] == "kept"


def test_legacy_projection_ignores_free_form_or_partial_state_mappings() -> None:
    partial_state = {"status": "completed", "state": "provider-private"}
    legacy = SimpleNamespace(
        parameters={"metric": 1.0},
        figures={},
        metadata={"state": partial_state},
        validation_warnings=(),
        quality_flags={},
        validation_summary="All checks passed",
    )

    result = ComputeResult.from_legacy_result(legacy)

    assert result.computation_state is None


def test_legacy_projection_accepts_only_explicit_four_axis_state_mapping() -> None:
    state = ComputationState.create(
        "canonical", "computed", "diagnostic", "diagnostic_only"
    )
    legacy = SimpleNamespace(
        parameters={"metric": 1.0},
        figures={},
        metadata={"computation_state": state.to_dict()},
        validation_warnings=(),
        quality_flags={},
        validation_summary="All checks passed",
    )

    result = ComputeResult.from_legacy_result(legacy)

    assert result.computation_state == state


def test_legacy_projection_prefers_explicit_state_over_private_state_alias() -> None:
    state = ComputationState.create(
        "canonical", "computed", "diagnostic", "diagnostic_only"
    )
    legacy = SimpleNamespace(
        parameters={"metric": 1.0},
        figures={},
        state={"status": "provider-complete"},
        metadata={"computation_state": state.to_dict()},
        validation_warnings=(),
        quality_flags={},
        validation_summary="All checks passed",
    )

    result = ComputeResult.from_legacy_result(legacy)

    assert result.computation_state == state


def _completed_run_with_projection(tmp_path: Path, result: ComputeResult, **kwargs) -> ComputeRun:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    artifact = RawArtifact.from_path(source, technique="ir")
    dataset = CanonicalDataset.direct_envelope(artifact)
    plan = AnalysisPlan.direct(dataset, output_dir=tmp_path / "out")
    return ComputeRun.completed(
        artifact=artifact,
        dataset=dataset,
        plan=plan,
        result=result,
        **kwargs,
    )


def test_compute_run_rejects_conflicting_provenance_projections(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="provenance"):
        _completed_run_with_projection(
            tmp_path,
            ComputeResult(metrics={"metric": 1.0}, provenance={"source": "result"}),
            provenance={"source": "run"},
        )


def test_compute_run_rejects_conflicting_uncertainty_projections(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="uncertainty"):
        _completed_run_with_projection(
            tmp_path,
            ComputeResult(metrics={"metric": 1.0}, uncertainty={"metric": {"std": 1.0}}),
            uncertainty={"metric": {"std": 2.0}},
        )


def test_workflow_step_rejects_conflicting_state_aliases() -> None:
    computed = ComputationState.create(
        "canonical", "computed", "diagnostic", "diagnostic_only"
    )
    needs_input = ComputationState.create(
        "canonical", "needs_input", "not_assessed", "diagnostic_only"
    )
    with pytest.raises(ValueError, match="state"):
        WorkflowStepResult(
            step_id="step",
            technique="nmr",
            status="completed",
            compute_run={
                "status": "completed",
                "computation_state": computed.to_dict(),
                "state": needs_input.to_dict(),
            },
        )


def test_workflow_step_ignores_provider_private_state_alias() -> None:
    step = WorkflowStepResult(
        step_id="step",
        technique="nmr",
        status="review_required",
        compute_run={"status": "completed", "state": "provider-private"},
    )

    assert step.computation_state is None


def test_capability_plan_rejects_outcome_state_mismatch() -> None:
    state = ComputationState.create(
        "canonical", "needs_input", "not_assessed", "diagnostic_only"
    )
    with pytest.raises(ValueError, match="outcome.*state|state.*outcome"):
        CapabilityPlanItem(
            capability_id="nmr.fft.v1",
            descriptor_version="1",
            outcome="executable",
            state=state,
        )


def test_capability_plan_rejects_invalid_descriptor_hash_and_selection() -> None:
    state = ComputationState.create(
        "canonical", "computed", "not_assessed", "diagnostic_only"
    )
    with pytest.raises(ValueError, match="descriptor_hash"):
        CapabilityPlanItem(
            capability_id="nmr.fft.v1",
            descriptor_version="1",
            outcome="executable",
            state=state,
            descriptor_hash="not-a-hash",
        )
    with pytest.raises(ValueError, match="selected_data_block_id"):
        CapabilityPlanItem(
            capability_id="nmr.fft.v1",
            descriptor_version="1",
            outcome="executable",
            state=state,
            data_block_ids=("a" * 64,),
            selected_data_block_id="b" * 64,
        )


def test_workflow_step_rejects_top_level_and_nested_state_mismatch() -> None:
    computed = ComputationState.create(
        "canonical", "computed", "diagnostic", "diagnostic_only"
    )
    needs_input = ComputationState.create(
        "canonical", "needs_input", "not_assessed", "diagnostic_only"
    )
    with pytest.raises(ValueError, match="state"):
        WorkflowStepResult(
            step_id="step",
            technique="nmr",
            status="completed",
            computation_state=needs_input,
            compute_run={
                "status": "completed",
                "computation_state": computed.to_dict(),
            },
        )


def test_workflow_step_rejects_run_and_result_state_mismatch() -> None:
    computed = ComputationState.create(
        "canonical", "computed", "diagnostic", "diagnostic_only"
    )
    needs_input = ComputationState.create(
        "canonical", "needs_input", "not_assessed", "diagnostic_only"
    )
    with pytest.raises(ValueError, match="state"):
        WorkflowStepResult(
            step_id="step",
            technique="nmr",
            status="review_required",
            compute_run={
                "status": "completed",
                "computation_state": computed.to_dict(),
                "result": {"computation_state": needs_input.to_dict()},
            },
        )


def test_workflow_step_rejects_conflicting_descriptor_projections() -> None:
    with pytest.raises(ValueError, match="descriptor"):
        WorkflowStepResult(
            step_id="step",
            technique="nmr",
            status="completed",
            descriptor_id="nmr.outer.v1",
            compute_run={
                "status": "completed",
                "descriptor_id": "nmr.inner.v1",
            },
        )


@pytest.mark.parametrize("field", ("provenance", "uncertainty"))
def test_workflow_step_rejects_conflicting_nested_projection_mappings(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        WorkflowStepResult(
            step_id="step",
            technique="nmr",
            status="completed",
            compute_run={
                "status": "completed",
                field: {"source": "run"},
                "result": {field: {"source": "result"}},
            },
        )
