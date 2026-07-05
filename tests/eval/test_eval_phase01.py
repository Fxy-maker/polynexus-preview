from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from tests.eval.models import EvalCase, GroundTruth
from tests.eval.runner import EvalRunner
from tests.eval.synth_generator import SynthGenerator


def _local_tmp_dir() -> Path:
    root = Path(__file__).resolve().parent / "_tmp"
    path = root / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def test_redistribute_weights_matches_phase0_rules() -> None:
    assert EvalRunner.redistribute_weights({"PHYS", "PEAK", "CROSS", "HUMAN"}) == {
        "PHYS": 0.25,
        "PEAK": 0.25,
        "CROSS": 0.25,
        "HUMAN": 0.25,
    }
    assert EvalRunner.redistribute_weights({"PHYS", "PEAK", "CROSS"}) == {
        "PHYS": 0.40,
        "PEAK": 0.35,
        "CROSS": 0.25,
    }
    assert EvalRunner.redistribute_weights({"PHYS", "PEAK"}) == {"PHYS": 0.55, "PEAK": 0.45}
    assert EvalRunner.redistribute_weights({"PHYS"}) == {"PHYS": 1.0}


def test_load_case_expands_single_value_ranges() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        case_path = tmp_dir / "case.json"
        case_path.write_text(
            json.dumps(
                {
                    "case_id": "waxs_single_range",
                    "technique": "waxs",
                    "submodule": "static",
                    "data_file": "synth:waxs_single_range",
                    "polymer_name": "PA6",
                    "polymer_phase": "alpha",
                    "config_overrides": {},
                    "ground_truth": {"Xc_pct": [40.0], "peak_centers": [[20.0]]},
                    "source": "synthetic",
                    "notes": "single-value range expansion test",
                }
            ),
            encoding="utf-8",
        )

        case = EvalRunner(eval_root=tmp_dir, project_root=tmp_dir).load_case(case_path)

        assert case.ground_truth.Xc_pct == (38.0, 42.0)
        assert case.ground_truth.peak_centers == [(19.0, 21.0)]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_generator_outputs_all_named_cases_and_runner_loads_them() -> None:
    tmp_dir = _local_tmp_dir()
    try:
        eval_root = tmp_dir / "eval"
        generated = SynthGenerator(output_dir=eval_root, seed=42).generate_all()

        assert len(generated) == len(SynthGenerator.CASE_IDS)
        assert len(list((eval_root / "synth_data").glob("*.xy"))) == len(SynthGenerator.CASE_IDS)
        assert len(list((eval_root / "cases" / "synth").glob("*.json"))) == len(SynthGenerator.CASE_IDS)
        assert (eval_root / "cases" / "real").is_dir()

        runner = EvalRunner(eval_root=eval_root, project_root=tmp_dir)
        cases = runner.load_all_cases(eval_root / "cases")

        assert not runner.load_errors
        assert len(cases) == len(SynthGenerator.CASE_IDS)
        result = runner.run_case(cases[0])
        assert result.phys_score == 1.0
        assert result.composite > 0.99
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_compute_metrics_includes_baseline_vs_tuned_comparison() -> None:
    runner = EvalRunner()
    case = EvalCase(
        case_id="waxs_benchmark_compare",
        technique="waxs",
        submodule="static",
        data_file="synth:waxs_benchmark_compare",
        polymer_name="PA6",
        polymer_phase="alpha",
        config_overrides={},
        ground_truth=GroundTruth(
            Xc_pct=(42.0, 48.0),
            peak_centers=[(19.8, 20.2)],
        ),
        source="synthetic",
        notes="baseline vs tuned benchmark comparison",
    )
    result = runner.compute_metrics(
        case,
        {
            "parameters_used": {"peak_function": "pseudo_voigt"},
            "baseline_output_parameters": {
                "Xc_pct": 44.0,
                "peak_centers": [17.0],
                "peaks": [{"center": 17.0, "fwhm": 0.8}],
            },
            "tuned_output_parameters": {
                "Xc_pct": 44.0,
                "peak_centers": [20.0],
                "peaks": [{"center": 20.0, "fwhm": 0.5}],
            },
        },
    )

    benchmark = result.details["benchmark"]
    assert benchmark["objective_improved"] is True
    assert benchmark["objective_delta"] > 0
    assert benchmark["baseline"]["composite"] < benchmark["tuned"]["composite"]
    assert benchmark["symptom_hit"] is True
