from __future__ import annotations

from typing import Any

from .analysis_evidence_constraints import summarize_constraints, symptom_action_hints
from .analysis_evidence_dsc import _dsc_actionable_lines, _dsc_structure_evidence
from .analysis_evidence_ir import (
    _ir_support_enrichment_bundle,
    _ir_symptom_bridge_lines,
    _ir_symptoms_from_constraints,
    _ir_temperature_2d_symptom_bridge_lines,
    _ir_temperature_2d_symptoms_from_constraints,
)
from .analysis_evidence_nmr_constraints import (
    _nmr_symptom_bridge_lines,
    _nmr_symptoms_from_constraints,
)
from .analysis_evidence_physical import (
    _ir_temperature_2d_metrics,
    evaluate_physical_constraints,
)
from .analysis_evidence_waxs import (
    _waxs_actionable_constraint_lines,
    _waxs_symptoms_from_constraints,
)
from .saxs_symptom_detector import detect_saxs_symptoms, symptom_bridge_lines
from .analysis_evidence_saxs import _saxs_post_analysis_bundle


def build_analysis_postprocess(
    technique_key: str,
    *,
    output: dict[str, Any],
    residual: dict[str, Any],
    validation: dict[str, Any],
    is_ir_temperature_2d: bool,
    signal_evidence: dict[str, Any],
    peak_evidence: dict[str, Any],
    assignment_evidence: dict[str, Any],
    reference_evidence: dict[str, Any],
    background_evidence: dict[str, Any],
    transform_evidence: dict[str, Any],
    structure_evidence: dict[str, Any],
    batch_evidence: dict[str, Any],
    condition_evidence: dict[str, Any],
    feature_evidence: dict[str, Any],
    confidence_signals: list[dict[str, Any]],
    risk_flags: list[str],
    residual_summary: str,
    residual_type: str,
    validation_summary: str,
    dsc_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dsc_bundle = dict(dsc_bundle or {})
    peak_evidence = dict(peak_evidence)
    assignment_evidence = dict(assignment_evidence)
    structure_evidence = dict(structure_evidence)
    feature_evidence = dict(feature_evidence)
    confidence_signals = list(confidence_signals)
    risk_flags = list(risk_flags)
    symptoms: list[dict[str, Any]] = []
    actionable_symptoms: list[str] = []
    stability_evidence: dict[str, Any] = {}

    constraints = evaluate_physical_constraints(technique_key, output, residual, validation)
    constraint_summary = summarize_constraints(constraints)
    for item in constraints:
        if item.get("triggered") and item.get("kind") in {"hard_fail", "soft_warn"}:
            risk_flags.append(str(item.get("name", "")).strip())

    if technique_key == "NMR":
        symptoms = _nmr_symptoms_from_constraints(constraints)
        for symptom in symptoms:
            actionable_symptoms.extend(_nmr_symptom_bridge_lines(symptom))

    if technique_key == "DSC":
        triggered_names = constraint_summary.get("triggered_names", {}) if isinstance(constraint_summary, dict) else {}
        soft_warn_names = {
            str(name).strip()
            for name in (triggered_names.get("soft_warn", []) if isinstance(triggered_names, dict) else [])
            if str(name).strip()
        }
        hard_fail_names = {
            str(name).strip()
            for name in (triggered_names.get("hard_fail", []) if isinstance(triggered_names, dict) else [])
            if str(name).strip()
        }
        actionable_symptoms.extend(_dsc_actionable_lines(soft_warn_names))
        structure_evidence = _dsc_structure_evidence(
            output,
            feature_bundle=dsc_bundle,
            constraint_summary=constraint_summary,
            hard_fail_names=hard_fail_names,
        )
        if structure_evidence:
            feature_evidence["structure_evidence"] = structure_evidence

    if technique_key == "IR" and not is_ir_temperature_2d:
        triggered_total = int(constraint_summary.get("triggered_total", 0) or 0)
        triggered_names = constraint_summary.get("triggered_names", {}) if isinstance(constraint_summary, dict) else {}
        triggered_soft_warn = set()
        if isinstance(triggered_names, dict):
            triggered_soft_warn = {
                str(item).strip()
                for item in triggered_names.get("soft_warn", [])
                if str(item).strip()
            }
        ir_support_bundle = _ir_support_enrichment_bundle(
            peak_evidence=peak_evidence,
            assignment_evidence=assignment_evidence,
            reference_evidence=reference_evidence,
            background_evidence=background_evidence,
            structure_evidence=structure_evidence,
            triggered_total=triggered_total,
            triggered_soft_warn=triggered_soft_warn,
        )
        peak_evidence = ir_support_bundle.get("peak_evidence", {})
        assignment_evidence = ir_support_bundle.get("assignment_evidence", {})
        structure_evidence = ir_support_bundle.get("structure_evidence", {})
        feature_evidence.update(ir_support_bundle.get("feature_evidence", {}))
        confidence_signals.extend(ir_support_bundle.get("confidence_signals", []))

    if technique_key == "IR" and is_ir_temperature_2d:
        ir_2d_metrics = _ir_temperature_2d_metrics(output, validation)
        symptoms = _ir_temperature_2d_symptoms_from_constraints(constraints, ir_2d_metrics)
        for symptom in symptoms:
            actionable_symptoms.extend(_ir_temperature_2d_symptom_bridge_lines(symptom, output))
    elif technique_key == "IR":
        symptoms = _ir_symptoms_from_constraints(constraints, output, residual, validation)
        for symptom in symptoms:
            actionable_symptoms.extend(_ir_symptom_bridge_lines(symptom, output))

    if technique_key == "SAXS":
        symptoms = detect_saxs_symptoms(
            output,
            residual,
            validation,
            constraints=constraints,
            constraint_summary=constraint_summary,
            signal_evidence=signal_evidence,
            peak_evidence=peak_evidence,
            transform_evidence=transform_evidence,
            structure_evidence=structure_evidence,
            batch_evidence=batch_evidence,
            condition_evidence=condition_evidence,
        )
        saxs_post_bundle = _saxs_post_analysis_bundle(
            output,
            symptoms=symptoms,
            constraint_summary=constraint_summary,
        )
        stability_evidence = saxs_post_bundle.get("stability_evidence", {})
        feature_evidence.update(saxs_post_bundle.get("feature_evidence", {}))
        confidence_signals.extend(saxs_post_bundle.get("confidence_signals", []))
    else:
        saxs_post_bundle = {}

    if technique_key == "WAXS":
        symptoms = _waxs_symptoms_from_constraints(constraints, output, validation, residual)
        for symptom in symptoms:
            actionable_symptoms.extend(symptom_bridge_lines(symptom))

    if residual_summary:
        actionable_symptoms.append(residual_summary)
    if validation_summary and validation_summary not in actionable_symptoms:
        actionable_symptoms.append(validation_summary)
    if not (technique_key == "IR" and is_ir_temperature_2d):
        actionable_symptoms.extend(symptom_action_hints(technique_key, residual_type, output))
    if technique_key == "SAXS":
        actionable_symptoms.extend(saxs_post_bundle.get("actionable_symptoms", []))
    elif technique_key == "WAXS":
        triggered_names = constraint_summary.get("triggered_names", {}) if isinstance(constraint_summary, dict) else {}
        soft_warn_names = triggered_names.get("soft_warn", []) if isinstance(triggered_names, dict) else []
        actionable_symptoms.extend(
            item
            for item in _waxs_actionable_constraint_lines(set(soft_warn_names))
            if not any(item in str(existing) for existing in actionable_symptoms)
        )

    actionable_symptoms = list(dict.fromkeys(item for item in actionable_symptoms if str(item).strip()))

    return {
        "constraints": constraints,
        "constraint_summary": constraint_summary,
        "risk_flags": risk_flags,
        "symptoms": symptoms,
        "actionable_symptoms": actionable_symptoms,
        "feature_evidence": feature_evidence,
        "confidence_signals": confidence_signals,
        "peak_evidence": peak_evidence,
        "assignment_evidence": assignment_evidence,
        "structure_evidence": structure_evidence,
        "stability_evidence": stability_evidence,
    }
