from __future__ import annotations

from dataclasses import replace
import importlib
import importlib.util
from unittest.mock import patch
import pytest

from polynexus.core.compute import ComputeRunService, RawArtifact
from polynexus.gui.main_window_run_mixin import MainWindowRunMixin

from polynexus.gui.main_window import (
    AITuneSignals,
    AITuneWorker,
    AnalysisWorker,
    BatchWorker,
    JointHubWorker,
)


def test_main_window_reuses_worker_classes_from_dedicated_workers_module() -> None:
    spec = importlib.util.find_spec("polynexus.gui.main_window_workers")
    assert spec is not None

    module = importlib.import_module("polynexus.gui.main_window_workers")

    assert AnalysisWorker is module.AnalysisWorker
    assert BatchWorker is module.BatchWorker
    assert JointHubWorker is module.JointHubWorker
    assert AITuneSignals is module.AITuneSignals
    assert AITuneWorker is module.AITuneWorker


def test_analysis_and_batch_workers_expose_cooperative_lifecycle_signals() -> None:
    analysis = AnalysisWorker("saxs", "sample.edf", "out")
    batch = BatchWorker("saxs", ["sample.edf"], "out")

    assert hasattr(analysis, "stage")
    assert hasattr(analysis, "cancelled")
    assert hasattr(batch, "stage")
    assert hasattr(batch, "cancelled")
    analysis.cancel()
    batch.cancel()
    assert analysis._cancel_requested is True
    assert batch._cancel_requested is True


def test_analysis_worker_emits_compute_run_from_shared_service(tmp_path) -> None:
    class FakeResult:
        parameters = {"peak": 1.2}
        figures = {}
        metadata = {}

    class FakeEngine:
        def __init__(self):
            self.calls = []

        def run_pipeline(self, input_path, output_path, **kwargs):
            self.calls.append((input_path, output_path, kwargs))
            return FakeResult()

    class FakeComputeRunService:
        instances = []

        def __init__(self, engine_factory):
            self.engine_factory = engine_factory
            self.run_direct_kwargs = None
            self.__class__.instances.append(self)

        def run_direct(self, **kwargs):
            self.run_direct_kwargs = kwargs
            return ComputeRunService(self.engine_factory).run_direct(**kwargs)

    input_file = tmp_path / "sample.txt"
    input_file.write_text("data", encoding="utf-8")
    engine = FakeEngine()
    config = object()
    mask_edit_candidate = {"mask": "candidate"}
    worker = AnalysisWorker(
        "ir",
        str(input_file),
        str(tmp_path / "out"),
        config=config,
        submodule_id="baseline",
        engine=engine,
        mask_edit_candidate=mask_edit_candidate,
        compute_service_factory=FakeComputeRunService,
    )
    received = []
    errors = []
    worker.finished.connect(received.append)
    worker.error_msg.connect(errors.append)

    worker.run()

    assert errors == []
    assert received[0].status == "completed"
    assert worker.compute_run is received[0]
    assert worker.engine is engine
    assert FakeComputeRunService.instances[0].run_direct_kwargs == {
        "technique": "ir",
        "path": str(input_file),
        "output_dir": str(tmp_path / "out"),
        "config": config,
        "submodule_id": "baseline",
        "engine": engine,
        "pipeline_options": {
            "skip_to": None,
            "mask_edit_candidate": mask_edit_candidate,
        },
    }


def test_analysis_worker_exposes_canonical_template_and_capabilities(tmp_path) -> None:
    class FakeResult:
        parameters = {}
        figures = {}
        metadata = {}

    class FakeEngine:
        def run_pipeline(self, input_path, output_path, **kwargs):
            return FakeResult()

    class FakeComputeRunService:
        def __init__(self, engine_factory):
            self.engine_factory = engine_factory

        def run_direct(self, **kwargs):
            return ComputeRunService(self.engine_factory).run_direct(**kwargs)

    input_file = tmp_path / "sample.csv"
    input_file.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
    worker = AnalysisWorker(
        "ir", str(input_file), str(tmp_path / "out"), engine=FakeEngine(),
        compute_service_factory=FakeComputeRunService,
    )
    received = []
    errors = []
    worker.finished.connect(received.append)
    worker.error_msg.connect(errors.append)

    worker.run()

    assert errors == []
    assert received[0].canonical_template.template_id == "spectrum_1d.v1"
    assert len(received[0].capability_items) == 2


