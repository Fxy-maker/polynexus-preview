from __future__ import annotations

from typing import Any


def _ir_temperature_2d_sequence_constraint_symptoms(
    triggered: dict[str, Any],
    metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    symptom_list: list[dict[str, Any]] = []

    def add(name: str, summary: str, target_params: list[str], observed: dict[str, Any], expected: list[str]) -> None:
        item = triggered.get(name)
        if not item:
            return
        symptom_list.append(
            {
                "name": name,
                "severity": str(item.get("severity", "") or "").strip() or "WARN",
                "source": "IR_temperature_2d",
                "summary": summary,
                "target_params": target_params,
                "observed": observed,
                "expected_evidence_change": expected,
            }
        )

    add(
        "sequence_axis_incomplete",
        "The 2D IR sequence axis is incomplete, so perturbation ordering is not yet trustworthy.",
        ["temperature_axis_source", "time_axis_source"],
        {
            "n_frames": metrics.get("n_frames"),
            "stage_counts": metrics.get("stage_counts"),
            "temperature_missing_count": metrics.get("temperature_missing_count"),
            "time_missing_count": metrics.get("time_missing_count"),
            "heating_monotonic": metrics.get("heating_monotonic"),
            "cooling_monotonic": metrics.get("cooling_monotonic"),
            "hold_monotonic": metrics.get("hold_monotonic"),
        },
        [
            "temperature/time axis recovery should become complete",
            "heating/cooling/hold ordering should stabilize",
        ],
    )
    add(
        "temperature_axis_missing",
        "The 2D IR sequence does not yet have a reliable temperature axis.",
        ["temperature_axis_source", "sequence_order_source"],
        {
            "temperature_missing_count": metrics.get("temperature_missing_count"),
            "sequence_order_source": metrics.get("sequence_order_source"),
            "stage_counts": metrics.get("stage_counts"),
        },
        [
            "temperature recovery should become explicit",
            "the sequence axis should no longer depend on guessed order",
        ],
    )
    add(
        "stage_order_ambiguous",
        "Heating, hold, and cooling are not in a clean order yet.",
        ["stage_sequence", "sequence_order_source"],
        {
            "heating_monotonic": metrics.get("heating_monotonic"),
            "cooling_monotonic": metrics.get("cooling_monotonic"),
            "hold_monotonic": metrics.get("hold_monotonic"),
            "sequence_order_source": metrics.get("sequence_order_source"),
        },
        [
            "stage ordering should become monotonic and explicit",
            "mixed sequence directions should not be interpreted as real transitions",
        ],
    )
    add(
        "hold_time_missing_or_estimated",
        "Hold-time values are missing or only estimated, so the hold segment is less trustworthy.",
        ["time_axis_source", "hold_time_source"],
        {
            "time_missing_count": metrics.get("time_missing_count"),
            "hold_time_missing_count": metrics.get("hold_time_missing_count"),
            "hold_time_estimated_count": metrics.get("hold_time_estimated_count"),
        },
        [
            "hold times should be recovered explicitly",
            "estimated hold segments should not drive the conclusion",
        ],
    )
    add(
        "matrix_shape_inconsistent",
        "The 2D IR matrix and correlation shapes are inconsistent.",
        ["matrix_shape", "sync_shape", "async_shape"],
        {
            "matrix_shape": metrics.get("matrix_shape"),
            "dynamic_shape": metrics.get("dynamic_shape"),
            "sync_shape": metrics.get("sync_shape"),
            "async_shape": metrics.get("async_shape"),
        },
        [
            "dynamic and correlation shapes should agree",
            "2D-COS maps should be square and aligned with the tracked axis",
        ],
    )
    add(
        "negative_matrix_fraction_high",
        "The absorbance matrix contains too many non-positive values.",
        ["baseline_method", "mute_zone", "matrix_recovery"],
        {
            "neg_fraction": metrics.get("neg_fraction"),
            "nan_fraction": metrics.get("nan_fraction"),
            "dynamic_rms": metrics.get("dynamic_rms"),
        },
        [
            "baseline over-subtraction should weaken",
            "dynamic matrix sign balance should move toward a stable range",
        ],
    )
    add(
        "matrix_nan_fraction_high",
        "The 2D IR matrix contains too many NaN values.",
        ["matrix_recovery", "interpolation_grid"],
        {
            "nan_fraction": metrics.get("nan_fraction"),
            "wavenumber_grid_consistent": metrics.get("wavenumber_grid_consistent"),
        },
        [
            "spectral interpolation should become complete",
            "matrix holes should be filled before 2D-COS interpretation",
        ],
    )
    add(
        "wavenumber_grid_inconsistent",
        "The per-frame wavenumber grids are not aligned to a shared axis.",
        ["wavenumber_grid", "matrix_shape"],
        {
            "wavenumber_grid_consistent": metrics.get("wavenumber_grid_consistent"),
            "sequence_order_source": metrics.get("sequence_order_source"),
        },
        [
            "all frames should share the same wavenumber grid",
            "grid alignment should be fixed before cross-peak ranking",
        ],
    )
    add(
        "frame_intensity_scale_unstable",
        "The frame-to-frame intensity scale is drifting too much.",
        ["normalization_method", "baseline_method", "frame_scale"],
        {
            "frame_intensity_scale_spread": metrics.get("frame_intensity_scale_spread"),
            "dynamic_rms": metrics.get("dynamic_rms"),
        },
        [
            "frame scale should stabilize across the series",
            "normalization should stop erasing the temperature trend",
        ],
    )

    return symptom_list


__all__ = ["_ir_temperature_2d_sequence_constraint_symptoms"]
