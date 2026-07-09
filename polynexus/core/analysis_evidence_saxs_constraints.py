from __future__ import annotations

from typing import Any

from .analysis_evidence_saxs_condition import _condition_values
from .analysis_evidence_utils import _clean_float, _relative_spread, _safe_int


_SAXS_CONSTRAINT_NAMES = {
    "missing_condition_axis",
    "strain_axis_low_confidence",
    "strain_sequence_nonmonotonic",
    "strain_duplicate_frames",
    "low_q_void_dominant",
    "strain_void_lamellar_conflict",
    "lamellar_anchor_lost_under_strain",
    "qstar_rel_without_lamellar_support",
    "orientation_shift_breaks_lamellar_comparison",
}


def _evaluate_saxs_constraint(
    item_name: str,
    output: dict[str, Any],
    observed: Any = None,
    batch_rows: list[dict[str, Any]] | None = None,
) -> tuple[bool, Any]:
    batch_rows = batch_rows if isinstance(batch_rows, list) else []
    condition_label = str(output.get("condition_label", "") or "").strip().lower()

    if item_name == "missing_condition_axis":
        condition_value = _clean_float(output.get("condition_value"))
        if condition_value is None:
            condition_value = _clean_float(output.get("temperature_C"))
        if condition_value is None:
            condition_value = _clean_float(output.get("strain_pct"))
        raw_file = str(output.get("file", "") or "").strip().lower()
        current_observed = {
            "condition_value": condition_value,
            "condition_label": condition_label,
            "file": raw_file,
        }
        triggered = (
            condition_label in {"temperature", "strain"}
            and condition_value is None
            and raw_file.startswith("check-")
        )
        return triggered, current_observed

    if item_name == "strain_axis_low_confidence":
        strain_confidence = _clean_float(
            output.get("strain_axis_confidence", output.get("condition_confidence"))
        )
        if strain_confidence is None:
            strain_confidence = _clean_float(output.get("condition_confidence"))
        current_observed = {
            "condition_label": condition_label,
            "strain_axis_confidence": strain_confidence,
            "condition_continuity_score": _clean_float(output.get("condition_continuity_score")),
        }
        triggered = (
            condition_label == "strain"
            and strain_confidence is not None
            and strain_confidence < 0.70
        )
        return triggered, current_observed

    if item_name == "strain_sequence_nonmonotonic":
        strain_values = _condition_values(output, batch_rows, "strain")
        current_observed = {
            "strain_values": strain_values,
            "sequence_direction": "unknown",
        }
        if len(strain_values) >= 2:
            increasing = all(b >= a for a, b in zip(strain_values, strain_values[1:]))
            decreasing = all(b <= a for a, b in zip(strain_values, strain_values[1:]))
            if increasing:
                current_observed["sequence_direction"] = "increasing"
            elif decreasing:
                current_observed["sequence_direction"] = "decreasing"
            else:
                current_observed["sequence_direction"] = "mixed"
        triggered = bool(strain_values) and current_observed.get("sequence_direction") == "mixed"
        return triggered, current_observed

    if item_name == "strain_duplicate_frames":
        strain_values = _condition_values(output, batch_rows, "strain")
        duplicates = max(0, len(strain_values) - len({str(value) for value in strain_values}))
        current_observed = {
            "strain_values": strain_values,
            "strain_duplicate_count": duplicates,
        }
        return duplicates > 0, current_observed

    if item_name == "low_q_void_dominant":
        has_voids = bool(output.get("has_voids")) or _safe_int(
            output.get("has_voids_row_count"),
            default=0,
        ) > 0
        phi_void = _clean_float(output.get("phi_void_mean", output.get("phi_void")))
        phi_void_span = _clean_float(output.get("phi_void_span"))
        porod_slope = _clean_float(output.get("porod_slope_mean", output.get("porod_slope")))
        q_star_valid = output.get("Q_star_valid")
        if porod_slope is not None and porod_slope > -3.5:
            has_voids = True
        current_observed = {
            "has_voids": has_voids,
            "phi_void": phi_void,
            "phi_void_span": phi_void_span,
            "porod_slope": porod_slope,
            "Q_star_valid": q_star_valid,
        }
        triggered = has_voids and (
            (phi_void is not None and phi_void >= 0.02)
            or (phi_void_span is not None and phi_void_span >= 0.015)
            or (porod_slope is not None and porod_slope > -3.5)
            or bool(output.get("beam_stop_contaminated"))
            or bool(output.get("mask_truncated"))
            or q_star_valid is False
        )
        return triggered, current_observed

    if item_name == "strain_void_lamellar_conflict":
        has_voids = bool(output.get("has_voids")) or _safe_int(
            output.get("has_voids_row_count"),
            default=0,
        ) > 0
        phi_void = _clean_float(output.get("phi_void_mean", output.get("phi_void")))
        q_star_rel = _clean_float(
            output.get("Q_star_rel_mean", output.get("Q_star_rel", output.get("Q_rel")))
        )
        q_star_rel_span = _clean_float(output.get("Q_star_rel_span"))
        l_bragg = _clean_float(output.get("L_bragg"))
        l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
        l_best = _clean_float(output.get("L_best", output.get("L_nm")))
        l_spread = _relative_spread([value for value in (l_bragg, l_corr, l_best) if value is not None])
        porod_slope = _clean_float(output.get("porod_slope_mean", output.get("porod_slope")))
        void_proxy = (
            has_voids
            or bool(output.get("beam_stop_contaminated"))
            or bool(output.get("mask_truncated"))
            or output.get("Q_star_valid") is False
        )
        if porod_slope is not None and porod_slope > -3.5:
            void_proxy = True
        current_observed = {
            "has_voids": has_voids,
            "phi_void": phi_void,
            "Q_star_rel": q_star_rel,
            "Q_star_rel_span": q_star_rel_span,
            "L_bragg": l_bragg,
            "L_corr": l_corr,
            "L_best": l_best,
            "l_spread": l_spread,
            "porod_slope": porod_slope,
        }
        triggered = condition_label == "strain" and (
            void_proxy
            and (
                (phi_void is not None and phi_void >= 0.02)
                or (q_star_rel_span is not None and q_star_rel_span >= 0.05)
                or (l_spread is not None and l_spread > 0.05)
                or (porod_slope is not None and porod_slope > -3.5)
                or bool(output.get("beam_stop_contaminated"))
                or bool(output.get("mask_truncated"))
                or output.get("Q_star_valid") is False
            )
        )
        return triggered, current_observed

    if item_name == "lamellar_anchor_lost_under_strain":
        has_voids = bool(output.get("has_voids")) or _safe_int(
            output.get("has_voids_row_count"),
            default=0,
        ) > 0
        l_bragg = _clean_float(output.get("L_bragg"))
        l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
        l_best = _clean_float(output.get("L_best", output.get("L_nm")))
        l_values = [value for value in (l_bragg, l_corr, l_best) if value is not None]
        l_spread = _relative_spread(l_values)
        void_proxy = (
            has_voids
            or bool(output.get("beam_stop_contaminated"))
            or bool(output.get("mask_truncated"))
            or output.get("Q_star_valid") is False
        )
        current_observed = {
            "has_voids": has_voids,
            "L_bragg": l_bragg,
            "L_corr": l_corr,
            "L_best": l_best,
            "l_spread": l_spread,
            "Q_star_valid": output.get("Q_star_valid"),
        }
        triggered = condition_label == "strain" and (
            len(l_values) < 2 or l_spread is None or l_spread > 0.08
        ) and void_proxy
        return triggered, current_observed

    if item_name == "qstar_rel_without_lamellar_support":
        q_star_rel = _clean_float(
            output.get("Q_star_rel_mean", output.get("Q_star_rel", output.get("Q_rel")))
        )
        q_star_rel_span = _clean_float(output.get("Q_star_rel_span"))
        l_bragg = _clean_float(output.get("L_bragg"))
        l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
        l_best = _clean_float(output.get("L_best", output.get("L_nm")))
        l_values = [value for value in (l_bragg, l_corr, l_best) if value is not None]
        l_spread = _relative_spread(l_values)
        current_observed = {
            "Q_star_rel": q_star_rel,
            "Q_star_rel_span": q_star_rel_span,
            "L_bragg": l_bragg,
            "L_corr": l_corr,
            "L_best": l_best,
            "l_spread": l_spread,
        }
        triggered = condition_label == "strain" and q_star_rel is not None and (
            len(l_values) < 2
            or l_spread is None
            or l_spread > 0.08
            or (q_star_rel_span is not None and q_star_rel_span > 0.05)
        )
        return triggered, current_observed

    if item_name == "orientation_shift_breaks_lamellar_comparison":
        f_herman = _clean_float(output.get("f_Herman_mean", output.get("f_Herman", output.get("f_herman"))))
        f_herman_span = _clean_float(output.get("f_Herman_span"))
        q_star_rel_span = _clean_float(output.get("Q_star_rel_span"))
        current_observed = {
            "f_Herman": f_herman,
            "f_Herman_span": f_herman_span,
            "Q_star_rel_span": q_star_rel_span,
        }
        triggered = (
            condition_label == "strain"
            and f_herman is not None
            and (f_herman_span is not None and f_herman_span > 0.35)
            and (q_star_rel_span is None or q_star_rel_span > 0.03)
        )
        return triggered, current_observed

    return False, observed


__all__ = [
    "_SAXS_CONSTRAINT_NAMES",
    "_evaluate_saxs_constraint",
]
