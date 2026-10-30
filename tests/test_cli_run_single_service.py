import json
from types import SimpleNamespace

from polynexus.core.compute import ComputeRunService
from polynexus.core.input_formats import inspect_format
from polynexus.cli.run_single_service import run_single
from polynexus.cli.run_format_inspection import run_format_inspection


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


def test_run_single_json_exposes_canonical_template_and_capabilities(tmp_path, capsys):
    class FakeResult:
        parameters = {"peak": 1}
        figures = {}
        metadata = {}

    class FakeEngine:
        def run_pipeline(self, input_path, output_path, **kwargs):
            return FakeResult()

    input_file = tmp_path / "sample.csv"
    input_file.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")
    args = SimpleNamespace(
        cmd="ir", input=str(input_file), output=str(tmp_path / "out"), skip_to=None, json=True
    )
    _FakeComputeRunService.instances.clear()

    assert run_single(
        args,
        get_engine_fn=lambda technique: FakeEngine(),
        compute_run_service_factory=_FakeComputeRunService,
    ) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["canonical_template"]["template_id"] == "spectrum_1d.v1"
    assert [item["capability_id"] for item in payload["capability_items"]] == [
        "curve.extrema.v1", "curve.summary.v1"
    ]


def test_run_single_passes_explicit_rheology_analysis_spec_to_shared_compute_run(
    tmp_path, capsys
):
    class FakeResult:
        parameters = {"rheology_groups": {}}
        figures = {}
        metadata = {}

    class FakeEngine:
        def run_pipeline(self, _input_path, _output_path, **_kwargs):
            return FakeResult()

    input_file = tmp_path / "steady.csv"
    input_file.write_text(
        "Shear Rate (1/s),Shear Stress (Pa)\n1,7\n2,9\n4,13\n",
        encoding="utf-8",
    )
    spec = {
        "yield_stress": {
            "model": "bingham",
            "stress_measurement_id": "sheet-0-table-0",
        }
    }
    spec_file = tmp_path / "analysis.json"
    spec_file.write_text(json.dumps(spec), encoding="utf-8")
    args = type(
        "Args",
        (),
        {
            "cmd": "rheology",
            "input": str(input_file),
            "output": str(tmp_path / "out"),
            "skip_to": None,
            "analysis_spec": str(spec_file),
            "json": True,
        },
    )()
    _FakeComputeRunService.instances.clear()

    assert run_single(
        args,
        get_engine_fn=lambda technique: FakeEngine() if technique == "rheology" else None,
        compute_run_service_factory=_FakeComputeRunService,
    ) == 0

    captured = _FakeComputeRunService.instances[0].run_direct_kwargs
    assert captured["pipeline_options"]["rheology_analysis"] == spec
    assert json.loads(capsys.readouterr().out)["status"] == "completed"


def test_run_single_passes_explicit_sec_analysis_spec_to_shared_compute_run(
    tmp_path, capsys
):
    class FakeResult:
        parameters = {"sec_groups": {}}
        figures = {}
        metadata = {}

    class FakeEngine:
        def run_pipeline(self, _input_path, _output_path, **_kwargs):
            return FakeResult()

    input_file = tmp_path / "chromatogram.csv"
    input_file.write_text("Elution Volume (mL),RI (mV)\n1,1\n2,2\n3,1\n", encoding="utf-8")
    spec = {
        "response_measurement_id": "sheet-0-table-0",
        "calibration_coordinates": [1.0, 2.0, 3.0],
        "calibration_molar_masses": [1000.0, 100.0, 10.0],
        "calibration_id": "polystyrene-kit-v1",
        "standard_source": "lab-record://sec-standards/2026-09",
        "standard_ids": ["PS-1000", "PS-100", "PS-10"],
        "distribution_mode": "mass",
    }
    spec_file = tmp_path / "calibration.json"
    spec_file.write_text(json.dumps(spec), encoding="utf-8")
    args = SimpleNamespace(
        cmd="sec",
        input=str(input_file),
        output=str(tmp_path / "out"),
        skip_to=None,
        analysis_spec=str(spec_file),
        json=True,
    )
    _FakeComputeRunService.instances.clear()

    assert run_single(
        args,
        get_engine_fn=lambda technique: FakeEngine() if technique == "sec" else None,
        compute_run_service_factory=_FakeComputeRunService,
    ) == 0

    captured = _FakeComputeRunService.instances[0].run_direct_kwargs
    assert captured["pipeline_options"]["sec_analysis"] == spec
    assert json.loads(capsys.readouterr().out)["status"] == "completed"


def test_format_inspection_cli_emits_shared_contract(tmp_path, capsys):
    source = tmp_path / "sample.ngb-ds1"
    source.write_bytes(b"\x00\x00Netzsch TA file\x00_db_format_1\x00")
    args = SimpleNamespace(input=str(source), technique="tga", json=True)

    assert run_format_inspection(args) == 2

    payload = json.loads(capsys.readouterr().out)
    assert payload["plugin_id"] == "netzsch.ta.v1"
    assert payload["status"] == "needs_reader"
    assert payload["reason_codes"] == ["format_signature_unrecognized"]
    assert payload["inspection_id"] == inspect_format(source, technique="tga").inspection_id
