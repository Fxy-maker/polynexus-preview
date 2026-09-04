from __future__ import annotations

import json
from pathlib import Path

import pytest

from polynexus.core.ai_platform.contracts import ComputationState, ProviderResultInput
from polynexus.core.ai_platform.capabilities import CapabilityDescriptor
from polynexus.core.compute.models import CanonicalDataset, RawArtifact
from polynexus.core.exploration import (
    CanonicalAdmission,
    CanonicalAdmissionRegistry,
    ExplorationExecutorDescriptor,
    ExplorationExecutorRegistry,
    ExplorationRequest,
    ExplorationRun,
    ExplorationRunStore,
    ExplorationRunner,
    implementation_hash_for,
    ExplorationEvidenceSelection,
    ExplorationBudget,
    AutomaticExplorationRunner,
    CapabilityPromotionEvidence,
    CapabilityPromotionService,
    ExplorationWorkerLimits,
    IsolatedExplorationRunner,
)
from polynexus.core.project_workflow.workspace import ProjectWorkspace


SOURCE_ARTIFACT_ID = "a" * 64
SOURCE_CONTENT_HASH = "b" * 64
IMPLEMENTATION_HASH = "c" * 64


def _descriptor(
    *,
    executor: object | None = None,
    executor_id: str = "dma.loss_tangent_exploration",
    version: str = "1",
    implementation_hash: str | None = None,
    techniques: tuple[str, ...] = ("dma",),
) -> ExplorationExecutorDescriptor:
    if implementation_hash is None:
        implementation_hash = implementation_hash_for(executor or _executor)
    return ExplorationExecutorDescriptor.create(
        executor_id=executor_id,
        version=version,
        implementation_hash=implementation_hash,
        supported_techniques=techniques,
        input_contract={
            "canonical": {"kinds": ["dataset"], "techniques": ["dma"], "required_axes": []},
            "parameters": {"window": {"type": "integer", "required": False, "min": 1, "max": 10}},
        },
        output_contract={
            "required_metrics": {
                "tan_delta_peak": {"status": "computed", "unit": "1", "method": "exploration-fit"}
            },
            "required_provenance": ["source_content_hash"],
        },
    )


def _raw_artifact() -> RawArtifact:
    return RawArtifact(
        artifact_id=SOURCE_ARTIFACT_ID,
        path="D:/fixtures/dma.csv",
        technique="dma",
        format="csv",
        sha256=SOURCE_CONTENT_HASH,
    )


def _admission() -> CanonicalAdmission:
    artifact = _raw_artifact()
    dataset = CanonicalDataset.direct_envelope(artifact)
    return CanonicalAdmission.from_objects(dataset, artifact)


def _executor(request: ExplorationRequest) -> ProviderResultInput:
    return _provider_result(request)


def _slow_executor(request: ExplorationRequest) -> ProviderResultInput:
    import time

    time.sleep(0.5)
    return _provider_result(request)


def _network_executor(request: ExplorationRequest) -> ProviderResultInput:
    import socket

    socket.create_connection(("127.0.0.1", 9), timeout=0.1)
    return _provider_result(request)


def _permission_executor(request: ExplorationRequest) -> ProviderResultInput:
    raise PermissionError("blocked")


def _filesystem_executor(request: ExplorationRequest) -> ProviderResultInput:
    with open("D:/outside-polynexus-exploration.txt", "r", encoding="utf-8"):
        pass
    return _provider_result(request)


def _large_output_executor(request: ExplorationRequest) -> ProviderResultInput:
    return ProviderResultInput.create(
        source_artifact_id=SOURCE_ARTIFACT_ID,
        technique="dma",
        metrics={"tan_delta_peak": "x" * 2048},
        metric_manifest=(
            {"path": "tan_delta_peak", "status": "computed", "unit": "1", "method": "exploration-fit"},
        ),
        computation_state=ComputationState.create("canonical", "computed", "diagnostic", "diagnostic_only"),
        provenance={"source_content_hash": SOURCE_CONTENT_HASH},
    )


def _undeclared_metric_executor(request: ExplorationRequest) -> ProviderResultInput:
    return ProviderResultInput.create(
        source_artifact_id=SOURCE_ARTIFACT_ID,
        technique="dma",
        metrics={"tan_delta_peak": 0.83, "extra": 1.0},
        metric_manifest=(
            {"path": "tan_delta_peak", "status": "computed", "unit": "1", "method": "exploration-fit"},
            {"path": "extra", "status": "computed", "unit": "1", "method": "other"},
        ),
        computation_state=ComputationState.create("canonical", "computed", "diagnostic", "diagnostic_only"),
        provenance={"source_content_hash": SOURCE_CONTENT_HASH},
    )