def test_analysis_worker_routes_portable_export_through_shared_compute(tmp_path) -> None:
    class FakeResult:
        parameters = {"mass_loss": 2.0}
        figures = {}
        metadata = {}

    class FakeEngine:
        def run_pipeline(self, input_path, output_path, **kwargs):
            assert input_path.endswith("sample.csv")
            return FakeResult()

    class FakeComputeRunService:
        instances = []

        def __init__(self, engine_factory):
            self.engine_factory = engine_factory
            self.run_direct_kwargs = None
            self.__class__.instances.append(self)

        def run_direct(self, **kwargs):
            self.run_direct_kwargs = kwargs
            return ComputeRunService(self.engine_factory).run_direct(**kwargs)

    raw = tmp_path / "sample.ngb-ds1"
    raw.write_bytes(b"opaque vendor bytes")
    exported = tmp_path / "sample.csv"
    exported.write_text("Temperature (C),Mass (%)\n25,100\n100,98\n", encoding="utf-8")
    worker = AnalysisWorker(
        "tga",
        str(raw),
        str(tmp_path / "out"),
        engine=FakeEngine(),
        portable_export={
            "raw_source": str(raw),
            "export_path": str(exported),
            "exporter": "Proteus portable CSV",
        },
        compute_service_factory=FakeComputeRunService,
    )
    received = []
    errors = []
    worker.finished.connect(received.append)
    worker.error_msg.connect(errors.append)

    worker.run()

    assert errors == []
    assert received[0].status == "completed"
    kwargs = FakeComputeRunService.instances[0].run_direct_kwargs
    assert kwargs["path"] == str(exported)
    assert kwargs["source_artifact_id"] == received[0].artifact.artifact_id
    assert kwargs["canonical_template"].payload["portable_export_binding"]["raw_source_sha256"]


def test_batch_worker_runs_each_file_through_shared_compute_run_service(tmp_path) -> None:
    class FakeResult:
        parameters = {"peak": 1.2}
        figures = {}
        metadata = {}

    class FakeEngine:
        def __init__(self):
            self.calls = []

        def run_pipeline(self, input_path, output_path, **kwargs):
            self.calls.append((input_path, output_path, kwargs))
            return FakeResult()

    class FakeComputeRunService:
        def __init__(self, engine_factory):
            self.engine_factory = engine_factory

        def run_direct(self, **kwargs):
            return ComputeRunService(self.engine_factory).run_direct(**kwargs)

    input_file = tmp_path / "sample.csv"
    input_file.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
    engine = FakeEngine()
    worker = BatchWorker(
        "ir",
        [str(input_file)],
        str(tmp_path / "out"),
        compute_service_factory=FakeComputeRunService,
    )
    completed = []
    file_done = []
    worker.batch_finished.connect(completed.append)
    worker.file_done.connect(lambda filename, params: file_done.append((filename, params)))

    with patch("polynexus.gui.main_window.get_engine", return_value=engine):
        worker.run()

    assert len(completed) == 1
    row = completed[0][0]
    assert row["file"] == input_file.name
    assert row["path"] == str(input_file)
    assert row["output_dir"] == str((tmp_path / "out" / "sample").resolve())
    assert row["params"] == {"peak": 1.2}
    assert row["compute_run"].status == "completed"
    assert row["compute_run"].canonical_template.template_id == "spectrum_1d.v1"
    assert len(row["compute_run"].capability_items) == 2
    assert file_done == [(input_file.name, {"peak": 1.2})]
    assert engine.calls == [
        (str(input_file), str((tmp_path / "out" / "sample").resolve()), {})
    ]


def test_analysis_worker_accepts_a_directory_through_the_shared_service(tmp_path) -> None:
    class FakeResult:
        parameters = {}
        figures = {}
        metadata = {}

    class FakeEngine:
        def __init__(self):
            self.calls = []

        def run_pipeline(self, input_path, output_path, **kwargs):
            self.calls.append((input_path, output_path, kwargs))
            return FakeResult()

    class FakeComputeRunService:
        def __init__(self, engine_factory):
            self.engine_factory = engine_factory

        def run_direct(self, **kwargs):
            return ComputeRunService(self.engine_factory).run_direct(**kwargs)

    directory = tmp_path / "sequence"
    nested = directory / "temperature-80C"
    sibling = directory / "temperature-90C"
    nested.mkdir(parents=True)
    sibling.mkdir()
    (nested / "frame-001.csv").write_text("q,I\n0.1,1.0\n", encoding="utf-8")
    (sibling / "frame-002.csv").write_text("q,I\n0.2,2.0\n", encoding="utf-8")
    engine = FakeEngine()
    worker = AnalysisWorker(
        "saxs",
        str(directory),
        str(tmp_path / "out"),
        engine=engine,
        compute_service_factory=FakeComputeRunService,
    )
    received = []
    errors = []
    worker.finished.connect(received.append)
    worker.error_msg.connect(errors.append)

    worker.run()

    assert errors == []
    assert received[0].status == "completed"
    assert received[0].artifact.path == str(directory.resolve())
    assert engine.calls == [
        (str(directory.resolve()), str((tmp_path / "out").resolve()), {"skip_to": None})
    ]
    assert worker.compute_run is received[0]


