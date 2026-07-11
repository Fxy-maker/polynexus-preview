from __future__ import annotations

from typing import Any

from .analysis_evidence_constraints import physical_constraint_inventory
from .analysis_evidence_dsc import _DSC_CONSTRAINT_NAMES, _evaluate_dsc_constraint
from .analysis_evidence_ir import (
    _IR_STATIC_CONSTRAINT_NAMES,
    _evaluate_ir_static_constraint,
    _ir_band_support_metrics,
    _ir_temperature_2d_constraint_rows,
)
from .analysis_evidence_nmr_constraints import _NMR_CONSTRAINT_NAMES, _evaluate_nmr_constraint
from .analysis_evidence_saxs import _SAXS_CONSTRAINT_NAMES, _evaluate_saxs_constraint
from .analysis_evidence_utils import _clean_float, _match_constraint_value
from .analysis_evidence_waxs import _WAXS_CONSTRAINT_NAMES, _evaluate_waxs_constraint


def evaluate_physical_constraints(
    technique: str,
    output_parameters: dict[str, Any] | None = None,
    residual_pattern: dict[str, Any] | None = None,
    validation_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    from .analysis_evidence_physical import _ir_temperature_2d_metrics, _is_ir_temperature_2d

    output = dict(output_parameters or {})
    residual = dict(residual_pattern or {})
    validation = dict(validation_context or {})
    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}
    technique_key = str(technique or "").upper()
    residual_key = str(residual.get("residual_type", "") or "").strip().lower()
    is_ir_temperature_2d = technique_key == "IR" and _is_ir_temperature_2d(output, validation)
    ir_2d_metrics = _ir_temperature_2d_metrics(output, validation) if is_ir_temperature_2d else {}
    ir_support = _ir_band_support_metrics(output, validation) if technique_key == "IR" else {}
    evaluated: list[dict[str, Any]] = []

    batch_rows = output.get("_batch_data") if isinstance(output.get("_batch_data"), list) else []

    for item in physical_constraint_inventory(technique_key):
        observed = _match_constraint_value(output, item.field)
        triggered = False

        if item.name == "beamstop_contamination":
            triggered = bool(observed)
        elif item.name == "mask_truncated":
            triggered = bool(observed)
        elif item.name == "low_peak_snr":
            snr = _clean_float(observed)
            triggered = snr is not None and snr < 3.0
            observed = snr
        elif item.name == "l_consistency":
            l_bragg = _clean_float(output.get("L_bragg"))
            l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
            if l_bragg is None or l_corr is None:
                triggered = False
            else:
                rel = abs(l_bragg - l_corr) / max(abs(l_bragg), abs(l_corr), 1e-9)
                observed = {"L_bragg": l_bragg, "L_corr": l_corr, "rel_diff": rel}
                triggered = rel > 0.03
        elif item.name == "fit_regions_unstable":
            fit_regions = output.get("fit_regions")
            if isinstance(fit_regions, list) and fit_regions:
                failing = []
                for region in fit_regions:
                    if not isinstance(region, dict):
                        continue
                    region_r2 = _clean_float(region.get("r_squared"))
                    region_rmse = _clean_float(region.get("rmse"))
                    label = str(
                        region.get("region", "") or region.get("name", "") or "unknown"
                    ).strip()
                    if (region_r2 is not None and region_r2 < 0.25) or (
                        region_rmse is not None and region_rmse > 0.35
                    ):
                        failing.append(
                            {
                                "region": label,
                                "r_squared": region_r2,
                                "rmse": region_rmse,
                            }
                        )
                observed = {
                    "failing_regions": failing,
                    "total_regions": len(fit_regions),
                }
                triggered = len(failing) >= 2
        elif item.name == "correlation_over_oscillation":
            fit_regions = output.get("fit_regions")
            oscillation_flags = []
            if isinstance(fit_regions, list):
                for region in fit_regions:
                    if not isinstance(region, dict):
                        continue
                    label = str(
                        region.get("region", "") or region.get("name", "") or ""
                    ).strip().lower()
                    if label not in {"correlation", "idf", "correlation_function"}:
                        continue
                    peak_count = _clean_float(region.get("peak_count"))
                    zero_crossings = _clean_float(region.get("zero_crossings"))
                    if (peak_count is not None and peak_count >= 8) or (
                        zero_crossings is not None and zero_crossings >= 10
                    ):
                        oscillation_flags.append(
                            {
                                "region": label,
                                "peak_count": peak_count,
                                "zero_crossings": zero_crossings,
                            }
                        )
            observed = {"oscillation_regions": oscillation_flags}
            triggered = bool(oscillation_flags)
        elif technique_key == "SAXS" and item.name in _SAXS_CONSTRAINT_NAMES:
            triggered, observed = _evaluate_saxs_constraint(
                item.name,
                output,
                observed,
                batch_rows,
            )
        elif item.name == "quality_floor":
            quality = _clean_float(observed)
            triggered = quality is not None and quality < 0.5
            observed = quality
        elif item.name == "multi_scan_consistency":
            triggered = bool(output.get("scan_r_squared"))
            observed = output.get("scan_r_squared")
        elif item.name == "peak_visibility":
            n_peaks = _clean_float(observed)
            triggered = n_peaks is not None and n_peaks <= 0
            observed = n_peaks
        elif item.name == "peak_structure":
            n_peaks = _clean_float(observed)
            triggered = n_peaks is not None and n_peaks > 0
            observed = n_peaks
        elif item.name == "fit_quality_vs_phys":
            r2 = _clean_float(observed)
            quality = _clean_float(output.get("quality_score"))
            if r2 is not None and quality is not None:
                triggered = abs(r2 - quality) > 0.05
                observed = {"r_squared": r2, "quality_score": quality}
        elif item.name == "assignment_confidence":
            score = _clean_float(observed)
            triggered = score is not None and score < 0.7
            observed = score
        elif item.name == "fit_quality":
            fit_quality = None
            if isinstance(output.get("quality_metrics"), dict):
                fit_quality = _clean_float(output["quality_metrics"].get("fit_quality"))
            if fit_quality is None:
                fit_quality = _clean_float(output.get("quality_fit_quality"))
            triggered = fit_quality is not None and fit_quality < 1.0
            observed = fit_quality
        elif item.name == "peak_snr":
            snr = _clean_float(observed)
            triggered = snr is not None and snr < 5.0
            observed = snr
        elif technique_key == "NMR" and item.name in _NMR_CONSTRAINT_NAMES:
            triggered, observed = _evaluate_nmr_constraint(item.name, output)
        elif (
            technique_key == "IR"
            and not is_ir_temperature_2d
            and item.name in _IR_STATIC_CONSTRAINT_NAMES
        ):
            triggered, observed = _evaluate_ir_static_constraint(
                item.name,
                ir_support,
                residual_key,
                residual,
            )
        elif technique_key == "DSC" and item.name in _DSC_CONSTRAINT_NAMES:
            triggered, observed = _evaluate_dsc_constraint(
                item.name,
                output,
                residual_key,
                validation,
            )
        elif technique_key == "WAXS" and item.name in _WAXS_CONSTRAINT_NAMES:
            triggered, observed = _evaluate_waxs_constraint(
                item.name,
                output,
                observed,
                config_snapshot,
            )

        if validation.get("cross_validation") and item.name in {
            "l_consistency",
            "multi_scan_consistency",
            "multi_scan_inconsistent",
        }:
            observed = validation.get("cross_validation")

        evaluated.append(
            {
                **item.to_dict(),
                "triggered": triggered,
                "observed": observed,
            }
        )

    if is_ir_temperature_2d:
        evaluated.extend(_ir_temperature_2d_constraint_rows(ir_2d_metrics))

    return evaluated
