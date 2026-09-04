from __future__ import annotations

import json
from pathlib import Path

import pytest

from polynexus.core.ai_platform.contracts import ComputationState, ProviderResultInput
from polynexus.core.exploration import (
    ExplorationExecutorDescriptor,
    ExplorationExecutorRegistry,
    ExplorationRequest,
    ExplorationRun,
    ExplorationRunStore,
    ExplorationRunner,
)
from polynexus.core.project_workflow.workspace import ProjectWorkspace


SOURCE_ARTIFACT_ID = "a" * 64
SOURCE_CONTENT_HASH = "b" * 64
IMPLEMENTATION_HASH = "c" * 64


def _descriptor(
    *,
    executor_id: str = "dma.loss_tangent_exploration",
    version: str = "1",
    implementation_hash: str = IMPLEMENTATION_HASH,
    techniques: tuple[str, ...] = ("dma",),
) -> ExplorationExecutorDescriptor:
    return ExplorationExecutorDescriptor.create(
        executor_id=executor_id,
        version=version,
        implementation_hash=implementation_hash,
        supported_techniques=techniques,
        input_contract={"source": "content_addressed_raw_artifact"},
        output_contract={"result": "provider_result_input"},
    )


def _request(
    *,
    descriptor: ExplorationExecutorDescriptor | None = None,
    parameters: dict[str, object] | None = None,
) -> ExplorationRequest:
    descriptor = descriptor or _descriptor()
    return ExplorationRequest.create(
        source_artifact_id=SOURCE_ARTIFACT_ID,
        source_content_hash=SOURCE_CONTENT_HASH,
        technique="DMA",
        executor_id=descriptor.executor_id,
        executor_version=descriptor.version,
        executor_implementation_hash=descriptor.implementation_hash,
        method_intent="Find the loss-tangent peak for comparison.",
        parameters={} if parameters is None else parameters,
        parent_run_id="compute-run-001",
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


def _runner_with_result(descriptor: ExplorationExecutorDescriptor) -> ExplorationRunner:
    registry = ExplorationExecutorRegistry()
    registry.register(descriptor, lambda request: _provider_result(request))
    return ExplorationRunner(registry)


def test_exploration_request_and_run_are_deterministic_and_hash_sensitive() -> None:
    descriptor = _descriptor()
    runner = _runner_with_result(descriptor)

    first = runner.run(_request(descriptor=descriptor, parameters={"window": 4}))
    same = runner.run(_request(descriptor=descriptor, parameters={"window": 4}))
    changed_parameters = runner.run(_request(descriptor=descriptor, parameters={"window": 5}))
    changed_executor = runner.run(
        _request(descriptor=_descriptor(implementation_hash="d" * 64), parameters={"window": 4})
    )

    assert first.status == "completed"
    assert first == same
    assert first.run_id != changed_parameters.run_id
    assert first.run_id != changed_executor.run_id
    assert first.request.request_id == same.request.request_id


def test_unregistered_executor_is_retained_as_needs_input() -> None:
    request = _request()

    run = ExplorationRunner(ExplorationExecutorRegistry()).run(request)

    assert run.status == "needs_input"
    assert run.computation_state.computability == "needs_input"
    assert run.computation_state.promotion == "diagnostic_only"
    assert run.reason_codes == ("exploration_executor_unregistered",)
    assert run.provider_result is None


def test_executor_exception_and_invalid_output_become_retained_failed_runs() -> None:
    descriptor = _descriptor()
    registry = ExplorationExecutorRegistry()
    registry.register(descriptor, lambda request: (_ for _ in ()).throw(RuntimeError("boom")))
    failed = ExplorationRunner(registry).run(_request(descriptor=descriptor))

    assert failed.status == "failed"
    assert failed.reason_codes == ("exploration_executor_failed",)
    assert failed.failure_metadata == {"error_type": "RuntimeError"}

    invalid_registry = ExplorationExecutorRegistry()
    invalid_registry.register(descriptor, lambda request: {"not": "a ProviderResultInput"})
    invalid = ExplorationRunner(invalid_registry).run(_request(descriptor=descriptor))

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
    descriptor = _descriptor()
    registry = ExplorationExecutorRegistry()
    registry.register(descriptor, lambda request: _provider_result(request, **result_kwargs))

    run = ExplorationRunner(registry).run(_request(descriptor=descriptor))

    assert run.status == "failed"
    assert run.reason_codes == (reason_code,)


def test_registry_rejects_duplicate_executor_version_but_allows_a_new_version() -> None:
    registry = ExplorationExecutorRegistry()
    first = _descriptor()
    registry.register(first, lambda request: _provider_result(request))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(first, lambda request: _provider_result(request))

    second = _descriptor(version="2")
    registry.register(second, lambda request: _provider_result(request))
    assert registry.resolve(second.executor_id, second.version) is not None

    with pytest.raises(TypeError, match="callable"):
        registry.register(_descriptor(version="3"), "return arbitrary code")  # type: ignore[arg-type]


def test_runner_accepts_a_valid_serialized_shared_provider_result() -> None:
    descriptor = _descriptor()
    registry = ExplorationExecutorRegistry()
    registry.register(descriptor, lambda request: _provider_result(request).to_dict())

    run = ExplorationRunner(registry).run(_request(descriptor=descriptor))

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

    evidence = run.to_evidence_item()

    assert evidence.status == "review_required"
    assert evidence.source_runs == (run.run_id,)
    assert evidence.raw_sources == (SOURCE_ARTIFACT_ID,)
    observed = evidence.to_dict()["observed_results"]
    assert observed["provider_result"] == run.provider_result.to_dict()
    assert observed["metric_manifest"] == [
        dict(row) for row in run.provider_result.metric_manifest
    ]
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
