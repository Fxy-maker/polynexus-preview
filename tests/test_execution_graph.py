"""Focused tests for the deterministic AI-platform execution graph."""

from __future__ import annotations

import pytest

from polynexus.core.ai_platform.contracts import ComputationState
from polynexus.core.ai_platform.execution import (
    ExecutionContext,
    ExecutionGraph,
    ExecutionNode,
    ExecutionResult,
    NodeResult,
)
from polynexus.core.compute.service import ComputeRunService


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
    node = ExecutionNode.create(node_id="summary", capability_id="curve.summary.v1")
    graph = ExecutionGraph.create(nodes=(node,))
    context = ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test")
    result = graph.execute(context=context, executors={})
    item = result.node_results[0]
    assert item.status == "failed"
    assert item.state.computability == "failed"
    assert item.error == "missing_executor:curve.summary.v1"
    restored = ExecutionGraph.from_dict(graph.to_dict())
    assert restored == graph
    assert restored.graph_id == graph.graph_id


def test_executor_exception_becomes_json_safe_failed_provenance():
    node = ExecutionNode.create(node_id="summary", capability_id="curve.summary.v1")

    def explode(_):
        raise RuntimeError("boom")

    item = ExecutionGraph.create(nodes=(node,)).execute(
        context=ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="py-test"),
        executors={"curve.summary.v1": explode},
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
    node = ExecutionNode.create(node_id="summary", capability_id="curve.summary.v1")
    graph = ExecutionGraph.create((node,))
    context = ExecutionContext.create(input_hashes=("a" * 64,), runtime_fingerprint="test")
    calls: list[bool] = []
    key = node.cache_key(context)
    tampered = NodeResult(
        "summary", "other.capability.v1", "completed",
        ComputationState.create("canonical", "computed", "not_assessed", "diagnostic_only"), key,
        output={"tampered": True},
    )
    result = graph.execute(context, {"curve.summary.v1": lambda _: calls.append(True) or {"ok": True}}, cache={key: tampered})
    assert calls == [True]
    assert result.node_results[0].output == {"ok": True}
    calls.clear()
    result2 = graph.execute(context, {"curve.summary.v1": lambda _: calls.append(True) or {"ok": True}}, cache={key: object()})
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
        (ExecutionNode.create(node_id="summary", capability_id="curve.summary.v1"),)
    )
    context = ExecutionContext.create(
        input_hashes=("a" * 64,), runtime_fingerprint="test"
    )

    result = ComputeRunService().execute_graph(
        graph,
        context,
        {"curve.summary.v1": lambda request: {"ok": True}},
    )

    assert isinstance(result, ExecutionResult)
    assert result.node_results[0].output == {"ok": True}


def test_compute_run_service_graph_adapter_rehydrates_serialized_contracts():
    graph = ExecutionGraph.create(
        (ExecutionNode.create(node_id="summary", capability_id="curve.summary.v1"),)
    )
    context = ExecutionContext.create(
        input_hashes=("a" * 64,), runtime_fingerprint="test"
    )

    result = ComputeRunService().execute_graph(
        graph.to_dict(),
        context.to_dict(),
        {"curve.summary.v1": lambda request: {"ok": True}},
    )

    assert result.node_results[0].output == {"ok": True}


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
    node = ExecutionNode.create(node_id="fid", capability_id="nmr.fid_fft.v1")
    context = ExecutionContext.create(runtime_fingerprint="test")
    missing = ExecutionGraph.create((node,)).execute(context, {})
    assert missing.node_results[0].status == "needs_input"
    assert missing.node_results[0].state.reason_codes == ("executor_unavailable",)

    bound = ExecutionGraph.create((node,)).execute(
        context,
        {"canonical.nmr.fid_fft": lambda _: {"spectrum": []}},
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
