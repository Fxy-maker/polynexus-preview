"""WAXS sub-engine — modular polymer WAXS analysis.

Architecture mirrors saxs_engine/:
    config.py       — WAXSConfig dataclass
    io.py           — multi-format data loading (reuses SAXS EDF reader)
    preprocess.py   — polarisation correction, background, 2D→1D, Caglioti
    core.py         — peak fitting, amorphous subtraction, crystallinity,
                      Scherrer, Williamson-Hall, crystal system ID
    waxs_output.py  — SCI-quality figures & data export
    waxs_strain.py  — in-situ strain series analysis
    waxs_temperature.py — in-situ temperature series analysis
    waxs_orientation.py — Herman orientation factor
    waxs_multiscale.py  — multi-scale correlation
"""

from .config import WAXSConfig
from .io import (
    WAXSScan, WAXSDataset,
    load_scan, load_project,
    q_to_two_theta, two_theta_to_q,
    ensure_two_theta, ensure_q,
)
from .preprocess import (
    integrate_2d_to_1d,
    sector_integrate,
    polarisation_correction,
    subtract_air_scattering,
    subtract_background,
    smooth_profile,
    caglioti_correction,
    preprocess_pipeline,
)
from .core import (
    WAXSResult,
    gaussian, lorentzian, pseudo_voigt, pearson_vii,
    detect_peaks, fit_peaks,
    fit_amorphous_halo,
    compute_crystallinity_peak_area,
    scherrer_size, scherrer_from_peaks,
    williamson_hall,
    identify_crystal_system,
    analyze_scan,
)
from .waxs_output import (
    export_parameters_csv,
    export_strain_csv,
)


from .waxs_orientation import (
    extract_azimuthal_profile,
    herman_orientation_factor,
    herman_from_2d_waxs,
    classify_waxs_texture,
)
from .waxs_temperature import (
    WAXSTempResult, analyze_temperature_series, export_temperature_csv,
)
from .waxs_strain import (
    WAXSStrainPhase, WAXSStrainPointResult, WAXSStrainSeriesResult,
    detect_strain_phase_waxs, detect_polymorph_transition,
    analyze_strain_series,
)
from .waxs_multiscale import (
    multiscale_correlation,
)
__all__ = [
    "WAXSConfig",
    "WAXSScan", "WAXSDataset",
    "load_scan", "load_project",
    "q_to_two_theta", "two_theta_to_q",
    "ensure_two_theta", "ensure_q",
    "integrate_2d_to_1d",
    "polarisation_correction",
    "subtract_air_scattering",
    "subtract_background",
    "smooth_profile",
    "caglioti_correction",
    "preprocess_pipeline",
    "WAXSResult",
    "gaussian", "lorentzian", "pseudo_voigt", "pearson_vii",
    "detect_peaks", "fit_peaks",
    "fit_amorphous_halo",
    "compute_crystallinity_peak_area",
    "scherrer_size", "scherrer_from_peaks",
    "williamson_hall",
    "identify_crystal_system",
    "analyze_scan",
    "export_parameters_csv",
    "export_strain_csv",
    "WAXSStrainPhase",
    "WAXSStrainPointResult",
    "WAXSStrainSeriesResult",
    "detect_strain_phase_waxs",
    "detect_polymorph_transition",
    "analyze_strain_series",
    "extract_azimuthal_profile",
    "herman_orientation_factor",
    "herman_from_2d_waxs",
    "classify_waxs_texture",
    "WAXSTempResult",
    "analyze_temperature_series",
    "export_temperature_csv",
    "multiscale_correlation",
]
