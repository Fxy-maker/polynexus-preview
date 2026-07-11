from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _non_empty_mapping, _safe_int


def _saxs_strain_structure_layers(
    output: dict[str, Any],
    structure_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    condition_label = str(output.get("condition_label", "") or "").strip()
    if condition_label.lower() != "strain":
        return {}

    structure_evidence = dict(structure_evidence or {})
    feature_evidence: dict[str, Any] = {}

    strain_structure_evidence = _non_empty_mapping(
        [
            ("Q_star_rel", _clean_float(output.get("Q_star_rel", output.get("Q_rel")))),
            ("Q_star_rel_mean", _clean_float(output.get("Q_star_rel_mean"))),
            ("Q_star_rel_span", _clean_float(output.get("Q_star_rel_span"))),
            ("has_voids", output.get("has_voids")),
            (
                "void_detected_frames",
                _safe_int(output.get("void_detected_frames"), default=0)
                if output.get("void_detected_frames") is not None
                else None,
            ),
            ("phi_void", _clean_float(output.get("phi_void"))),
            ("phi_void_mean", _clean_float(output.get("phi_void_mean"))),
            ("phi_void_span", _clean_float(output.get("phi_void_span"))),
            ("void_AR", _clean_float(output.get("void_AR"))),
            ("f_Herman", _clean_float(output.get("f_Herman", output.get("f_herman")))),
            ("f_Herman_mean", _clean_float(output.get("f_Herman_mean"))),
            ("f_Herman_span", _clean_float(output.get("f_Herman_span"))),
            ("porod_slope", _clean_float(output.get("porod_slope"))),
            ("porod_slope_mean", _clean_float(output.get("porod_slope_mean"))),
            ("porod_slope_span", _clean_float(output.get("porod_slope_span"))),
        ]
    )
    if strain_structure_evidence:
        feature_evidence["strain_structure_evidence"] = strain_structure_evidence

    phase_distribution = output.get("phase_distribution")
    phase_boundary_candidates = output.get("phase_boundary_candidates")
    phase_evidence = _non_empty_mapping(
        [
            ("dominant_phase", str(output.get("dominant_phase", "") or "").strip() or None),
            (
                "phase_distribution",
                phase_distribution if isinstance(phase_distribution, dict) and phase_distribution else None,
            ),
            (
                "phase_boundary_candidates",
                phase_boundary_candidates
                if isinstance(phase_boundary_candidates, list) and phase_boundary_candidates
                else None,
            ),
            ("phase_support_mean", _clean_float(output.get("phase_support_mean"))),
            ("phase_support_span", _clean_float(output.get("phase_support_span"))),
            (
                "phase_ambiguous_frame_count",
                _safe_int(output.get("phase_ambiguous_frame_count"), default=0)
                if output.get("phase_ambiguous_frame_count") is not None
                else None,
            ),
            (
                "frame_low_conf_count",
                _safe_int(output.get("frame_low_conf_count"), default=0)
                if output.get("frame_low_conf_count") is not None
                else None,
            ),
            (
                "void_dominant_frame_count",
                _safe_int(output.get("void_dominant_frame_count"), default=0)
                if output.get("void_dominant_frame_count") is not None
                else None,
            ),
            ("effective_param_ratio", _clean_float(output.get("effective_param_ratio"))),
            (
                "strain_reliability_status",
                str(output.get("strain_reliability_status", "") or "").strip() or None,
            ),
            (
                "strain_reliability_reason",
                str(output.get("strain_reliability_reason", "") or "").strip() or None,
            ),
            ("paper_figure_candidate", output.get("paper_figure_candidate")),
            ("paper_conclusion_candidate", output.get("paper_conclusion_candidate")),
            ("paper_conclusion_ready", output.get("paper_conclusion_ready")),
        ]
    )
    if phase_evidence:
        feature_evidence["phase_evidence"] = phase_evidence
        feature_evidence["strain_phase_evidence"] = phase_evidence
        if isinstance(strain_structure_evidence, dict):
            strain_structure_evidence = dict(strain_structure_evidence)
            strain_structure_evidence["dominant_phase"] = (
                str(output.get("dominant_phase", "") or "").strip() or None
            )
            strain_structure_evidence["phase_support_mean"] = _clean_float(output.get("phase_support_mean"))
            strain_structure_evidence["phase_support_span"] = _clean_float(output.get("phase_support_span"))
            strain_structure_evidence["phase_ambiguous_frame_count"] = (
                _safe_int(output.get("phase_ambiguous_frame_count"), default=0)
                if output.get("phase_ambiguous_frame_count") is not None
                else None
            )
            strain_structure_evidence["frame_low_conf_count"] = (
                _safe_int(output.get("frame_low_conf_count"), default=0)
                if output.get("frame_low_conf_count") is not None
                else None
            )
            strain_structure_evidence["void_dominant_frame_count"] = (
                _safe_int(output.get("void_dominant_frame_count"), default=0)
                if output.get("void_dominant_frame_count") is not None
                else None
            )
            strain_structure_evidence["effective_param_ratio"] = _clean_float(
                output.get("effective_param_ratio")
            )
            strain_structure_evidence["strain_reliability_status"] = (
                str(output.get("strain_reliability_status", "") or "").strip() or None
            )
            strain_structure_evidence["strain_reliability_reason"] = (
                str(output.get("strain_reliability_reason", "") or "").strip() or None
            )
            strain_structure_evidence["paper_figure_candidate"] = output.get("paper_figure_candidate")
            strain_structure_evidence["paper_conclusion_candidate"] = output.get("paper_conclusion_candidate")
            strain_structure_evidence["paper_conclusion_ready"] = output.get("paper_conclusion_ready")
            feature_evidence["strain_structure_evidence"] = strain_structure_evidence

            structure_evidence = dict(structure_evidence)
            structure_evidence["dominant_phase"] = strain_structure_evidence.get("dominant_phase")
            structure_evidence["phase_support_mean"] = strain_structure_evidence.get("phase_support_mean")
            structure_evidence["phase_support_span"] = strain_structure_evidence.get("phase_support_span")
            structure_evidence["phase_ambiguous_frame_count"] = strain_structure_evidence.get(
                "phase_ambiguous_frame_count"
            )
            structure_evidence["frame_low_conf_count"] = strain_structure_evidence.get("frame_low_conf_count")
            structure_evidence["void_dominant_frame_count"] = strain_structure_evidence.get(
                "void_dominant_frame_count"
            )
            structure_evidence["effective_param_ratio"] = strain_structure_evidence.get("effective_param_ratio")
            structure_evidence["strain_reliability_status"] = strain_structure_evidence.get(
                "strain_reliability_status"
            )
            structure_evidence["strain_reliability_reason"] = strain_structure_evidence.get(
                "strain_reliability_reason"
            )
            structure_evidence["paper_figure_candidate"] = strain_structure_evidence.get(
                "paper_figure_candidate"
            )
            structure_evidence["paper_conclusion_candidate"] = strain_structure_evidence.get(
                "paper_conclusion_candidate"
            )
            structure_evidence["paper_conclusion_ready"] = strain_structure_evidence.get(
                "paper_conclusion_ready"
            )
            feature_evidence["structure_evidence"] = structure_evidence

    return {
        "feature_evidence": feature_evidence,
        "structure_evidence": structure_evidence,
    }


__all__ = ["_saxs_strain_structure_layers"]