def _request(
    *,
    descriptor: ExplorationExecutorDescriptor | None = None,
    parameters: dict[str, object] | None = None,
    executor: object | None = None,
    admission: CanonicalAdmission | None = None,
) -> ExplorationRequest:
    descriptor = descriptor or _descriptor(executor=executor)
    return ExplorationRequest.create(
        source_artifact_id=SOURCE_ARTIFACT_ID,
        source_content_hash=SOURCE_CONTENT_HASH,
        technique="DMA",
        executor_id=descriptor.executor_id,
        executor_version=descriptor.version,
        executor_implementation_hash=descriptor.implementation_hash,
        executor_descriptor_hash=descriptor.descriptor_hash,
        method_intent="Find the loss-tangent peak for comparison.",
        parameters={} if parameters is None else parameters,
        parent_run_id="compute-run-001",
        canonical_admission=admission or _admission(),
    )


def _provider_result(
    request: ExplorationRequest,
    *,
    source_artifact_id: str = SOURCE_ARTIFACT_ID,
    technique: str = "dma",
    source_content_hash: str = SOURCE_CONTENT_HASH,
) -> ProviderResultInput:
    return ProviderResultInput.create(
        source_artifact_id=source_artifact_id,
        technique=technique,
        metrics={"tan_delta_peak": 0.83},
        metric_manifest=(
            {
                "path": "tan_delta_peak",
                "status": "computed",
                "value": 0.83,
                "unit": "1",
                "method": "exploration-fit",
            },
        ),
        computation_state=ComputationState.create(
            "canonical", "computed", "diagnostic", "diagnostic_only"
        ),
        provenance={"source_content_hash": source_content_hash},
    )


def _runner_with_result(descriptor: ExplorationExecutorDescriptor | None = None) -> ExplorationRunner:
    executor = _executor
    descriptor = descriptor or _descriptor(executor=executor)
    registry = ExplorationExecutorRegistry()
    registry.register(descriptor, executor)
    admissions = CanonicalAdmissionRegistry((_admission(),))
    return ExplorationRunner(registry, admissions)


def test_exploration_request_and_run_are_deterministic_and_hash_sensitive() -> None:
    descriptor = _descriptor(executor=_executor)
    runner = _runner_with_result(descriptor)

    first = runner.run(_request(descriptor=descriptor, parameters={"window": 4}))
    same = runner.run(_request(descriptor=descriptor, parameters={"window": 4}))
    changed_parameters = runner.run(_request(descriptor=descriptor, parameters={"window": 5}))
    changed_executor = runner.run(
        _request(descriptor=_descriptor(executor=_executor, version="2"), parameters={"window": 4})
    )

    assert first.status == "completed"
    assert first == same
    assert first.run_id != changed_parameters.run_id
    assert first.run_id != changed_executor.run_id
    assert first.request.request_id == same.request.request_id


def test_unregistered_executor_is_retained_as_needs_input() -> None:
    request = _request(descriptor=_descriptor(executor=_executor))

    run = ExplorationRunner(ExplorationExecutorRegistry()).run(request)

    assert run.status == "needs_input"
    assert run.computation_state.computability == "needs_input"
    assert run.computation_state.promotion == "diagnostic_only"
    assert run.reason_codes == ("exploration_executor_unregistered",)
    assert run.provider_result is None


def test_executor_exception_and_invalid_output_become_retained_failed_runs() -> None:
    def raising(request: ExplorationRequest) -> ProviderResultInput:
        raise RuntimeError("boom")

    descriptor = _descriptor(executor=raising)
    registry = ExplorationExecutorRegistry()
    registry.register(descriptor, raising)
    failed = ExplorationRunner(registry, CanonicalAdmissionRegistry((_admission(),))).run(_request(descriptor=descriptor, executor=raising))

    assert failed.status == "failed"
    assert failed.reason_codes == ("exploration_executor_failed",)
    assert failed.failure_metadata == {"error_type": "RuntimeError"}

    def invalid_output(request: ExplorationRequest) -> dict[str, str]:
        return {"not": "a ProviderResultInput"}

    invalid_descriptor = _descriptor(executor=invalid_output)
    invalid_registry = ExplorationExecutorRegistry()
    invalid_registry.register(invalid_descriptor, invalid_output)
    invalid = ExplorationRunner(invalid_registry, CanonicalAdmissionRegistry((_admission(),))).run(_request(descriptor=invalid_descriptor, executor=invalid_output))

    assert invalid.status == "failed"
    assert invalid.reason_codes == ("exploration_invalid_provider_result",)


