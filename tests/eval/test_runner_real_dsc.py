from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.eval.runner import EvalRunner


class _FakeDSCResult:
    def __init__(self, params: dict[str, Any]) -> None:
        self.parameters = dict(params)


class _FakeDSCScan:
    def __init__(self, label: str, t0: float, t1: float, r2: float, quality: float, tm: float, xc: float) -> None:
        self.label = label
        self.T = [t0, (t0 + t1) / 2.0, t1]
        self.HF = [0.0, 1.0, 0.0]
        self.Tg_C = float("nan")
        self.Tm_peak_C = tm
        self.Tc_peak_C = float("nan")
        self.Tcc_peak_C = 177.0
        self.DHm_Jg = 48.0
        self.DHc_Jg = float("nan")
        self.DHcc_Jg = 6.2
        self.Xc_pct = xc
        self.quality_score = quality
        self.r_squared = r2
        self.fit_rmse = 0.12
        self.fit_regions = [{"kind": "Tm"}]
        self.peak_components = [{"type": "melting", "peak_C": tm}]

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "scan_label": self.label,
            "Tg_C": self.Tg_C,
            "Tm_peak_C": self.Tm_peak_C,
            "Tc_peak_C": self.Tc_peak_C,
            "Tcc_peak_C": self.Tcc_peak_C,
            "DHm_Jg": self.DHm_Jg,
            "DHc_Jg": self.DHc_Jg,
            "DHcc_Jg": self.DHcc_Jg,
            "Xc_pct": self.Xc_pct,
            "quality_score": self.quality_score,
            "r_squared": self.r_squared,
            "fit_rmse": self.fit_rmse,
            "n_peaks": len(self.peak_components),
        }


class _FakeDSCEngine:
    def __init__(self) -> None:
        self._dsc_config = type(
            "Cfg",
            (),
            {
                "baseline_corr": "auto",
                "smooth_window": 11,
                "Tg_method": "half_height",
                "user_DHm0": 230.0,
                "__dataclass_fields__": {"baseline_corr": None, "smooth_window": None, "Tg_method": None, "user_DHm0": None},
                "to_dict": lambda self: {
                    "baseline_corr": "auto",
                    "smooth_window": 11,
                    "Tg_method": "half_height",
                    "user_DHm0": 230.0,
                },
            },
        )()
        self.active_submodule = ""
        self.result = _FakeDSCResult(
            {
                "Tg_C": 50.0,
                "Tm_peak_C": 222.4,
                "Tc_peak_C": 170.0,
                "Tcc_peak_C": 177.0,
                "DHm_Jg": 33.8,
                "DHc_Jg": float("nan"),
                "DHcc_Jg": 6.5,
                "Xc_pct": 11.9,
                "quality_score": 0.85,
                "r_squared": 0.887885,
                "fit_rmse": 0.419453,
                "n_peaks": 3,
            }
        )
        self._results = [_FakeDSCScan("FXY-PA6/heat 50-260C", 50.0, 260.0, 0.887885, 0.85, 222.4, 11.9)]
        self.run_calls: list[tuple[str, str]] = []

    def run_pipeline(self, filepath: str, output_dir: str = "") -> _FakeDSCResult:
        self.run_calls.append((filepath, output_dir))
        return self.result

    def get_parameters(self) -> dict[str, Any]:
        return dict(self.result.parameters)


def test_eval_runner_executes_real_dsc_standard_case(monkeypatch, tmp_path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    case_path = project_root / "tests" / "eval" / "cases" / "real" / "dsc_real_standard_pa6.json"
    runner = EvalRunner(project_root=project_root)
    case = runner.load_case(case_path)
    source_file = tmp_path / "FXY-PA6.txt"
    source_file.touch()
    case.config_overrides["source_file"] = str(source_file)

    assert case.technique == "dsc"
    assert case.submodule == "standard"
    assert runner._uses_real_engine(case) is True

    fake_engine = _FakeDSCEngine()
    captured: dict[str, Any] = {}

    def _fake_get_engine(name: str, config=None, log_fn=None, submodule_id=None):
        captured["name"] = name
        captured["submodule_id"] = submodule_id
        fake_engine.active_submodule = submodule_id or ""
        return fake_engine

    monkeypatch.setattr("polynexus.core.get_engine", _fake_get_engine)

    result = runner.run_case(case)

    assert captured["name"] == "dsc"
    assert captured["submodule_id"] == "dsc.standard"
    assert fake_engine.run_calls == [(str(source_file.resolve()), "")]
    assert result.parameters_used["engine"] == "dsc"
    assert result.parameters_used["submodule"] == "dsc.standard"
    assert result.output_parameters["Tm_peak_C"] == 222.4
    assert result.output_parameters["Tcc_peak_C"] == 177.0
    assert result.output_parameters["Xc_pct"] == 11.9
    assert result.output_parameters["r_squared_method"] == "median_valid_scan_peak_fit_r2"
    assert result.output_parameters["scan_r_squared"][0]["r_squared"] == 0.887885
    assert round(result.phys_score, 6) == 0.6
    assert result.peak_score == 1.0
    assert round(result.composite, 6) == 0.78
    assert result.details["peak"]["available"] is True
    assert result.details["peak"]["field"] == "dsc.temperature_peaks"
    assert [item["field"] for item in result.details["peak"]["peaks"]] == ["Tm_peak_C", "Tcc_peak_C"]
