from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.eval.runner import EvalRunner


@dataclass
class _FakeSAXSConfig:
    experiment_type: str = "static"
    condition_label: str = "Condition"
    condition_unit: str = ""
    q_bragg_min: float = 0.15
    q_bragg_max: float = 0.90
    q_corr_min: float = 0.15
    q_corr_max: float = 1.20
    savgol_window: int = 7
    savgol_order: int = 2
    do_avrami: bool = False
    do_melt_detection: bool = True
    use_sasmodels_fit: bool = False


class _FakeLongPeriod:
    L_confidence = 0.72
    L_bragg = 8.8
    L_lorentz = 8.6
    L_corr_peak = 8.4


class _FakeAnalysis:
    q = [0.01, 0.02, 0.03]
    r_squared = 0.83
    quality_score = 0.79
    r_squared_method = "saxs_temperature_fit"
    fit_rmse = 0.11
    fit_regions = [{"region": "peak", "r_squared": 0.81, "rmse": 0.12}]
    q_peak_snr = 4.6
    quality_flag = "OK"
    validation_summary = "All checks passed"
    condition_value = -20.0
    long_period = _FakeLongPeriod()


class _FakeResult:
    def __init__(self, params: dict[str, Any]) -> None:
        self.parameters = dict(params)


class _FakeSAXSEngine:
    def __init__(self) -> None:
        self.cfg = _FakeSAXSConfig()
        self.active_submodule = ""
        self.result = _FakeResult(
            {
                "n_temperatures": 17,
                "T_range_C": "-20-150",
                "Tm_peak_C": 123.4,
                "Avrami_n": 2.3,
                "condition_label": "Temperature",
                "condition_source": "header",
                "condition_confidence": 0.9,
                "batch_frames": 17,
            }
        )
        self._analysis = _FakeAnalysis()
        self._batch_results = [self._analysis]
        self.run_calls: list[tuple[str, str]] = []

    def run_pipeline(self, filepath: str, output_dir: str = "") -> _FakeResult:
        self.run_calls.append((filepath, output_dir))
        return self.result

    def get_parameters(self) -> dict[str, Any]:
        return dict(self.result.parameters)


def test_eval_runner_executes_real_saxs_temperature_case(monkeypatch, tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    case_path = project_root / "tests" / "eval" / "cases" / "real" / "saxs_real_temperature_check_20260618.json"
    runner = EvalRunner(project_root=project_root)
    case = runner.load_case(case_path)
    source_dir = tmp_path / "temperature_series"
    source_dir.mkdir()
    case.config_overrides["source_file"] = str(source_dir)

    assert case.technique == "saxs"
    assert runner._uses_real_engine(case) is True

    fake_engine = _FakeSAXSEngine()
    captured: dict[str, Any] = {}

    def _fake_get_engine(name: str, config=None, log_fn=None, submodule_id=None):
        captured["name"] = name
        captured["submodule_id"] = submodule_id
        fake_engine.active_submodule = submodule_id or ""
        return fake_engine

    monkeypatch.setattr("polynexus.core.get_engine", _fake_get_engine)

    result = runner.run_case(case)

    assert captured["name"] == "saxs"
    assert captured["submodule_id"] == "saxs.temperature"
    assert fake_engine.run_calls == [(str(source_dir.resolve()), "")]
    assert result.parameters_used["engine"] == "saxs"
    assert result.parameters_used["submodule"] == "saxs.temperature"
    assert result.parameters_used["experiment_type"] == "temperature"
    assert result.parameters_used["condition_label"] == "Temperature"
    assert result.parameters_used["condition_unit"] == "C"
    assert result.output_parameters["n_temperatures"] == 17
    assert result.output_parameters["condition_label"] == "Temperature"
    assert result.output_parameters["condition_source"] == "header"
    assert result.output_parameters["condition_confidence"] == 0.9
    assert result.output_parameters["r_squared"] == 0.83
    assert result.output_parameters["quality_score"] == 0.79
    assert result.phys_score == 1.0
    assert result.peak_score == 1.0
    assert result.composite == 1.0
    assert result.details["available_metrics"] == ["PHYS"]


def test_eval_runner_executes_real_saxs_strain_case(monkeypatch, tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    case_path = project_root / "tests" / "eval" / "cases" / "real" / "saxs_real_strain_pad8_series.json"
    runner = EvalRunner(project_root=project_root)
    case = runner.load_case(case_path)
    source_dir = tmp_path / "strain_series"
    source_dir.mkdir()
    case.config_overrides["source_file"] = str(source_dir)

    assert case.technique == "saxs"
    assert case.submodule == "strain"
    assert runner._uses_real_engine(case) is True

    fake_engine = _FakeSAXSEngine()
    fake_engine.result = _FakeResult(
        {
            "n_strains": 5,
            "strain_range_pct": "0-400",
            "condition_label": "Strain",
            "condition_source": "filename",
            "condition_confidence": 0.76,
            "condition_continuity_score": 0.82,
            "batch_frames": 5,
            "r_squared": 0.83,
            "quality_score": 0.81,
            "quality_flag": "OK",
            "validation_summary": "All checks passed",
        }
    )
    captured: dict[str, Any] = {}

    def _fake_get_engine(name: str, config=None, log_fn=None, submodule_id=None):
        captured["name"] = name
        captured["submodule_id"] = submodule_id
        fake_engine.active_submodule = submodule_id or ""
        return fake_engine

    monkeypatch.setattr("polynexus.core.get_engine", _fake_get_engine)

    result = runner.run_case(case)

    assert captured["name"] == "saxs"
    assert captured["submodule_id"] == "saxs.strain"
    assert fake_engine.run_calls == [(str(source_dir.resolve()), "")]
    assert result.parameters_used["engine"] == "saxs"
    assert result.parameters_used["submodule"] == "saxs.strain"
    assert result.parameters_used["experiment_type"] == "strain"
    assert result.parameters_used["condition_label"] == "Strain"
    assert result.parameters_used["condition_unit"] == "%"
    assert result.output_parameters["n_strains"] == 5
    assert result.output_parameters["condition_label"] == "Strain"
    assert result.output_parameters["condition_confidence"] == 0.76
    assert result.output_parameters["r_squared"] == 0.83
    assert result.output_parameters["quality_score"] == 0.79
    assert result.phys_score == 1.0
    assert result.peak_score == 1.0
    assert result.composite == 1.0
    assert result.details["available_metrics"] == ["PHYS"]
