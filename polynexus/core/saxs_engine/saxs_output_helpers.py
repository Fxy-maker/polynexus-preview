from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def _csv_number(value) -> float:
    return round(float(value), 10)


def _finite_csv(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return _csv_number(number) if np.isfinite(number) else ""


def _json_number(value) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def _detector_provenance_csv_fields(report: Any) -> dict[str, Any]:
    """Flatten existing detector provenance for table/CSV consumers only."""
    fields: dict[str, Any] = {
        "Detector_source_kind": None,
        "Detector_quality_level": None,
        "Detector_reason_codes": None,
        "Geometry_provenance_source": None,
        "Geometry_field_sources": None,
        "Geometry_provenance_validity": None,
        "Mask_provenance_source": None,
        "Mask_configured": None,
        "Mask_shape": None,
        "Mask_provenance_validity": None,
    }
    if not isinstance(report, Mapping):
        return fields

    for output_key, report_key in (
        ("Detector_source_kind", "source_kind"),
        ("Detector_quality_level", "level"),
    ):
        value = report.get(report_key)
        fields[output_key] = getattr(value, "value", value)

    reasons = report.get("reason_codes")
    if isinstance(reasons, str):
        fields["Detector_reason_codes"] = reasons
    elif isinstance(reasons, (list, tuple)):
        fields["Detector_reason_codes"] = "|".join(str(item) for item in reasons)

    geometry = report.get("geometry_provenance")
    if isinstance(geometry, Mapping):
        fields["Geometry_provenance_source"] = geometry.get("source")
        fields["Geometry_provenance_validity"] = geometry.get("validity")
        source_fields = geometry.get("field_sources")
        if isinstance(source_fields, Mapping):
            fields["Geometry_field_sources"] = "|".join(
                f"{key}:{source_fields[key]}"
                for key in sorted(source_fields, key=str)
            ) or None

    mask = report.get("mask_provenance")
    if isinstance(mask, Mapping):
        fields["Mask_provenance_source"] = mask.get("source")
        configured = mask.get("configured")
        fields["Mask_configured"] = configured if isinstance(configured, bool) else None
        fields["Mask_provenance_validity"] = mask.get("validity")
        shape = mask.get("shape")
        if isinstance(shape, (list, tuple, np.ndarray)) and len(shape) == 2:
            try:
                fields["Mask_shape"] = f"{int(shape[0])}x{int(shape[1])}"
            except (TypeError, ValueError):
                fields["Mask_shape"] = None
    return fields


def _result_effective_lc_value(result) -> float:
    """Return the effective lc value for plotting when batch metadata provides one."""
    final = getattr(result, "final_parameters", None)
    if isinstance(final, dict) and final:
        for key in ("lc_nm_effective", "lc_effective_nm"):
            if key in final:
                value = _json_number(final.get(key))
                return float(value) if value is not None else np.nan

    sp = getattr(result, "structure", None)
    if sp is not None and np.isfinite(getattr(sp, "lc", np.nan)):
        return float(sp.lc)
    return np.nan


def export_parameters_csv(
    result_or_dict,
    output_dir: str,
    filename: str = "saxs_parameters.csv",
) -> str:
    """Export analysis parameters to CSV file."""
    import os

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)

    if hasattr(result_or_dict, "structure"):
        d = _result_to_params_dict(result_or_dict)
    else:
        d = result_or_dict
    df = pd.DataFrame([{k: v for k, v in d.items() if not k.startswith("_")}])
    df.to_csv(path, index=False)
    return str(path)


def export_1d_profile(
    q: np.ndarray,
    I: np.ndarray,  # noqa: E741 - preserve the public SAXS intensity parameter name
    output_dir: str,
    filename: str = "saxs_1d_profile.csv",
    I_smooth: Optional[np.ndarray] = None,
) -> str:
    """Export 1D scattering curve data."""
    import os

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)

    data = {"q_nm1": q, "I_au": I}
    if I_smooth is not None and len(I_smooth) == len(I):
        data["I_smooth_au"] = I_smooth

    df = pd.DataFrame(data)
    df.to_csv(path, index=False)
    return str(path)


