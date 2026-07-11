from __future__ import annotations

from .analysis_evidence_builder import build_analysis_evidence
from .analysis_evidence_common import (
    _collect_source_fields,
    _common_summary_details,
    _xray_common_feature_bundle,
)
from .analysis_evidence_constraints import summarize_constraints, symptom_action_hints
from .analysis_evidence_dsc import (
    _DSC_CONSTRAINT_NAMES,
    _dsc_actionable_lines,
    _dsc_feature_bundle,
    _dsc_structure_evidence,
    _dsc_summary_details,
    _evaluate_dsc_constraint,
)
from .analysis_evidence_ir import (
    _IR_STATIC_CONSTRAINT_NAMES,
    _evaluate_ir_static_constraint,
    _ir_band_support_metrics,
    _ir_static_analysis_bundle,
    _ir_summary_details,
    _ir_support_enrichment_bundle,
    _ir_symptom_bridge_lines,
    _ir_symptoms_from_constraints,
    _ir_temperature_2d_constraint_rows,
    _ir_temperature_2d_feature_bundle,
    _ir_temperature_2d_summary_details,
    _ir_temperature_2d_symptom_bridge_lines,
    _ir_temperature_2d_symptoms_from_constraints,
)
from .analysis_evidence_models import AnalysisEvidence
from .analysis_evidence_nmr import (
    _NMR_CONSTRAINT_NAMES,
    _evaluate_nmr_constraint,
    _nmr_analysis_bundle,
    _nmr_peak_rows,
    _nmr_summary_details,
    _nmr_symptom_bridge_lines,
    _nmr_symptoms_from_constraints,
)
from .analysis_evidence_physical import (
    _ir_temperature_2d_metrics,
    _is_ir_temperature_2d,
    evaluate_physical_constraints,
)
from .analysis_evidence_saxs import (
    _SAXS_CONSTRAINT_NAMES,
    _evaluate_saxs_constraint,
    _saxs_condition_feature_bundle,
    _saxs_context_bundle,
    _saxs_core_feature_bundle,
    _saxs_post_analysis_bundle,
    _saxs_summary_details,
)
from .analysis_evidence_utils import (
    _clean_float,
    _clamp_unit,
    _inverse_ratio_score,
    _match_constraint_value,
    _mean_finite,
    _non_empty_mapping,
    _relative_spread,
    _safe_int,
    _shape_tuple,
)
from .analysis_evidence_waxs import (
    _WAXS_CONSTRAINT_NAMES,
    _evaluate_waxs_constraint,
    _waxs_actionable_constraint_lines,
    _waxs_feature_bundle,
    _waxs_summary_details,
    _waxs_symptoms_from_constraints,
)
from .saxs_symptom_detector import detect_saxs_symptoms, symptom_bridge_lines
