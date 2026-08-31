"""Focused tests for the deterministic AI-platform execution graph."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

import pytest

import polynexus.core.ai_platform.capabilities as capabilities_module
from polynexus.core.ai_platform.contracts import ComputationState, ProviderResultInput
from polynexus.core.ai_platform.contracts import AxisProvenance, DataBlock
from polynexus.core.ai_platform.capabilities import (
    CapabilityDescriptor,
    CapabilityDescriptorRegistry,
    default_descriptor_registry,
)
from polynexus.core.ai_platform.execution import (
    ExecutionContext,
    ExecutionGraph,
    ExecutionNode,
    ExecutionResult,
    NodeResult,
)
from polynexus.core.ai_platform.planner import CapabilityPlanner
from polynexus.core.compute.service import ComputeRunService


def detector_block(*, with_calibration: bool = True) -> DataBlock:
    calibration = {
        "scope": "saxs.detector_calibration",
        "status": "reviewed",
        "record_locator": "calibrations/saxs-detector.json",
        "record_sha256": "b" * 64,
    }
    return DataBlock.create(
        kind="matrix",
        shape=(2, 2),
        dims=("detector_y", "detector_x"),
        coords={"detector_y": (0, 1), "detector_x": (0, 1)},
        coord_units={"detector_y": "px", "detector_x": "px"},
        array_ref={"uri": "artifact://detector", "sha256": "a" * 64},
        axis_provenance={
            "detector_y": AxisProvenance.create("detector_y", "observed", "detector_pixel"),
            "detector_x": AxisProvenance.create("detector_x", "observed", "detector_pixel"),
        },
        source_artifact_id="artifact-detector",
        metadata={
            "technique": "saxs",
            "measurement_family": "detector_image",
            "calibrations": [calibration] if with_calibration else [],
        },
    )


def detector_admission(*, with_calibration: bool = True):
    block = detector_block(with_calibration=with_calibration)
    descriptor = default_descriptor_registry().get("saxs.detector_radial_profile.v1")
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(block,), target_capabilities=(descriptor.capability_id,)
    )[0]
    return block, descriptor, item


def test_execution_graph_orders_dependencies_and_records_node_provenance():
    graph = ExecutionGraph.create(
        nodes=(
            ExecutionNode.create(node_id="normalize", capability_id="curve.normalize.v1"),
            ExecutionNode.create(
                node_id="summary",
                capability_id="curve.summary.v1",
                dependencies=("normalize",),
            ),
        )
    )
    result = graph.execute(
        context=ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test"),
        executors={
            "curve.normalize.v1": lambda _: {"normalized": True},
            "curve.summary.v1": lambda _: {"point_count": 3},
        },
    )
    assert tuple(item.node_id for item in result.node_results) == ("normalize", "summary")
    assert result.node_results[0].output == {"normalized": True}
    assert all(item.provenance.get("cache_key") for item in result.node_results)
    assert result.node_results[1].provenance["dependencies"][0]["node_id"] == "normalize"


def test_execution_graph_reuses_same_cache_key_for_same_inputs_and_parameters():
    node = ExecutionNode.create(
        node_id="summary",
        capability_id="curve.summary.v1",
        parameters={"window": 3},
    )
    context = ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test")
    assert node.cache_key(context) == node.cache_key(context)
    assert node.cache_key(context) != ExecutionNode.create(
        node_id="summary",
        capability_id="curve.summary.v1",
        parameters={"window": 4},
    ).cache_key(context)


def test_execution_context_metadata_that_reaches_executor_changes_cache_key():
    node = ExecutionNode.create(
        node_id="summary", capability_id="curve.summary.v1"
    )
    first = ExecutionContext.create(
        input_hashes=("a" * 64,),
        runtime_fingerprint="py-test",
        metadata={"sample_role": "reference"},
    )
    second = ExecutionContext.create(
        input_hashes=("a" * 64,),
        runtime_fingerprint="py-test",
        metadata={"sample_role": "unknown"},
    )

    assert node.cache_key(first) != node.cache_key(second)


def test_execution_node_metadata_that_reaches_executor_changes_cache_key():
    context = ExecutionContext.create(
        input_hashes=("a" * 64,), runtime_fingerprint="py-test"
    )
    first = ExecutionNode.create(
        node_id="summary",
        capability_id="curve.summary.v1",
        metadata={"input_role": "reference"},
    )
    second = ExecutionNode.create(
        node_id="summary",
        capability_id="curve.summary.v1",
        metadata={"input_role": "unknown"},
    )

    assert first.cache_key(context) != second.cache_key(context)


def test_calibration_change_invalidates_only_calibration_sensitive_nodes():
    source = ExecutionNode.create(node_id="source", capability_id="source.identity.v1")
    calibrated = ExecutionNode.create(
        node_id="calibrated",
        capability_id="saxs.calibrate.v1",
        dependencies=("source",),
    )
    old = ExecutionContext.create(
        input_hashes=("a" * 64,), calibration_hashes=("b" * 64,), runtime_fingerprint="py-test"
    )
    new = ExecutionContext.create(
        input_hashes=("a" * 64,), calibration_hashes=("c" * 64,), runtime_fingerprint="py-test"
    )
    assert source.cache_key(old) == source.cache_key(new)
    assert calibrated.cache_key(old) != calibrated.cache_key(new)


def test_needs_input_node_does_not_call_executor():
    calls: list[bool] = []
    node = ExecutionNode.create(
        node_id="absolute",
        capability_id="saxs.absolute_intensity.v1",
        state=ComputationState.create(
            data_availability="canonical",
            computability="needs_input",
            validity="not_assessed",
            promotion="diagnostic_only",
            missing_inputs=("calibration:q",),
        ),
    )
    result = ExecutionGraph.create(nodes=(node,)).execute(
        context=ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test"),
        executors={"saxs.absolute_intensity.v1": lambda _: calls.append(True)},
    )
    assert calls == []
    assert result.node_results[0].state.computability == "needs_input"
    assert result.node_results[0].status == "needs_input"


def test_missing_executor_is_a_stable_failed_result_and_graph_serializes():
    node = ExecutionNode.create(node_id="summary", capability_id="test.summary.v1")
    graph = ExecutionGraph.create(nodes=(node,))
    context = ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test")
    result = graph.execute(context=context, executors={})
    item = result.node_results[0]
    assert item.status == "failed"
    assert item.state.computability == "failed"
    assert item.error == "missing_executor:test.summary.v1"
    restored = ExecutionGraph.from_dict(graph.to_dict())
    assert restored == graph
    assert restored.graph_id == graph.graph_id


def test_executor_exception_becomes_json_safe_failed_provenance():
    node = ExecutionNode.create(node_id="summary", capability_id="test.summary.v1")

    def explode(_):
        raise RuntimeError("boom")

    item = ExecutionGraph.create(nodes=(node,)).execute(
        context=ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test"),
        executors={"test.summary.v1": explode},
    ).node_results[0]
    assert item.status == "failed"
    assert item.error == "executor_error:RuntimeError"
    assert "boom" not in item.error
    assert isinstance(item.provenance["cache_key"], str)
    assert item.to_dict()["provenance"]["parameters"] == {}


def test_graph_rejects_unknown_dependencies_and_cycles():
    with pytest.raises(ValueError, match="unknown dependency"):
        ExecutionGraph.create(
            nodes=(ExecutionNode.create(node_id="a", capability_id="x", dependencies=("missing",)),)
        )
    with pytest.raises(ValueError, match="cycle"):
        ExecutionGraph.create(
            nodes=(
                ExecutionNode.create(node_id="a", capability_id="x", dependencies=("b",)),
                ExecutionNode.create(node_id="b", capability_id="y", dependencies=("a",)),
            )
        )


def test_execution_node_factory_rejects_string_dependency_sequence():
    with pytest.raises(TypeError, match="dependencies"):
        ExecutionNode.create(
            node_id="summary",
            capability_id="curve.summary.v1",
            dependencies="source",
        )


def test_execution_context_and_result_round_trip_are_json_safe():
    context = ExecutionContext.create(
        input_hashes=("b" * 64, "a" * 64),
        calibration_hashes=("d" * 64, "c" * 64),
        runtime_fingerprint="py-test",
        metadata={"seed": 1},
    )
    assert ExecutionContext.from_dict(context.to_dict()) == context
    graph = ExecutionGraph.create(nodes=(ExecutionNode.create(node_id="a", capability_id="x"),))
    result = graph.execute(context=context, executors={"x": lambda _: {"ok": True}})
    assert result.from_dict(result.to_dict()) == result


def test_blocked_state_is_not_relabelled_as_needs_input_and_node_result_is_consistent():
    blocked = ExecutionNode.create(
        node_id="q", capability_id="saxs.absolute.v1",
        state=ComputationState.create("canonical", "blocked", "not_assessed", "diagnostic_only", reason_codes=("synthetic_axis",)),
    )
    item = ExecutionGraph.create((blocked,)).execute(
        ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="test"),
        executors={"saxs.absolute.v1": lambda _: {"bad": True}},
    ).node_results[0]
    assert item.status == "blocked"
    assert item.state.computability == "blocked"
    with pytest.raises(ValueError, match="state"):
        NodeResult("q", "saxs.absolute.v1", "completed", item.state, item.cache_key)
    with pytest.raises(ValueError, match="error"):
        NodeResult("q", "saxs.absolute.v1", "failed", ComputationState.create("canonical", "failed", "not_assessed", "diagnostic_only"), item.cache_key)


def test_cache_entries_are_validated_and_malformed_entries_are_ignored():
    node = ExecutionNode.create(node_id="summary", capability_id="test.summary.v1")
    graph = ExecutionGraph.create((node,))
    context = ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="test")
    calls: list[bool] = []
    key = node.cache_key(context)
    tampered = NodeResult(
        "summary", "other.capability.v1", "completed",
        ComputationState.create("canonical", "computed", "not_assessed", "diagnostic_only"), key,
        output={"tampered": True},
    )
    result = graph.execute(context, {"test.summary.v1": lambda _: calls.append(True) or {"ok": True}}, cache={key: tampered})
    assert calls == [True]
    assert result.node_results[0].output == {"ok": True}
    calls.clear()
    result2 = graph.execute(context, {"test.summary.v1": lambda _: calls.append(True) or {"ok": True}}, cache={key: object()})
    assert calls == [True]
    assert result2.node_results[0].output == {"ok": True}


def test_cache_keys_are_content_keys_and_graph_order_is_canonical():
    context = ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="test")
    left = ExecutionNode.create(node_id="left", capability_id="curve.summary.v1")
    right = ExecutionNode.create(node_id="right", capability_id="curve.summary.v1")
    assert left.cache_key(context) == right.cache_key(context)
    graph_a = ExecutionGraph.create((right, left))
    graph_b = ExecutionGraph.create((left, right))
    assert graph_a.graph_id == graph_b.graph_id
    assert graph_a.to_dict() == graph_b.to_dict()


def test_result_loader_rejects_forged_graph_identity_and_cache_key():
    graph = ExecutionGraph.create((ExecutionNode.create(node_id="a", capability_id="x"),))
    result = graph.execute(ExecutionContext.create(runtime_fingerprint="test"), {"x": lambda _: {"ok": True}})
    payload = result.to_dict()
    payload["graph_id"] = "x"
    with pytest.raises(ValueError, match="graph_id"):
        result.from_dict(payload)
    item = result.node_results[0].to_dict()
    item["cache_key"] = "x"
    with pytest.raises(ValueError, match="SHA-256"):
        NodeResult.from_dict(item)


def test_compute_run_service_exposes_narrow_shared_graph_adapter():
    graph = ExecutionGraph.create(
        (ExecutionNode.create(node_id="summary", capability_id="test.summary.v1"),)
    )
    context = ExecutionContext.create(
        input_hashes=("a" * 64,), runtime_fingerprint="test"
    )

    result = ComputeRunService().execute_graph(
        graph,
        context,
        {"test.summary.v1": lambda request: {"ok": True}},
    )

    assert isinstance(result, ExecutionResult)
    assert result.node_results[0].output == {"ok": True}


def test_compute_run_service_graph_adapter_rehydrates_serialized_contracts():
    graph = ExecutionGraph.create(
        (ExecutionNode.create(node_id="summary", capability_id="test.summary.v1"),)
    )
    context = ExecutionContext.create(
        input_hashes=("a" * 64,), runtime_fingerprint="test"
    )

    result = ComputeRunService().execute_graph(
        graph.to_dict(),
        context.to_dict(),
        {"test.summary.v1": lambda request: {"ok": True}},
    )

    assert result.node_results[0].output == {"ok": True}


def test_compute_run_service_forwards_planner_admission_to_core_graph():
    block, descriptor, admission = detector_admission()
    graph = ExecutionGraph.create(
        (
            ExecutionNode.create(
                node_id="radial",
                capability_id=descriptor.capability_id,
                descriptor_version=descriptor.version,
            ),
        )
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )

    result = ComputeRunService().execute_graph(
        graph,
        context,
        {descriptor.capability_id: lambda _: {"q": [1.0]}},
        admissions={"radial": admission},
    )

    assert result.node_results[0].status == "completed"


def test_known_unsupported_descriptor_cannot_be_overridden_by_executor():
    node = ExecutionNode.create(node_id="dma", capability_id="dma.master_curve.v1")
    result = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(runtime_fingerprint="test"),
        {"dma.master_curve.v1": lambda _: {"fabricated": 1}},
    )

    item = result.node_results[0]
    assert item.status == "not_applicable"
    assert item.state.reason_codes == ("capability_unsupported",)
    assert item.output is None


def test_known_experimental_descriptor_requires_real_executor_binding():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial", capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
        calibration_sensitive=False,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,), calibration_hashes=("b" * 64,), runtime_fingerprint="test"
    )
    missing = ExecutionGraph.create((node,)).execute(context, {})
    assert missing.node_results[0].status == "needs_input"
    assert missing.node_results[0].state.reason_codes == ("planner_admission_required",)

    bound = ExecutionGraph.create((node,)).execute(
        context,
        {"canonical.saxs.detector_radial_profile": lambda _: {"q": []}},
        admissions={"radial": admission},
    )
    assert bound.node_results[0].status == "completed"


def test_descriptor_version_mismatch_is_not_executed():
    node = ExecutionNode.create(
        node_id="fid", capability_id="nmr.fid_fft.v1", descriptor_version="99"
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(runtime_fingerprint="test"),
        {"nmr.fid_fft.v1": lambda _: calls.append(True)},
    ).node_results[0]
    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("descriptor_version_mismatch",)


def test_registered_capability_requires_planner_admission_before_executor():
    block, descriptor, admission = detector_admission()
    assert admission.outcome == "executable"
    calls: list[bool] = []
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(
            input_hashes=(block.block_id,),
            calibration_hashes=("b" * 64,),
            runtime_fingerprint="test",
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("planner_admission_required",)
    assert item.state.missing_inputs == ("planner_admission",)


def test_builtin_capability_cannot_be_downgraded_by_an_omitting_registry():
    """A narrow custom registry must not hide Core's built-in descriptors."""

    class EmptyRegistry:
        def get(self, _capability_id, **_kwargs):
            raise ValueError("descriptor omitted")

    node = ExecutionNode.create(
        node_id="radial",
        capability_id="saxs.detector_radial_profile.v1",
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(runtime_fingerprint="test"),
        {node.capability_id: lambda _: calls.append(True) or {"forged": True}},
        descriptor_registry=EmptyRegistry(),
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("planner_admission_required",)


def test_builtin_capability_cannot_be_replaced_by_a_custom_descriptor():
    """A plugin catalog cannot override Core's descriptor semantics."""

    builtin_id = "saxs.detector_radial_profile.v1"
    forged = CapabilityDescriptor.create(
        capability_id=builtin_id,
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={},
        status="unsupported",
    )
    registry = CapabilityDescriptorRegistry((forged,))
    node = ExecutionNode.create(node_id="radial", capability_id=builtin_id)
    calls: list[bool] = []

    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(runtime_fingerprint="test"),
        {builtin_id: lambda _: calls.append(True) or {"forged": True}},
        descriptor_registry=registry,
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("planner_admission_required",)


def test_unavailable_builtin_catalog_cannot_be_replaced_by_a_custom_descriptor(monkeypatch):
    """A failed Core catalog must block instead of trusting a custom fallback."""

    builtin_id = "saxs.detector_radial_profile.v1"
    forged = CapabilityDescriptor.create(
        capability_id=builtin_id,
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={},
        status="available",
    )
    registry = CapabilityDescriptorRegistry((forged,))

    def unavailable():
        raise RuntimeError("catalog unavailable")

    monkeypatch.setattr(capabilities_module, "default_descriptor_registry", unavailable)
    node = ExecutionNode.create(node_id="radial", capability_id=builtin_id)
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(runtime_fingerprint="test"),
        {builtin_id: lambda _: calls.append(True) or {"forged": True}},
        descriptor_registry=registry,
    ).node_results[0]

    assert calls == []
    assert item.status == "blocked"
    assert item.state.reason_codes == ("descriptor_registry_unavailable",)


