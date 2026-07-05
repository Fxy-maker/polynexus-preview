"""IR sub-engine — modular polymer IR spectroscopy analysis.

Architecture:
    config.py      — IRConfig with polymer peak database + correction factors
    io.py          — experimental (SPA/CSV/DPT) + computational (Gaussian/ORCA)
    preprocess.py  — rubberband baseline, ATR correction, normalisation
    core.py        — peak detection/fitting, simulation, comparison, crystallinity
    ir_output.py   — SCI figures & data export
"""

from .config import IRConfig
from .io import (
    IRSpectrum, ComputedMode,
    load_spectrum, load_project,
    load_computed_modes,
    parse_gaussian_frequencies, parse_orca_frequencies,
    simulate_spectrum,
)
from .preprocess import (
    transmittance_to_absorbance, absorbance_to_transmittance,
    atr_correction,
    baseline_rubberband, baseline_mute_zone, baseline_als, correct_baseline,
    smooth_profile, normalise_spectrum,
    preprocess_pipeline,
)
from .core import (
    IRResult,
    detect_peaks, fit_peaks,
    assign_peaks, identify_polymer_from_peaks,
    match_computed_to_experiment,
    compute_crystallinity_ratio,
    measure_band_height, measure_band_area, compute_polymer_band_indices,
    analyze_spectrum,
)
from .ir_output import (
    set_sci_style, generate_all_figures,
    fig_ir1_spectrum, fig_ir2_peak_fit,
    fig_ir3_comparison, fig_ir4_crystallinity,
    export_parameters_csv,
)
from .ir_temperature import (
    IRTempFrame, IRTemp2DResult,
    detect_temperature_2d, parse_temperature_condition,
    analyze_temperature_2d_series, compute_2d_correlation,
    generate_temperature_2d_figures,
    export_temperature_2d_csv,
)


from .ir_state import (
    judge_from_dsc,
    judge_from_ir_crystallinity_bands,
    judge_polymer_state,
    IR_CRYSTALLINITY_BANDS,
)
from .ir_periodic import (
    generate_castep_phonon_input, generate_vasp_vib_incar,
    generate_qe_phonon_input, correct_lo_to_splitting,
    predict_ir_active_modes, POLYMER_SPACE_GROUPS, IR_ACTIVE_POINT_GROUPS,
)
from .ir_input_gen import (
    generate_gaussian_input,
    generate_orca_input,
    generate_xyz_from_smiles,
    POLYMER_SMILES,
    GAUSSIAN_ROUTES,
    ORCA_ROUTES,
)
__all__ = [
    "IRConfig",
    "IRSpectrum", "ComputedMode",
    "load_spectrum", "load_project",
    "load_computed_modes",
    "parse_gaussian_frequencies", "parse_orca_frequencies",
    "simulate_spectrum",
    "transmittance_to_absorbance", "absorbance_to_transmittance",
    "atr_correction",
    "baseline_rubberband", "baseline_mute_zone", "baseline_als", "correct_baseline",
    "smooth_profile", "normalise_spectrum",
    "preprocess_pipeline",
    "IRResult",
    "detect_peaks", "fit_peaks",
    "assign_peaks", "identify_polymer_from_peaks",
    "match_computed_to_experiment",
    "compute_crystallinity_ratio",
    "measure_band_height", "measure_band_area", "compute_polymer_band_indices",
    "analyze_spectrum",
    "set_sci_style", "generate_all_figures",
    "fig_ir1_spectrum", "fig_ir2_peak_fit",
    "fig_ir3_comparison", "fig_ir4_crystallinity",
    "export_parameters_csv",
    "IRTempFrame", "IRTemp2DResult",
    "detect_temperature_2d", "parse_temperature_condition",
    "analyze_temperature_2d_series", "compute_2d_correlation",
    "generate_temperature_2d_figures",
    "export_temperature_2d_csv",
]
