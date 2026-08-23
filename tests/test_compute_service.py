"""Regression coverage for the direct legacy-engine compute façade."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
        pipeline_options={"skip_to": None, "plot_mode": "preview"},
    )

    assert run.status == "completed"
    assert run.artifact.path == str(source.resolve())
    assert run.dataset is not None
    assert run.dataset.template_id == "raw-file-envelope.v1"
    assert run.plan is not None
    assert run.plan.output_dir == str((tmp_path / "out").resolve())
    assert dict(run.plan.pipeline_options) == {"skip_to": None, "plot_mode": "preview"}
    assert dict(run.plan.parameter_sources) == {"skip_to": "user", "plot_mode": "user"}
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
            str(source),
            str(tmp_path / "out"),
            {"skip_to": None, "plot_mode": "preview"},
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