@pytest.mark.parametrize(
    ("result_kwargs", "reason_code"),
    (
        ({"source_artifact_id": "e" * 64}, "exploration_provider_result_source_mismatch"),
        ({"technique": "tga"}, "exploration_provider_result_technique_mismatch"),
        ({"source_content_hash": "f" * 64}, "exploration_provider_result_content_mismatch"),
    ),
)
def test_runner_rejects_misaligned_provider_result(
    result_kwargs: dict[str, str], reason_code: str
) -> None:
    def mismatched(request: ExplorationRequest) -> ProviderResultInput:
        return _provider_result(request, **result_kwargs)

    descriptor = _descriptor(executor=mismatched)
    registry = ExplorationExecutorRegistry()
    registry.register(descriptor, mismatched)

    run = ExplorationRunner(registry, CanonicalAdmissionRegistry((_admission(),))).run(_request(descriptor=descriptor, executor=mismatched))

    assert run.status == "failed"
    assert run.reason_codes == (reason_code,)


def test_registry_rejects_duplicate_executor_version_but_allows_a_new_version() -> None:
    registry = ExplorationExecutorRegistry()
    first = _descriptor()
    registry.register(first, _executor)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(first, _executor)

    second = _descriptor(version="2")
    registry.register(second, _executor)
    assert registry.resolve(second.executor_id, second.version) is not None

    with pytest.raises(TypeError, match="callable"):
        registry.register(_descriptor(version="3"), "return arbitrary code")  # type: ignore[arg-type]


def test_runner_accepts_a_valid_serialized_shared_provider_result() -> None:
    descriptor = _descriptor()
    registry = ExplorationExecutorRegistry()
    def serialized(request: ExplorationRequest) -> dict[str, object]:
        return _provider_result(request).to_dict()
    descriptor = _descriptor(executor=serialized)
    registry.register(descriptor, serialized)

    run = ExplorationRunner(registry, CanonicalAdmissionRegistry((_admission(),))).run(_request(descriptor=descriptor, executor=serialized))

    assert run.status == "completed"
    assert run.provider_result is not None
    assert run.provider_result.available_metric_paths == ("tan_delta_peak",)


def test_exploration_run_json_round_trip_detects_tampering() -> None:
    descriptor = _descriptor()
    run = _runner_with_result(descriptor).run(_request(descriptor=descriptor))

    assert ExplorationRun.from_dict(run.to_dict()) == run
    tampered = run.to_dict()
    tampered["reason_codes"] = ["tampered"]
    with pytest.raises(ValueError, match="hash"):
        ExplorationRun.from_dict(tampered)


def test_completed_exploration_projects_shared_result_into_reviewable_evidence() -> None:
    descriptor = _descriptor()
    run = _runner_with_result(descriptor).run(_request(descriptor=descriptor))

    selection = ExplorationEvidenceSelection.create(
        metric_paths=("tan_delta_peak",),
        claim_scope="Exploration result",
    )
    evidence = run.to_evidence_item(selection)

    assert evidence.status == "review_required"
    assert evidence.source_runs == (run.run_id,)
    assert evidence.raw_sources == (SOURCE_ARTIFACT_ID,)
    observed = evidence.to_dict()["observed_results"]
    assert observed["selected_metrics"] == {"tan_delta_peak": 0.83}
    assert observed["metric_manifest"] == [
        dict(row) for row in run.provider_result.metric_manifest
    ]
    assert observed["selection"] == selection.to_dict()
    assert observed["curated_projection_only"] is True
    assert "curated_projection_only" in evidence.limitations
    assert "exploration_method_requires_review" in evidence.limitations


def test_exploration_store_is_append_only_and_verifies_manifest_integrity(tmp_path: Path) -> None:
    descriptor = _descriptor()
    run = _runner_with_result(descriptor).run(_request(descriptor=descriptor))
    store = ExplorationRunStore(ProjectWorkspace.open(tmp_path))

    assert store.save(run) == run
    assert store.load(run.run_id) == run
    manifest = tmp_path / ".polynexus" / "research" / "exploration" / f"{run.run_id}.json"
    assert manifest.is_file()
    assert store.save(run) == run

    with pytest.raises(ValueError, match="immutable"):
        store.save(ExplorationRun.failed(run.request, "different_failure"))

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["status"] = "failed"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid"):
        store.load(run.run_id)
    records = store.list_records()
    assert len(records) == 1
    assert records[0]["run"] is None
    assert records[0]["error"]