def test_registered_capability_executes_only_with_trusted_matching_admission():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        context,
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True]
    assert item.status == "completed"
    assert item.provenance["descriptor_hash"] == descriptor.content_hash
    assert item.provenance["admission_hash"] == admission.admission_hash


def test_required_input_admission_cannot_execute_without_runtime_binding():
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.runtime_required_input.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_inputs": ("foo",)},
        output_schema={"value": {"type": "scalar"}},
    )
    registry = CapabilityDescriptorRegistry((descriptor,))
    block = detector_block()
    admission = CapabilityPlanner(registry).inspect(
        data_blocks=(block,),
        target_capabilities=(descriptor.capability_id,),
        available_inputs={"foo": {"status": "computed"}},
    )[0]
    assert admission.outcome == "executable"

    calls: list[bool] = []
    item = ExecutionGraph.create(
        (ExecutionNode.create("runtime", descriptor.capability_id),)
    ).execute(
        ExecutionContext.create(input_hashes=(block.block_id,), runtime_fingerprint="test"),
        {descriptor.capability_id: lambda _: calls.append(True) or {"value": 1}},
        descriptor_registry=registry,
        admissions={"runtime": admission},
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("required_input_context_missing",)
    assert item.state.missing_inputs == ("foo",)


def test_required_input_status_only_runtime_declaration_is_not_a_binding():
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.runtime_required_input_status_only.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_inputs": ("foo",)},
        output_schema={"value": {"type": "scalar"}},
    )
    registry = CapabilityDescriptorRegistry((descriptor,))
    block = detector_block()
    admission = CapabilityPlanner(registry).inspect(
        data_blocks=(block,),
        target_capabilities=(descriptor.capability_id,),
        available_inputs={"foo": {"status": "computed"}},
    )[0]
    calls: list[bool] = []
    item = ExecutionGraph.create(
        (ExecutionNode.create("runtime", descriptor.capability_id),)
    ).execute(
        ExecutionContext.create(
            input_hashes=(block.block_id,),
            runtime_fingerprint="test",
            metadata={"available_inputs": {"foo": {"status": "computed"}}},
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"value": 1}},
        descriptor_registry=registry,
        admissions={"runtime": admission},
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("required_input_context_missing",)


