from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.eval.runner import EvalRunner


class _FakeIRConfig:
    baseline_method: str = "rubberband"
    baseline_lam: float = 1e6
    baseline_p: float = 0.001
    atr_correction: bool = False
    atr_crystal: str = "diamond"
    atr_angle_deg: float = 45.0
    smooth_method: str = "savgol"
    smooth_window: int = 7
    smooth_order: int = 3
    normalise: bool = True
    normalization_method: str = "minmax"
    peak_height_min: float = 0.03
    peak_prominence_min: float = 0.02
    peak_distance: float = 18.0
    peak_max_count: int = 40
    peak_fit_window_cm1: float = 35.0
    assignment_tolerance_cm1: float = 18.0
    band_tolerance_cm1: float = 10.0
    polymer_name: str = "PA6"
    crystallinity_band: str = ""
    crystallinity_ref_band: str = ""
    freq_correction_factor: float = 0.9613
    lineshape: str = "lorentzian"
    fwhm_default: float = 8.0
    output_dir: str = ""
    fig_format: str = "svg"
    fig_dpi: int = 300

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_method": self.baseline_method,
            "peak_height_min": self.peak_height_min,
            "peak_prominence_min": self.peak_prominence_min,
            "peak_distance": self.peak_distance,
            "smooth_window": self.smooth_window,
            "normalization_method": self.normalization_method,
            "polymer_name": self.polymer_name,
            "lineshape": self.lineshape,
        }


class _FakeIRResult:
    def __init__(self, params: dict[str, Any]) -> None:
        self.parameters = dict(params)


class _FakeIRTemp2DResult:
    def __init__(self) -> None:
        self.parameters = {
            "n_frames": 17,
            "n_bands_tracked": 4,
            "sequence_axis_mode": "filename",
            "sequence_order_source": "metadata",
            "sequence_axis_score": 0.88,
            "matrix_quality_score": 0.81,
            "cos_signal_score": 0.79,
            "band_tracking_score": 0.84,
            "interpretation_ready": True,
            "paper_conclusion_ready": True,
            "low_confidence_frame_ratio": 0.12,
        }


class _FakeIRPeak:
    def __init__(self, wavenumber: float, assignment: str) -> None:
        self._payload = {
            "wavenumber": wavenumber,
            "height": 1.0,
            "prominence": 0.4,
            "area": 2.0,
            "fwhm_cm1": 12.0,
            "assignment": assignment,
        }

    def get(self, key: str, default=None):
        return self._payload.get(key, default)


class _FakeIRFrame:
    def __init__(self) -> None:
        self.peaks = [_FakeIRPeak(3290.0, "N-H stretch"), _FakeIRPeak(2917.0, "vas(CH2)")]
        self.n_peaks = 2
        self.polymer_name = "PA6"
        self.polymer_score = 0.71
        self.Xc_pct = 13.7
        self.Xc_method = "PA6_A1200_A1637_uncalibrated"
        self.r_squared = 0.996
        self.wavenumber = [4000.0, 3500.0, 3000.0, 2000.0, 1500.0, 1000.0, 550.0]
        self.absorbance = [0.0, 0.1, 0.2, 0.5, 0.8, 0.3, 0.1]
        self.absorbance_fit = [0.0, 0.09, 0.21, 0.48, 0.79, 0.29, 0.1]


class _FakeIREngine:
    def __init__(self) -> None:
        self._ir_config = _FakeIRConfig()
        self.active_submodule = ""
        self.result = _FakeIRResult(
            {
                "n_peaks": 2,
                "polymer_name": "PA6",
                "polymer_score": 0.71,
                "quality_score": 0.71,
                "raw_score": 0.71,
                "Xc_pct": 13.7,
                "Xc_method": "PA6_A1200_A1637_uncalibrated",
                "r_squared": 0.996,
            }
        )
        self._results = [_FakeIRFrame()]
        self._temperature_2d_result = _FakeIRTemp2DResult()
        self.run_calls: list[tuple[str, str]] = []

    def run_pipeline(self, filepath: str, output_dir: str = "") -> _FakeIRResult:
        self.run_calls.append((filepath, output_dir))
        return self.result

    def get_parameters(self) -> dict[str, Any]:
        return dict(self.result.parameters)


