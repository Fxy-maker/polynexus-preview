"""Regression tests for the shared ComputeRun projection admission parser."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

import pytest

from polynexus.core.ai_platform.contracts import ComputationState
from polynexus.core.agent_workflow.evidence import build_evidence
from polynexus.core.agent_workflow.models import WorkflowStepResult
from polynexus.core.compute.projection import (
    ComputeRunProjection,
    merge_compute_run_projections,
    read_compute_run_projection,
)


def _state(*, computability: str = "computed") -> dict[str, object]:
    validity = "validated" if computability == "computed" else "not_assessed"
    return ComputationState.create(
        data_availability="canonical",
        computability=computability,
        validity=validity,
        promotion="results_candidate" if validity == "validated" else "diagnostic_only",
    ).to_dict()


def test_missing_compute_run_is_the_only_legacy_fallback() -> None:
    projection = read_compute_run_projection({"results_summary": {"Tm_C": 220.0}})

    assert projection.present is False
    assert projection.valid is True
    assert projection.allows_legacy_fallback is True


def test_present_compute_run_requires_a_complete_shared_projection() -> None:
    projection = read_compute_run_projection(
        {"compute_run": {"status": "completed", "result": {"metrics": {}}}}
    )

    assert projection.present is True
    assert projection.valid is False
    assert projection.allows_legacy_fallback is False
    assert "compute_run_state_missing" in projection.reason_codes


def test_completed_projection_exposes_one_canonical_four_axis_state() -> None:
    state = _state()
    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "completed",
                "computation_state": state,
                "result": {"metrics": {}, "computation_state": state},
            }
        }
    )

    assert projection.valid is True
    assert projection.computed is True
    assert projection.state is not None
    assert projection.state.to_dict() == state


def test_projection_rejects_manifest_value_without_explicit_row_status() -> None:
    state = _state()
    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "completed",
                "computation_state": state,
                "result": {
                    "metric_manifest": [
                        {"path": "forged", "kind": "scalar", "value": 999.0}
                    ]
                },
            }
        }
    )

    assert projection.valid is False
    assert projection.computed is False
    assert "compute_run_metric_manifest_status_missing" in projection.reason_codes


def test_projection_rejects_manifest_value_that_disagrees_with_result_metrics() -> None:
    state = _state()
    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "completed",
                "computation_state": state,
                "result": {
                    "metrics": {"forged": 1.0},
                    "metric_manifest": [
                        {
                            "path": "forged",
                            "kind": "scalar",
                            "status": "computed",
                            "value": 999.0,
                        }
                    ],
                },
            }
        }
    )

    assert projection.valid is False
    assert projection.computed is False
    assert "compute_run_metric_manifest_value_mismatch" in projection.reason_codes


def test_projection_rejects_computed_manifest_path_missing_from_result_metrics() -> None:
    state = _state()
    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "completed",
                "computation_state": state,
                "result": {
                    "metrics": {"measured": 1.0},
                    "metric_manifest": [
                        {
                            "path": "forged",
                            "kind": "scalar",
                            "status": "computed",
                            "value": 999.0,
                        }
                    ],
                },
            }
        }
    )

    assert projection.valid is False
    assert projection.computed is False
    assert "compute_run_metric_manifest_metrics_missing" in projection.reason_codes


def test_projection_rejects_conflicting_nested_state_aliases() -> None:
    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "completed",
                "computation_state": _state(),
                "result": {
                    "metrics": {},
                    "computation_state": _state(computability="needs_input"),
                },
            }
        }
    )

    assert projection.valid is False
    assert projection.computed is False
    assert "compute_run_state_mismatch" in projection.reason_codes


def test_projection_rejects_computation_state_subclass_alias_forgery() -> None:
    computed = ComputationState.create(
        data_availability="canonical",
        computability="computed",
        validity="validated",
        promotion="results_candidate",
    )
    needs_input = ComputationState.create(
        data_availability="canonical",
        computability="needs_input",
        validity="not_assessed",
        promotion="diagnostic_only",
    )

    class ForgedState(ComputationState):
        def to_dict(self) -> dict[str, object]:
            return computed.to_dict()

    forged = ForgedState(
        data_availability=needs_input.data_availability,
        computability=needs_input.computability,
        validity=needs_input.validity,
        promotion=needs_input.promotion,
        missing_inputs=needs_input.missing_inputs,
        reason_codes=needs_input.reason_codes,
        preconditions=needs_input.preconditions,
        next_actions=needs_input.next_actions,
    )
    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "completed",
                "computation_state": computed,
                "result": {"computation_state": forged},
            }
        }
    )

    assert projection.valid is False
    assert projection.computed is False
    assert "compute_run_state_invalid" in projection.reason_codes


def test_projection_snapshots_mapping_subclasses_before_validation() -> None:
    class ForgedMapping(dict[str, object]):
        def get(self, key: str, default: object = None) -> object:
            if key == "status":
                return "completed"
            return super().get(key, default)

    projection = read_compute_run_projection(
        {
            "compute_run": ForgedMapping(
                status="needs_input",
                computation_state=_state(computability="needs_input"),
            )
        }
    )

    assert projection.valid is False
    assert projection.computed is False
    assert projection.status == "needs_input"


def test_projection_does_not_allow_mapping_subclass_to_hide_compute_run() -> None:
    class HidingMapping(dict[str, object]):
        def __contains__(self, key: object) -> bool:
            if key == "compute_run":
                return False
            return super().__contains__(key)

    projection = read_compute_run_projection(
        HidingMapping(
            compute_run={"status": "needs_input"},
            Xc_pct=999.0,
        )
    )

    assert projection.present is True
    assert projection.valid is False
    assert projection.allows_legacy_fallback is False


def test_projection_rejects_generic_mapping_that_hides_compute_run() -> None:
    """A Mapping implementation cannot opt an explicit envelope into fallback."""

    class SneakyMapping(Mapping[str, object]):
        def __init__(self) -> None:
            self._values: dict[str, object] = {
                "compute_run": {"status": "needs_input"},
                "Xc_pct": 999.0,
            }

        def __getitem__(self, key: str) -> object:
            return self._values[key]

        def __iter__(self):
            # Hide the explicit field from ``dict(mapping)`` while retaining
            # it in the backing object, reproducing the trust-boundary bypass.
            return iter(("Xc_pct",))

        def __len__(self) -> int:
            return len(self._values)

    projection = read_compute_run_projection(SneakyMapping())

    assert projection.present is True
    assert projection.valid is False
    assert projection.allows_legacy_fallback is False
    assert "compute_run_container_invalid" in projection.reason_codes


def test_cli_projection_uses_the_parser_snapshot_not_mapping_get() -> None:
    """A valid parser result must not be replaced by a later mutable lookup."""

    from polynexus.cli.batch_run_service import _compute_run_projection

    state = _state()
    canonical = {
        "status": "completed",
        "computation_state": state,
        "artifact": {"artifact_id": "canonical"},
    }

    class ForgedLookup(dict[str, object]):
        def get(self, key: str, default: object = None) -> object:
            if key == "compute_run":
                return {
                    **canonical,
                    "artifact": {"artifact_id": "forged"},
                }
            return super().get(key, default)

    projection = _compute_run_projection(ForgedLookup(compute_run=canonical))

    assert projection is not None
    assert projection["artifact"]["artifact_id"] == "canonical"


def test_needs_input_projection_cannot_fallback_to_legacy_values() -> None:
    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "needs_input",
                "computation_state": _state(computability="needs_input"),
            }
        }
    )

    assert projection.present is True
    assert projection.valid is False
    assert projection.computed is False
    assert projection.allows_legacy_fallback is False


def test_provider_private_state_alias_is_not_accepted_as_shared_state() -> None:
    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "completed",
                "state": "provider-private",
                "result": {"metrics": {}},
            }
        }
    )

    assert projection.valid is False
    assert projection.allows_legacy_fallback is False


def test_gui_rejects_present_malformed_serialized_run_instead_of_legacy_fallback() -> None:
    from polynexus.gui.analysis_run_service import compute_run_payload

    with pytest.raises(ValueError, match="GUI compute_run projection is invalid"):
        compute_run_payload(
            {
                "status": "completed",
                "artifact": {"artifact_id": "source"},
                "result": {"metrics": {"Tm_C": 220.0}},
            }
        )


def test_cli_rejects_present_malformed_serialized_run_instead_of_legacy_fallback() -> None:
    from polynexus.cli.batch_run_service import _compute_run_projection

    with pytest.raises(ValueError, match="CLI compute_run projection is invalid"):
        _compute_run_projection(
            {
                "compute_run": {
                    "status": "completed",
                    "artifact": {"artifact_id": "source"},
                    "result": {"metrics": {"Tm_C": 220.0}},
                },
                "Tm_C": 999.0,
            }
        )


def test_top_level_null_compute_run_remains_present_after_workflow_roundtrip() -> None:
    step = WorkflowStepResult.from_dict(
        {
            "step_id": "tm",
            "technique": "dsc",
            "status": "completed",
            "result_summary": {"Tm_C": 220.0},
            "compute_run": None,
        }
    )

    assert step.compute_run_present is True
    assert step.to_dict()["compute_run"] is None
    assert build_evidence((step,)).observed == ()


def test_top_level_metrics_and_manifest_must_agree() -> None:
    """A malformed envelope cannot hide its metric source at the top level."""

    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "completed",
                "computation_state": _state(),
                "metrics": {"forged": 1.0},
                "metric_manifest": [
                    {
                        "path": "forged",
                        "kind": "scalar",
                        "status": "computed",
                        "value": 999.0,
                    }
                ],
            }
        }
    )

    assert projection.valid is False
    assert projection.computed is False
    assert "compute_run_metric_manifest_value_mismatch" in projection.reason_codes


def test_projection_constructor_rejects_computation_state_subclass() -> None:
    """The parser result DTO cannot be manually forged with polymorphic state."""

    computed = ComputationState.create(
        data_availability="canonical",
        computability="computed",
        validity="validated",
        promotion="results_candidate",
    )

    class ForgedState(ComputationState):
        def to_dict(self) -> dict[str, object]:
            return computed.to_dict()

    forged = ForgedState(
        data_availability="canonical",
        computability="needs_input",
        validity="not_assessed",
        promotion="diagnostic_only",
    )

    with pytest.raises(TypeError, match="exact ComputationState"):
        ComputeRunProjection(
            present=True,
            valid=True,
            status="completed",
            state=forged,
        )


def test_projection_rejects_mapping_computation_state_subclass() -> None:
    """Mapping-capable state subclasses cannot enter the trusted parser."""

    computed = ComputationState.create(
        data_availability="canonical",
        computability="computed",
        validity="validated",
        promotion="results_candidate",
    )

    class ForgedState(ComputationState, dict[str, object]):
        def to_dict(self) -> dict[str, object]:
            return computed.to_dict()

    forged = ForgedState(
        data_availability="canonical",
        computability="needs_input",
        validity="not_assessed",
        promotion="diagnostic_only",
    )
    projection = read_compute_run_projection(
        {
            "compute_run": {
                "status": "completed",
                "computation_state": forged,
            }
        }
    )

    assert projection.valid is False
    assert projection.computed is False
    assert "compute_run_state_invalid" in projection.reason_codes


def test_merge_reparses_manual_projection_before_trusting_validity() -> None:
    """A hand-built valid flag cannot bypass strict payload validation."""

    state = _state()
    payload = {
        "status": "completed",
        "computation_state": state,
        "result": {
            "metrics": {"forged": 1.0},
            "metric_manifest": [
                {
                    "path": "forged",
                    "kind": "scalar",
                    "status": "computed",
                    "value": 999.0,
                }
            ],
        },
    }
    forged = ComputeRunProjection(
        present=True,
        valid=True,
        status="completed",
        state=ComputationState.from_dict(state),
        result=payload["result"],
        payload=payload,
    )

    merged = merge_compute_run_projections(forged)

    assert merged.valid is False
    assert merged.computed is False
    assert "compute_run_metric_manifest_value_mismatch" in merged.reason_codes


def test_merge_rejects_present_projection_without_payload() -> None:
    """A present hand-built sentinel has no parser attestation to trust."""

    forged = ComputeRunProjection(
        present=True,
        valid=True,
        status="completed",
        state=ComputationState.from_dict(_state()),
    )

    merged = merge_compute_run_projections(forged)

    assert merged.valid is False
    assert merged.computed is False
    assert "compute_run_projection_payload_missing" in merged.reason_codes


def test_merge_rejects_noncanonical_absent_projection_with_extra_fields() -> None:
    """Only the parser's empty absent sentinel may authorize legacy fallback."""

    forged = ComputeRunProjection(
        present=False,
        valid=True,
        descriptor_id="forged",
        provenance={"source": "forged"},
        reason_codes=("forged",),
    )

    merged = merge_compute_run_projections(forged)

    assert merged.valid is False
    assert merged.computed is False
    assert "compute_run_projection_absent_invalid" in merged.reason_codes


