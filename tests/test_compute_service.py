"""Regression coverage for the direct legacy-engine compute façade."""

from __future__ import annotations

import ast
import errno
import inspect
import json
import os
from collections.abc import Iterator, Mapping
from pathlib import Path
import subprocess
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


class NoneResultProvider:
    def __init__(self) -> None:
        self.calls = 0

    def run_pipeline(self, path: str, output_dir: str, **options: Any) -> None:
        self.calls += 1
        return None


class MissingResultAttributesProvider:
    def __init__(self) -> None:
        self.calls = 0

    def run_pipeline(self, path: str, output_dir: str, **options: Any) -> object:
        self.calls += 1
        return object()


class EmptyLegacyResult:
    parameters: dict[str, Any] = {}
    figures: dict[str, str] = {}
    metadata: dict[str, Any] = {}


class BadPath(os.PathLike[str]):
    def __fspath__(self) -> str:
        raise RuntimeError("path protocol must not escape")


class BadMapping(Mapping[str, Any]):
    def __getitem__(self, key: str) -> Any:
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        raise RuntimeError("mapping materialization must not escape")

    def __len__(self) -> int:
        return 0


class StringableTechnique:
    def __str__(self) -> str:
        raise RuntimeError("technique coercion must not escape")


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


def test_direct_run_forwards_json_safe_mask_edit_candidate_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("data", encoding="utf-8")
    engine = FakeEngine(EmptyLegacyResult())
    candidate = {"regions": [{"q_min": 0.1, "q_max": 0.2}], "enabled": True}

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="saxs",
        path=source,
        output_dir=tmp_path / "out",
        pipeline_options={"skip_to": "plot", "mask_edit_candidate": candidate},
    )

    assert run.status == "completed"
    assert run.plan is not None
    assert run.to_dict()["plan"]["pipeline_options"]["mask_edit_candidate"] == candidate
    assert engine.calls[0][2]["mask_edit_candidate"] is candidate


def test_direct_run_rejects_non_json_safe_mask_edit_candidate(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("data", encoding="utf-8")
    engine = FakeEngine(EmptyLegacyResult())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="saxs",
        path=source,
        output_dir=tmp_path / "out",
        pipeline_options={"mask_edit_candidate": object()},
    )

    assert run.status == "needs_input"
    assert run.reasons == ("pipeline_option_invalid",)
    assert engine.calls == []


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


@pytest.mark.parametrize(
    "provider",
    (NoneResultProvider(), MissingResultAttributesProvider()),
    ids=("none-result", "missing-standard-attributes"),
)
def test_direct_run_rejects_malformed_provider_result_with_opaque_failure(
    tmp_path: Path, provider: NoneResultProvider | MissingResultAttributesProvider
) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")

    run = ComputeRunService().run_direct(
        technique="ir",
        path=source,
        output_dir=tmp_path / "out",
        engine=provider,
    )

    assert run.status == "failed"
    assert run.reasons == ("provider_execution_failed",)
    assert run.dataset is not None
    assert run.plan is not None
    assert run.result is None
    assert provider.calls == 1
    payload = run.to_dict()
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload
    assert "Traceback" not in json.dumps(payload)


def test_direct_run_accepts_legacy_result_with_empty_required_mappings(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    engine = FakeEngine(EmptyLegacyResult())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir", path=source, output_dir=tmp_path / "out"
    )

    assert run.status == "completed"
    assert run.result is not None
    assert run.result.metrics == {}
    assert run.result.figures == {}
    assert run.result.metadata == {}


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

    engine = FakeEngine(EmptyLegacyResult())
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

    engine = FakeEngine(EmptyLegacyResult())
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
    engine = FakeEngine(EmptyLegacyResult())

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