@pytest.mark.parametrize("binding", ("available", "computed", "completed", "ready"))
def test_required_input_status_literal_is_not_a_runtime_binding(binding: str):
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.runtime_required_input_status_literal.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_inputs": ("foo",)},
        output_schema={"value": {"type": "scalar"}},
    )
    registry = CapabilityDescriptorRegistry((descriptor,))
    block = detector_block()
    admission = CapabilityPlanner(registry).inspect(
        data_blocks=(block,),
        target_capabilities=(descriptor.capability_id,),
        available_inputs={"foo": {"status": "computed"}},
    )[0]
    calls: list[bool] = []
    item = ExecutionGraph.create(
        (ExecutionNode.create("runtime", descriptor.capability_id),)
    ).execute(
        ExecutionContext.create(
            input_hashes=(block.block_id,),
            runtime_fingerprint="test",
            metadata={"foo": binding},
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"value": 1}},
        descriptor_registry=registry,
        admissions={"runtime": admission},
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("required_input_context_missing",)


@pytest.mark.parametrize(
    "binding",
    (
        {"value": None, "unit": "s"},
        {"value": "", "unit": "s"},
        {"ref": None, "unit": "s"},
    ),
)
def test_required_input_null_explicit_binding_is_not_materialized(binding: Mapping[str, object]):
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.runtime_required_input_null.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_inputs": ("foo",)},
        output_schema={"value": {"type": "scalar"}},
    )
    registry = CapabilityDescriptorRegistry((descriptor,))
    block = detector_block()
    admission = CapabilityPlanner(registry).inspect(
        data_blocks=(block,),
        target_capabilities=(descriptor.capability_id,),
        available_inputs={"foo": {"status": "computed"}},
    )[0]
    calls: list[bool] = []
    item = ExecutionGraph.create(
        (ExecutionNode.create("runtime", descriptor.capability_id),)
    ).execute(
        ExecutionContext.create(
            input_hashes=(block.block_id,),
            runtime_fingerprint="test",
            metadata={"available_inputs": {"foo": binding}},
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"value": 1}},
        descriptor_registry=registry,
        admissions={"runtime": admission},
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("required_input_context_missing",)


