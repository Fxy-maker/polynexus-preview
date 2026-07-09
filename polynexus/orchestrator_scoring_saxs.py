from __future__ import annotations

from typing import Any


def _saxs_evidence_snapshot(
    self: Any,
    output: dict[str, Any],
    analysis_evidence: dict[str, Any],
) -> dict[str, float]:
    if self.technique != "saxs":
        return {
            "fallback_ratio": 0.0,
            "raw_snapshot_rows": 0.0,
            "raw_vs_calibrated_gap": 0.0,
            "thickness_chain_risk": 0.0,
            "q_contamination_frame_ratio": 0.0,
            "mask_truncated_frame_ratio": 0.0,
            "low_conf_frame_ratio": 0.0,
        }

    batch_evidence = (
        analysis_evidence.get("batch_evidence", {})
        if isinstance(analysis_evidence, dict)
        else {}
    )
    if not isinstance(batch_evidence, dict):
        batch_evidence = {}
    batch_summary = batch_evidence.get("batch_calibration_summary", {})
    if not isinstance(batch_summary, dict):
        batch_summary = {}

    batch_frames = self._safe_float(output.get("batch_frames") or batch_evidence.get("batch_frames"))
    if batch_frames <= 0:
        batch_frames = self._safe_float(batch_summary.get("batch_rows"))

    fallback_ratio = self._safe_float(batch_summary.get("fallback_ratio"))
    raw_snapshot_rows = self._safe_float(batch_summary.get("raw_snapshot_rows"))
    gap_terms = [
        batch_summary.get("lc_gap_mean"),
        batch_summary.get("L_gap_mean"),
        batch_summary.get("Xc_gap_mean"),
        batch_summary.get("phi_gap_mean"),
    ]
    raw_vs_calibrated_gap = self._mean_or_none(gap_terms)
    if raw_vs_calibrated_gap is None:
        raw_vs_calibrated_gap = 0.0

    symptom_names = {
        str(item.get("name", "")).strip()
        for item in self._analysis_symptoms(analysis_evidence)
        if isinstance(item, dict)
    }

    thickness_chain_risk = max(
        fallback_ratio,
        raw_vs_calibrated_gap,
        1.0
        - self._safe_float(
            analysis_evidence.get("stability_evidence", {}).get(
                "method_agreement_score",
                1.0,
            )
        )
        if isinstance(analysis_evidence.get("stability_evidence"), dict)
        else 0.0,
    )
    if "thickness_chain_unreliable" in symptom_names:
        thickness_chain_risk = max(thickness_chain_risk, 0.7)

    def ratio_from(summary_key: str, fallback_keys: tuple[str, ...]) -> float:
        count = self._safe_float(batch_evidence.get(summary_key))
        if count <= 0:
            for key in fallback_keys:
                count = self._safe_float(output.get(key))
                if count > 0:
                    break
        if batch_frames <= 0:
            return 0.0
        return max(0.0, min(1.0, count / max(batch_frames, 1.0)))

    return {
        "fallback_ratio": max(0.0, min(1.0, fallback_ratio)),
        "raw_snapshot_rows": max(0.0, raw_snapshot_rows),
        "raw_vs_calibrated_gap": max(0.0, float(raw_vs_calibrated_gap)),
        "thickness_chain_risk": max(0.0, min(1.0, thickness_chain_risk)),
        "q_contamination_frame_ratio": ratio_from(
            "qstar_contaminated_frame_count",
            ("qstar_contaminated_frame_count", "guinier_lost_frame_count"),
        ),
        "mask_truncated_frame_ratio": ratio_from(
            "mask_truncated_frame_count",
            ("mask_truncated_frame_count",),
        ),
        "low_conf_frame_ratio": ratio_from(
            "low_conf_frame_count",
            ("low_conf_frame_count",),
        ),
    }
