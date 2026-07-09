from __future__ import annotations

import math
from typing import Any

import numpy as np

from polynexus.core.dsc_engine import aggregate_dsc_result_metrics
from polynexus.core.dsc_residual_analyzer import DSCResidualAnalyzer, DSCResidualPattern
from polynexus.core.ir_residual_analyzer import IRResidualAnalyzer, IRResidualPattern
from polynexus.core.residual_analyzer import ResidualPattern
from polynexus.core.saxs_residual_analyzer import SAXSResidualAnalyzer, SAXSResidualPattern
from polynexus.core.waxs_residual_analyzer import WAXSResidualAnalyzer


def _output_parameters(self: Any, engine: Any) -> dict[str, Any]:
    if self.technique == "dsc":
        return self._dsc_output_parameters(engine)
    if self.technique == "saxs":
        return self._saxs_output_parameters(engine)
    if self.technique == "ir":
        return self._ir_output_parameters(engine)
    if self.technique == "nmr":
        return self._nmr_output_parameters(engine)
    output = dict(getattr(engine.result, "parameters", {}) or {})
    waxs_results = getattr(engine, "_results", []) or []
    if waxs_results:
        first = waxs_results[0]
        peaks = []
        for peak in getattr(first, "peaks", []) or []:
            item = {
                "center": peak.get("two_theta"),
                "fwhm": peak.get("fwhm_deg"),
                "area": peak.get("area"),
                "hkl": peak.get("hkl", ""),
            }
            peaks.append({k: self._to_plain_value(v) for k, v in item.items() if v is not None})
        if peaks:
            output["peaks"] = peaks
            output["peak_centers"] = [peak["center"] for peak in peaks if "center" in peak]
        two_theta = getattr(first, "two_theta", [])
        if len(two_theta) > 0:
            output["x_min"] = float(two_theta[0])
            output["x_max"] = float(two_theta[-1])
        if hasattr(first, "r_squared"):
            output["r_squared"] = self._safe_float(getattr(first, "r_squared"))
    return self._to_plain_value(output)


def _dsc_output_parameters(self: Any, engine: Any) -> dict[str, Any]:
    output = self._flatten_dsc_parameters(dict(getattr(engine.result, "parameters", {}) or {}))
    dsc_results = getattr(engine, "_results", []) or []
    if dsc_results:
        first = dsc_results[0]
        aggregate = aggregate_dsc_result_metrics(dsc_results)
        output.update(
            {
                "scan_mode": getattr(first, "technique", None),
                "Tg_C": getattr(first, "Tg_C", None),
                "Tg_method": getattr(first, "Tg_method", None),
                "DTg_C": getattr(first, "DTg_C", None),
                "DCp_JgK": getattr(first, "DCp_JgK", None),
                "Tm_onset_C": getattr(first, "Tm_onset_C", None),
                "Tm_peak_C": getattr(first, "Tm_peak_C", None),
                "Tm_end_C": getattr(first, "Tm_end_C", None),
                "Tc_onset_C": getattr(first, "Tc_onset_C", None),
                "Tc_peak_C": getattr(first, "Tc_peak_C", None),
                "Tc_end_C": getattr(first, "Tc_end_C", None),
                "Tcc_onset_C": getattr(first, "Tcc_onset_C", None),
                "Tcc_peak_C": getattr(first, "Tcc_peak_C", None),
                "DHm_Jg": getattr(first, "DHm_Jg", None),
                "DHc_Jg": getattr(first, "DHc_Jg", None),
                "DHcc_Jg": getattr(first, "DHcc_Jg", None),
                "Xc_pct": getattr(first, "Xc_pct", None),
                "quality_score": aggregate.get("quality_score"),
                "r_squared": aggregate.get("r_squared"),
                "fit_rmse": aggregate.get("fit_rmse"),
                "scan_r_squared": aggregate.get("scan_r_squared"),
                "r_squared_method": aggregate.get("r_squared_method"),
                "n_peaks": len(getattr(first, "peak_components", []) or []),
                "peak_components": getattr(first, "peak_components", []),
            }
        )
        output["tm"] = output.get("Tm_peak_C")
        output["tc"] = output.get("Tc_peak_C")
        if output["tc"] is None or self._is_nan(output["tc"]):
            output["tc"] = output.get("Tcc_peak_C")
        output["delta_hm"] = output.get("DHm_Jg")
        output["xc"] = output.get("Xc_pct")
        output["raw_score"] = output.get("quality_score")
        if len(getattr(first, "T", [])) > 0:
            output["x_min"] = float(first.T[0])
            output["x_max"] = float(first.T[-1])
    return self._to_plain_value({key: value for key, value in output.items() if value is not None})