def test_merge_rejects_projection_subclass_even_with_valid_payload() -> None:
    """Projection subclasses must not smuggle untrusted field overrides."""

    class ForgedProjection(ComputeRunProjection):
        pass

    state = _state()
    payload = {
        "status": "completed",
        "computation_state": state,
    }
    forged = ForgedProjection(
        present=True,
        valid=True,
        status="completed",
        state=ComputationState.from_dict(state),
        payload=payload,
    )

    merged = merge_compute_run_projections(forged)

    assert merged.valid is False
    assert merged.computed is False
    assert "compute_run_projection_type_invalid" in merged.reason_codes


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("valid", False),
        ("status", "needs_input"),
        (
            "state",
            ComputationState.create(
                data_availability="canonical",
                computability="needs_input",
                validity="not_assessed",
                promotion="diagnostic_only",
            ),
        ),
        ("result", {"metrics": {"metric": 999.0}}),
        ("descriptor_id", "forged-descriptor"),
        ("provenance", {"source_artifact_id": "forged"}),
        ("uncertainty", {"metric": {"std": 999.0}}),
    ),
)
def test_merge_rejects_manual_projection_field_override(
    field_name: str,
    replacement: object,
) -> None:
    """Every normalized field must agree with the strict payload parse."""

    state = _state()
    payload = {
        "status": "completed",
        "descriptor_id": "descriptor-1",
        "computation_state": state,
        "provenance": {"source_artifact_id": "artifact-1"},
        "uncertainty": {"metric": {"std": 0.1}},
        "result": {
            "metrics": {"metric": 1.0},
            "metric_manifest": [
                {
                    "path": "metric",
                    "kind": "scalar",
                    "status": "computed",
                    "value": 1.0,
                }
            ],
        },
    }
    parsed = read_compute_run_projection({"compute_run": payload})
    assert parsed.valid is True
    forged = replace(parsed, **{field_name: replacement})

    merged = merge_compute_run_projections(forged)

    assert merged.valid is False
    assert merged.computed is False
    assert "compute_run_projection_fields_mismatch" in merged.reason_codes
