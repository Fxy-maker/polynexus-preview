from __future__ import annotations

from typing import Any

from .analysis_evidence_common import _xray_common_feature_bundle
from .analysis_evidence_finalize import finalize_analysis_evidence
from .analysis_evidence_models import AnalysisEvidence
from .analysis_evidence_physical import (
    _is_ir_temperature_2d,
)
from .analysis_evidence_postprocess import build_analysis_postprocess
from .analysis_evidence_summary import build_analysis_summary
from .analysis_evidence_technique_bundles import (
    build_dsc_technique_bundle,
    build_ir_technique_bundle,
    build_nmr_technique_bundle,
    build_saxs_technique_bundle,
    build_waxs_technique_bundle,
)
from .analysis_evidence_utils import _clean_float


def build_analysis_evidence(
    technique: str,
    output_parameters: dict[str, Any] | None = None,
    residual_pattern: dict[str, Any] | None = None,
    validation_context: dict[str, Any] | None = None,
) -> AnalysisEvidence:
    output = dict(output_parameters or {})
    residual = dict(residual_pattern or {})
    validation = dict(validation_context or {})
    technique_key = str(technique or "").upper()
    is_ir_temperature_2d = technique_key == "IR" and _is_ir_temperature_2d(output, validation)

    fit_evidence: dict[str, Any] = {}
    physical_evidence: dict[str, Any] = {}
    residual_evidence: dict[str, Any] = {}
    feature_evidence: dict[str, Any] = {}
    signal_evidence: dict[str, Any] = {}
    peak_evidence: dict[str, Any] = {}
    assignment_evidence: dict[str, Any] = {}
    reference_evidence: dict[str, Any] = {}
    background_evidence: dict[str, Any] = {}
    phase_evidence: dict[str, Any] = {}
    transform_evidence: dict[str, Any] = {}
    structure_evidence: dict[str, Any] = {}
    raw_structure_evidence: dict[str, Any] = {}
    batch_evidence: dict[str, Any] = {}
    condition_evidence: dict[str, Any] = {}
    stability_evidence: dict[str, Any] = {}
    symptoms: list[dict[str, Any]] = []
    risk_flags: list[str] = []
    confidence_signals: list[dict[str, Any]] = []
    actionable_symptoms: list[str] = []

    r_squared = _clean_float(output.get("r_squared"))
    quality_score = _clean_float(output.get("quality_score"))
    fit_rmse = _clean_float(output.get("fit_rmse"))
    quality_flag = str(output.get("quality_flag", "") or "").strip()
    validation_summary = str(output.get("validation_summary", "") or "").strip()
    residual_type = str(residual.get("residual_type", "") or "").strip()
    residual_summary = str(residual.get("summary", "") or "").strip()

    if r_squared is not None:
        fit_evidence["r_squared"] = r_squared
    if quality_score is not None:
        fit_evidence["quality_score"] = quality_score
    if fit_rmse is not None:
        fit_evidence["fit_rmse"] = fit_rmse
    if quality_flag:
        physical_evidence["quality_flag"] = quality_flag
        if quality_flag != "OK":
            risk_flags.append(quality_flag)
    if validation_summary:
        physical_evidence["validation_summary"] = validation_summary

    residual_evidence.update(
        {
            "residual_type": residual_type or "unknown",
            "summary": residual_summary,
            "max_residual_region": residual.get("max_residual_region", "unknown"),
            "rmse": _clean_float(residual.get("rmse")),
            "r_squared": _clean_float(residual.get("r_squared")),
            "peak_regions": residual.get("peak_regions", []),
        }
    )

    if technique_key in {"WAXS", "SAXS"}:
        xray_bundle = _xray_common_feature_bundle(
            technique_key,
            output,
            quality_score=quality_score,
        )
        physical_evidence.update(xray_bundle.get("physical_evidence", {}))
        feature_evidence.update(xray_bundle.get("feature_evidence", {}))
        confidence_signals.extend(xray_bundle.get("confidence_signals", []))

    if technique_key == "SAXS":
        saxs_bundle = build_saxs_technique_bundle(
            output,
            quality_flag=quality_flag,
            validation_summary=validation_summary,
            feature_evidence=feature_evidence,
        )
        feature_evidence = dict(saxs_bundle.get("feature_evidence", {}))
        signal_evidence = saxs_bundle.get("signal_evidence", {})
        peak_evidence = saxs_bundle.get("peak_evidence", {})
        transform_evidence = saxs_bundle.get("transform_evidence", {})
        structure_evidence = saxs_bundle.get("structure_evidence", {})
        raw_structure_evidence = saxs_bundle.get("raw_structure_evidence", {})
        batch_evidence = saxs_bundle.get("batch_evidence", {})
        condition_evidence = saxs_bundle.get("condition_evidence", {})
        confidence_signals.extend(saxs_bundle.get("confidence_signals", []))

    dsc_bundle: dict[str, Any] = {}
    if technique_key == "DSC":
        dsc_result = build_dsc_technique_bundle(
            output,
            validation,
            validation_summary=validation_summary,
            residual_type=residual_type,
            residual_summary=residual_summary,
            feature_evidence=feature_evidence,
        )
        dsc_bundle = dsc_result.get("dsc_bundle", {})
        physical_evidence.update(dsc_result.get("physical_evidence", {}))
        feature_evidence = dict(dsc_result.get("feature_evidence", {}))
        peak_evidence = dsc_result.get("peak_evidence", {})
        confidence_signals.extend(dsc_result.get("confidence_signals", []))

    if technique_key == "IR" and is_ir_temperature_2d:
        ir_bundle = build_ir_technique_bundle(
            output,
            validation,
            is_temperature_2d=True,
            feature_evidence=feature_evidence,
        )
        feature_evidence = dict(ir_bundle.get("feature_evidence", {}))
        signal_evidence = ir_bundle.get("signal_evidence", {})
        peak_evidence = ir_bundle.get("peak_evidence", {})
        transform_evidence = ir_bundle.get("transform_evidence", {})
        structure_evidence = ir_bundle.get("structure_evidence", {})
        confidence_signals.extend(ir_bundle.get("confidence_signals", []))
    elif technique_key == "IR":
        ir_bundle = build_ir_technique_bundle(
            output,
            validation,
            is_temperature_2d=False,
            feature_evidence=feature_evidence,
        )
        feature_evidence = dict(ir_bundle.get("feature_evidence", {}))
        signal_evidence = ir_bundle.get("signal_evidence", {})
        peak_evidence = ir_bundle.get("peak_evidence", {})
        background_evidence = ir_bundle.get("background_evidence", {})
        assignment_evidence = ir_bundle.get("assignment_evidence", {})
        reference_evidence = ir_bundle.get("reference_evidence", {})
        phase_evidence = ir_bundle.get("phase_evidence", {})
        structure_evidence = ir_bundle.get("structure_evidence", {})
        confidence_signals.extend(ir_bundle.get("confidence_signals", []))

    if technique_key == "NMR":
        nmr_bundle = build_nmr_technique_bundle(output, feature_evidence=feature_evidence)
        feature_evidence = dict(nmr_bundle.get("feature_evidence", {}))
        signal_evidence = nmr_bundle.get("signal_evidence", {})
        peak_evidence = nmr_bundle.get("peak_evidence", {})
        assignment_evidence = nmr_bundle.get("assignment_evidence", {})
        phase_evidence = nmr_bundle.get("phase_evidence", {})
        structure_evidence = nmr_bundle.get("structure_evidence", {})
        confidence_signals.extend(nmr_bundle.get("confidence_signals", []))

    if technique_key == "WAXS":
        waxs_bundle = build_waxs_technique_bundle(
            output,
            validation,
            feature_evidence=feature_evidence,
        )
        feature_evidence = dict(waxs_bundle.get("feature_evidence", {}))
        peak_evidence = waxs_bundle.get("peak_evidence", {})
        background_evidence = waxs_bundle.get("background_evidence", {})
        phase_evidence = waxs_bundle.get("phase_evidence", {})
        structure_evidence = waxs_bundle.get("structure_evidence", {})
        condition_evidence = waxs_bundle.get("condition_evidence", {})
        confidence_signals.extend(waxs_bundle.get("confidence_signals", []))

    postprocess_bundle = build_analysis_postprocess(
        technique_key,
        output=output,
        residual=residual,
        validation=validation,
        is_ir_temperature_2d=is_ir_temperature_2d,
        signal_evidence=signal_evidence,
        peak_evidence=peak_evidence,
        assignment_evidence=assignment_evidence,
        reference_evidence=reference_evidence,
        background_evidence=background_evidence,
        transform_evidence=transform_evidence,
        structure_evidence=structure_evidence,
        batch_evidence=batch_evidence,
        condition_evidence=condition_evidence,
        feature_evidence=feature_evidence,
        confidence_signals=confidence_signals,
        risk_flags=risk_flags,
        residual_summary=residual_summary,
        residual_type=residual_type,
        validation_summary=validation_summary,
        dsc_bundle=dsc_bundle,
    )
    constraints = list(postprocess_bundle.get("constraints", []))
    constraint_summary = dict(postprocess_bundle.get("constraint_summary", {}))
    risk_flags = list(postprocess_bundle.get("risk_flags", []))
    symptoms = list(postprocess_bundle.get("symptoms", []))
    actionable_symptoms = list(postprocess_bundle.get("actionable_symptoms", []))
    feature_evidence = dict(postprocess_bundle.get("feature_evidence", {}))
    confidence_signals = list(postprocess_bundle.get("confidence_signals", []))
    peak_evidence = dict(postprocess_bundle.get("peak_evidence", {}))
    assignment_evidence = dict(postprocess_bundle.get("assignment_evidence", {}))
    structure_evidence = dict(postprocess_bundle.get("structure_evidence", {}))
    stability_evidence = dict(postprocess_bundle.get("stability_evidence", {}))

    summary_bundle = build_analysis_summary(
        technique_key,
        is_ir_temperature_2d=is_ir_temperature_2d,
        output=output,
        validation=validation,
        quality_flag=quality_flag,
        residual_type=residual_type,
        risk_flags=risk_flags,
        constraints=constraints,
        constraint_summary=constraint_summary,
        signal_evidence=signal_evidence,
        peak_evidence=peak_evidence,
        assignment_evidence=assignment_evidence,
        reference_evidence=reference_evidence,
        structure_evidence=structure_evidence,
        batch_evidence=batch_evidence,
        condition_evidence=condition_evidence,
        stability_evidence=stability_evidence,
        raw_structure_evidence=raw_structure_evidence,
        confidence_signals=confidence_signals,
    )
    confidence_signals = list(summary_bundle.get("confidence_signals", []))

    return finalize_analysis_evidence(
        technique_key=technique_key,
        summary=str(summary_bundle.get("summary", "") or ""),
        fit_evidence=fit_evidence,
        physical_evidence=physical_evidence,
        residual_evidence=residual_evidence,
        feature_evidence=feature_evidence,
        signal_evidence=signal_evidence,
        peak_evidence=peak_evidence,
        assignment_evidence=assignment_evidence,
        reference_evidence=reference_evidence,
        background_evidence=background_evidence,
        phase_evidence=phase_evidence,
        transform_evidence=transform_evidence,
        structure_evidence=structure_evidence,
        raw_structure_evidence=raw_structure_evidence,
        batch_evidence=batch_evidence,
        condition_evidence=condition_evidence,
        stability_evidence=stability_evidence,
        symptoms=symptoms,
        risk_flags=risk_flags,
        confidence_signals=confidence_signals,
        actionable_symptoms=actionable_symptoms,
        constraints=constraints,
        constraint_summary=constraint_summary,
        validation=validation,
    )
