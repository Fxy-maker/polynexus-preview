"""Regression coverage for the direct legacy-engine compute façade."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from polynexus.core.compute.service import ComputeRunService


class FakeEngine:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def run_pipeline(self, path: str, output_dir: str, **options: Any) -> Any:
        self.calls.append((path, output_dir, options))
        return self.result


class ExplodingProvider:
    def run_pipeline(self, path: str, output_dir: str, **options: Any) -> Any:
        raise RuntimeError("provider internals must not escape")


class LegacyResultWithoutEvidenceAccess:
    parameters = {"t_half_s": 12.5}
    figures = {"curve": "curve.svg"}
    metadata = {"provider": "fake"}
    validation_warnings = ["no_background"]
    quality_flags = {"fit": "WARN"}
    validation_summary = "fit needs inspection"
    validation_passed = False

    @property
    def analysis_evidence(self) -> object:
        raise AssertionError("compute result projection must not access analysis_evidence")


def test_direct_run_completes_with_projected_legacy_warnings(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("data", encoding="utf-8")
    legacy_result = LegacyResultWithoutEvidenceAccess()
    engine = FakeEngine(legacy_result)

    run = ComputeRunService(lambda technique, config=None, submodule_id=None: engine).run_direct(
        technique="dsc",
        path=source,
        output_dir=tmp_path / "out",
        pipeline_options={"skip_to": None},
    )

    assert run.status == "completed"
    assert run.artifact.path == str(source.resolve())
    assert run.dataset is not None
    assert run.dataset.template_id == "raw-file-envelope.v1"
    assert run.plan is not None
    assert run.plan.output_dir == str((tmp_path / "out").resolve())
    assert dict(run.plan.pipeline_options) == {"skip_to": None}
    assert dict(run.plan.parameter_sources) == {"skip_to": "user"}
    assert run.result is not None
    assert run.result.metrics == {"t_half_s": 12.5}
    assert run.result.figures == {"curve": "curve.svg"}
    assert run.result.metadata == {"provider": "fake"}
    assert run.result.warnings == (
        "no_background",
        "quality_flag:fit:WARN",
        "fit needs inspection",
    )
    assert run.legacy_result is legacy_result
    assert "legacy_result" not in run.to_dict()
    assert engine.calls == [
        (
            str(source.resolve()),
            str((tmp_path / "out").resolve()),
            {"skip_to": None},
        )
    ]


def test_direct_run_returns_needs_input_without_factory_for_missing_path(tmp_path: Path) -> None:
    factory_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def factory(*args: Any, **kwargs: Any) -> FakeEngine:
        factory_calls.append((args, kwargs))
        return FakeEngine(SimpleNamespace())

    run = ComputeRunService(factory).run_direct(
        technique="ir",
        path=tmp_path / "missing.csv",
        output_dir=tmp_path / "out",
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_missing",)
    assert run.artifact.sha256 == ""
    assert factory_calls == []


def test_direct_run_returns_needs_input_for_unknown_engine(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    factory_calls: list[tuple[str, Any, Any]] = []

    def factory(technique: str, config: Any = None, submodule_id: str | None = None) -> None:
        factory_calls.append((technique, config, submodule_id))
        return None

    run = ComputeRunService(factory).run_direct(
        technique="unknown",
        path=source,
        output_dir=tmp_path / "out",
        config={"mode": "test"},
        submodule_id="submodule-a",
    )

    assert run.status == "needs_input"
    assert run.reasons == ("technique_unknown",)
    assert run.dataset is None
    assert run.plan is None
    assert factory_calls == [("unknown", {"mode": "test"}, "submodule-a")]


def test_direct_run_returns_opaque_failure_with_constructed_provenance(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")

    run = ComputeRunService().run_direct(
        technique="ir",
        path=source,
        output_dir=tmp_path / "out",
        engine=ExplodingProvider(),
    )

    assert run.status == "failed"
    assert run.reasons == ("provider_execution_failed",)
    assert run.dataset is not None
    assert run.plan is not None
    assert run.result is None
    assert "provider internals" not in run.to_dict()["reasons"]


@pytest.mark.parametrize("source_kind", ("normal", "relative", "home"))
def test_direct_run_uses_one_canonical_source_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source_kind: str
) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    raw_path: str | Path = source
    if source_kind == "relative":
        monkeypatch.chdir(tmp_path)
        raw_path = Path("input.csv")
    elif source_kind == "home":
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        raw_path = Path("~") / "input.csv"

    engine = FakeEngine(SimpleNamespace())
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir", path=raw_path, output_dir=tmp_path / "out"
    )

    assert run.status == "completed"
    assert run.artifact.path == str(source.resolve())
    assert engine.calls[0][0] == run.artifact.path


def test_direct_run_resolves_symlink_source_for_artifact_and_provider(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    link = tmp_path / "linked-input.csv"
    try:
        link.symlink_to(source)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    engine = FakeEngine(SimpleNamespace())
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir", path=link, output_dir=tmp_path / "out"
    )

    assert run.status == "completed"
    assert run.artifact.path == str(source.resolve())
    assert engine.calls[0][0] == run.artifact.path


@pytest.mark.parametrize("output_dir", (Path("relative-output"), Path("")))
def test_direct_run_uses_resolved_plan_output_dir_for_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output_dir: Path
) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    engine = FakeEngine(SimpleNamespace())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir", path=source, output_dir=output_dir
    )

    assert run.status == "completed"
    assert run.plan is not None
    assert run.plan.output_dir == str(output_dir.resolve())
    assert engine.calls[0][1] == run.plan.output_dir


def test_direct_run_returns_needs_input_when_artifact_hashing_becomes_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    engine = FakeEngine(SimpleNamespace())

    def unreadable_from_path(*args: Any, **kwargs: Any) -> Any:
        raise OSError("input disappeared after existence check")

    monkeypatch.setattr(
        "polynexus.core.compute.service.RawArtifact.from_path", unreadable_from_path
    )
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir", path=source, output_dir=tmp_path / "out"
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_unreadable",)
    assert engine.calls == []


def test_direct_run_returns_json_safe_needs_input_for_malformed_source_path(
    tmp_path: Path,
) -> None:
    run = ComputeRunService().run_direct(
        technique="ir",
        path="\x00",
        output_dir=tmp_path / "out",
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_unreadable",)
    assert run.artifact.path == "\x00"
    assert run.artifact.format == ""
    assert run.artifact.sha256 == ""
    assert json.loads(json.dumps(run.to_dict(), sort_keys=True)) == run.to_dict()


def test_direct_run_rejects_non_regular_source_without_invoking_provider(tmp_path: Path) -> None:
    directory = tmp_path / "raw-directory"
    directory.mkdir()
    engine = FakeEngine(SimpleNamespace())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir", path=directory, output_dir=tmp_path / "out"
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_unreadable",)
    assert engine.calls == []


def test_direct_run_rejects_unsupported_option_before_provider_execution(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    engine = FakeEngine(SimpleNamespace())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir",
        path=source,
        output_dir=tmp_path / "out",
        pipeline_options={"bad_option": True},
    )

    assert run.status == "needs_input"
    assert run.reasons == ("pipeline_option_unsupported",)
    assert engine.calls == []


def test_compute_sources_do_not_import_removed_runtime_boundaries() -> None:
    import polynexus.core.compute.models as models
    import polynexus.core.compute.service as service

    forbidden = (
        "analysis_evidence",
        "project_workflow",
        "agent_workflow",
        "rag",
        "joint",
    )

    for module in (models, service):
        tree = ast.parse(inspect.getsource(module))
        imported_names = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        ]
        assert not any(
            any(component in imported_name.lower() for component in forbidden)
            for imported_name in imported_names
        )
