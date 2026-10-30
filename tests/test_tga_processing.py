from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polynexus.core.compute import ComputeRunService
from polynexus.core.engine import get_engine
from polynexus.core.tga import TGAEngine
from polynexus.core.tga_processing import TGAProcessingConfig


def _write_curve(path: Path, x: np.ndarray, mass: np.ndarray, *, x_header: str, mass_header: str) -> Path:
    rows = [f"{x_header},{mass_header}"]
    rows.extend(f"{x_value:.10g},{mass_value:.10g}" for x_value, mass_value in zip(x, mass, strict=True))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _two_step_curve() -> tuple[np.ndarray, np.ndarray]:
    temperature = np.linspace(25.0, 800.0, 156)
    first_loss = 20.0 / (1.0 + np.exp(-(temperature - 300.0) / 8.0))
    second_loss = 30.0 / (1.0 + np.exp(-(temperature - 500.0) / 10.0))
    return temperature, 100.0 - first_loss - second_loss


def _only_curve(metrics: dict) -> dict:
    curves = metrics["tga_curves"]
    assert len(curves) == 1
    return next(iter(curves.values()))


def test_tga_derives_traceable_normalized_dtg_and_two_event_candidates(tmp_path: Path) -> None:
    temperature, mass = _two_step_curve()
    source = _write_curve(
        tmp_path / "two-step.csv",
        temperature,
        mass,
        x_header="Temperature (C)",
        mass_header="Mass (%)",
    )
    config = TGAProcessingConfig(
        normalization_reference_points=5,
        dtg_window_points=11,
        dtg_polynomial_order=2,
        event_prominence_noise_factor=3.0,
        event_minimum_mass_loss_percent=1.0,
        residue_targets=(400.0, 700.0, 900.0),
    )
    engine = TGAEngine(config=config)
    source_bytes = source.read_bytes()

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="tga", path=source, output_dir="", engine=engine
    )

    assert run.status == "completed"
    assert run.result is not None
    assert run.canonical_template is not None
    assert source.read_bytes() == source_bytes
    curve = _only_curve(dict(run.result.metrics))
    assert curve["normalization"]["status"] == "computed"
    assert curve["normalization"]["method"] == "initial_window_median"
    assert curve["normalization"]["output_unit"] == "percent_initial_mass"
    assert curve["dtg"]["status"] == "computed"
    assert curve["dtg"]["method"] == "local_polynomial_derivative"
    assert curve["dtg"]["parameters"]["window_points"] == 11
    assert curve["dtg"]["parameters"]["sign_convention"] == "-d(normalized_mass)/d(x)"

    events = curve["mass_loss_events"]
    assert events["status"] == "computed"
    assert events["event_count"] == 2
    ordered = [
        events[key]
        for key in sorted(
            key for key in events if key.startswith("event_") and key != "event_count"
        )
    ]
    assert [event["peak_x"] for event in ordered] == sorted(event["peak_x"] for event in ordered)
    assert ordered[0]["peak_x"] == pytest.approx(300.0, abs=10.0)
    assert ordered[1]["peak_x"] == pytest.approx(500.0, abs=10.0)
    for event in ordered:
        assert event["onset_candidate_x"] < event["peak_x"] < event["endset_candidate_x"]
        assert (
            event["canonical_index_start"]
            < event["peak_index"]
            < event["canonical_index_end"]
        )
        assert event["interval_mass_loss_percent"] > 1.0
        assert event["method"] == "dtg_peak_prominence_bases"
        assert event["parameters"] == events["parameters"]
        assert event["axis_unit"] == "°C"

    residue = curve["residue"]
    assert residue["final_recorded_mass_percent"] == pytest.approx(50.0, abs=0.2)
    assert residue["target_001"]["mass_percent"] == pytest.approx(80.0, abs=0.2)
    assert residue["target_002"]["mass_percent"] == pytest.approx(50.0, abs=0.2)
    assert residue["target_003"]["status"] == "unavailable"
    assert residue["target_003"]["unavailable_reason"] == "target_outside_recorded_axis"

    measurement_id = next(iter(dict(run.result.metrics)["tga_curves"]))
    canonical_signal = np.asarray(
        run.canonical_template.measurements[0].channels["intensity"],
        dtype=float,
    )
    np.testing.assert_array_equal(
        engine.result.raw_data[f"{measurement_id}:signal"],
        canonical_signal,
    )
    np.testing.assert_allclose(
        engine.result.raw_data[f"{measurement_id}:normalized_mass_percent"][:5],
        mass[:5] / np.median(mass[:5]) * 100.0,
    )
    assert engine.result.raw_data[f"{measurement_id}:dtg"].shape == mass.shape
    assert engine.result.raw_data[
        f"{measurement_id}:smoothed_mass_percent"
    ].shape == mass.shape