@pytest.mark.parametrize(
    ("parameters", "metadata"),
    (
        ({"foo": (1, 2, 3)}, {}),
        ({}, {"available_inputs": {"foo": {"value": (1, 2, 3)}}}),
        ({}, {"context": {"input_bindings": {"foo": (1, 2, 3)}}}),
    ),
)
def test_required_input_executes_with_explicit_runtime_binding(
    parameters: Mapping[str, object], metadata: Mapping[str, object]
):
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.runtime_required_input_bound.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_inputs": ("foo",)},
        output_schema={"value": {"type": "scalar"}},
    )
    registry = CapabilityDescriptorRegistry((descriptor,))
    block = detector_block()
    admission = CapabilityPlanner(registry).inspect(
        data_blocks=(block,),
        target_capabilities=(descriptor.capability_id,),
        available_inputs={"foo": {"status": "computed"}},
    )[0]
    calls: list[bool] = []
    item = ExecutionGraph.create(
        (ExecutionNode.create("runtime", descriptor.capability_id, parameters=parameters),)
    ).execute(
        ExecutionContext.create(
            input_hashes=(block.block_id,), runtime_fingerprint="test", metadata=metadata
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"value": 1}},
        descriptor_registry=registry,
        admissions={"runtime": admission},
    ).node_results[0]

    assert calls == [True]
    assert item.status == "completed"


def test_dataclass_replacement_cannot_rebind_a_trusted_admission():
    approved_block, descriptor, admission = detector_admission()
    unapproved_block = detector_block(with_calibration=False)
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    forged = replace(
        admission,
        selected_data_block_id=unapproved_block.block_id,
        data_block_ids=(approved_block.block_id, unapproved_block.block_id),
    )
    assert forged.is_trusted_admission is False
    calls: list[bool] = []
    result = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(
            input_hashes=(unapproved_block.block_id,),
            calibration_hashes=("b" * 64,),
            runtime_fingerprint="test",
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
        admissions={"radial": forged},
    ).node_results[0]

    assert calls == []
    assert result.status == "blocked"
    assert result.state.reason_codes == ("planner_admission_untrusted",)


def test_dataclass_replacement_cannot_promote_a_trusted_admission():
    _, descriptor, admission = detector_admission()
    promoted = replace(
        admission,
        outcome="executable",
        state=ComputationState.create(
            "canonical", "computed", "not_assessed", "diagnostic_only"
        ),
    )
    assert promoted.is_trusted_admission is False


def test_plan_item_subclass_cannot_override_admission_authority():
    _, descriptor, admission = detector_admission()

    class ForgedPlanItem(type(admission)):
        @property
        def is_trusted_admission(self):
            return True

    forged = ForgedPlanItem(
        capability_id=admission.capability_id,
        descriptor_version=admission.descriptor_version,
        outcome=admission.outcome,
        state=admission.state,
        data_block_ids=admission.data_block_ids,
        selected_data_block_id=admission.selected_data_block_id,
        next_actions=admission.next_actions,
        descriptor_hash=admission.descriptor_hash,
        metadata=admission.metadata,
    )
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    calls: list[bool] = []
    result = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(
            input_hashes=(admission.selected_input_id,),
            calibration_hashes=("b" * 64,),
            runtime_fingerprint="test",
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
        admissions={"radial": forged},
    ).node_results[0]

    assert calls == []
    assert result.status == "blocked"
    assert result.state.reason_codes == ("planner_admission_untrusted",)