@pytest.mark.parametrize(
    ("path", "expected_path"),
    (
        pytest.param(None, "<invalid-path:NoneType>", id="none"),
        pytest.param(object(), "<invalid-path:object>", id="object"),
        pytest.param(BadPath(), "<invalid-path:BadPath>", id="exploding-pathlike"),
    ),
)
def test_direct_run_contains_malformed_path_types_before_engine_factory(
    tmp_path: Path, path: object, expected_path: str
) -> None:
    factory_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def factory(*args: Any, **kwargs: Any) -> FakeEngine:
        factory_calls.append((args, kwargs))
        return FakeEngine(SimpleNamespace())

    run = ComputeRunService(factory).run_direct(
        technique="ir",
        path=path,  # type: ignore[arg-type]
        output_dir=tmp_path / "out",
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_unreadable",)
    assert run.artifact.path == expected_path
    assert run.artifact.format == ""
    assert run.artifact.sha256 == ""
    payload = run.to_dict()
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload
    assert factory_calls == []


def test_direct_run_completes_for_a_directory_with_a_manifest_backed_envelope(
    tmp_path: Path,
) -> None:
    source = tmp_path / "raw-directory"
    nested = source / "temperature-80C"
    sibling = source / "temperature-90C"
    nested.mkdir(parents=True)
    sibling.mkdir()
    nested_frame = nested / "frame-001.csv"
    nested_frame.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    (sibling / "frame-002.csv").write_text("q,I\n0.2,2.0\n", encoding="utf-8")
    engine = FakeEngine(EmptyLegacyResult())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="saxs", path=source, output_dir=tmp_path / "out"
    )

    assert run.status == "completed"
    assert run.artifact.path == str(source.resolve())
    assert run.artifact.format == "directory"
    assert run.dataset is not None
    assert run.dataset.template_id == "raw-directory-envelope.v1"
    assert run.dataset.payload["kind"] == "raw_directory"
    assert run.plan is not None
    assert engine.calls == [(run.artifact.path, run.plan.output_dir, {})]
    payload = run.to_dict()
    public_json = json.dumps(payload)
    assert "q,I" not in public_json
    assert "0.1,1.0" not in public_json
    assert "temperature-80C" not in public_json
    assert "frame-001.csv" not in public_json


def test_direct_run_rejects_empty_directory_without_invoking_provider(tmp_path: Path) -> None:
    directory = tmp_path / "raw-directory"
    directory.mkdir()
    engine = FakeEngine(SimpleNamespace())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir", path=directory, output_dir=tmp_path / "out"
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_unreadable",)
    assert engine.calls == []


def test_direct_run_rejects_nested_symlink_in_directory_without_provider(tmp_path: Path) -> None:
    directory = tmp_path / "raw-directory"
    nested = directory / "temperature-80C"
    nested.mkdir(parents=True)
    target = tmp_path / "frame.csv"
    target.write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    try:
        (nested / "linked-frame.csv").symlink_to(target)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    engine = FakeEngine(SimpleNamespace())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir", path=directory, output_dir=tmp_path / "out"
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_unreadable",)
    assert engine.calls == []


def test_direct_run_rejects_root_directory_symlink_before_factory(tmp_path: Path) -> None:
    target = tmp_path / "raw-directory"
    target.mkdir()
    (target / "frame.csv").write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    linked_root = tmp_path / "linked-raw-directory"
    try:
        linked_root.symlink_to(target, target_is_directory=True)
    except OSError as error:
        if error.errno in {errno.EACCES, errno.EPERM} or error.winerror in {5, 1314}:
            pytest.skip(f"directory symlink creation unavailable: {error}")
        raise
    factory_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def factory(*args: Any, **kwargs: Any) -> FakeEngine:
        factory_calls.append((args, kwargs))
        return FakeEngine(EmptyLegacyResult())

    run = ComputeRunService(factory).run_direct(
        technique="ir", path=linked_root, output_dir=tmp_path / "out"
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_unreadable",)
    assert run.artifact.path == str(linked_root)
    assert factory_calls == []


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior")
def test_direct_run_rejects_root_directory_junction_before_factory(tmp_path: Path) -> None:
    target = tmp_path / "raw-directory"
    target.mkdir()
    (target / "frame.csv").write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    linked_root = tmp_path / "linked-raw-directory"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(linked_root), str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        diagnostic = f"{result.stdout}\n{result.stderr}".casefold()
        if "access is denied" in diagnostic or "privilege" in diagnostic:
            pytest.skip(f"junction creation unavailable: {diagnostic.strip()}")
        pytest.fail(f"junction setup failed: {diagnostic.strip()}")
    factory_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def factory(*args: Any, **kwargs: Any) -> FakeEngine:
        factory_calls.append((args, kwargs))
        return FakeEngine(EmptyLegacyResult())

    run = ComputeRunService(factory).run_direct(
        technique="ir", path=linked_root, output_dir=tmp_path / "out"
    )

    assert run.status == "needs_input"
    assert run.reasons == ("raw_artifact_unreadable",)
    assert run.artifact.path == str(linked_root)
    assert factory_calls == []


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


@pytest.mark.parametrize("output_dir", ("\x00", None))
def test_direct_run_rejects_invalid_output_dir_before_plan_or_provider(
    tmp_path: Path, output_dir: object
) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    engine = FakeEngine(SimpleNamespace())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir",
        path=source,
        output_dir=output_dir,  # type: ignore[arg-type]
    )

    assert run.status == "needs_input"
    assert run.reasons == ("output_directory_invalid",)
    assert run.artifact.sha256
    assert run.dataset is None
    assert run.plan is None
    assert run.result is None
    assert json.loads(json.dumps(run.to_dict(), sort_keys=True)) == run.to_dict()
    assert engine.calls == []


