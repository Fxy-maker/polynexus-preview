from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from polynexus.core.compute import ComputeRunService
from polynexus.core.tga import TGAEngine
from polynexus.core.tga_processing import TGAProcessingConfig


def _write_two_step_curve(path: Path) -> Path:
    temperature = np.linspace(25.0, 800.0, 156)
    mass = (
        100.0
        - 20.0 / (1.0 + np.exp(-(temperature - 300.0) / 8.0))
        - 30.0 / (1.0 + np.exp(-(temperature - 500.0) / 10.0))
    )
    rows = ["Temperature (C),Mass (%)"]
    rows.extend(f"{x:.10g},{y:.10g}" for x, y in zip(temperature, mass, strict=True))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_tga_window_sensitivity_reuses_canonical_template_and_preserves_primary_config(
    tmp_path: Path,
) -> None:
    source = _write_two_step_curve(tmp_path / "curve.csv")
    primary_config = TGAProcessingConfig(dtg_window_points=11)
    created: list[TGAEngine] = []

    def factory(_technique: str, config: Any = None, submodule_id: str | None = None) -> TGAEngine:
        engine = TGAEngine(config=config)
        engine.load = lambda _path: (_ for _ in ()).throw(
            AssertionError("TGA sensitivity candidates must reuse the canonical template")
        )
        created.append(engine)
        return engine

    primary_engine = factory("tga", config=primary_config)
    run = ComputeRunService(factory).run_direct(
        technique="tga",
        path=source,
        output_dir="",
        config=primary_config,
        engine=primary_engine,
        pipeline_options={"method_sensitivity": {"dtg_window": [5, 11, 15]}},
    )

    assert run.status == "completed"
    assert primary_engine.processing_config.dtg_window_points == 11
    assert len(created) == 3
    assert run.result is not None
    maximum_rate = next(
        item
        for item in run.result.method_sensitivities
        if item.metric_path.endswith("dtg.maximum_mass_loss_rate")
    )
    assert maximum_rate.primary_method == "11"
    assert set(maximum_rate.candidates) == {"5", "15"}
    assert all(value is not None for value in maximum_rate.candidates.values())
    assert maximum_rate.parameters["dimension"] == "dtg_window"
    assert maximum_rate.parameters["config_attribute"] == "dtg_window_points"
    assert maximum_rate.parameters["primary_input"] == "canonical_template"
    assert maximum_rate.parameters["candidate_inputs"] == {
        "5": "canonical_template",
        "15": "canonical_template",
    }
    public = run.to_dict()["result"]["method_sensitivities"]
    assert any(item["metric_path"] == maximum_rate.metric_path for item in public)


def test_tga_invalid_sensitivity_candidate_is_retained_without_changing_primary_run(
    tmp_path: Path,
) -> None:
    source = _write_two_step_curve(tmp_path / "invalid-candidate.csv")
    primary_config = TGAProcessingConfig(dtg_window_points=11, dtg_polynomial_order=2)
    run = ComputeRunService().run_direct(
        technique="tga",
        path=source,
        output_dir="",
        config=primary_config,
        pipeline_options={"method_sensitivity": {"dtg_polynomial_order": [2, 15]}},
    )

    assert run.status == "completed"
    assert run.result is not None
    maximum_rate = next(
        item
        for item in run.result.method_sensitivities
        if item.metric_path.endswith("dtg.maximum_mass_loss_rate")
    )
    assert maximum_rate.primary_method == "2"
    assert maximum_rate.candidates["15"] is None
    assert "method_failed:15:ValueError" in maximum_rate.warnings
    assert maximum_rate.parameters["candidate_inputs"]["15"] == "candidate_configuration_invalid"
    assert run.result.metrics["tga_curves"]
