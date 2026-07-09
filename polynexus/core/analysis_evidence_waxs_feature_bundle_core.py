from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _non_empty_mapping
from .analysis_evidence_waxs_metrics import _waxs_peak_metrics, _waxs_structure_metrics


def _waxs_core_feature_evidence(
    output: dict[str, Any],
    *,
    config_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config_snapshot = config_snapshot if isinstance(config_snapshot, dict) else {}
    waxs_metrics = _waxs_peak_metrics(output)
    peak_count = waxs_metrics.get("peak_count")
    peak_positions = waxs_metrics.get("peak_positions", [])
    peak_widths = waxs_metrics.get("peak_widths", [])
    peak_areas = waxs_metrics.get("peak_areas", [])
    peak_evidence = _non_empty_mapping(
        [
            ("peak_count", peak_count if peak_count is not None else None),
            ("peak_positions", peak_positions if peak_positions else None),
            ("peak_widths", peak_widths if peak_widths else None),
            ("peak_areas", peak_areas if peak_areas else None),
            ("peak_gap_spread", _clean_float(waxs_metrics.get("peak_gap_spread"))),
            ("peak_width_spread", _clean_float(waxs_metrics.get("peak_width_spread"))),
            ("peak_area_ratio", _clean_float(waxs_metrics.get("peak_area_ratio"))),
            ("scherrer_support_peaks", peak_count if peak_count is not None else None),
        ]
    )
    background_evidence = _non_empty_mapping(
        [
            (
                "background_method",
                str(
                    output.get(
                        "background_method",
                        config_snapshot.get("background_method", ""),
                    )
                    or ""
                ).strip()
                or None,
            ),
            (
                "amorphous_subtraction",
                str(
                    output.get(
                        "amorphous_subtraction",
                        config_snapshot.get("amorphous_subtraction", ""),
                    )
                    or ""
                ).strip()
                or None,
            ),
            (
                "amorphous_n_peaks",
                _clean_float(
                    output.get(
                        "amorphous_n_peaks",
                        config_snapshot.get("amorphous_n_peaks"),
                    )
                ),
            ),
            (
                "two_theta_offset",
                _clean_float(
                    output.get(
                        "two_theta_offset",
                        config_snapshot.get("two_theta_offset"),
                    )
                ),
            ),
        ]
    )
    phase_evidence = _non_empty_mapping(
        [
            ("Xc_pct", _clean_float(output.get("Xc_pct", output.get("Xc")))),
            (
                "crystallinity_method",
                str(
                    output.get(
                        "crystallinity_method",
                        output.get(
                            "Xc_method",
                            config_snapshot.get("crystallinity_method", ""),
                        ),
                    )
                    or ""
                ).strip()
                or None,
            ),
            ("crystal_system", str(output.get("crystal_system", "") or "").strip() or None),
            (
                "unit_cell_params_present",
                bool(output.get("unit_cell_params", config_snapshot.get("unit_cell_params", {})))
                or None,
            ),
            ("D_Scherrer_nm", _clean_float(output.get("D_Scherrer_nm"))),
            ("D_uncertainty_nm", _clean_float(output.get("D_uncertainty_nm"))),
            ("D_WH_nm", _clean_float(output.get("D_WH_nm"))),
            ("D_WH_uncertainty_nm", _clean_float(output.get("D_WH_uncertainty_nm"))),
            ("epsilon_WH_pct", _clean_float(output.get("epsilon_WH_pct"))),
            ("epsilon_WH_uncertainty_pct", _clean_float(output.get("epsilon_WH_uncertainty_pct"))),
            ("WH_fit_r_squared", _clean_float(output.get("WH_fit_r_squared"))),
            (
                "size_reliability_status",
                str(output.get("size_reliability_status", "") or "").strip() or None,
            ),
            (
                "instrument_broadening_model",
                str(output.get("instrument_broadening_model", "") or "").strip() or None,
            ),
        ]
    )
    structure_evidence = _waxs_structure_metrics(
        output,
        peak_metrics=waxs_metrics,
        config_snapshot=config_snapshot,
    )

    return {
        "peak_metrics": waxs_metrics,
        "peak_evidence": peak_evidence,
        "background_evidence": background_evidence,
        "phase_evidence": phase_evidence,
        "structure_evidence": structure_evidence,
        "peak_count": peak_count,
        "structure_support_score": _clean_float(structure_evidence.get("structure_support_score")),
    }


__all__ = ["_waxs_core_feature_evidence"]