def test_runner_requires_registered_canonical_admission_and_contract_valid_input() -> None:
    descriptor = _descriptor(executor=_executor)
    request_without_admission = _request(descriptor=descriptor, admission=None)
    # _request defaults to an admission, so construct the missing case directly.
    request_without_admission = ExplorationRequest.create(
        source_artifact_id=SOURCE_ARTIFACT_ID,
        source_content_hash=SOURCE_CONTENT_HASH,
        technique="dma",
        executor_id=descriptor.executor_id,
        executor_version=descriptor.version,
        executor_implementation_hash=descriptor.implementation_hash,
        executor_descriptor_hash=descriptor.descriptor_hash,
        method_intent="missing canonical admission",
        parameters={},
    )
    runner = _runner_with_result(descriptor)
    missing = runner.run(request_without_admission)
    assert missing.status == "needs_input"
    assert missing.reason_codes == ("exploration_canonical_admission_missing",)

    unregistered = runner.run(
        _request(descriptor=descriptor, admission=CanonicalAdmission.from_objects(
            CanonicalDataset.direct_envelope(_raw_artifact()), _raw_artifact(),
            axis_provenance={"temperature": "fixture"},
        ))
    )
    assert unregistered.status == "needs_input"
    assert unregistered.reason_codes == ("exploration_canonical_admission_unregistered",)

    invalid_parameter = runner.run(_request(descriptor=descriptor, parameters={"window": 0}))
    assert invalid_parameter.status == "failed"
    assert invalid_parameter.reason_codes == ("exploration_input_contract_violation",)
    assert "exploration_parameter_below_min:window" in invalid_parameter.failure_metadata["violations"]


def test_runner_rejects_undeclared_output_and_self_asserted_implementation_hash() -> None:
    descriptor = _descriptor(executor=_undeclared_metric_executor)
    registry = ExplorationExecutorRegistry()
    registry.register(descriptor, _undeclared_metric_executor)
    runner = ExplorationRunner(registry, CanonicalAdmissionRegistry((_admission(),)))
    run = runner.run(_request(descriptor=descriptor, executor=_undeclared_metric_executor))
    assert run.status == "failed"
    assert run.reason_codes == ("exploration_output_contract_violation",)
    assert "exploration_output_metric_undeclared:extra" in run.failure_metadata["violations"]

    with pytest.raises(ValueError, match="implementation hash"):
        ExplorationExecutorRegistry().register(
            _descriptor(executor=_executor, implementation_hash="c" * 64), _executor
        )

    descriptor_mismatch = ExplorationRequest.create(
        source_artifact_id=SOURCE_ARTIFACT_ID,
        source_content_hash=SOURCE_CONTENT_HASH,
        technique="dma",
        executor_id=descriptor.executor_id,
        executor_version=descriptor.version,
        executor_implementation_hash=descriptor.implementation_hash,
        executor_descriptor_hash="d" * 64,
        method_intent="descriptor mismatch",
        parameters={},
        canonical_admission=_admission(),
    )
    assert ExplorationRunner(
        registry, CanonicalAdmissionRegistry((_admission(),))
    ).run(descriptor_mismatch).reason_codes == ("exploration_executor_descriptor_mismatch",)


def test_automatic_exploration_retains_seeded_attempts_and_budget_stop() -> None:
    descriptor = _descriptor(executor=_executor)
    runner = _runner_with_result(descriptor)
    result = AutomaticExplorationRunner(runner).run(
        _request(descriptor=descriptor),
        ({"window": 1}, {"window": 1}, {"window": 2}, {"window": 3}),
        seed=41,
        budget=ExplorationBudget(max_attempts=2),
    )
    assert result.seed == 41
    assert result.stop_reason == "budget_max_attempts"
    assert len(result.attempts) == 2
    assert [attempt.request.attempt_id for attempt in result.attempts] == [
        "attempt-00000001", "attempt-00000002"
    ]
    assert all(attempt.request.seed == 41 for attempt in result.attempts)
    assert result.to_dict()["budget_hash"]


