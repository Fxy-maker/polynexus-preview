from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tests.eval.models import EvalCase, GroundTruth
from tests.eval.runner import EvalRunner


@dataclass
class _FakeNMRConfig:
    baseline_method: str = "polynomial"
    peak_height_min: float = 0.03
    peak_distance_ppm: float = 1.0
    polymer_name: str = "PA6"

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_method": self.baseline_method,
            "peak_height_min": self.peak_height_min,
            "peak_distance_ppm": self.peak_distance_ppm,
            "polymer_name": self.polymer_name,
        }


class _FakeNMRResult:
    parameters = {
        "n_peaks": 2,
        "dominant_peak_ppm": 100.0,
        "median_snr": 14.0,
        "Xc_pct": 38.0,
    }
    peaks = [
        {"ppm": 100.0, "height": 1.0, "fwhm_ppm": 1.2, "assignment": "backbone"},
        {"ppm": 40.0, "height": 0.6, "fwhm_ppm": 1.4, "assignment": "aliphatic"},
    ]
    ppm = np.array([180.0, 100.0, 40.0, 0.0])
    r_squared = 0.98
    median_snr = 14.0
    dominant_peak_ppm = 100.0
    Xc_pct = 38.0
    sample_state = "solid"
    nucleus = "13C"


class _FakeNMREngine:
    def __init__(self) -> None:
        self._cfg = _FakeNMRConfig()
        self.active_submodule = ""
        self._results = [_FakeNMRResult()]
        self.run_calls: list[tuple[str, str]] = []

    def run_pipeline(self, filepath: str, output_dir: str = "") -> SimpleNamespace:
        self.run_calls.append((filepath, output_dir))
        return SimpleNamespace(parameters=dict(_FakeNMRResult.parameters))

    def get_parameters(self) -> dict[str, object]:
        return dict(_FakeNMRResult.parameters)


def test_eval_runner_executes_real_nmr_case(monkeypatch, tmp_path: Path) -> None:
    source_file = tmp_path / "solid_13c.csv"
    source_file.write_text("ppm,intensity\n180,0.1\n100,1.0\n40,0.6\n0,0.1\n", encoding="utf-8")
    case = EvalCase(
        case_id="nmr-real-13c",
        technique="nmr",
        submodule="solid_c",
        data_file="ignored-by-source-file-override",
        polymer_name="PA6",
        polymer_phase=None,
        config_overrides={"source_file": str(source_file)},
        ground_truth=GroundTruth(peak_shifts=[(99.0, 101.0), (39.0, 41.0)]),
        source="expert_review",
        notes="Real-engine bridge contract test.",
    )
    fake_engine = _FakeNMREngine()
    captured: dict[str, str] = {}

    def _fake_get_engine(name: str, config=None, log_fn=None, submodule_id=None):
        captured["name"] = name
        captured["submodule_id"] = submodule_id or ""
        fake_engine.active_submodule = submodule_id or ""
        return fake_engine

    monkeypatch.setattr("polynexus.core.get_engine", _fake_get_engine)
    runner = EvalRunner(project_root=tmp_path)

    assert runner._uses_real_engine(case) is True
    result = runner.run_case(case)

    assert captured == {"name": "nmr", "submodule_id": "nmr.solid_c"}
    assert fake_engine.run_calls == [(str(source_file.resolve()), "")]
    assert result.parameters_used["engine"] == "nmr"
    assert result.parameters_used["submodule"] == "nmr.solid_c"
    assert result.output_parameters["peak_shifts"] == [100.0, 40.0]
    assert result.output_parameters["n_peaks"] == 2
    assert result.output_parameters["Xc_pct"] == 38.0
    assert result.phys_score == 1.0
    assert result.peak_score == 1.0