def test_batch_worker_maps_portable_exports_by_raw_stem(tmp_path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    raw_files = []
    for name in ("run-a", "run-b"):
        raw = tmp_path / f"{name}.ngb-ds1"
        raw.write_bytes(name.encode("utf-8"))
        (export_dir / f"{name}.csv").write_text("x,y\n1,2\n", encoding="utf-8")
        raw_files.append(str(raw))

    worker = BatchWorker(
        "tga",
        raw_files,
        str(tmp_path / "out"),
        portable_export={
            "raw_source": str(tmp_path),
            "export_directory": str(export_dir),
            "exporter": "Proteus portable CSV",
        },
    )

    pairs = worker._portable_export_pairs()
    assert pairs is not None
    assert pairs[raw_files[0]].endswith("run-a.csv")
    assert pairs[raw_files[1]].endswith("run-b.csv")

    (export_dir / "run-b.csv").unlink()
    with pytest.raises(ValueError, match="ambiguous"):
        worker._portable_export_pairs()


def test_batch_worker_executes_each_portable_pair_as_its_own_compute_run(tmp_path) -> None:
    class FakeEngine:
        def run_pipeline(self, input_path, output_path, **kwargs):
            raise AssertionError("portable batch should execute the canonical export path")

    class FakeResult:
        metrics = {"ok": 1}

    class FakeRun:
        status = "completed"
        result = FakeResult()

    class FakeComputeRunService:
        calls = []

        def __init__(self, _engine_factory):
            pass

        def run_direct(self, **kwargs):
            self.__class__.calls.append(kwargs)
            return FakeRun()

    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    raw_files = []
    exports = {}
    for name in ("run-a", "run-b"):
        raw = tmp_path / f"{name}.ngb-ds1"
        raw.write_bytes(name.encode("utf-8"))
        exported = export_dir / f"{name}.csv"
        exported.write_text(
            "Temperature (C),Mass (%)\n25,100\n100,98\n",
            encoding="utf-8",
        )
        raw_files.append(str(raw))
        exports[name] = exported

    worker = BatchWorker(
        "tga",
        raw_files,
        str(tmp_path / "out"),
        portable_export={
            "raw_source": str(tmp_path),
            "export_directory": str(export_dir),
            "exporter": "Proteus portable CSV",
        },
        compute_service_factory=FakeComputeRunService,
    )
    completed = []
    errors = []
    worker.batch_finished.connect(completed.append)
    worker.error_msg.connect(errors.append)

    with patch("polynexus.gui.main_window.get_engine", return_value=FakeEngine()):
        worker.run()

    assert errors == []
    assert len(completed) == 1
    assert [call["path"] for call in FakeComputeRunService.calls] == [
        str(exports["run-a"].resolve()),
        str(exports["run-b"].resolve()),
    ]
    assert [call["source_artifact_id"] for call in FakeComputeRunService.calls] == [
        RawArtifact.from_path(path, technique="tga").artifact_id for path in raw_files
    ]
    assert all(call["canonical_template"].payload["portable_export_binding"] for call in FakeComputeRunService.calls)


def test_run_mixin_unwraps_completed_compute_run_and_rejects_missing_legacy_result(
    tmp_path,
) -> None:
    class LegacyResult:
        parameters = {}
        figures = {}
        metadata = {}

    class FakeEngine:
        def run_pipeline(self, input_path, output_path, **kwargs):
            return legacy_result

    class Harness:
        _current_technique = " IR "

        def __init__(self):
            self.errors = []

        def _on_error(self, message):
            self.errors.append(message)

    source = tmp_path / "sample.txt"
    source.write_text("data", encoding="utf-8")
    legacy_result = LegacyResult()
    compute_run = ComputeRunService(lambda *args, **kwargs: FakeEngine()).run_direct(
        technique="ir",
        path=source,
        output_dir=tmp_path / "out",
    )
    harness = Harness()

    assert MainWindowRunMixin._legacy_result_from_compute_run(harness, compute_run) is legacy_result
    assert harness._compute_runs == {"ir": compute_run}
    assert harness.errors == []
    assert (
        MainWindowRunMixin._legacy_result_from_compute_run(
            harness, replace(compute_run, legacy_result=None)
        )
        is None
    )
    assert harness.errors == ["compute_run_legacy_result_missing"]
