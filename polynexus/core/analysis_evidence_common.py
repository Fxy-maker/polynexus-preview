from __future__ import annotations

from typing import Any


def _clean_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _common_summary_details(
    *,
    quality_flag: str,
    residual_type: str,
    risk_flags: list[str],
    constraints: list[dict[str, Any]],
    constraint_summary: dict[str, Any],
) -> dict[str, Any]:
    summary_bits: list[str] = []
    if quality_flag:
        summary_bits.append(f"quality={quality_flag}")
    if residual_type and residual_type != "unknown":
        summary_bits.append(f"residual={residual_type}")
    if risk_flags:
        summary_bits.append(f"risks={len(list(dict.fromkeys(risk_flags)))}")
    if constraints:
        summary_bits.append(f"constraints={len(constraints)}")
    if constraint_summary.get("status") not in {"", "ok"}:
        summary_bits.append(f"constraint_status={constraint_summary.get('status')}")
    if constraint_summary.get("triggered_total"):
        summary_bits.append(f"triggered_constraints={constraint_summary.get('triggered_total')}")
    return {"summary_bits": summary_bits}


def _xray_common_feature_bundle(
    technique_key: str,
    output: dict[str, Any],
    *,
    quality_score: float | None = None,
) -> dict[str, Any]:
    physical_evidence: dict[str, Any] = {}
    feature_evidence: dict[str, Any] = {}
    confidence_signals: list[dict[str, Any]] = []

    for key in (
        "L_bragg",
        "L_lorentz",
        "L_corr_peak",
        "L_nm",
        "L_best",
        "L_confidence",
        "q_peak_snr",
        "invariant_Q",
        "invariant_Q_rel",
        "invariant_Q_valid",
        "Q_star",
        "Q_star_rel",
        "Q_star_valid",
        "has_voids",
        "phi_void",
        "void_AR",
        "f_Herman",
        "f_herman",
        "porod_slope",
    ):
        if key in output:
            physical_evidence[key] = output.get(key)

    for key in ("beam_stop_contaminated", "mask_truncated", "condition_value", "condition_label", "temperature_C", "strain_pct"):
        if key in output:
            physical_evidence[key] = output.get(key)

    if output.get("fit_regions") is not None:
        feature_evidence["fit_regions"] = output.get("fit_regions", [])

    if output.get("quality_score") is not None:
        confidence_signals.append({"name": "quality_score", "value": quality_score, "source": technique_key})
    if output.get("q_peak_snr") is not None:
        confidence_signals.append(
            {"name": "q_peak_snr", "value": _clean_float(output.get("q_peak_snr")), "source": technique_key}
        )
    if output.get("L_confidence") is not None:
        confidence_signals.append(
            {"name": "L_confidence", "value": _clean_float(output.get("L_confidence")), "source": technique_key}
        )
    if output.get("pyfai_q_peak_diff_pct") is not None:
        confidence_signals.append(
            {
                "name": "pyfai_q_peak_diff_pct",
                "value": _clean_float(output.get("pyfai_q_peak_diff_pct")),
                "source": "cross_validation",
            }
        )

    return {
        "physical_evidence": physical_evidence,
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
    }


def _collect_source_fields(
    *,
    fit_evidence: dict[str, Any],
    physical_evidence: dict[str, Any],
    feature_evidence: dict[str, Any],
    residual_evidence: dict[str, Any],
    signal_evidence: dict[str, Any],
    peak_evidence: dict[str, Any],
    reference_evidence: dict[str, Any],
    background_evidence: dict[str, Any],
    phase_evidence: dict[str, Any],
    transform_evidence: dict[str, Any],
    structure_evidence: dict[str, Any],
    raw_structure_evidence: dict[str, Any],
    batch_evidence: dict[str, Any],
    condition_evidence: dict[str, Any],
    stability_evidence: dict[str, Any],
    symptoms: list[dict[str, Any]],
) -> list[str]:
    return sorted(
        set(
            list(fit_evidence.keys())
            + list(physical_evidence.keys())
            + list(feature_evidence.keys())
            + list(residual_evidence.keys())
            + list(signal_evidence.keys())
            + list(peak_evidence.keys())
            + list(background_evidence.keys())
            + list(phase_evidence.keys())
            + list(transform_evidence.keys())
            + list(structure_evidence.keys())
            + list(reference_evidence.keys())
            + list(raw_structure_evidence.keys())
            + list(batch_evidence.keys())
            + list(condition_evidence.keys())
            + list(stability_evidence.keys())
            + (["symptoms"] if symptoms else [])
        )
    )