def _nmr_output_parameters(self: Any, engine: Any) -> dict[str, Any]:
    output = self._flatten_nmr_parameters(dict(getattr(engine.result, "parameters", {}) or {}))
    if not output:
        output = self._flatten_nmr_parameters(dict(engine.get_parameters() or {}))
    nmr_results = getattr(engine, "_results", []) or []
    if nmr_results:
        first = nmr_results[0]
        peaks = []
        for peak in getattr(first, "peaks", []) or []:
            item = {
                "ppm": peak.get("ppm"),
                "height": peak.get("height"),
                "area": peak.get("area"),
                "fwhm_ppm": peak.get("fwhm_ppm"),
                "assignment": peak.get("assignment", ""),
                "region": peak.get("region", ""),
                "snr": peak.get("snr"),
            }
            peaks.append({k: self._to_plain_value(v) for k, v in item.items() if v is not None})
        r_squared = self._safe_float(getattr(first, "r_squared", output.get("r_squared", 0.0)))
        median_snr = self._safe_float(getattr(first, "median_snr", output.get("median_snr", 0.0)))
        quality_score = r_squared if r_squared != 0.0 else max(0.0, min(1.0, median_snr / 20.0))
        output.update(
            {
                "nucleus": getattr(first, "nucleus", output.get("nucleus")),
                "sample_state": getattr(first, "sample_state", output.get("sample_state")),
                "n_peaks": getattr(first, "n_peaks", output.get("n_peaks")),
                "Xc_pct": getattr(first, "Xc_pct", output.get("Xc_pct")),
                "xc": getattr(first, "Xc_pct", output.get("Xc_pct")),
                "Xc_method": getattr(first, "Xc_method", output.get("Xc_method", "")),
                "peak_area_total": getattr(first, "peak_area_total", output.get("peak_area_total")),
                "dominant_peak_ppm": getattr(first, "dominant_peak_ppm", output.get("dominant_peak_ppm")),
                "mean_fwhm_ppm": getattr(first, "mean_fwhm_ppm", output.get("mean_fwhm_ppm")),
                "median_snr": getattr(first, "median_snr", output.get("median_snr")),
                "r_squared": r_squared,
                "quality_score": quality_score,
                "raw_score": quality_score,
                "r_squared_method": "nmr_peak_deconvolution_r2",
            }
        )
        if peaks:
            output["peaks"] = peaks
            output["peak_centers"] = [peak["ppm"] for peak in peaks if "ppm" in peak]
        ppm = getattr(first, "ppm", [])
        if len(ppm) > 0:
            output["x_min"] = float(np.nanmin(ppm))
            output["x_max"] = float(np.nanmax(ppm))
    return self._to_plain_value({key: value for key, value in output.items() if value is not None})


def _ir_output_parameters(self: Any, engine: Any) -> dict[str, Any]:
    output = self._flatten_ir_parameters(dict(getattr(engine.result, "parameters", {}) or {}))
    if not output:
        output = self._flatten_ir_parameters(dict(engine.get_parameters() or {}))
    ir_results = getattr(engine, "_results", []) or []
    if ir_results:
        first = ir_results[0]
        peaks = []
        for peak in getattr(first, "peaks", []) or []:
            item = {
                "wavenumber": peak.get("wavenumber"),
                "height": peak.get("height"),
                "prominence": peak.get("prominence"),
                "area": peak.get("area"),
                "fwhm_cm1": peak.get("fwhm_cm1"),
                "assignment": peak.get("assignment", ""),
                "ref_wavenumber": peak.get("ref_wavenumber"),
            }
            peaks.append({k: self._to_plain_value(v) for k, v in item.items() if v is not None})

        r_squared = self._safe_float(getattr(first, "r_squared", output.get("r_squared", 0.0)))
        polymer_score = self._safe_float(getattr(first, "polymer_score", output.get("polymer_score", 1.0)))
        if polymer_score == 0.0 and getattr(first, "polymer_name", ""):
            polymer_score = 1.0
        output.update(
            {
                "n_peaks": getattr(first, "n_peaks", output.get("n_peaks")),
                "polymer_name": getattr(first, "polymer_name", output.get("polymer")),
                "polymer_score": polymer_score,
                "quality_score": polymer_score,
                "raw_score": polymer_score,
                "Xc_pct": getattr(first, "Xc_pct", output.get("Xc_pct")),
                "xc": getattr(first, "Xc_pct", output.get("Xc_pct")),
                "Xc_method": getattr(first, "Xc_method", output.get("Xc_method", "")),
                "r_squared": r_squared,
                "r_squared_method": "ir_peak_region_fit_r2",
            }
        )
        if peaks:
            output["peaks"] = peaks
            output["peak_centers"] = [peak["wavenumber"] for peak in peaks if "wavenumber" in peak]
        wn = getattr(first, "wavenumber", [])
        if len(wn) > 0:
            output["x_min"] = float(np.nanmin(wn))
            output["x_max"] = float(np.nanmax(wn))
    return self._to_plain_value({key: value for key, value in output.items() if value is not None})


