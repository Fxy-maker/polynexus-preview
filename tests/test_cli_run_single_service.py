from types import SimpleNamespace

from polynexus.cli.run_single_service import run_single


def test_run_single_uses_engine_and_formatter(tmp_path, capsys):
    class FakeResult:
        parameters = {"r_squared": 0.99}

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

    args = SimpleNamespace(cmd="waxs", input=str(input_file), output="", skip_to="plot", type="strain")
    rows = []

    result = run_single(
        args,
        get_engine_fn=lambda technique: fake_engine if technique == "waxs" else None,
        format_technique_result_lines_fn=lambda technique, output, parameters: rows.append(
            (technique, output, dict(parameters))
        ) or [f"{technique}:{output}:{parameters['r_squared']}"],
    )

    assert result == 0
    assert fake_engine.cfg.experiment_type == "strain"
    assert fake_engine.calls == [(str(input_file), str(tmp_path / "waxs_results"), "plot")]
    assert rows == [("waxs", str(tmp_path / "waxs_results"), {"r_squared": 0.99})]
    assert "waxs:" in capsys.readouterr().out


def test_run_single_reports_unknown_technique(capsys):
    args = SimpleNamespace(cmd="mystery", input="sample.dat", output="", skip_to=None)

    assert run_single(args, get_engine_fn=lambda technique: None) == 1
    assert "Unknown technique: mystery" in capsys.readouterr().out
