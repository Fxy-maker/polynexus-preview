from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _non_empty_mapping


def _nmr_symptoms_from_constraints(constraints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = {
        "nmr_low_peak_count",
        "nmr_low_snr",
        "nmr_broad_linewidth",
        "nmr_weak_assignment",
        "nmr_solvent_risk",
        "nmr_xc_assignment_missing",
        "nmr_xc_assignment_limited",
    }
    symptoms: list[dict[str, Any]] = []
    for item in constraints:
        name = str(item.get("name", "") or "").strip()
        if name not in names or not item.get("triggered"):
            continue
        symptoms.append(
            _non_empty_mapping(
                [
                    ("name", name),
                    ("severity", item.get("severity") or "WARN"),
                    ("summary", item.get("description")),
                    ("target", item.get("field") or name),
                    ("observed", item.get("observed")),
                ]
            )
        )
    return symptoms


def _nmr_symptom_bridge_lines(symptom: dict[str, Any] | None) -> list[str]:
    if not isinstance(symptom, dict):
        return []
    name = str(symptom.get("name", "") or "").strip()
    mapping = {
        "nmr_low_peak_count": "nmr_low_peak_count -> review peak threshold and deconvolution settings before trusting assignments",
        "nmr_low_snr": "nmr_low_snr -> review baseline correction and peak threshold before trusting assignments",
        "nmr_broad_linewidth": "nmr_broad_linewidth -> review baseline, apodization, and peak fitting before trusting phase assignment",
        "nmr_weak_assignment": "nmr_weak_assignment -> add or verify peak assignments before promoting structural conclusions",
        "nmr_solvent_risk": "nmr_solvent_risk -> exclude likely solvent peaks before using assignment evidence",
        "nmr_xc_assignment_missing": "nmr_xc_assignment_missing -> assign crystalline and amorphous peaks before trusting NMR Xc",
        "nmr_xc_assignment_limited": "nmr_xc_assignment_limited -> keep NMR Xc diagnostic until crystalline and amorphous peaks are assigned",
    }
    return [mapping[name]] if name in mapping else []


_NMR_CONSTRAINT_NAMES = {
    "nmr_low_peak_count",
    "nmr_low_snr",
    "nmr_broad_linewidth",
    "nmr_weak_assignment",
    "nmr_solvent_risk",
    "nmr_xc_assignment_missing",
    "nmr_xc_assignment_limited",
}


def _evaluate_nmr_constraint(
    item_name: str,
    output: dict[str, Any],
    residual_key: str | None = None,
) -> tuple[bool, Any]:
    del residual_key

    from .analysis_evidence_nmr import _nmr_peak_rows

    peak_rows = _nmr_peak_rows(output)
    if item_name == "nmr_low_peak_count":
        n_peaks = _clean_float(output.get("n_peaks"))
        return n_peaks is not None and n_peaks < 2, n_peaks
    if item_name == "nmr_low_snr":
        snr = _clean_float(output.get("median_snr", output.get("snr")))
        return snr is not None and snr < 5.0, snr
    if item_name == "nmr_broad_linewidth":
        linewidth = _clean_float(output.get("mean_fwhm_ppm", output.get("linewidth_ppm")))
        return linewidth is not None and linewidth > 20.0, linewidth
    if item_name == "nmr_weak_assignment":
        assigned_count = sum(1 for row in peak_rows if row.get("assignment"))
        match_count = _clean_float(output.get("n_matches"))
        n_peaks = _clean_float(output.get("n_peaks"))
        observed = {"assigned_peak_count": assigned_count, "n_matches": match_count, "n_peaks": n_peaks}
        triggered = bool(
            (peak_rows and n_peaks is not None and n_peaks > 0 and assigned_count == 0)
            or (match_count is not None and match_count <= 0)
        )
        return triggered, observed
    if item_name == "nmr_solvent_risk":
        solvent_peaks = [
            {"index": row.get("index"), "possible_solvent": row.get("possible_solvent")}
            for row in peak_rows
            if row.get("possible_solvent")
        ]
        return bool(solvent_peaks), solvent_peaks
    if item_name == "nmr_xc_assignment_missing":
        phases = {str(row.get("phase", "") or "").lower() for row in peak_rows if row.get("phase")}
        xc_method = str(output.get("Xc_method") or "").strip()
        needs_assignment = xc_method == "requires_crystalline_amorphous_assignment" and output.get("Xc_pct") is None
        has_crystalline = bool(phases & {"c", "crystalline"})
        has_amorphous = bool(phases & {"a", "amorphous"})
        observed = {"Xc_method": xc_method or None, "phases": sorted(phases)}
        return bool(needs_assignment and not (has_crystalline and has_amorphous)), observed
    if item_name == "nmr_xc_assignment_limited":
        phases = {str(row.get("phase", "") or "").lower() for row in peak_rows if row.get("phase")}
        xc_method = str(output.get("Xc_method") or "").strip()
        phase_count = _clean_float(output.get("phase_assignment_count"))
        if phase_count is not None and phase_count <= 0:
            phases = set()
        has_crystalline = bool(phases & {"c", "crystalline"})
        has_amorphous = bool(phases & {"a", "amorphous"})
        observed = {
            "Xc_method": xc_method or None,
            "Xc_pct": _clean_float(output.get("Xc_pct")),
            "phase_assignment_count": phase_count,
            "phases": sorted(phases),
        }
        triggered = bool(
            output.get("Xc_pct") is not None
            and xc_method == "requires_crystalline_amorphous_assignment"
            and not (has_crystalline and has_amorphous)
        )
        return triggered, observed
    return False, None
