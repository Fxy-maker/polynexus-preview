from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _safe_int


_EVENT_CONSTRAINT_NAMES = {
    "Tg_without_DCp_step",
    "Tg_outside_supported_window",
    "melting_without_supported_event",
    "cold_crystallization_conflicts_with_melting",
    "event_polarity_conflict",
    "peak_components_too_sparse",
    "peak_width_nonphysical",
    "crystallinity_without_event_support",
}


def _evaluate_dsc_event_constraint(
    item_name: str,
    output: dict[str, Any],
    context: dict[str, Any],
) -> tuple[bool, Any] | None:
    if item_name not in _EVENT_CONSTRAINT_NAMES:
        return None

    peak_rows = context["peak_rows"]
    scan_mode = context["scan_mode"]
    dtg = context["dtg"]
    dcp = context["dcp"]
    tg_c = context["tg_c"]
    tm_peak = context["tm_peak"]
    tm_onset = context["tm_onset"]
    tcc_peak = context["tcc_peak"]
    tcc_onset = context["tcc_onset"]
    tc_peak = context["tc_peak"]
    dhm = context["dhm"]
    dhcc = context["dhcc"]
    xc_pct = context["xc_pct"]
    tg_window_low = context["tg_window_low"]
    tg_window_high = context["tg_window_high"]
    exo_up = context["exo_up"]
    supported_components = context["supported_components"]
    supported_melting_components = context["supported_melting_components"]
    max_melt_width = context["max_melt_width"]

    def _near_event(
        event_type: set[str],
        center_c: float | None,
        tolerance_c: float = 12.0,
    ) -> list[dict[str, Any]]:
        if center_c is None:
            return []
        matched: list[dict[str, Any]] = []
        for row in peak_rows:
            row_type = str(row.get("type", "") or "").strip().lower()
            peak_c = _clean_float(row.get("peak_C"))
            if row_type not in event_type or peak_c is None:
                continue
            if abs(peak_c - center_c) <= tolerance_c:
                matched.append(row)
        return matched

    if item_name == "Tg_without_DCp_step":
        observed = {
            "Tg_C": tg_c,
            "DTg_C": dtg,
            "DCp_JgK": dcp,
        }
        triggered = tg_c is not None and (
            dcp is None
            or abs(dcp) < 0.005
            or dtg is None
            or dtg <= 0
        )
        return triggered, observed

    if item_name == "Tg_outside_supported_window":
        observed = {
            "Tg_C": tg_c,
            "Tg_search_low_C": tg_window_low,
            "Tg_search_high_C": tg_window_high,
        }
        triggered = (
            tg_c is not None
            and tg_window_low is not None
            and tg_window_high is not None
            and (tg_c < tg_window_low or tg_c > tg_window_high)
        )
        return triggered, observed

    if item_name == "melting_without_supported_event":
        melt_rows = _near_event({"melting", "deconv_melting"}, tm_peak, tolerance_c=18.0)
        observed = {
            "Tm_peak_C": tm_peak,
            "DHm_Jg": dhm,
            "supported_melting_component_count": len(supported_melting_components),
            "supported_components": melt_rows,
        }
        triggered = tm_peak is not None and (
            not melt_rows or dhm is None or dhm <= 0
            or len(supported_melting_components) < 1
        )
        return triggered, observed

    if item_name == "cold_crystallization_conflicts_with_melting":
        gap_to_melt_onset = None
        if tcc_peak is not None and tm_onset is not None:
            gap_to_melt_onset = tm_onset - tcc_peak
        observed = {
            "Tcc_peak_C": tcc_peak,
            "Tcc_onset_C": tcc_onset,
            "Tm_onset_C": tm_onset,
            "Tm_peak_C": tm_peak,
            "gap_to_melt_onset_C": gap_to_melt_onset,
        }
        triggered = (
            tcc_peak is not None
            and (
                (tm_onset is not None and tcc_peak >= tm_onset - 5.0)
                or (tm_peak is not None and abs(tm_peak - tcc_peak) < 15.0)
            )
        )
        return triggered, observed

    if item_name == "event_polarity_conflict":
        conflicting_types: list[str] = []
        signed_conflicts: list[dict[str, Any]] = []
        peak_types = {
            str(row.get("type", "") or "").strip().lower()
            for row in peak_rows
            if str(row.get("type", "") or "").strip()
        }
        exo_up_known = isinstance(exo_up, bool)
        exo_sign = 1.0 if exo_up is True else -1.0
        if exo_up_known:
            for row in supported_components or peak_rows:
                row_type = str(row.get("type", "") or "").strip().lower()
                enthalpy = _clean_float(row.get("enthalpy_Jg"))
                if enthalpy is None:
                    continue
                if row_type in {"melting", "deconv_melting"} and enthalpy * exo_sign > 0:
                    signed_conflicts.append({"type": row_type, "enthalpy_Jg": enthalpy})
                if row_type in {"crystallisation", "crystallization", "cold_crystallisation", "cold_crystallization", "recrystallisation", "recrystallization"} and enthalpy * exo_sign < 0:
                    signed_conflicts.append({"type": row_type, "enthalpy_Jg": enthalpy})
        if scan_mode == "heating":
            if tc_peak is not None:
                conflicting_types.append("cooling_crystallisation_present_on_heating")
            if "crystallisation" in peak_types:
                conflicting_types.append("crystallisation_component_on_heating")
        elif scan_mode == "cooling":
            if tm_peak is not None:
                conflicting_types.append("melting_present_on_cooling")
            if {"melting", "deconv_melting"} & peak_types:
                conflicting_types.append("melting_component_on_cooling")
        observed = {
            "scan_mode": scan_mode or None,
            "exo_up": exo_up if exo_up is not None else None,
            "exo_up_known": exo_up_known,
            "peak_types": sorted(peak_types),
            "conflicting_types": conflicting_types,
            "signed_conflicts": signed_conflicts,
        }
        return bool(conflicting_types or signed_conflicts), observed

    if item_name == "peak_components_too_sparse":
        thermal_claims = [
            value
            for value in (tg_c, tm_peak, tc_peak, tcc_peak, xc_pct)
            if value is not None
        ]
        observed = {
            "peak_component_count": len(peak_rows),
            "supported_component_count": len(supported_components),
            "n_peaks": _safe_int(output.get("n_peaks"), default=len(peak_rows)),
            "thermal_claim_count": len(thermal_claims),
        }
        return bool(thermal_claims) and len(supported_components) < 1, observed

    if item_name == "peak_width_nonphysical":
        invalid_rows: list[dict[str, Any]] = []
        for row in peak_rows:
            row_type = str(row.get("type", "") or "").strip().lower()
            onset = _clean_float(row.get("onset_C"))
            end = _clean_float(row.get("end_C"))
            sigma_c = _clean_float(row.get("sigma_C"))
            width = None
            invalid = False
            if onset is not None and end is not None:
                width = end - onset
                if width <= 0 or width < 1.0:
                    invalid = True
                if row_type in {"melting", "deconv_melting"} and width > max_melt_width:
                    invalid = True
                if width > 80.0:
                    invalid = True
            if sigma_c is not None and sigma_c <= 0:
                invalid = True
            if invalid:
                bad = dict(row)
                if width is not None:
                    bad["width_C"] = width
                invalid_rows.append(bad)
        observed = {
            "max_melting_peak_width_C": max_melt_width,
            "invalid_components": invalid_rows,
        }
        return bool(invalid_rows), observed

    melt_rows = _near_event({"melting", "deconv_melting"}, tm_peak, tolerance_c=18.0)
    observed = {
        "Xc_pct": xc_pct,
        "DHm_Jg": dhm,
        "DHcc_Jg": dhcc,
        "supported_melting_components": melt_rows,
    }
    triggered = xc_pct is not None and xc_pct > 0 and (
        dhm is None
        or dhm <= 0
        or not melt_rows
        or len(supported_melting_components) < 1
    )
    return triggered, observed


__all__ = ["_evaluate_dsc_event_constraint"]