def test_calibration_sensitive_admission_requires_runtime_calibration_context():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial", capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(input_hashes=(block.block_id,), runtime_fingerprint="test"),
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("calibration_context_missing",)


def test_calibration_sensitive_admission_requires_matching_runtime_calibration_identity():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial", capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(
            input_hashes=(block.block_id,),
            calibration_hashes=("c" * 64,),
            runtime_fingerprint="test",
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("calibration_binding_mismatch",)


def test_admission_is_bound_to_the_selected_data_block_hash():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial", capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(
            input_hashes=("c" * 64,), calibration_hashes=("b" * 64,), runtime_fingerprint="test"
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("planner_admission_input_mismatch",)
    assert item.state.missing_inputs == (f"data_block:{block.block_id}",)


def test_untrusted_forged_plan_item_cannot_admit_execution():
    block, descriptor, trusted = detector_admission()
    forged = type(trusted)(
        capability_id=trusted.capability_id,
        descriptor_version=trusted.descriptor_version,
        outcome=trusted.outcome,
        state=trusted.state,
        data_block_ids=trusted.data_block_ids,
        selected_data_block_id=trusted.selected_data_block_id,
        next_actions=trusted.next_actions,
        descriptor_hash=trusted.descriptor_hash,
        metadata=trusted.metadata,
    )
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(
            input_hashes=(block.block_id,),
            calibration_hashes=("b" * 64,),
            runtime_fingerprint="test",
        ),
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
        admissions={"radial": forged},
    ).node_results[0]

    assert calls == []
    assert item.status == "blocked"
    assert item.state.reason_codes == ("planner_admission_untrusted",)


def test_node_state_cannot_promote_core_result_without_validation():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
        state=ComputationState.create(
            "canonical", "computed", "validated", "results_candidate"
        ),
    )
    item = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(
            input_hashes=(block.block_id,),
            calibration_hashes=("b" * 64,),
            runtime_fingerprint="test",
        ),
        {descriptor.capability_id: lambda _: {"q": [1.0]}},
        admissions={"radial": admission},
    ).node_results[0]

    assert item.status == "completed"
    assert item.state.validity == "not_assessed"
    assert item.state.promotion == "diagnostic_only"


def test_non_completed_cache_result_is_a_miss_and_reexecutes():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    key = node.cache_key(context, descriptor=descriptor, admission_hash=admission.admission_hash)
    failed = NodeResult(
        node.node_id,
        node.capability_id,
        "failed",
        ComputationState.create("canonical", "failed", "not_assessed", "diagnostic_only"),
        key,
        error="old_failure",
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        context,
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
        cache={key: failed},
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True]
    assert item.status == "completed"


def test_registered_capability_bare_cache_output_is_a_miss():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    key = node.cache_key(context, descriptor=descriptor, admission_hash=admission.admission_hash)
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        context,
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [2.0]}},
        cache={key: {"forged": True}},
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True]
    assert item.status == "completed"
    assert item.to_dict()["output"] == {"q": [2.0]}


def test_registered_capability_none_cache_output_is_a_miss():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    key = node.cache_key(context, descriptor=descriptor, admission_hash=admission.admission_hash)
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        context,
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [3.0]}},
        cache={key: None},
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True]
    assert item.status == "completed"
    assert item.to_dict()["output"] == {"q": [3.0]}


def test_completed_cache_result_cannot_restore_promotion_from_cache():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial", capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    key = node.cache_key(context, descriptor=descriptor, admission_hash=admission.admission_hash)
    elevated = NodeResult(
        node.node_id,
        node.capability_id,
        "completed",
        ComputationState.create("canonical", "computed", "validated", "results_candidate"),
        key,
        output={"q": [1.0]},
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        context,
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [2.0]}},
        cache={key: elevated},
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True]
    assert item.status == "completed"
    assert item.to_dict()["output"] == {"q": [2.0]}
    assert item.state.validity == "not_assessed"
    assert item.state.promotion == "diagnostic_only"


def test_registered_cache_result_without_core_output_fingerprint_is_a_miss():
    """A matching identity alone must not make a caller-supplied result trusted."""

    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    key = node.cache_key(context, descriptor=descriptor, admission_hash=admission.admission_hash)
    forged = NodeResult(
        node.node_id,
        node.capability_id,
        "completed",
        ComputationState.create("canonical", "computed", "not_assessed", "diagnostic_only"),
        key,
        output={"q": [1.0]},
        provenance={
            "node_id": node.node_id,
            "capability_id": node.capability_id,
            "descriptor_version": node.descriptor_version,
            "descriptor_hash": descriptor.content_hash,
            "cache_key": key,
            "admission_hash": admission.admission_hash,
        },
    )
    calls: list[bool] = []
    item = ExecutionGraph.create((node,)).execute(
        context,
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [2.0]}},
        cache={key: forged},
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True]
    assert item.to_dict()["output"] == {"q": [2.0]}


def test_core_generated_cache_result_is_reused_for_registered_descriptor():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    cache: dict[str, object] = {}
    calls: list[bool] = []

    def executor(_):
        calls.append(True)
        return {"q": [1.0]}

    graph = ExecutionGraph.create((node,))

    first = graph.execute(
        context,
        {descriptor.capability_id: executor},
        cache=cache,
        admissions={"radial": admission},
    ).node_results[0]
    second = graph.execute(
        context,
        {descriptor.capability_id: executor},
        cache=cache,
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True]
    assert first.output == second.output
    assert first.to_dict()["output"] == {"q": [1.0]}


