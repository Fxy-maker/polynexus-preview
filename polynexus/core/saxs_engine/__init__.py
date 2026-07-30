"""
saxs_engine — Modular SAXS analysis engine for PolyNexus.

Modules:
  io          — Module 1: Data input (EDF, dat, txt, 2D images)
  preprocess  — Module 2: Background, normalization, integration, smoothing
  core        — Module 3: Core computation (L, correlation, IDF, Porod, Kratky)
  config      — Configuration dataclasses
  saxs_strain      — Module 4B: In-situ tensile SAXS (phase detection, Herman, voids)
  saxs_temperature — Module 4C: In-situ temperature SAXS (Gibbs-Thomson, Avrami)
  saxs_anisotropy  — Module 5: Anisotropy analysis (azimuthal, Herman, pattern classification)
  saxs_output      — Module 7+9: SCI visualization & data export
"""

from .config import SAXSConfig, ExperimentCondition
from .saxs_quality_contracts import (
    DataQualityReport,
    DetectorQualityReport,
    GuinierEvidence,
    GuinierSequenceEvidence,
    MetricEvidence,
    MetricEvidenceSummary,
    QualityLevel,
    RescueCandidate,
    RescueValidationReport,
    build_data_quality_report,
    build_guinier_evidence,
    build_guinier_sequence_evidence,
    build_porod_evidence,
    build_kratky_evidence,
    build_invariant_evidence,
    build_lamellar_evidence,
    build_series_metric_evidence,
    build_series_detector_quality_report,
    build_series_orientation_evidence,
    build_detector_quality_report,
    build_orientation_evidence,
    build_saxs_scientific_acceptance_audit,
    Sanitized1DProfile,
    sanitize_1d_profile,
    contract_json,
)
from .processed_profile import ProcessedProfile
from .saxs_mask_edit import (
    MaskEditValidationError,
    apply_confirmed_mask_edit,
    build_mask_edit_candidate,
    confirm_mask_edit_candidate,
    mask_digest,
    validate_mask_edit_candidate,
)
from .io import (
    read_image, read_1d_profile, extract_geometry_from_header,
    scan_experiment_dir, assemble_dataset, recover_condition_axis,
)
from .preprocess import (
    build_integrator, integrate_full, integrate_sectors,
    integrate_chi_sectors, default_integration_fn,
    subtract_background, normalize_intensity, smooth_profile,
    apply_thermal_correction, preprocess_pipeline,
    detect_beamstop_edge, find_first_nonzero_q,
    _integrate_pyfai_shadow,
)
from .core import (
    LongPeriodResult, StructureParams, SAXSResult,
    bragg_long_period, scattering_invariant, lorentz_fit_long_period,
    correlation_function, idf_analysis, ensemble_long_period,
    compute_structure_params, guinier_analysis, porod_analysis,
    kratky_analysis, sasmodels_fit, sasmodels_fit_with_fallback,
    classify_single_frame_lc_reliability,
    analyze_single, validate_saxs_results,
)
from .saxs_strain import (
    StrainPhase, StrainPointResult, StrainSeriesResult,
    detect_strain_phase, herman_orientation_factor, herman_from_sector_data,
    detect_voids, analyze_strain_series, check_invariant_conservation,
)
from .saxs_temperature import (
    TempPhase, TemperaturePointResult, TempSeriesResult,
    detect_temperature_phase, gibbs_thomson_analysis,
    avrami_kinetics, avrami_from_temp_series,
    detect_melting_from_saxs, analyze_temperature_series,
)
from .saxs_anisotropy import (
    AnisotropyResult,
    extract_azimuthal_profile, extract_azimuthal_at_peaks,
    herman_from_azimuthal, herman_multi_q,
    classify_2d_pattern, analyze_peak_widths,
    analyze_anisotropy, detect_in_plane_orientation_axis,
)
from .saxs_sequence_rescue import (
    build_sequence_rescue_candidates,
    validate_sequence_rescue_candidate,
)
from .saxs_ai_rescue import (
    SAXSConfirmedRerunAudit,
    SAXSAIRescueDecision,
    SAXSAIRescuePlan,
    assess_saxs_ai_candidate,
    assess_saxs_confirmed_rerun,
    build_saxs_confirmed_rerun_evidence,
    build_saxs_ai_rescue_plan,
    validate_saxs_confirmation_report,
    validate_saxs_ai_intent,
)
from .saxs_output import (
    export_parameters_csv,
    export_1d_profile,
    export_strain_series_csv,
    export_temp_series_csv,
)