def test_eval_runner_executes_real_ir_standard_case(monkeypatch) -> None:
    project_root = Path(__file__).resolve().parents[2]
    case_path = project_root / "tests" / "eval" / "cases" / "real" / "ir_real_standard_pa6_yl.json"
    runner = EvalRunner(project_root=project_root)
    case = runner.load_case(case_path)

    assert case.technique == "ir"
    assert runner._uses_real_engine(case) is True

    fake_engine = _FakeIREngine()
    captured: dict[str, Any] = {}

    def _fake_get_engine(name: str, config=None, log_fn=None, submodule_id=None):
        captured["name"] = name
        captured["submodule_id"] = submodule_id
        fake_engine.active_submodule = submodule_id or ""
        return fake_engine

    monkeypatch.setattr("polynexus.core.get_engine", _fake_get_engine)

    result = runner.run_case(case)

    assert captured["name"] == "ir"
    assert captured["submodule_id"] == "ir.standard"
    assert fake_engine.run_calls == [(str(Path(case.config_overrides["source_file"]).resolve()), "")]
    assert result.parameters_used["engine"] == "ir"
    assert result.parameters_used["submodule"] == "ir.standard"
    assert result.output_parameters["n_peaks"] == 2
    assert result.output_parameters["polymer_name"] == "PA6"
    assert result.output_parameters["peak_centers"] == [3290.0, 2917.0]
    assert result.output_parameters["peak_wavenumbers"] == [3290.0, 2917.0]
    assert result.output_parameters["r_squared"] == 0.996
    assert result.phys_score == 1.0
    assert result.peak_score == 1.0
    assert result.composite == 1.0


def test_eval_runner_executes_real_ir_temperature_2d_case(monkeypatch) -> None:
    project_root = Path(__file__).resolve().parents[2]
    case_path = project_root / "tests" / "eval" / "cases" / "real" / "ir_temperature_2d_real_pa6.json"
    runner = EvalRunner(project_root=project_root)
    case = runner.load_case(case_path)

    assert case.technique == "ir"
    assert case.submodule == "temperature_2d"
    assert runner._uses_real_engine(case) is True

    fake_engine = _FakeIREngine()
    captured: dict[str, Any] = {}

    def _fake_get_engine(name: str, config=None, log_fn=None, submodule_id=None):
        captured["name"] = name
        captured["submodule_id"] = submodule_id
        fake_engine.active_submodule = submodule_id or ""
        return fake_engine

    monkeypatch.setattr("polynexus.core.get_engine", _fake_get_engine)

    result = runner.run_case(case)

    assert captured["name"] == "ir"
    assert captured["submodule_id"] == "ir.temperature_2d"
    assert fake_engine.run_calls == [(str(Path(case.config_overrides["source_file"]).resolve()), "")]
    assert result.parameters_used["engine"] == "ir"
    assert result.parameters_used["submodule"] == "ir.temperature_2d"
    assert result.output_parameters["engine"] == "ir"
    assert result.output_parameters["submodule"] == "ir.temperature_2d"
    assert result.output_parameters["sequence_axis_mode"] == "filename"
    assert result.output_parameters["sequence_order_source"] == "metadata"
    assert result.output_parameters["sequence_axis_score"] == 0.88
    assert result.output_parameters["matrix_quality_score"] == 0.81
    assert result.output_parameters["interpretation_ready"] is True
    assert result.output_parameters["paper_conclusion_ready"] is True
    assert result.details["available_metrics"] == ["PHYS"]
    assert result.phys_score == 1.0
    assert result.peak_score == 1.0
    assert result.composite == 1.0