def test_core_cache_hit_result_can_be_reinserted_without_forcing_reexecution():
    """The transient cache_hit marker is not part of result authenticity."""

    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    cache: dict[str, object] = {}
    calls: list[bool] = []
    graph = ExecutionGraph.create((node,))

    def executor(_):
        calls.append(True)
        return {"q": [1.0]}

    graph.execute(
        context,
        {descriptor.capability_id: executor},
        cache=cache,
        admissions={"radial": admission},
    )
    cache_hit = graph.execute(
        context,
        {descriptor.capability_id: executor},
        cache=cache,
        admissions={"radial": admission},
    ).node_results[0]
    key = node.cache_key(context, descriptor=descriptor, admission_hash=admission.admission_hash)
    cache[key] = cache_hit

    reinserted = graph.execute(
        context,
        {descriptor.capability_id: executor},
        cache=cache,
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True]
    assert reinserted.to_dict()["output"] == {"q": [1.0]}


def test_registered_cache_output_tampering_is_detected_by_fingerprint():
    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    cache: dict[str, object] = {}
    calls: list[bool] = []
    graph = ExecutionGraph.create((node,))
    graph.execute(
        context,
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [1.0]}},
        cache=cache,
        admissions={"radial": admission},
    )
    key = node.cache_key(context, descriptor=descriptor, admission_hash=admission.admission_hash)
    original = cache[key]
    assert isinstance(original, NodeResult)
    tampered = original.to_dict()
    tampered["output"] = {"q": [99.0]}
    cache[key] = tampered

    item = graph.execute(
        context,
        {descriptor.capability_id: lambda _: calls.append(True) or {"q": [2.0]}},
        cache=cache,
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True, True]
    assert item.to_dict()["output"] == {"q": [2.0]}


def test_registered_cache_node_result_subclass_is_not_trusted():
    """Cache authority is limited to the exact Core NodeResult DTO."""

    block, descriptor, admission = detector_admission()
    node = ExecutionNode.create(
        node_id="radial",
        capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
    )
    context = ExecutionContext.create(
        input_hashes=(block.block_id,),
        calibration_hashes=("b" * 64,),
        runtime_fingerprint="test",
    )
    cache: dict[str, object] = {}
    calls: list[bool] = []
    graph = ExecutionGraph.create((node,))

    def executor(_):
        calls.append(True)
        return {"q": [1.0]}

    graph.execute(
        context,
        {descriptor.capability_id: executor},
        cache=cache,
        admissions={"radial": admission},
    )
    key = node.cache_key(context, descriptor=descriptor, admission_hash=admission.admission_hash)
    original = cache[key]
    assert isinstance(original, NodeResult)

    class ForgedNodeResult(NodeResult):
        pass

    cache[key] = ForgedNodeResult(
        original.node_id,
        original.capability_id,
        original.status,
        original.state,
        original.cache_key,
        original.output,
        original.provenance,
        original.error,
    )

    item = graph.execute(
        context,
        {descriptor.capability_id: executor},
        cache=cache,
        admissions={"radial": admission},
    ).node_results[0]

    assert calls == [True, True]
    assert item.to_dict()["output"] == {"q": [1.0]}


def test_descriptor_required_calibration_is_in_cache_identity():
    _, descriptor, _ = detector_admission()
    node = ExecutionNode.create(
        node_id="radial", capability_id=descriptor.capability_id,
        descriptor_version=descriptor.version,
        calibration_sensitive=False,
    )
    old = ExecutionContext.create(
        input_hashes=("a" * 64,), calibration_hashes=("b" * 64,), runtime_fingerprint="test"
    )
    new = ExecutionContext.create(
        input_hashes=("a" * 64,), calibration_hashes=("c" * 64,), runtime_fingerprint="test"
    )
    assert node.cache_key(old, descriptor=descriptor) != node.cache_key(new, descriptor=descriptor)


def _dependent_descriptor_registry() -> tuple[
    CapabilityDescriptorRegistry,
    CapabilityDescriptor,
    CapabilityDescriptor,
]:
    dependency = CapabilityDescriptor.create(
        capability_id="saxs.detector_profile.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
    )
    target = CapabilityDescriptor.create(
        capability_id="saxs.dependent_profile.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
        dependencies=(dependency.capability_id,),
    )
    return CapabilityDescriptorRegistry((dependency, target)), dependency, target


def test_descriptor_dependency_without_graph_node_is_blocked_before_executor():
    registry, dependency, target = _dependent_descriptor_registry()
    block = detector_block()
    planner = CapabilityPlanner(registry)
    dependency_admission = planner.inspect(
        data_blocks=(block,), target_capabilities=(dependency.capability_id,)
    )[0]
    admission = planner.inspect(
        data_blocks=(block,),
        target_capabilities=(target.capability_id,),
        available_capabilities={dependency.capability_id: dependency_admission},
    )[0]
    calls: list[bool] = []
    result = ExecutionGraph.create(
        (ExecutionNode.create("target", target.capability_id),)
    ).execute(
        ExecutionContext.create(
            input_hashes=(block.block_id,),
            runtime_fingerprint="test",
        ),
        {target.capability_id: lambda _: calls.append(True) or {"profile": [1.0]}},
        descriptor_registry=registry,
        admissions={"target": admission},
    )

    item = result.node_results[0]
    assert calls == []
    assert item.status == "blocked"
    assert item.state.reason_codes == ("descriptor_dependency_missing",)


def test_descriptor_dependency_node_is_ordered_and_executes_when_edge_is_declared():
    registry, dependency, target = _dependent_descriptor_registry()
    block = detector_block()
    planner = CapabilityPlanner(registry)
    dependency_admission = planner.inspect(
        data_blocks=(block,), target_capabilities=(dependency.capability_id,)
    )[0]
    target_admission = planner.inspect(
        data_blocks=(block,),
        target_capabilities=(target.capability_id,),
        available_capabilities={dependency.capability_id: dependency_admission},
    )[0]
    calls: list[str] = []
    result = ExecutionGraph.create(
        (
            ExecutionNode.create("target", target.capability_id, dependencies=("dependency",)),
            ExecutionNode.create("dependency", dependency.capability_id),
        )
    ).execute(
        ExecutionContext.create(input_hashes=(block.block_id,), runtime_fingerprint="test"),
        {
            dependency.capability_id: lambda _: calls.append("dependency") or {"profile": [1.0]},
            target.capability_id: lambda request: calls.append("target") or {
                "dependency": request["dependencies"]["dependency"],
            },
        },
        descriptor_registry=registry,
        admissions={"dependency": dependency_admission, "target": target_admission},
    )

    assert calls == ["dependency", "target"]
    target_result = next(item for item in result.node_results if item.node_id == "target")
    assert target_result.status == "completed"
    assert target_result.provenance["dependencies"][0]["node_id"] == "dependency"