__all__ = [
    "SAXSConfig", "ExperimentCondition", "DataQualityReport", "DetectorQualityReport",
    "GuinierEvidence", "GuinierSequenceEvidence", "MetricEvidence", "MetricEvidenceSummary", "QualityLevel", "RescueCandidate",
    "RescueValidationReport", "build_data_quality_report", "build_guinier_evidence",
    "build_guinier_sequence_evidence",
    "build_porod_evidence", "build_kratky_evidence",
    "build_invariant_evidence", "build_lamellar_evidence",
    "build_series_metric_evidence", "build_series_detector_quality_report",
    "build_series_orientation_evidence",
    "build_detector_quality_report", "build_orientation_evidence",
    "build_saxs_scientific_acceptance_audit",
    "Sanitized1DProfile", "sanitize_1d_profile",
    "contract_json",
    "ProcessedProfile",
    "MaskEditValidationError", "apply_confirmed_mask_edit",
    "build_mask_edit_candidate", "confirm_mask_edit_candidate",
    "mask_digest", "validate_mask_edit_candidate",
    "read_image", "read_1d_profile", "extract_geometry_from_header",
    "scan_experiment_dir", "assemble_dataset", "recover_condition_axis",
    "build_integrator", "integrate_full", "integrate_sectors",
    "integrate_chi_sectors", "default_integration_fn", "subtract_background",
    "normalize_intensity", "smooth_profile", "apply_thermal_correction",
    "preprocess_pipeline", "detect_beamstop_edge", "find_first_nonzero_q",
    "_integrate_pyfai_shadow",
    "LongPeriodResult", "StructureParams", "SAXSResult", "bragg_long_period",
    "scattering_invariant", "lorentz_fit_long_period", "correlation_function",
    "idf_analysis", "ensemble_long_period", "compute_structure_params",
    "guinier_analysis", "porod_analysis", "kratky_analysis", "sasmodels_fit",
    "sasmodels_fit_with_fallback", "classify_single_frame_lc_reliability",
    "analyze_single", "validate_saxs_results", "StrainPhase",
    "StrainPointResult", "StrainSeriesResult", "detect_strain_phase",
    "herman_orientation_factor", "herman_from_sector_data", "detect_voids",
    "analyze_strain_series", "check_invariant_conservation", "TempPhase",
    "TemperaturePointResult", "TempSeriesResult", "detect_temperature_phase",
    "gibbs_thomson_analysis", "avrami_kinetics", "avrami_from_temp_series",
    "detect_melting_from_saxs", "analyze_temperature_series", "AnisotropyResult",
    "extract_azimuthal_profile", "extract_azimuthal_at_peaks",
    "herman_from_azimuthal", "herman_multi_q", "classify_2d_pattern",
    "analyze_peak_widths", "analyze_anisotropy", "detect_in_plane_orientation_axis", "export_parameters_csv",
    "build_sequence_rescue_candidates", "validate_sequence_rescue_candidate",
    "SAXSAIRescueDecision", "SAXSAIRescuePlan",
    "SAXSConfirmedRerunAudit", "assess_saxs_ai_candidate",
    "assess_saxs_confirmed_rerun", "build_saxs_confirmed_rerun_evidence",
    "build_saxs_ai_rescue_plan", "validate_saxs_confirmation_report",
    "validate_saxs_ai_intent",
    "export_1d_profile", "export_strain_series_csv", "export_temp_series_csv",
]
