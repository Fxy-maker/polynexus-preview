"""DSC sub-engine — modular polymer DSC analysis.

Architecture mirrors saxs_engine/:
    config.py        — DSCConfig dataclass
    io.py            — multi-format data loading
    preprocess.py    — calibration, baseline correction, smoothing
    core.py         — Tg, Tm, DH, crystallinity, peak deconvolution
    dsc_kinetics.py — isothermal & non-isothermal crystallisation kinetics
    dsc_output.py   — SCI-quality figures & data export
"""

from .config import DSCConfig
from .io import DSCScan, load_scan, load_project, normalise_scan, split_scan_segments
from .core import (
    DSCResult,
    compute_Tg,
    find_thermal_events,
    compute_crystallinity,
    deconvolve_peaks,
    assess_quality,
    analyze_scan,
    aggregate_dsc_result_metrics,
)
from .preprocess import (
    baseline_linear,
    baseline_polynomial,
    baseline_spline,
    baseline_blank_subtract,
    baseline_tangential,
    correct_baseline,
    smooth_profile,
    smooth_savgol,
    smooth_moving_average,
    calibrate_temperature,
    calibrate_enthalpy,
    calibrate_heat_capacity,
    normalise_rate,
    preprocess_pipeline,
)
from .dsc_kinetics import (
    AvramiResult,
    IsothermalSegment,
    IsothermalKineticsResult,
    NonIsothermalResult,
    NonIsothermalCurve,
    NonIsothermalKineticsSeries,
    detect_isothermal_segments,
    relative_crystallinity,
    relative_crystallinity_isothermal,
    relative_crystallinity_nonisothermal,
    relative_crystallinity_from_T,
    extract_nonisothermal_rate,
    extract_nonisothermal_curves,
    avrami_fit,
    avrami_from_dsc,
    analyze_isothermal_scan,
    analyze_isothermal_scans,
    analyze_nonisothermal_scans,
    ozawa_analysis,
    kissinger_analysis,
    friedman_analysis,
    mo_analysis,
    analyze_kinetics,
)
from .dsc_output import (
    export_parameters_csv,
)


from .dsc_mdsc import (
    MDSCResult, deconvolve_mdsc, deconvolve_mdsc_simple,
    analyse_glass_transition_mdsc, detect_enthalpic_relaxation,
)
from .dsc_multistep import (
    POLYMORPH_DB, TRANSITION_TYPES,
    classify_transition, detect_multistep_events,
)
from .dsc_flash import (
    correct_thermal_lag,
    analyze_flash_heating,
    analyze_flash_cooling,
    critical_cooling_rate,
)
__all__ = [
    # config
    "DSCConfig",
    # io
    "DSCScan", "load_scan", "load_project", "normalise_scan", "split_scan_segments",
    # core
    "DSCResult",
    "compute_Tg", "find_thermal_events", "compute_crystallinity",
    "deconvolve_peaks", "assess_quality", "analyze_scan",
    "aggregate_dsc_result_metrics",
    # preprocess
    "baseline_linear", "baseline_polynomial", "baseline_spline",
    "baseline_blank_subtract", "baseline_tangential",
    "correct_baseline", "smooth_profile", "smooth_savgol",
    "smooth_moving_average",
    "calibrate_temperature", "calibrate_enthalpy",
    "calibrate_heat_capacity", "normalise_rate",
    "preprocess_pipeline",
    # kinetics
    "AvramiResult", "IsothermalSegment", "IsothermalKineticsResult",
    "NonIsothermalResult", "NonIsothermalCurve", "NonIsothermalKineticsSeries",
    "detect_isothermal_segments",
    "relative_crystallinity", "relative_crystallinity_isothermal",
    "relative_crystallinity_nonisothermal", "relative_crystallinity_from_T",
    "extract_nonisothermal_rate", "extract_nonisothermal_curves",
    "avrami_fit", "avrami_from_dsc",
    "analyze_isothermal_scan", "analyze_isothermal_scans",
    "analyze_nonisothermal_scans",
    "ozawa_analysis", "kissinger_analysis",
    "friedman_analysis", "mo_analysis",
    "analyze_kinetics",
    # output
    "export_parameters_csv",
]