def test_curated_evidence_rejects_unavailable_metric() -> None:
    descriptor = _descriptor(executor=_executor)
    run = _runner_with_result(descriptor).run(_request(descriptor=descriptor))
    selection = ExplorationEvidenceSelection.create(
        metric_paths=("missing_metric",), claim_scope="should fail"
    )
    with pytest.raises(ValueError, match="not computed"):
        selection.project(run)


def test_capability_promotion_requires_all_independent_gates_and_returns_new_version() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="dma.loss_tangent.exploration",
        version="1",
        techniques=("dma",),
        input_contract={"input_type": "provider_result", "required_inputs": ("provider_result",)},
        output_schema={"metric_paths": ("tan_delta_peak",)},
        status="experimental",
    )
    evidence = tuple(
        CapabilityPromotionEvidence(kind=kind, evidence_id=f"{kind}-001", passed=True)
        for kind in ("independent_replay", "standard_sample", "negative_control", "uncertainty")
    )
    with pytest.raises(ValueError, match="unique"):
        CapabilityPromotionService.assess(descriptor, (*evidence, evidence[0]))
    blocked = CapabilityPromotionService.assess(descriptor, evidence)
    assert not blocked.passed
    with pytest.raises(ValueError, match="gates"):
        CapabilityPromotionService.promote(blocked)

    assessment = CapabilityPromotionService.assess(
        descriptor, evidence, human_scientific_review=True
    )
    promoted = CapabilityPromotionService.promote(assessment)
    assert promoted.status == "available"
    assert promoted.version == "1.promoted"
    assert promoted.content_hash != descriptor.content_hash
    assert descriptor.status == "experimental"


def test_isolated_worker_reuses_core_validation_and_enforces_network_and_timeout() -> None:
    descriptor = _descriptor(executor=_executor)
    runner = _runner_with_result(descriptor)
    isolated = IsolatedExplorationRunner(runner, ExplorationWorkerLimits(wall_time_s=10))
    completed = isolated.run(_request(descriptor=descriptor, executor=_executor))
    assert completed.status == "completed"
    assert completed.provider_result is not None

    network_descriptor = _descriptor(executor=_network_executor)
    network_registry = ExplorationExecutorRegistry()
    network_registry.register(network_descriptor, _network_executor)
    network_runner = ExplorationRunner(network_registry, CanonicalAdmissionRegistry((_admission(),)))
    blocked = IsolatedExplorationRunner(
        network_runner, ExplorationWorkerLimits(wall_time_s=10)
    ).run(_request(descriptor=network_descriptor, executor=_network_executor))
    assert blocked.status == "failed"
    assert blocked.reason_codes == ("exploration_worker_failed",)
    assert blocked.failure_metadata["error_type"] == "PermissionError", blocked.failure_metadata

    slow_descriptor = _descriptor(executor=_slow_executor)
    slow_registry = ExplorationExecutorRegistry()
    slow_registry.register(slow_descriptor, _slow_executor)
    slow_runner = ExplorationRunner(slow_registry, CanonicalAdmissionRegistry((_admission(),)))
    timed_out = IsolatedExplorationRunner(
        slow_runner, ExplorationWorkerLimits(wall_time_s=0.05)
    ).run(_request(descriptor=slow_descriptor, executor=_slow_executor))
    assert timed_out.status == "failed"
    assert timed_out.reason_codes == ("exploration_worker_timeout",)

    filesystem_descriptor = _descriptor(executor=_filesystem_executor)
    filesystem_registry = ExplorationExecutorRegistry()
    filesystem_registry.register(filesystem_descriptor, _filesystem_executor)
    filesystem_runner = ExplorationRunner(
        filesystem_registry, CanonicalAdmissionRegistry((_admission(),))
    )
    restricted = IsolatedExplorationRunner(filesystem_runner).run(
        _request(descriptor=filesystem_descriptor, executor=_filesystem_executor)
    )
    assert restricted.status == "failed"
    assert restricted.reason_codes == ("exploration_worker_failed",)
    assert restricted.failure_metadata["error_type"] == "PermissionError"

    large_descriptor = _descriptor(executor=_large_output_executor)
    large_registry = ExplorationExecutorRegistry()
    large_registry.register(large_descriptor, _large_output_executor)
    large_runner = ExplorationRunner(large_registry, CanonicalAdmissionRegistry((_admission(),)))
    limited = IsolatedExplorationRunner(
        large_runner, ExplorationWorkerLimits(max_output_bytes=512)
    ).run(_request(descriptor=large_descriptor, executor=_large_output_executor))
    assert limited.status == "failed"
    assert limited.reason_codes == ("exploration_worker_output_limit",)