def test_descriptor_dependency_cannot_downgrade_to_opaque_when_runtime_registry_omits_it():
    """A canonical dependency stays fail-closed when its descriptor is absent."""

    full_registry, dependency, target = _dependent_descriptor_registry()
    target_only_registry = CapabilityDescriptorRegistry((target,))
    block = detector_block()
    planner = CapabilityPlanner(full_registry)
    dependency_admission = planner.inspect(
        data_blocks=(block,), target_capabilities=(dependency.capability_id,)
    )[0]
    target_admission = planner.inspect(
        data_blocks=(block,),
        target_capabilities=(target.capability_id,),
        available_capabilities={dependency.capability_id: dependency_admission},
    )[0]
    calls: list[str] = []

    result = ExecutionGraph.create(
        (
            ExecutionNode.create("target", target.capability_id, dependencies=("dependency",)),
            ExecutionNode.create("dependency", dependency.capability_id),
        )
    ).execute(
        ExecutionContext.create(input_hashes=(block.block_id,), runtime_fingerprint="test"),
        {
            dependency.capability_id: lambda _: calls.append("dependency") or {"profile": [1.0]},
            target.capability_id: lambda _: calls.append("target") or {"profile": [1.0]},
        },
        descriptor_registry=target_only_registry,
        admissions={"target": target_admission},
    )

    assert calls == []
    dependency_result = next(item for item in result.node_results if item.node_id == "dependency")
    target_result = next(item for item in result.node_results if item.node_id == "target")
    assert dependency_result.status == "blocked"
    assert dependency_result.state.reason_codes == ("descriptor_dependency_registry_missing",)
    assert target_result.status == "blocked"
    assert target_result.state.reason_codes == ("descriptor_dependency_registry_missing",)


def test_descriptor_dependency_requires_its_own_trusted_admission():
    full_registry, dependency, target = _dependent_descriptor_registry()
    block = detector_block()
    planner = CapabilityPlanner(full_registry)
    target_admission = planner.inspect(
        data_blocks=(block,),
        target_capabilities=(target.capability_id,),
        available_capabilities={
            dependency.capability_id: planner.inspect(
                data_blocks=(block,), target_capabilities=(dependency.capability_id,)
            )[0]
        },
    )[0]
    calls: list[str] = []

    result = ExecutionGraph.create(
        (
            ExecutionNode.create("target", target.capability_id, dependencies=("dependency",)),
            ExecutionNode.create("dependency", dependency.capability_id),
        )
    ).execute(
        ExecutionContext.create(input_hashes=(block.block_id,), runtime_fingerprint="test"),
        {
            dependency.capability_id: lambda _: calls.append("dependency") or {"profile": [1.0]},
            target.capability_id: lambda _: calls.append("target") or {"profile": [1.0]},
        },
        descriptor_registry=full_registry,
        admissions={"target": target_admission},
    )

    assert calls == []
    dependency_result = next(item for item in result.node_results if item.node_id == "dependency")
    target_result = next(item for item in result.node_results if item.node_id == "target")
    assert dependency_result.status == "needs_input"
    assert dependency_result.state.reason_codes == ("planner_admission_required",)
    assert target_result.status == "blocked"
    assert target_result.state.reason_codes == ("descriptor_dependency_admission_missing",)


def test_target_admission_binds_dependency_descriptor_identity_across_registries():
    """A target admission cannot be replayed with a changed dependency descriptor."""

    dependency_id = "saxs.registry_dependency.v1"
    dependency_a = CapabilityDescriptor.create(
        capability_id=dependency_id,
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
    )
    dependency_b = CapabilityDescriptor.create(
        capability_id=dependency_id,
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series", "variant": "changed"}},
    )
    target_a = CapabilityDescriptor.create(
        capability_id="saxs.registry_target.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
        dependencies=(dependency_id,),
    )
    target_b = CapabilityDescriptor.create(
        capability_id=target_a.capability_id,
        techniques=target_a.techniques,
        input_contract=target_a.input_contract,
        output_schema=target_a.output_schema,
        dependencies=target_a.dependencies,
    )
    registry_a = CapabilityDescriptorRegistry((dependency_a, target_a))
    registry_b = CapabilityDescriptorRegistry((dependency_b, target_b))
    block = detector_block()
    planner_a = CapabilityPlanner(registry_a)
    planner_b = CapabilityPlanner(registry_b)
    dependency_admission_a = planner_a.inspect(
        data_blocks=(block,), target_capabilities=(dependency_id,)
    )[0]
    target_admission_a = planner_a.inspect(
        data_blocks=(block,),
        target_capabilities=(target_a.capability_id,),
        available_capabilities={dependency_id: dependency_admission_a},
    )[0]
    dependency_admission_b = planner_b.inspect(
        data_blocks=(block,), target_capabilities=(dependency_id,)
    )[0]
    calls: list[str] = []

    result = ExecutionGraph.create(
        (
            ExecutionNode.create("target", target_a.capability_id, dependencies=("dependency",)),
            ExecutionNode.create("dependency", dependency_id),
        )
    ).execute(
        ExecutionContext.create(input_hashes=(block.block_id,), runtime_fingerprint="test"),
        {
            dependency_id: lambda _: calls.append("dependency") or {"profile": [1.0]},
            target_a.capability_id: lambda _: calls.append("target") or {"profile": [1.0]},
        },
        descriptor_registry=registry_b,
        admissions={"dependency": dependency_admission_b, "target": target_admission_a},
    )

    assert calls == ["dependency"]
    target_result = next(item for item in result.node_results if item.node_id == "target")
    assert target_result.status == "blocked"
    assert target_result.state.reason_codes == ("descriptor_dependency_admission_mismatch",)