def test_tga_non_increasing_axis_keeps_base_run_and_localizes_unavailable_outputs(tmp_path: Path) -> None:
    x = np.asarray([25.0, 100.0, 90.0, 200.0, 300.0, 400.0])
    mass = np.asarray([10.0, 9.9, 9.8, 8.0, 7.0, 6.0])
    source = _write_curve(
        tmp_path / "non-monotonic.csv", x, mass, x_header="Temperature (C)", mass_header="Weight (mg)"
    )
    engine = get_engine("tga")
    assert engine is not None

    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="tga", path=source, output_dir="", engine=engine
    )

    assert run.status == "completed"
    assert run.result is not None
    curve = _only_curve(dict(run.result.metrics))
    assert curve["normalization"]["status"] == "computed"
    assert curve["residue"]["status"] == "computed"
    assert curve["dtg"] == {
        "status": "unavailable",
        "unavailable_reason": "axis_not_strictly_increasing",
    }
    assert curve["mass_loss_events"] == {
        "status": "unavailable",
        "unavailable_reason": "dtg_unavailable",
    }
    assert run.result.metrics["point_count"] == 6


def test_tga_time_axis_keeps_unknown_units_and_does_not_label_targets_as_temperature(tmp_path: Path) -> None:
    time = np.linspace(0.0, 20.0, 41)
    mass = 12.0 - 2.0 / (1.0 + np.exp(-(time - 10.0)))
    source = _write_curve(
        tmp_path / "time.csv", time, mass, x_header="Elapsed time", mass_header="Sample mass"
    )
    engine = TGAEngine(config=TGAProcessingConfig(residue_targets=(10.0,)))

    result = engine.run_pipeline(str(source), "")

    curve = _only_curve(result.parameters)
    assert curve["axis_kind"] == "time"
    assert curve["dtg"]["status"] == "computed"
    assert curve["dtg"]["axis_unit"] == "unknown"
    assert curve["dtg"]["rate_unit"] == "percent_initial_mass_per_unknown"
    assert curve["residue"]["target_001"] == {
        "status": "unavailable",
        "requested_x": 10.0,
        "axis_unit": "unknown",
        "unavailable_reason": "temperature_axis_required",
    }
    assert set(result.validation_warnings) == {
        "coordinate_unit_unknown",
        "intensity_unit_unknown",
    }


def test_tga_compute_manifest_exposes_derived_series_and_method_metadata(tmp_path: Path) -> None:
    temperature, mass = _two_step_curve()
    source = _write_curve(
        tmp_path / "manifest.csv",
        temperature,
        mass,
        x_header="Temperature (C)",
        mass_header="Mass (%)",
    )
    run = ComputeRunService().run_direct(technique="tga", path=source, output_dir="")

    assert run.status == "completed"
    assert run.result is not None
    manifest = {item["path"]: item for item in run.result.metric_manifest(source=str(source))}
    normalized_path = next(path for path in manifest if path.endswith("derived.normalized_mass_percent"))
    dtg_path = next(path for path in manifest if path.endswith("derived.dtg"))
    peak_path = next(path for path in manifest if path.endswith("mass_loss_events.event_001.peak_x"))
    assert manifest[normalized_path]["kind"] == "series"
    assert manifest[normalized_path]["method"] == "initial_window_median"
    assert manifest[normalized_path]["unit"] == "percent_initial_mass"
    assert manifest[dtg_path]["method"] == "local_polynomial_derivative"
    assert manifest[peak_path]["method"] == "dtg_peak_prominence_bases"
    assert manifest[peak_path]["unit"] == "°C"


def test_tga_unknown_temperature_unit_does_not_interpolate_a_requested_residue(
    tmp_path: Path,
) -> None:
    temperature = np.linspace(25.0, 500.0, 40)
    mass = np.linspace(20.0, 10.0, 40)
    source = _write_curve(
        tmp_path / "unknown-temperature-unit.csv",
        temperature,
        mass,
        x_header="Temperature",
        mass_header="Mass (mg)",
    )
    result = TGAEngine(
        config=TGAProcessingConfig(residue_targets=(400.0,))
    ).run_pipeline(str(source), "")

    curve = _only_curve(result.parameters)
    assert curve["residue"]["target_001"]["status"] == "unavailable"
    assert (
        curve["residue"]["target_001"]["unavailable_reason"]
        == "temperature_unit_unknown"
    )


def test_tga_nonpositive_reference_localizes_normalization_failure(tmp_path: Path) -> None:
    source = _write_curve(
        tmp_path / "zero-reference.csv",
        np.linspace(25.0, 200.0, 8),
        np.zeros(8),
        x_header="Temperature (C)",
        mass_header="Mass (mg)",
    )
    engine = TGAEngine()

    result = engine.run_pipeline(str(source), "")

    curve = _only_curve(result.parameters)
    assert curve["normalization"] == {
        "status": "unavailable",
        "unavailable_reason": "normalization_reference_nonpositive",
    }
    assert curve["dtg"]["unavailable_reason"] == "normalization_unavailable"
    assert curve["mass_loss_events"]["unavailable_reason"] == "dtg_unavailable"
    assert curve["derived"]["normalized_mass_percent"] is None
    assert result.parameters["point_count"] == 8