def _saxs_output_parameters(self: Any, engine: Any) -> dict[str, Any]:
    output = dict(getattr(engine.result, "parameters", {}) or {})
    if not output:
        output = dict(engine.get_parameters() or {})
    analysis = getattr(engine, "_analysis", None)
    batch_results = getattr(engine, "_batch_results", []) or []
    if analysis is None and batch_results:
        analysis = batch_results[0]

    quality_score = self._saxs_score(analysis, output)
    r_squared = self._safe_float(getattr(analysis, "r_squared", None)) if analysis is not None else 0.0
    if analysis is None or not math.isfinite(r_squared):
        r_squared = quality_score
    output["r_squared"] = r_squared
    output["quality_score"] = (
        self._safe_float(getattr(analysis, "quality_score", quality_score))
        if analysis is not None
        else quality_score
    )
    output["raw_score"] = output["quality_score"]
    output["r_squared_method"] = getattr(analysis, "r_squared_method", "") or "saxs_peak_region_fit_r2"
    output["fit_rmse"] = getattr(analysis, "fit_rmse", None) if analysis is not None else None
    output["fit_regions"] = getattr(analysis, "fit_regions", None) if analysis is not None else None
    if "Xc" in output and "Xc_pct" not in output:
        xc = self._safe_float(output.get("Xc"))
        output["Xc_pct"] = xc * 100.0 if 0.0 <= xc <= 1.0 else xc
        output["xc"] = output["Xc_pct"]
    if analysis is not None:
        q = getattr(analysis, "q", [])
        if len(q) > 0:
            output["x_min"] = float(q[0])
            output["x_max"] = float(q[-1])
        condition_value = getattr(analysis, "condition_value", None)
        if condition_value is not None:
            output["condition_value"] = condition_value
        lp = getattr(analysis, "long_period", None)
        if lp is not None:
            output["L_confidence"] = getattr(lp, "L_confidence", None)
            output["L_bragg"] = getattr(lp, "L_bragg", None)
            output["L_lorentz"] = getattr(lp, "L_lorentz", None)
            output["L_corr_peak"] = getattr(lp, "L_corr_peak", None)
        output["q_peak_snr"] = getattr(analysis, "q_peak_snr", None)
        output["quality_flag"] = getattr(analysis, "quality_flag", "")
        output["validation_summary"] = getattr(analysis, "validation_summary", "")
    return self._to_plain_value({key: value for key, value in output.items() if value is not None})


def _saxs_score(self: Any, analysis: Any, output: dict[str, Any]) -> float:
    sas_r2 = self._safe_float(output.get("sasmodels_R2"))
    if math.isfinite(sas_r2) and sas_r2 > 0:
        return max(0.0, min(1.0, sas_r2))
    if analysis is not None:
        lp = getattr(analysis, "long_period", None)
        confidence = self._safe_float(getattr(lp, "L_confidence", 0.0)) if lp is not None else 0.0
        if confidence > 0:
            return max(0.0, min(1.0, confidence))
    snr = self._safe_float(output.get("q_peak_snr"))
    if snr > 0:
        return max(0.0, min(1.0, snr / 20.0))
    return 0.0


def _residual_pattern(self: Any, engine: Any) -> dict[str, Any]:
    if self.technique == "dsc":
        return self._dsc_residual_pattern(engine)
    if self.technique == "saxs":
        return self._saxs_residual_pattern(engine)
    if self.technique == "ir":
        return self._ir_residual_pattern(engine)
    if self.technique == "nmr":
        return self._nmr_residual_pattern(engine)
    waxs_results = getattr(engine, "_results", []) or []
    if not waxs_results:
        return self._empty_residual_pattern().to_dict()
    first = waxs_results[0]
    y_obs = getattr(first, "I", [])
    y_fit = getattr(first, "I_fit", [])
    two_theta = getattr(first, "two_theta", [])
    if len(y_obs) == 0 or len(y_fit) == 0 or len(two_theta) == 0:
        return self._empty_residual_pattern().to_dict()
    context = {
        "output_parameters": self._output_parameters(engine),
        "config_snapshot": self._config_snapshot(engine),
    }
    return WAXSResidualAnalyzer.analyze(y_obs, y_fit, two_theta, context=context).to_dict()


