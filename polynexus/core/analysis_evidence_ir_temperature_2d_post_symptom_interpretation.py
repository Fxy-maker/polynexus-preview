from __future__ import annotations

from typing import Any


def _ir_temperature_2d_interpretation_constraint_symptoms(
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
        "weak_cos_signal",
        "2D-COS signal is too weak for stable synchronous/asynchronous interpretation.",
        ["baseline_method", "matrix_recovery", "transition_review"],
        {
            "sync_cross_peak_count": metrics.get("sync_cross_peak_count"),
            "async_cross_peak_count": metrics.get("async_cross_peak_count"),
            "dynamic_rms": metrics.get("dynamic_rms"),
            "top_sync_cross_peak_cm1": metrics.get("top_sync_cross_peak_cm1"),
            "top_async_cross_peak_cm1": metrics.get("top_async_cross_peak_cm1"),
        },
        [
            "sync and async cross peaks should become repeatable",
            "cross-peak ranking should stabilize",
        ],
    )
    add(
        "cross_peak_near_diagonal",
        "The strongest 2D-COS cross peak is still too close to the diagonal.",
        ["cross_peak_exclusion_cm1", "cross_peak_threshold"],
        {
            "top_sync_diagonal_distance_cm1": metrics.get("top_sync_diagonal_distance_cm1"),
            "top_async_diagonal_distance_cm1": metrics.get("top_async_diagonal_distance_cm1"),
        },
        [
            "top cross peaks should move away from the diagonal band",
            "self-correlation leakage should weaken",
        ],
    )
    add(
        "cross_peak_without_band_assignment",
        "The leading 2D-COS peaks do not yet map cleanly onto reference bands.",
        ["assignment_tolerance_cm1", "cross_peak_exclusion_cm1"],
        {
            "assigned_cross_peak_count": metrics.get("assigned_cross_peak_count"),
            "unassigned_cross_peak_count": metrics.get("unassigned_cross_peak_count"),
            "top_sync_assigned": metrics.get("top_sync_assigned"),
            "top_async_assigned": metrics.get("top_async_assigned"),
        },
        [
            "assigned cross-peak count should rise",
            "top peaks should align with known bands before interpretation is promoted",
        ],
    )
    add(
        "async_peak_without_sync_support",
        "The asynchronous peak does not yet have enough synchronous support.",
        ["cross_peak_exclusion_cm1", "assignment_tolerance_cm1"],
        {
            "async_with_sync_support_count": metrics.get("async_with_sync_support_count"),
            "top_async_has_sync_support": metrics.get("top_async_has_sync_support"),
        },
        [
            "async peaks should be backed by a stable sync pair",
            "Noda-order interpretation should stop depending on isolated async peaks",
        ],
    )
    add(
        "noda_rule_not_applicable",
        "The current 2D-COS evidence is not yet strong enough for Noda-rule interpretation.",
        ["sequence_axis_source", "assignment_tolerance_cm1", "cross_peak_exclusion_cm1"],
        {
            "noda_rule_interpretation_ready": metrics.get("noda_rule_interpretation_ready"),
            "top_async_has_sync_support": metrics.get("top_async_has_sync_support"),
            "assigned_cross_peak_count": metrics.get("assigned_cross_peak_count"),
        },
        [
            "Noda-rule interpretation should wait until sync/async support becomes explicit",
            "the perturbation ordering and peak assignment chain should become complete",
        ],
    )
    add(
        "insufficient_perturbation_frames",
        "There are not enough perturbation frames to support stable 2D-COS interpretation.",
        ["n_frames", "stage_sequence"],
        {
            "n_frames": metrics.get("n_frames"),
            "stage_counts": metrics.get("stage_counts"),
        },
        [
            "more frames should be present before paper-ready interpretation",
            "the perturbation series should have enough change points",
        ],
    )

    return symptom_list


__all__ = ["_ir_temperature_2d_interpretation_constraint_symptoms"]
