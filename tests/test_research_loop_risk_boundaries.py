from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from polynexus.cli.parser import build_parser
from polynexus.cli.run_research_loop_service import run_research_loop
from polynexus.core.project_workflow.models import canonical_json
from polynexus.core.project_workflow.research_loop import (
    ResearchAction,
    ResearchLoopService,
    ResearchTaskStore,
)
from polynexus.core.project_workflow.workspace import ProjectWorkspace
from polynexus.suite import handoff as suite_handoff


class _RunWorkflow:
    """Tiny formal-run boundary used to exercise orchestration only."""

    def __init__(self, *, hash_run_ids: bool = False) -> None:
        self.calls = 0
        self.requests = []
        self.hash_run_ids = hash_run_ids

    def run(self, request):
        self.calls += 1
        self.requests.append(request)
        return SimpleNamespace(
            run_id=(
                f"run-{request.request_hash[:16]}"
                if self.hash_run_ids
                else f"run-{self.calls}"
            ),
            status="review_required",
            reason_codes=(),
            manifest_path="",
        )


def _ready_service(
    tmp_path: Path, *, hash_run_ids: bool = False
) -> tuple[ResearchLoopService, _RunWorkflow, str]:
    workflow = _RunWorkflow(hash_run_ids=hash_run_ids)
    service = ResearchLoopService.open(tmp_path, project_service=workflow)
    task = service.create_task(
        task_id="risk-task",
        project_id="demo",
        research_question="exercise the recovery boundary",
    )
    service.propose_mapping(task.task_id, {"raw/sample.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    service.run(task.task_id)
    return service, workflow, task.task_id


def _confirmed_service(
    tmp_path: Path,
) -> tuple[ResearchLoopService, _RunWorkflow, str]:
    """Create a task that is confirmed but has not started a formal run."""
    workflow = _RunWorkflow()
    service = ResearchLoopService.open(tmp_path, project_service=workflow)
    task = service.create_task(
        task_id="confirmed-task",
        project_id="demo",
        research_question="exercise request validation",
    )
    service.propose_mapping(task.task_id, {"raw/sample.csv": {"sample_id": "A"}})
    service.confirm_mapping(task.task_id, approved=True, approver="user")
    return service, workflow, task.task_id


def _write_handoff_package(root: Path, *, run_ids: list[str] | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    package_inputs = {
        "ars-writing-input.json": {},
        "result-tables.json": {},
        "writing-evidence.json": {
            "techniques": {
                "nmr": {"evidence": [{"evidence_id": "evidence-1"}]}
            }
        },
        "evidence.json": {"items": [{"evidence_id": "evidence-1"}]},
        "citation-metrics.json": {
            "records": [{"metric_id": "metric-1", "evidence_id": "evidence-1"}]
        },
        "figure-index.json": {"figures": [{"id": "figure-1"}]},
    }
    for name, payload in package_inputs.items():
        (root / name).write_text(canonical_json(payload) + "\n", encoding="utf-8")
    selected_run_ids = list(run_ids or ["run-1"])
    runs_root = root / "runs"
    runs_root.mkdir(exist_ok=True)
    run_manifest_paths: list[str] = []
    for run_id in selected_run_ids:
        run_manifest_paths.append(f"runs/{run_id}.json")
        (runs_root / f"{run_id}.json").write_text(
            canonical_json(
                {
                    "run_id": run_id,
                    "request_parameters": {"research_task_id": "risk-task"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    artifact_hashes = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    unsigned = {
        "package_id": "risk-package",
        "version": 1,
        "status": "completed",
        "run_ids": selected_run_ids,
        "run_manifests": run_manifest_paths,
        "artifact_hashes": artifact_hashes,
    }
    manifest = {
        **unsigned,
        "package_hash": hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest(),
    }
    (root / "manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")


def _package_hash(root: Path) -> str:
    return str(json.loads((root / "manifest.json").read_text(encoding="utf-8"))["package_hash"])


def _refresh_package_hash(root: Path) -> None:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    unsigned = dict(manifest)
    unsigned.pop("package_hash", None)
    manifest["package_hash"] = hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()
    manifest_path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")


def _fake_view(run_ids: tuple[str, ...] = ("run-1",)) -> SimpleNamespace:
    return SimpleNamespace(
        package_id="risk-package",
        version=1,
        status="completed",
        human_review=(),
        techniques=(),
        run_ids=run_ids,
        metrics=(),
    )


def _attach_minimal_handoff(
    service: ResearchLoopService,
    task_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Open the ARS channel with a small but fully bound package fixture."""
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    latest_run_id = service.resume(task_id).run_ids[-1]
    _write_handoff_package(package, run_ids=[latest_run_id])
    monkeypatch.setattr(
        suite_handoff,
        "load_evidence_package_view",
        lambda root: _fake_view((latest_run_id,)),
    )
    service.handoff_to_ars(task_id, package)
    return package


def _bind_persisted_run_manifest(
    service: ResearchLoopService,
    task_id: str,
    manifest_path: Path,
    *,
    request_hash: str | None = None,
) -> Path:
    """Replace the fake run's in-memory-only reference with a persisted one."""
    task = service.store.load(task_id)
    refs = [dict(value) for value in task.metadata["run_refs"]]
    run_ref = next(value for value in refs if value.get("run_id") == task.run_ids[-1])
    payload = {
        "run_id": run_ref["run_id"],
        "request_hash": request_hash or run_ref["request_hash"],
        "plan_hash": run_ref["plan_hash"],
        "recipe_hash": run_ref["recipe_hash"],
        "status": task.metadata["run_status"],
    }
    manifest_path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    run_ref["manifest_path"] = str(manifest_path)
    service.store.transition(
        task_id,
        task.status,
        metadata={**dict(task.metadata), "run_refs": refs},
    )
    return manifest_path


def test_handoff_rejects_manifest_tamper_and_artifact_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_handoff_package(tmp_path)
    monkeypatch.setattr(suite_handoff, "load_evidence_package_view", lambda root: _fake_view())

    assert suite_handoff.build_suite_handoff(tmp_path)["status"] == "ready"

    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                **json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8")),
                "status": "tampered",
            }
        ),
        encoding="utf-8",
    )
    manifest_result = suite_handoff.build_suite_handoff(tmp_path)
    assert manifest_result["status"] == "blocked"
    assert "evidence_package_integrity_invalid" in manifest_result["reason_codes"]

    # Restore the valid manifest, then alter a copied artifact without changing
    # its declared hash.
    _write_handoff_package(tmp_path)
    (tmp_path / "writing-evidence.json").write_text("tampered\n", encoding="utf-8")
    artifact_result = suite_handoff.build_suite_handoff(tmp_path)
    assert artifact_result["status"] == "blocked"
    assert "evidence_package_integrity_invalid" in artifact_result["reason_codes"]


def test_handoff_rejects_package_manifest_run_binding_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    _write_handoff_package(package, run_ids=["run-1"])
    monkeypatch.setattr(
        suite_handoff,
        "build_suite_handoff",
        lambda package_path, **kwargs: {
            "status": "ready",
            "handoff_id": "handoff-binding",
            "task_id": kwargs["task_id"],
            "package": {"path": str(package_path), "package_hash": _package_hash(package_path)},
            "run_ids": ["run-1"],
        },
    )
    # The package manifest declares a different run than the mocked handoff.
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    manifest["run_ids"] = ["run-2"]
    (package / "manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    _refresh_package_hash(package)

    with pytest.raises(ValueError, match="manifest"):
        service.handoff_to_ars(task_id, package)


def test_handoff_requires_complete_packager_run_manifest_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A handoff package must carry the packager's copied task-owned run."""
    service, _workflow, task_id = _ready_service(tmp_path)
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    _write_handoff_package(package, run_ids=["run-1"])
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    manifest.pop("run_manifests", None)
    (package / "manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    _refresh_package_hash(package)
    monkeypatch.setattr(
        suite_handoff,
        "build_suite_handoff",
        lambda package_path, **kwargs: {
            "status": "ready",
            "handoff_id": "handoff-run-manifest",
            "task_id": kwargs["task_id"],
            "package": {"path": str(package_path), "package_hash": _package_hash(package_path)},
            "run_ids": ["run-1"],
        },
    )

    with pytest.raises(ValueError, match="run manifest"):
        service.handoff_to_ars(task_id, package)


def test_handoff_rejects_ready_provider_without_package_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A compatible provider cannot advance a formal task without a manifest."""
    service, _workflow, task_id = _ready_service(tmp_path)
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    latest_run_id = service.resume(task_id).run_ids[-1]
    _write_handoff_package(package, run_ids=[latest_run_id])
    (package / "manifest.json").unlink()
    monkeypatch.setattr(
        suite_handoff,
        "build_suite_handoff",
        lambda package_path, **kwargs: {
            "status": "ready",
            "handoff_id": "handoff-no-manifest",
            "task_id": kwargs["task_id"],
            "package": {"path": str(package_path), "package_hash": "a" * 64},
            "files": {
                "ars_writing_input": "ars-writing-input.json",
                "result_tables": "result-tables.json",
                "writing_evidence": "writing-evidence.json",
                "evidence": "evidence.json",
                "citation_metrics": "citation-metrics.json",
                "figure_index": "figure-index.json",
            },
            "run_ids": [latest_run_id],
        },
    )

    with pytest.raises(ValueError, match="package manifest"):
        service.handoff_to_ars(task_id, package)
    persisted = service.store.load(task_id)
    assert persisted.status == "checkpointed"
    assert persisted.handoff_ids == ()


def test_handoff_rejects_manifest_run_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    _write_handoff_package(package, run_ids=["run-1"])
    (package / "runs" / "run-1.json").unlink()
    monkeypatch.setattr(
        suite_handoff,
        "build_suite_handoff",
        lambda package_path, **kwargs: {
            "status": "ready",
            "handoff_id": "handoff-missing-run-file",
            "task_id": kwargs["task_id"],
            "package": {"path": str(package_path), "package_hash": _package_hash(package_path)},
            "run_ids": ["run-1"],
        },
    )

    with pytest.raises(ValueError, match="run manifest"):
        service.handoff_to_ars(task_id, package)


def test_handoff_rejects_run_manifest_without_task_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    _write_handoff_package(package, run_ids=["run-1"])
    (package / "runs" / "run-1.json").write_text(
        canonical_json({"run_id": "run-1", "request_parameters": {}}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        suite_handoff,
        "build_suite_handoff",
        lambda package_path, **kwargs: {
            "status": "ready",
            "handoff_id": "handoff-missing-owner",
            "task_id": kwargs["task_id"],
            "package": {"path": str(package_path), "package_hash": _package_hash(package_path)},
            "run_ids": ["run-1"],
        },
    )

    with pytest.raises(ValueError, match="ownership|another task"):
        service.handoff_to_ars(task_id, package)


def test_handoff_rejects_run_manifest_owned_by_another_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    _write_handoff_package(package, run_ids=["run-1"])
    (package / "runs" / "run-1.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "request_parameters": {"research_task_id": "other-task"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        suite_handoff,
        "build_suite_handoff",
        lambda package_path, **kwargs: {
            "status": "ready",
            "handoff_id": "handoff-owner",
            "task_id": kwargs["task_id"],
            "package": {"path": str(package_path), "package_hash": _package_hash(package_path)},
            "run_ids": ["run-1"],
        },
    )

    with pytest.raises(ValueError, match="another task"):
        service.handoff_to_ars(task_id, package)


def test_handoff_rejects_missing_package_path_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    _write_handoff_package(package, run_ids=["run-1"])
    monkeypatch.setattr(
        suite_handoff,
        "build_suite_handoff",
        lambda package_path, **kwargs: {
            "status": "ready",
            "handoff_id": "handoff-no-package",
            "task_id": kwargs["task_id"],
            "run_ids": ["run-1"],
        },
    )

    with pytest.raises(ValueError, match="package"):
        service.handoff_to_ars(task_id, package)


def test_ars_actions_require_a_validated_handoff(tmp_path: Path) -> None:
    """A checkpoint alone must not open the ARS action channel."""
    service, _workflow, task_id = _ready_service(tmp_path)
    service.checkpoint(task_id)

    with pytest.raises(ValueError, match="handoff"):
        service.record_ars_actions(
            task_id,
            ({"kind": "edit", "payload": {"section": "Methods"}},),
        )


def test_formal_preflight_requires_a_validated_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caller-supplied ARS JSON cannot substitute for the package handoff."""
    service, _workflow, task_id = _ready_service(tmp_path)
    service.checkpoint(task_id)

    manuscript = {
        "source_id": "forged-source",
        "sections": [{"section_id": "results", "claim_ids": ["claim-1"]}],
        "claims": [{
            "claim_id": "claim-1",
            "evidence_ids": ["evidence-1"],
            "figure_ids": ["figure-1"],
            "citation_keys": ["ref-1"],
        }],
        "evidence": [{"evidence_id": "evidence-1"}],
        "figures": [{"figure_id": "figure-1"}],
        "citations": [{"key": "ref-1", "verified": True}],
        "ars_workflow": {"status": "completed", "integrity": "passed"},
        "methods": {"status": "complete"},
        "zotero": {"status": "verified", "connected": True},
        "format_report": {"status": "passed"},
        "human_review": [],
        "visible_text": "A clean scientific result.",
    }

    with pytest.raises(ValueError, match="handoff"):
        service.submission_preflight(task_id, manuscript)


def test_formal_preflight_requires_persisted_ars_completion_and_package_claim_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(task_id, ({"kind": "edit", "payload": {}},))[0]
    service.resolve_action(task_id, action.action_id, approved=True, note="edited")
    manuscript = {
        "source_id": "risk-package",
        "sections": [{"section_id": "results", "claim_ids": ["claim-1"]}],
        "claims": [{
            "claim_id": "claim-1",
            "text": "The measured signal changed.",
            "evidence_ids": ["evidence-1"],
            "metric_ids": ["metric-1"],
            "figure_ids": ["figure-1"],
        }],
        "evidence": [{"evidence_id": "evidence-1"}],
        "metrics": [{"metric_id": "metric-1"}],
        "figures": [{"figure_id": "figure-1"}],
        "citations": [{"key": "ref-1", "verified": True}],
        "methods": {"status": "complete"},
        "zotero": {"status": "verified", "connected": True},
        "format_report": {"status": "passed"},
        "human_review": [],
        "visible_text": "A clean scientific result.",
        # This caller-controlled field must never substitute for a persisted
        # ARS completion record.
        "ars_workflow": {"status": "completed", "integrity": "passed"},
    }

    with pytest.raises(ValueError, match="ARS completion"):
        service.submission_preflight(task_id, manuscript)

    completion = service.record_ars_completion(
        task_id,
        {"status": "completed", "integrity": "passed", "review_id": "review-1"},
    )
    assert completion["ars_completion"]["review_id"] == "review-1"
    assert service.submission_preflight(task_id, manuscript).status == "passed"


def test_formal_preflight_rejects_claim_references_not_in_handoff_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(task_id, ({"kind": "edit", "payload": {}},))[0]
    service.resolve_action(task_id, action.action_id, approved=True, note="edited")
    service.record_ars_completion(task_id, {"status": "completed", "integrity": "passed"})
    manuscript = {
        "source_id": "risk-package",
        "sections": [{"section_id": "results", "claim_ids": ["claim-1"]}],
        "claims": [{
            "claim_id": "claim-1",
            "text": "The measured signal changed.",
            "evidence_ids": ["forged-evidence"],
            "metric_ids": ["metric-1"],
            "figure_ids": ["figure-1"],
        }],
        "evidence": [{"evidence_id": "forged-evidence"}],
        "metrics": [{"metric_id": "metric-1"}],
        "figures": [{"figure_id": "figure-1"}],
        "citations": [{"key": "ref-1", "verified": True}],
        "methods": {"status": "complete"},
        "zotero": {"status": "verified", "connected": True},
        "format_report": {"status": "passed"},
        "human_review": [],
        "visible_text": "A clean scientific result.",
    }

    report = service.submission_preflight(task_id, manuscript)

    assert report.status == "failed"
    assert "package_evidence_unbound:forged-evidence" in report.errors


def test_formal_preflight_rejects_an_empty_data_research_manuscript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(task_id, ({"kind": "edit", "payload": {}},))[0]
    service.resolve_action(task_id, action.action_id, approved=True, note="edited")
    service.record_ars_completion(task_id, {"status": "completed", "integrity": "passed"})

    report = service.submission_preflight(
        task_id,
        {
            "source_id": "risk-package",
            "sections": [],
            "claims": [],
            "evidence": [],
            "figures": [{"figure_id": "figure-1"}],
            "citations": [{"key": "ref-1", "verified": True}],
            "methods": {"status": "complete"},
            "zotero": {"status": "verified", "connected": True},
            "format_report": {"status": "passed"},
            "human_review": [],
            "visible_text": "A clean scientific result.",
        },
    )

    assert report.status == "failed"
    assert "data_research_claims_missing" in report.errors


def test_new_ars_action_invalidates_an_earlier_completion_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(task_id, ({"kind": "edit", "payload": {}},))[0]
    service.resolve_action(task_id, action.action_id, approved=True, note="edited")
    service.record_ars_completion(task_id, {"status": "completed", "integrity": "passed"})
    service.record_ars_actions(task_id, ({"kind": "edit", "payload": {}},))

    assert "ars_completion_id" not in service.resume(task_id).metadata


def test_handoff_and_package_are_revalidated_after_initial_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing a pinned package or handoff record blocks later stages."""
    service, _workflow, task_id = _ready_service(tmp_path)
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    _write_handoff_package(package, run_ids=["run-1"])
    monkeypatch.setattr(suite_handoff, "load_evidence_package_view", lambda root: _fake_view())
    handed_off = service.handoff_to_ars(task_id, package)
    assert handed_off.status == "ars_in_progress"

    (package / "writing-evidence.json").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="handoff|integrity|package"):
        service.record_ars_actions(
            task_id,
            ({"kind": "edit", "payload": {}},),
        )

    # Restore the package and tamper with the immutable task-bound handoff
    # record itself.  A later resume must validate it instead of trusting only
    # the task's handoff ID.
    _write_handoff_package(package, run_ids=["run-1"])
    record = (
        tmp_path
        / ".polynexus"
        / "research"
        / "tasks"
        / task_id
        / "handoffs"
        / f"{handed_off.handoff_ids[-1]}.json"
    )
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload["status"] = "tampered"
    record.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="handoff"):
        service.resume(task_id)


def test_complete_export_revalidates_handoff_after_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A passed preflight must not make a later package mutation acceptable."""
    service, _workflow, task_id = _ready_service(tmp_path)
    package = tmp_path / "package"
    service.checkpoint(task_id, package_path=package)
    _write_handoff_package(package, run_ids=["run-1"])
    monkeypatch.setattr(suite_handoff, "load_evidence_package_view", lambda root: _fake_view())
    service.handoff_to_ars(task_id, package)
    action = service.record_ars_actions(task_id, ({"kind": "edit", "payload": {}},))[0]
    service.resolve_action(task_id, action.action_id, approved=True, note="ready")
    service.record_ars_completion(task_id, {"status": "completed", "integrity": "passed"})

    manuscript = {
        "source_id": "risk-package",
        "sections": [{"section_id": "results", "claim_ids": ["claim-1"]}],
        "claims": [{
            "claim_id": "claim-1",
            "text": "The measured signal changed.",
            "evidence_ids": ["evidence-1"],
            "metric_ids": ["metric-1"],
            "figure_ids": ["figure-1"],
        }],
        "evidence": [{"evidence_id": "evidence-1"}],
        "metrics": [{"metric_id": "metric-1"}],
        "figures": [{"figure_id": "figure-1"}],
        "citations": [{"key": "r", "verified": True}],
        "formulas": [],
        "methods": {"status": "complete"},
        "zotero": {"status": "verified", "connected": True},
        "format_report": {"status": "passed"},
        "human_review": [],
        "visible_text": "A clean scientific result.",
    }
    report = service.submission_preflight(task_id, manuscript)
    assert report.status == "passed"

    export_path = tmp_path / "manuscript.docx"
    export_path.write_bytes(b"docx")
    (package / "manifest.json").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="handoff|integrity|package"):
        service.complete_export(task_id, (export_path,))


def test_resolve_action_recovers_after_transition_crash_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(
        task_id,
        (
            {
                "kind": "edit",
                "payload": {"section": "Methods", "nested": [1, {"unit": "K"}]},
            },
        ),
    )[0]

    original_transition = service.store.transition
    crashed = False

    def crash_once(*args, **kwargs):
        nonlocal crashed
        if not crashed:
            crashed = True
            raise RuntimeError("simulated process loss")
        return original_transition(*args, **kwargs)

    monkeypatch.setattr(service.store, "transition", crash_once)
    with pytest.raises(RuntimeError, match="process loss"):
        service.resolve_action(task_id, action.action_id, approved=True, note="edited")
    monkeypatch.setattr(service.store, "transition", original_transition)

    recovered = service.resolve_action(task_id, action.action_id, approved=True, note="edited")
    assert recovered.status == "ars_in_progress"
    assert recovered.metadata["last_action"]["action_id"] == action.action_id

    # A repeated client delivery must not append another resolution revision.
    revision_before = service.resume(task_id).revision
    repeated = service.resolve_action(task_id, action.action_id, approved=True, note="edited")
    assert repeated.revision == revision_before
    assert service.store.load_action(task_id, action.action_id).revision == 2


def test_resolve_action_replay_with_conflicting_decision_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(
        task_id, ({"kind": "edit", "payload": {}},)
    )[0]
    service.resolve_action(task_id, action.action_id, approved=True, note="accepted")

    with pytest.raises(ValueError, match="different|already resolved"):
        service.resolve_action(task_id, action.action_id, approved=False, note="accepted")


def test_load_action_rejects_tampered_base_identity(tmp_path: Path) -> None:
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    task = store.create_task(project_id="demo", research_question="q")
    action = ResearchAction.create(task_id=task.task_id, kind="edit", payload={})
    store.save_action(action)
    action_path = (
        tmp_path
        / ".polynexus"
        / "research"
        / "tasks"
        / task.task_id
        / "actions"
        / f"{action.action_id}.json"
    )
    payload = json.loads(action_path.read_text(encoding="utf-8"))
    payload["task_id"] = "other-task"
    action_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid|hash"):
        store.load_action(task.task_id, action.action_id)


def test_load_task_rejects_tampered_revision_identity(tmp_path: Path) -> None:
    store = ResearchTaskStore(ProjectWorkspace.open(tmp_path))
    task = store.create_task(project_id="demo", research_question="q")
    revision_path = (
        tmp_path
        / ".polynexus"
        / "research"
        / "tasks"
        / task.task_id
        / "revisions"
        / "task-000001.json"
    )
    payload = json.loads(revision_path.read_text(encoding="utf-8"))
    payload["task_id"] = "other-task"
    revision_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid|hash|revision"):
        store.load(task.task_id)


def test_cli_redirects_provider_progress_to_stderr(monkeypatch, capsys, tmp_path: Path) -> None:
    class FakeTask:
        status = "checkpointed"

        def to_dict(self):
            return {"status": self.status}

    class FakeService:
        @classmethod
        def open(cls, root):
            return cls()

        def run(self, task_id, *, requested_outputs):
            print("provider progress should not corrupt JSON")
            return FakeTask()

    monkeypatch.setattr("polynexus.cli.run_research_loop_service.ResearchLoopService", FakeService)
    args = build_parser().parse_args(
        [
            "research-loop",
            "run",
            "--project-root",
            str(tmp_path),
            "--task-id",
            "task-1",
        ]
    )

    assert run_research_loop(args) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "operation": "run",
        "reason_codes": [],
        "status": "checkpointed",
        "task": {"status": "checkpointed"},
    }
    assert "provider progress" in captured.err


def test_recompute_same_outputs_carries_new_revision_nonce_and_parameters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, workflow, task_id = _ready_service(tmp_path, hash_run_ids=True)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    service.record_ars_actions(
        task_id,
        (
            {
                "kind": "recompute",
                "payload": {
                    "reason": "fit window",
                    "request_parameters": {"region": "amide-I"},
                },
            },
        ),
    )
    # Keep the requested outputs identical to the first run; only the
    # orchestration revision/action provenance should distinguish the run.
    recomputed = service.recompute(task_id)

    assert recomputed.status == "checkpointed"
    assert len(recomputed.run_ids) == 2
    assert len(set(recomputed.run_ids)) == 2
    assert workflow.requests[0].request_hash != workflow.requests[1].request_hash
    assert workflow.requests[0].parameters["research_task_revision"] != workflow.requests[1].parameters[
        "research_task_revision"
    ]
    assert workflow.requests[1].parameters["region"] == "amide-I"
    assert workflow.requests[1].parameters["recompute_payload"]["reason"] == "fit window"


def test_recompute_rejects_malformed_parameters_without_consuming_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(
        task_id,
        (
            {
                "kind": "recompute",
                "payload": {"request_parameters": ["not-a-mapping"]},
            },
        ),
    )[0]

    with pytest.raises(ValueError, match="request_parameters"):
        service.recompute(task_id)

    assert service.store.load_action(task_id, action.action_id).status == "pending"
    assert service.resume(task_id).status == "revision_required"


def test_recompute_recovers_when_process_stops_after_action_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The persisted recompute route, not a transient call stack, resumes work."""
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(
        task_id,
        ({"kind": "recompute", "payload": {"reason": "fit window"}},),
    )[0]

    original_transition = service.store.transition

    def stop_after_resolution(*args, **kwargs):
        if kwargs.get("stage") == "action_resolved":
            raise RuntimeError("simulated process loss")
        return original_transition(*args, **kwargs)

    monkeypatch.setattr(service.store, "transition", stop_after_resolution)
    with pytest.raises(RuntimeError, match="process loss"):
        service.recompute(task_id)

    monkeypatch.setattr(service.store, "transition", original_transition)

    stalled = service.resume(task_id)
    assert stalled.status == "revision_required"
    assert stalled.metadata["recompute_route"]["action_id"] == action.action_id
    assert service.store.load_action(task_id, action.action_id).status == "resolved"

    assert service.recompute(task_id).status == "checkpointed"


def test_run_rejects_non_json_parameters_without_leaving_running_head(
    tmp_path: Path,
) -> None:
    service, workflow, task_id = _confirmed_service(tmp_path)

    with pytest.raises((TypeError, ValueError)):
        service.run(task_id, request_parameters={"bad": object()})

    task = service.store.load(task_id)
    assert task.status == "blocked"
    assert task.metadata["run_error"]
    assert workflow.calls == 0
    # The blocked state is intentionally recoverable through a new mapping
    # confirmation; it must never be stranded in an un-runnable ``running``
    # state after request construction fails.
    assert service.resume(task_id).status == "blocked"


def test_run_cannot_bypass_pending_recompute_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(
        task_id,
        ({"kind": "recompute", "payload": {"reason": "fit window"}},),
    )[0]

    with pytest.raises(ValueError, match="recompute action"):
        service.run(task_id)

    assert workflow.calls == 1
    assert service.store.load_action(task_id, action.action_id).status == "pending"
    assert service.resume(task_id).status == "revision_required"


def test_mapping_confirmation_requires_a_real_boolean_decision(
    tmp_path: Path,
) -> None:
    service, _workflow, task_id = _confirmed_service(tmp_path)
    # Move the task back to the explicit confirmation state for this API
    # boundary test without inventing a confirmed mapping.
    service.store.transition(
        task_id,
        "awaiting_mapping_confirmation",
        mapping_confirmation={"status": "pending"},
        confirmed_mapping={},
    )

    with pytest.raises(ValueError, match="boolean"):
        service.confirm_mapping(task_id, approved="false", approver="user")  # type: ignore[arg-type]

    assert service.store.load(task_id).status == "awaiting_mapping_confirmation"


def test_action_resolution_requires_a_real_boolean_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(
        task_id,
        ({"kind": "edit", "payload": {}},),
    )[0]

    with pytest.raises(ValueError, match="boolean"):
        service.resolve_action(task_id, action.action_id, approved="false", note="bad")  # type: ignore[arg-type]

    assert service.store.load_action(task_id, action.action_id).status == "pending"
    assert service.resume(task_id).status == "ars_in_progress"


def test_restart_rejects_missing_run_manifest(tmp_path: Path) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    assert not service.store.load(task_id).metadata["run_refs"][0]["manifest_path"]

    restarted = ResearchLoopService.open(tmp_path, project_service=_RunWorkflow())
    with pytest.raises(ValueError, match="run manifest.*missing"):
        restarted.resume(task_id)


def test_restart_rejects_run_manifest_request_hash_mismatch(tmp_path: Path) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _bind_persisted_run_manifest(
        service,
        task_id,
        tmp_path / "run-1.json",
        request_hash="different-request-hash",
    )

    restarted = ResearchLoopService.open(tmp_path, project_service=_RunWorkflow())
    with pytest.raises(ValueError, match="request hash"):
        restarted.resume(task_id)


def test_restart_accepts_exact_persisted_run_binding(tmp_path: Path) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _bind_persisted_run_manifest(service, task_id, tmp_path / "run-1.json")

    restarted = ResearchLoopService.open(tmp_path, project_service=_RunWorkflow())
    assert restarted.resume(task_id).status == "checkpointed"


def test_resume_rejects_unsafe_action_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    task = service.store.load(task_id)
    service.store.transition(
        task_id,
        task.status,
        action_ids=("../escape",),
    )

    with pytest.raises(ValueError, match="action id"):
        service.resume(task_id)


def test_resume_rejects_missing_action_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    action = service.record_ars_actions(
        task_id,
        ({"kind": "edit", "payload": {"section": "Methods"}},),
    )[0]
    action_path = (
        tmp_path
        / ".polynexus"
        / "research"
        / "tasks"
        / task_id
        / "actions"
        / f"{action.action_id}.json"
    )
    action_path.unlink()

    with pytest.raises(ValueError, match="action.*missing|action.*invalid"):
        service.resume(task_id)


@pytest.mark.parametrize("replacement", (b"edit", b"longer-export"))
def test_completed_resume_revalidates_export_hash_and_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: bytes,
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    service.record_ars_completion(task_id, {"status": "completed", "integrity": "passed"})
    service.store.transition(task_id, "export_ready", stage="submission_preflight")
    export_path = tmp_path / "manuscript.docx"
    export_path.write_bytes(b"docx")

    completed = service.complete_export(task_id, (export_path,))
    artifact = completed.metadata["export_artifacts"][0]
    assert artifact["path"] == str(export_path.resolve())
    assert artifact["size"] == 4
    assert artifact["sha256"] == hashlib.sha256(b"docx").hexdigest()

    export_path.write_bytes(replacement)
    with pytest.raises(ValueError, match="export artifact.*integrity"):
        service.resume(task_id)


def test_completed_resume_requires_export_artifact_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    _attach_minimal_handoff(service, task_id, tmp_path, monkeypatch)
    service.record_ars_completion(task_id, {"status": "completed", "integrity": "passed"})
    export_path = tmp_path / "manuscript.docx"
    export_path.write_bytes(b"docx")
    task = service.store.transition(task_id, "export_ready", stage="submission_preflight")
    service.store.transition(
        task_id,
        "completed",
        stage="export_complete",
        metadata={**dict(task.metadata), "export_paths": (str(export_path.resolve()),)},
    )

    with pytest.raises(ValueError, match="export artifact.*metadata"):
        service.resume(task_id)


def test_direct_checkpoint_after_restart_rejects_missing_run_manifest(
    tmp_path: Path,
) -> None:
    service, _workflow, task_id = _ready_service(tmp_path)
    restarted = ResearchLoopService.open(tmp_path, project_service=_RunWorkflow())

    with pytest.raises(ValueError, match="run manifest.*missing"):
        restarted.checkpoint(task_id)