def _dsc_residual_pattern(self: Any, engine: Any) -> dict[str, Any]:
    dsc_results = getattr(engine, "_results", []) or []
    if not dsc_results:
        return DSCResidualPattern(
            rmse=0.0,
            r_squared=0.0,
            residual_type="random",
            max_residual_region="unknown",
            peak_regions=[],
            summary="DSC 残差数据不足，无法判断残差模式。",
        ).to_dict()
    result = self._select_dsc_residual_result(dsc_results)
    fit = getattr(result, "HF_fit", [])
    if len(fit) == len(getattr(result, "HF", [])):
        return DSCResidualAnalyzer.analyze(
            getattr(result, "T", []),
            getattr(result, "HF", []),
            fit,
        ).to_dict()
    return DSCResidualAnalyzer.analyze(getattr(result, "T", []), getattr(result, "HF", [])).to_dict()


def _saxs_residual_pattern(self: Any, engine: Any) -> dict[str, Any]:
    analysis = getattr(engine, "_analysis", None)
    batch_results = getattr(engine, "_batch_results", []) or []
    if analysis is None and batch_results:
        analysis = batch_results[0]
    if analysis is None:
        return SAXSResidualPattern(
            rmse=0.0,
            r_squared=0.0,
            residual_type="random",
            max_residual_region="unknown",
            peak_regions=[],
            summary="SAXS 残差数据不足，无法判断残差模式。",
        ).to_dict()
    q = getattr(analysis, "q", [])
    intensity = getattr(analysis, "I", [])
    fit = getattr(analysis, "I_smooth", None)
    return SAXSResidualAnalyzer.analyze(q, intensity, fit).to_dict()


def _ir_residual_pattern(self: Any, engine: Any) -> dict[str, Any]:
    ir_results = getattr(engine, "_results", []) or []
    if not ir_results:
        return IRResidualPattern(
            rmse=0.0,
            r_squared=0.0,
            residual_type="random",
            max_residual_region="unknown",
            peak_regions=[],
            summary="IR residual data is insufficient for pattern classification.",
        ).to_dict()
    first = ir_results[0]
    return IRResidualAnalyzer.analyze(
        getattr(first, "wavenumber", []),
        getattr(first, "absorbance", []),
        getattr(first, "absorbance_fit", None),
    ).to_dict()


def _nmr_residual_pattern(self: Any, engine: Any) -> dict[str, Any]:
    nmr_results = getattr(engine, "_results", []) or []
    if not nmr_results:
        return {
            "rmse": 0.0,
            "r_squared": 0.0,
            "residual_type": "random",
            "max_residual_region": "unknown",
            "peak_regions": [],
            "summary": "NMR residual data is insufficient for pattern classification.",
        }
    first = nmr_results[0]
    ppm = np.asarray(getattr(first, "ppm", []), dtype=float)
    y = np.asarray(getattr(first, "intensity", []), dtype=float)
    fit = np.asarray(getattr(first, "intensity_fit", []), dtype=float)
    if len(ppm) == 0 or len(y) == 0 or len(fit) != len(y):
        region = "unknown"
        residual_type = "random"
        rmse = 0.0
        r_squared = self._safe_float(getattr(first, "r_squared", 0.0))
        summary = "NMR fit residual array is unavailable; use peak metrics and SNR as the tuning context."
    else:
        residuals = y - fit
        rmse = float(np.sqrt(np.mean(residuals**2)))
        ss_res = float(np.sum(residuals**2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        max_idx = int(np.argmax(np.abs(residuals)))
        region = f"{float(ppm[max_idx]):.2f} ppm"
        if rmse > 0 and np.nanmedian(np.abs(np.diff(residuals))) > rmse * 0.7:
            residual_type = "noise"
        elif rmse > 0 and abs(float(residuals[max_idx])) > rmse * 2.0:
            residual_type = "peak_mismatch"
        else:
            residual_type = "random"
        summary = (
            f"NMR residual maximum near {region}; RMSE={rmse:.4g}, "
            f"residual_type={residual_type}. Tune peak_height_min, peak_distance_ppm, "
            "deconvolution_method, baseline_method, or apodization parameters."
        )
    return {
        "rmse": rmse,
        "r_squared": float(r_squared),
        "residual_type": residual_type,
        "max_residual_region": region,
        "peak_regions": [],
        "summary": summary,
    }


def _select_dsc_residual_result(self: Any, dsc_results: list[Any]) -> Any:
    meaningful = []
    for result in dsc_results:
        r_squared = self._safe_float(getattr(result, "r_squared", 0.0))
        if len(getattr(result, "fit_regions", []) or []) > 0 and r_squared != 0.0:
            meaningful.append((r_squared, result))
    if meaningful:
        return min(meaningful, key=lambda item: item[0])[1]
    return dsc_results[0]


def _empty_residual_pattern(self: Any) -> ResidualPattern:
    return ResidualPattern(
        rmse=0.0,
        r_squared=0.0,
        residual_type="random",
        max_residual_region="unknown",
        peak_regions=[],
        summary="残差数据不足，无法判断残差模式。",
    )