def export_strain_series_csv(
    strain_result,
    output_dir: str,
    filename: str = "strain_series_parameters.csv",
) -> str:
    """Export complete strain series data."""
    import os

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)

    df = strain_result.to_dataframe()
    df.to_csv(path, index=False)
    return str(path)


def export_temp_series_csv(
    temp_result,
    output_dir: str,
    filename: str = "temperature_series_parameters.csv",
) -> str:
    """Export complete temperature series data."""
    import os

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)

    df = temp_result.to_dataframe()
    df.to_csv(path, index=False)
    return str(path)


def _result_to_params_dict(result) -> Dict:
    """Extract a flat parameters dict from a SAXSResult for CSV export."""
    sp = result.structure
    lp = result.long_period
    final = getattr(result, "final_parameters", None)
    status_fields = (
        "lc_method",
        "calibrated_fallback_active",
        "calibrated_fallback_reason",
        "calibration_skipped_reason",
        "melting_window_status",
        "melting_window_reason",
        "lc_reliability_status",
        "lc_reliability_reason",
    )
    if isinstance(final, dict) and final:
        d = {k: v for k, v in final.items() if not str(k).startswith("_")}
        d.setdefault("label", result.label)
        for field in status_fields:
            if field not in d:
                value = getattr(result, field, None)
                if value not in (None, ""):
                    d[field] = value
        if lp is not None:
            d.setdefault("L_bragg", round(lp.L_bragg, 2) if np.isfinite(lp.L_bragg) else None)
            d.setdefault("L_lorentz", round(lp.L_lorentz, 2) if np.isfinite(lp.L_lorentz) else None)
            d.setdefault("L_confidence", round(lp.L_confidence, 2) if np.isfinite(lp.L_confidence) else None)
            d.setdefault("L_method", lp.method_used)
        if sp is not None:
            d.setdefault(
                "phi_c_invariant",
                round(getattr(sp, "phi_c_invariant", np.nan), 3)
                if np.isfinite(getattr(sp, "phi_c_invariant", np.nan))
                else None,
            )
            d.setdefault("Sv_nm1", f"{sp.Sv:.4e}" if np.isfinite(getattr(sp, "Sv", np.nan)) else None)
            d.setdefault(
                "lc_tangent_nm",
                round(getattr(sp, "lc_tangent_nm", np.nan), 2)
                if np.isfinite(getattr(sp, "lc_tangent_nm", np.nan))
                else None,
            )
            d.setdefault(
                "lc_gamma_min_nm",
                round(getattr(sp, "lc_gamma_min_nm", np.nan), 2)
                if np.isfinite(getattr(sp, "lc_gamma_min_nm", np.nan))
                else None,
            )
        d.setdefault(
            "L_pyfai_nm",
            round(float(getattr(result, "L_bragg_pyfai", np.nan)), 2)
            if np.isfinite(getattr(result, "L_bragg_pyfai", np.nan))
            else None,
        )
        d.setdefault(
            "q_peak_diff_pct",
            getattr(result, "pyfai_q_peak_diff_pct", None)
            if np.isfinite(getattr(result, "pyfai_q_peak_diff_pct", np.nan))
            else None,
        )
        d.setdefault("L_sas_nm", final.get("L_sas_nm"))
        d.setdefault("lc_sas_nm", final.get("lc_sas_nm"))
        d.setdefault("Xc_sas", final.get("Xc_sas"))
        d.setdefault("sasmodels_R2", final.get("sasmodels_R2"))
        d.setdefault("sasmodels_model_used", getattr(result, "sasmodels_model_used", "") or "")
        d.setdefault(
            "q_peak_snr",
            round(float(getattr(result, "q_peak_snr", np.nan)), 2)
            if np.isfinite(getattr(result, "q_peak_snr", np.nan))
            else None,
        )
        d.setdefault(
            "effective_q_min",
            round(float(getattr(result, "effective_q_min", np.nan)), 3)
            if np.isfinite(getattr(result, "effective_q_min", np.nan))
            else None,
        )
        d.setdefault("Q_star_valid", bool(getattr(result, "Q_star_valid", True)))
        d.setdefault("quality_flag", getattr(result, "quality_flag", "") or "")
        d.setdefault("validation_summary", getattr(result, "validation_summary", "") or "")
        for field in status_fields:
            value = getattr(result, field, None)
            if value not in (None, "") and field not in d:
                d[field] = value
        d.update(
            _detector_provenance_csv_fields(
                getattr(result, "raw_detector_quality_report", None)
            )
        )
        return d

    d = {
        "label": result.label,
        "L_nm": round(sp.L, 2) if sp and np.isfinite(sp.L) else None,
        "lc_nm": round(sp.lc, 2) if sp and np.isfinite(sp.lc) else None,
        "la_nm": round(sp.la, 2) if sp and np.isfinite(sp.la) else None,
        "phi_c": round(sp.phi_c, 3) if sp and np.isfinite(sp.phi_c) else None,
        "phi_c_invariant": round(getattr(sp, "phi_c_invariant", np.nan), 3) if sp and np.isfinite(getattr(sp, "phi_c_invariant", np.nan)) else None,
        "Q_invariant": f"{sp.Q_invariant:.4e}" if sp and np.isfinite(sp.Q_invariant) else None,
        "Q_star_valid": bool(getattr(result, "Q_star_valid", True)),
        "Sv_nm1": f"{sp.Sv:.4e}" if sp and np.isfinite(sp.Sv) else None,
        "L_bragg": round(lp.L_bragg, 2) if lp and np.isfinite(lp.L_bragg) else None,
        "L_lorentz": round(lp.L_lorentz, 2) if lp and np.isfinite(lp.L_lorentz) else None,
        "L_confidence": round(lp.L_confidence, 2) if lp and np.isfinite(lp.L_confidence) else None,
        "lc_confidence": round(getattr(sp, "confidence_lc", np.nan), 2) if sp and np.isfinite(getattr(sp, "confidence_lc", np.nan)) else None,
        "lc_tangent_nm": round(getattr(sp, "lc_tangent_nm", np.nan), 2) if sp and np.isfinite(getattr(sp, "lc_tangent_nm", np.nan)) else None,
        "lc_gamma_min_nm": round(getattr(sp, "lc_gamma_min_nm", np.nan), 2) if sp and np.isfinite(getattr(sp, "lc_gamma_min_nm", np.nan)) else None,
        "L_pyfai_nm": round(float(getattr(result, "L_bragg_pyfai", np.nan)), 2) if np.isfinite(getattr(result, "L_bragg_pyfai", np.nan)) else None,
        "q_peak_diff_pct": getattr(result, "pyfai_q_peak_diff_pct", None) if np.isfinite(getattr(result, "pyfai_q_peak_diff_pct", np.nan)) else None,
        "q_peak_snr": round(float(getattr(result, "q_peak_snr", np.nan)), 2) if np.isfinite(getattr(result, "q_peak_snr", np.nan)) else None,
        "L_sas_nm": final.get("L_sas_nm") if isinstance(final, dict) else None,
        "lc_sas_nm": final.get("lc_sas_nm") if isinstance(final, dict) else None,
        "Xc_sas": final.get("Xc_sas") if isinstance(final, dict) else None,
        "sasmodels_R2": final.get("sasmodels_R2") if isinstance(final, dict) else None,
        "sasmodels_model_used": getattr(result, "sasmodels_model_used", "") or "",
        "quality_flag": getattr(result, "quality_flag", "") or "",
        "validation_summary": getattr(result, "validation_summary", "") or "",
    }
    for field in status_fields:
        value = getattr(result, field, None)
        if value not in (None, "") and field not in d:
            d[field] = value
    d.update(
        _detector_provenance_csv_fields(
            getattr(result, "raw_detector_quality_report", None)
        )
    )
    return d
