from __future__ import annotations

from typing import Any


def _ir_temperature_2d_transition_constraint_symptoms(
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
        "transition_candidate_present",
        "A temperature-dependent transition candidate is present in the tracked bands.",
        ["transition_review", "band_tracking"],
        {
            "transition_count": metrics.get("transition_count"),
            "transition_temperatures_C": metrics.get("transition_temperatures_C"),
        },
        [
            "transition candidate should be verified against the raw sequence",
            "cross-peak interpretation should stay evidence-only until stable",
        ],
    )
    add(
        "band_index_jump_single_frame",
        "The band-index transition is still dominated by a single-frame jump.",
        ["band_tracking", "transition_review"],
        {
            "band_index_transition_support_band_count": metrics.get("band_index_transition_support_band_count"),
            "band_index_transition_frame_spread": metrics.get("band_index_transition_frame_spread"),
            "band_index_transition_max_jump_cm1": metrics.get("band_index_transition_max_jump_cm1"),
            "band_index_transition_max_jump_ratio": metrics.get("band_index_transition_max_jump_ratio"),
        },
        [
            "transition support should span more than one band index series",
            "single-frame spikes should stop dominating the transition readout",
        ],
    )
    add(
        "band_index_denominator_unstable",
        "The band-index denominator looks unstable, so the transition may be amplified by a weak local baseline.",
        ["band_tracking", "transition_review"],
        {
            "band_index_transition_denominator_unstable": metrics.get("band_index_transition_denominator_unstable"),
            "band_index_transition_max_jump_ratio": metrics.get("band_index_transition_max_jump_ratio"),
        },
        [
            "the band-index scale should be more balanced",
            "local denominator effects should stop dominating the transition shape",
        ],
    )
    add(
        "transition_single_frame_only",
        "The transition is only supported by a single-frame event so far.",
        ["band_tracking", "transition_review"],
        {
            "band_index_transition_support_band_count": metrics.get("band_index_transition_support_band_count"),
            "band_index_transition_frame_spread": metrics.get("band_index_transition_frame_spread"),
            "band_index_transition_reproducible": metrics.get("band_index_transition_reproducible"),
        },
        [
            "transition support should cover multiple band indices",
            "the transition should persist across adjacent frames",
        ],
    )
    add(
        "band_tracking_missing_key_band",
        "One or more tracked transition bands are still missing from the band-index chain.",
        ["band_tracking", "reference_band_chain"],
        {
            "band_index_series_count": metrics.get("band_index_series_count"),
            "band_index_transition_support_keys": metrics.get("band_index_transition_support_keys"),
        },
        [
            "the key band-index series should be present before transition claims are strengthened",
            "band tracking should cover all expected reference bands",
        ],
    )
    add(
        "temperature_trend_not_reproducible",
        "The temperature trend is not yet reproducible across the tracked band indices.",
        ["band_tracking", "transition_review"],
        {
            "band_index_transition_support_band_count": metrics.get("band_index_transition_support_band_count"),
            "band_index_transition_reproducible": metrics.get("band_index_transition_reproducible"),
            "band_index_transition_support_ratio": metrics.get("band_index_transition_support_ratio"),
        },
        [
            "the same transition should be supported by multiple tracked bands",
            "trend direction should stay consistent across the series",
        ],
    )

    return symptom_list


__all__ = ["_ir_temperature_2d_transition_constraint_symptoms"]