def test_target_dependency_binding_uses_its_direct_graph_node_not_another_same_capability_node():
    """A disconnected duplicate capability node cannot satisfy a target binding."""

    registry, dependency, target = _dependent_descriptor_registry()
    first_block = detector_block()
    second_block = DataBlock.create(
        kind=first_block.kind,
        shape=first_block.shape,
        dims=first_block.dims,
        coords=first_block.coords,
        coord_units=first_block.coord_units,
        array_ref={"uri": "artifact://detector-second", "sha256": "c" * 64},
        axis_provenance=first_block.axis_provenance,
        source_artifact_id="artifact-detector-second",
        metadata=first_block.metadata,
    )
    planner = CapabilityPlanner(registry)
    first_dependency_admission = planner.inspect(
        data_blocks=(first_block,), target_capabilities=(dependency.capability_id,)
    )[0]
    second_dependency_admission = planner.inspect(
        data_blocks=(second_block,), target_capabilities=(dependency.capability_id,)
    )[0]
    target_admission = planner.inspect(
        data_blocks=(first_block,),
        target_capabilities=(target.capability_id,),
        available_capabilities={dependency.capability_id: first_dependency_admission},
    )[0]
    calls: list[str] = []

    result = ExecutionGraph.create(
        (
            ExecutionNode.create("target", target.capability_id, dependencies=("z_dependency",)),
            ExecutionNode.create("a_dependency", dependency.capability_id),
            ExecutionNode.create("z_dependency", dependency.capability_id),
        )
    ).execute(
        ExecutionContext.create(
            input_hashes=(first_block.block_id, second_block.block_id),
            runtime_fingerprint="test",
        ),
        {
            dependency.capability_id: lambda _: calls.append("dependency") or {"profile": [1.0]},
            target.capability_id: lambda _: calls.append("target") or {"profile": [1.0]},
        },
        descriptor_registry=registry,
        admissions={
            "a_dependency": first_dependency_admission,
            "z_dependency": second_dependency_admission,
            "target": target_admission,
        },
    )

    target_result = next(item for item in result.node_results if item.node_id == "target")
    assert target_result.status == "blocked"
    assert target_result.state.reason_codes == ("descriptor_dependency_admission_mismatch",)
    assert calls == ["dependency", "dependency"]


def test_target_dependency_binding_rejects_multiple_direct_nodes_for_one_capability():
    """One capability-level binding cannot authorize two direct graph nodes."""

    registry, dependency, target = _dependent_descriptor_registry()
    block = detector_block()
    planner = CapabilityPlanner(registry)
    dependency_admission = planner.inspect(
        data_blocks=(block,), target_capabilities=(dependency.capability_id,)
    )[0]
    target_admission = planner.inspect(
        data_blocks=(block,),
        target_capabilities=(target.capability_id,),
        available_capabilities={dependency.capability_id: dependency_admission},
    )[0]
    calls: list[str] = []

    result = ExecutionGraph.create(
        (
            ExecutionNode.create(
                "target",
                target.capability_id,
                dependencies=("first_dependency", "second_dependency"),
            ),
            ExecutionNode.create("first_dependency", dependency.capability_id),
            ExecutionNode.create("second_dependency", dependency.capability_id),
        )
    ).execute(
        ExecutionContext.create(input_hashes=(block.block_id,), runtime_fingerprint="test"),
        {
            dependency.capability_id: lambda _: calls.append("dependency") or {"profile": [1.0]},
            target.capability_id: lambda _: calls.append("target") or {"profile": [1.0]},
        },
        descriptor_registry=registry,
        admissions={
            "first_dependency": dependency_admission,
            "second_dependency": dependency_admission,
            "target": target_admission,
        },
    )

    target_result = next(item for item in result.node_results if item.node_id == "target")
    assert target_result.status == "blocked"
    assert target_result.state.reason_codes == ("descriptor_dependency_ambiguous",)
    assert calls == ["dependency", "dependency"]


def test_provider_result_admission_binds_selected_input_to_execution_context():
    provider_input = ProviderResultInput.create(
        source_artifact_id="artifact-dsc",
        technique="dsc",
        metrics={"Tm_peak_C": 185.2},
        metric_manifest=(
            {"path": "Tm_peak_C", "kind": "scalar", "status": "computed", "value": 185.2},
        ),
    )
    descriptor = default_descriptor_registry().get("dsc.Tm.v1")
    admission = CapabilityPlanner((descriptor,)).inspect(
        provider_results=(provider_input,), target_capabilities=(descriptor.capability_id,)
    )[0]
    seen: list[tuple[str, ...]] = []
    node = ExecutionNode.create("tm", descriptor.capability_id, descriptor_version=descriptor.version)

    result = ExecutionGraph.create((node,)).execute(
        ExecutionContext.create(
            input_hashes=(provider_input.input_id,), runtime_fingerprint="test"
        ),
        {
            descriptor.executor_key: lambda request: seen.append(
                tuple(request["context"]["input_hashes"])
            ) or {"value": 185.2},
        },
        admissions={"tm": admission},
    )

    assert result.node_results[0].status == "completed"
    assert seen == [(provider_input.input_id,)]
    assert result.node_results[0].provenance["input_hashes"] == (provider_input.input_id,)


def test_provider_result_admission_rejects_context_without_selected_input():
    provider_input = ProviderResultInput.create(
        source_artifact_id="artifact-dsc",
        technique="dsc",
        metrics={"Tm_peak_C": 185.2},
        metric_manifest=(
            {"path": "Tm_peak_C", "kind": "scalar", "status": "computed", "value": 185.2},
        ),
    )
    descriptor = default_descriptor_registry().get("dsc.Tm.v1")
    admission = CapabilityPlanner((descriptor,)).inspect(
        provider_results=(provider_input,), target_capabilities=(descriptor.capability_id,)
    )[0]
    calls: list[bool] = []
    item = ExecutionGraph.create(
        (ExecutionNode.create("tm", descriptor.capability_id, descriptor_version=descriptor.version),)
    ).execute(
        ExecutionContext.create(input_hashes=("b" * 64,), runtime_fingerprint="test"),
        {descriptor.executor_key: lambda _: calls.append(True) or {"value": 185.2}},
        admissions={"tm": admission},
    ).node_results[0]

    assert calls == []
    assert item.status == "needs_input"
    assert item.state.reason_codes == ("planner_admission_input_mismatch",)
    assert item.state.missing_inputs == (f"provider_result:{provider_input.input_id}",)
