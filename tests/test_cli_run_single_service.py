import json
from types import SimpleNamespace

from polynexus.core.compute import ComputeRunService
from polynexus.cli.run_single_service import run_single


class _FakeComputeRunService:
    instances = []

    def __init__(self, engine_factory):
        self.engine_factory = engine_factory
        self.run_direct_kwargs = None
        self.__class__.instances.append(self)

    def run_direct(self, **kwargs):
        self.run_direct_kwargs = kwargs
        return ComputeRunService(self.engine_factory).run_direct(**kwargs)


def test_run_single_uses_engine_and_formatter(tmp_path, capsys):
    class FakeResult:
        parameters = {"r_squared": 0.99}
        figures = {}
        metadata = {}

    class FakeEngine:
        def __init__(self):
            self.cfg = SimpleNamespace(experiment_type="static")
            self.calls = []

        def run_pipeline(self, input_path, output_path, skip_to=None):
            self.calls.append((input_path, output_path, skip_to))
            return FakeResult()

    fake_engine = FakeEngine()
    input_file = tmp_path / "sample.raw"
    input_file.write_text("data", encoding="utf-8")

    args = SimpleNamespace(
        cmd="waxs",
        input=str(input_file),
        output="",
        skip_to="plot",
        type="strain",
        json=False,
    )
    rows = []
    _FakeComputeRunService.instances.clear()

    result = run_single(
        args,
        get_engine_fn=lambda technique: fake_engine if technique == "waxs" else None,
        format_technique_result_lines_fn=lambda technique, output, parameters: rows.append(
            (technique, output, dict(parameters))
        ) or [f"{technique}:{output}:{parameters['r_squared']}"],
        compute_run_service_factory=_FakeComputeRunService,
    )

    assert result == 0
    assert fake_engine.cfg.experiment_type == "strain"
    assert fake_engine.calls == [(str(input_file), str(tmp_path / "waxs_results"), "plot")]
    assert rows == [("waxs", str(tmp_path / "waxs_results"), {"r_squared": 0.99})]
    assert _FakeComputeRunService.instances[0].run_direct_kwargs["engine"] is fake_engine
    assert "waxs:" in capsys.readouterr().out


def test_run_single_reports_unknown_technique(capsys):
    args = SimpleNamespace(cmd="mystery", input="sample.dat", output="", skip_to=None, json=False)

    assert run_single(args, get_engine_fn=lambda technique: None) == 1
    assert "needs_input:" in capsys.readouterr().err


def test_run_single_json_prints_only_shared_compute_run(tmp_path, capsys):
    class FakeResult:
        parameters = {"r_squared": 0.99}
        figures = {}
        metadata = {}

    class FakeEngine:
        def run_pipeline(self, input_path, output_path, skip_to=None):
            return FakeResult()

    input_file = tmp_path / "sample.txt"
    input_file.write_text("data", encoding="utf-8")
    args = SimpleNamespace(
        cmd="ir",
        input=str(input_file),
        output=str(tmp_path / "out"),
        skip_to=None,
        json=True,
    )
    _FakeComputeRunService.instances.clear()

    code = run_single(
        args,
        get_engine_fn=lambda technique: FakeEngine(),
        format_technique_result_lines_fn=lambda *args: (_ for _ in ()).throw(
            AssertionError("formatter must not run for JSON output")
        ),
        compute_run_service_factory=_FakeComputeRunService,
    )

    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"
    assert _FakeComputeRunService.instances[0].run_direct_kwargs["technique"] == "ir"
