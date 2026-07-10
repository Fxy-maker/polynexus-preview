from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.eval.runner import EvalRunner


@dataclass
class _FakeWAXSConfig:
    peak_function: str = "pseudo_voigt"
    peak_distance: float = 0.22
    max_peaks: int = 5
    q_bragg_min: float = 15.0
    q_bragg_max: float = 25.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "peak_function": self.peak_function,
            "peak_distance": self.peak_distance,
            "max_peaks": self.max_peaks,
            "q_bragg_min": self.q_bragg_min,
            "q_bragg_max": self.q_bragg_max,
        }


class _FakeWAXSAnalysis:
    peaks = [
        {"two_theta": 17.8, "fwhm_deg": 0.42, "area": 180.0, "hkl": "110"},
        {"two_theta": 20.1, "fwhm_deg": 0.51, "area": 165.0, "hkl": "200"},
    ]
    two_theta = [2.0, 20.1, 80.0]
    r_squared = 0.88


class _FakeWAXSResult:
    def __init__(self, params: dict[str, Any]) -> None:
        self.parameters = dict(params)


class _FakeWAXSEngine:
    def __init__(self) -> None:
        self._waxs_config = _FakeWAXSConfig()
        self._results = [_FakeWAXSAnalysis()]
        self.run_calls: list[tuple[str, str]] = []

    def run_pipeline(self, filepath: str, output_dir: str = "") -> _FakeWAXSResult:
        self.run_calls.append((filepath, output_dir))
        return _FakeWAXSResult(
            {
                "n_peaks": 2,
                "Xc_pct": 67.4,
                "D_Scherrer_nm": 8.9,
                "quality_score": 0.91,
                "r_squared": 0.88,
            }
        )


def test_eval_runner_executes_real_waxs_static_case(monkeypatch, tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    case_path = project_root / "tests" / "eval" / "cases" / "real" / "waxs_real_static_pa6.json"
    runner = EvalRunner(project_root=project_root)
    case = runner.load_case(case_path)
    source_file = tmp_path / "PA6.raw"
    source_file.touch()
    case.config_overrides["source_file"] = str(source_file)

    assert case.technique == "waxs"
    assert runner._uses_real_engine(case) is True

    fake_engine = _FakeWAXSEngine()
    captured: dict[str, Any] = {}

    def _fake_get_engine(name: str, config=None, log_fn=None, submodule_id=None):
        captured["name"] = name
        captured["submodule_id"] = submodule_id
        return fake_engine

    monkeypatch.setattr("polynexus.core.get_engine", _fake_get_engine)

    result = runner.run_case(case)

    assert captured["name"] == "waxs"
    assert captured["submodule_id"] == "waxs.static"
    assert fake_engine.run_calls == [(str(source_file.resolve()), "")]
    assert result.parameters_used["engine"] == "waxs"
    assert result.parameters_used["submodule"] == "waxs.static"
    assert result.output_parameters["n_peaks"] == 2
    assert result.output_parameters["Xc_pct"] == 67.4
    assert result.output_parameters["D_Scherrer_nm"] == 8.9
    assert result.output_parameters["peak_centers"] == [17.8, 20.1]
    assert result.output_parameters["x_min"] == 2.0
    assert result.output_parameters["x_max"] == 80.0
    assert result.output_parameters["r_squared"] == 0.88
    assert result.phys_score == 1.0
    assert result.peak_score == 1.0
    assert result.details["available_metrics"] == ["PHYS"]
