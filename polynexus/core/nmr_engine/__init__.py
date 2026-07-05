"""NMR sub-engine — modular polymer ssNMR analysis."""

from .config import NMRConfig
from .io import (
    NMRSpectrum, NMRRelaxation, ComputedShift,
    load_spectrum, load_project, load_relaxation,
    load_computed_shifts, parse_castep_magres,
    NMR_EXTS, NMR_OUTPUT_DIRS,
)
from .preprocess import (
    apodization_exponential, apodization_gaussian,
    phase_correct, auto_phase, correct_baseline,
    normalise, preprocess_pipeline,
)
from .core import (
    NMRResult,
    detect_peaks, deconvolve_peaks, assign_peaks,
    compute_crystallinity_nmr,
    fit_t1_recovery, fit_t2_decay,
    match_computed_shifts, analyze_spectrum,
)
from .nmr_output import (
    set_sci_style, generate_all_figures,
    fig_nmr1_spectrum, fig_nmr2_deconvolution,
    fig_nmr3_comparison, fig_nmr4_crystallinity,
    fig_nmr5_region_integrals,
    export_parameters_csv, export_peaks_csv,
)

__all__ = [
    "NMRConfig",
    "NMRSpectrum", "NMRRelaxation", "ComputedShift",
    "load_spectrum", "load_project", "load_relaxation",
    "load_computed_shifts", "parse_castep_magres",
    "NMR_EXTS", "NMR_OUTPUT_DIRS",
    "apodization_exponential", "apodization_gaussian",
    "phase_correct", "auto_phase", "correct_baseline",
    "normalise", "preprocess_pipeline",
    "NMRResult",
    "detect_peaks", "deconvolve_peaks", "assign_peaks",
    "compute_crystallinity_nmr",
    "fit_t1_recovery", "fit_t2_decay",
    "match_computed_shifts", "analyze_spectrum",
    "set_sci_style", "generate_all_figures",
    "fig_nmr1_spectrum", "fig_nmr2_deconvolution",
    "fig_nmr3_comparison", "fig_nmr4_crystallinity",
    "fig_nmr5_region_integrals",
    "export_parameters_csv", "export_peaks_csv",
]