def test_direct_run_contains_exploding_pathlike_output_before_engine_factory(
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    factory_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def factory(*args: Any, **kwargs: Any) -> FakeEngine:
        factory_calls.append((args, kwargs))
        return FakeEngine(SimpleNamespace())

    run = ComputeRunService(factory).run_direct(
        technique="ir", path=source, output_dir=BadPath()
    )

    assert run.status == "needs_input"
    assert run.reasons == ("output_directory_invalid",)
    assert run.dataset is None
    assert run.plan is None
    assert json.loads(json.dumps(run.to_dict(), sort_keys=True)) == run.to_dict()
    assert factory_calls == []


def test_direct_run_contains_exploding_pipeline_mapping_before_engine_factory(
    tmp_path: Path,
) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    factory_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def factory(*args: Any, **kwargs: Any) -> FakeEngine:
        factory_calls.append((args, kwargs))
        return FakeEngine(SimpleNamespace())

    run = ComputeRunService(factory).run_direct(
        technique="ir",
        path=source,
        output_dir=tmp_path / "out",
        pipeline_options=BadMapping(),
    )

    assert run.status == "needs_input"
    assert run.reasons == ("pipeline_option_invalid",)
    assert run.dataset is None
    assert run.plan is None
    assert json.loads(json.dumps(run.to_dict(), sort_keys=True)) == run.to_dict()
    assert factory_calls == []


@pytest.mark.parametrize("technique", ("", None, object(), StringableTechnique()))
def test_direct_run_contains_invalid_technique_before_engine_factory(
    tmp_path: Path, technique: object
) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    factory_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def factory(*args: Any, **kwargs: Any) -> FakeEngine:
        factory_calls.append((args, kwargs))
        return FakeEngine(SimpleNamespace())

    run = ComputeRunService(factory).run_direct(
        technique=technique,  # type: ignore[arg-type]
        path=source,
        output_dir=tmp_path / "out",
    )

    assert run.status == "needs_input"
    assert run.reasons == ("technique_invalid",)
    assert run.artifact.technique == "unknown"
    assert run.dataset is None
    assert run.plan is None
    assert json.loads(json.dumps(run.to_dict(), sort_keys=True)) == run.to_dict()
    assert factory_calls == []


def test_direct_run_normalizes_technique_once_for_all_compute_boundaries(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    engine = FakeEngine(EmptyLegacyResult())
    factory_techniques: list[str] = []

    def factory(technique: str, **kwargs: Any) -> FakeEngine:
        factory_techniques.append(technique)
        return engine

    run = ComputeRunService(factory).run_direct(
        technique="  IR  ", path=source, output_dir=tmp_path / "out"
    )

    assert run.status == "completed"
    assert run.dataset is not None
    assert run.plan is not None
    assert run.artifact.technique == run.dataset.technique == run.plan.technique == "ir"
    assert factory_techniques == ["ir"]


@pytest.mark.parametrize(
    "skip_to",
    (pytest.param("unknown", id="unknown-string"), pytest.param(object(), id="object")),
)
def test_direct_run_rejects_invalid_skip_to_before_plan_or_provider(
    tmp_path: Path, skip_to: object
) -> None:
    source = tmp_path / "input.csv"
    source.write_text("data", encoding="utf-8")
    engine = FakeEngine(SimpleNamespace())

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="ir",
        path=source,
        output_dir=tmp_path / "out",
        pipeline_options={"skip_to": skip_to},
    )

    assert run.status == "needs_input"
    assert run.reasons == ("pipeline_option_invalid",)
    assert run.dataset is None
    assert run.plan is None
    assert run.result is None
    assert json.loads(json.dumps(run.to_dict(), sort_keys=True)) == run.to_dict()
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
