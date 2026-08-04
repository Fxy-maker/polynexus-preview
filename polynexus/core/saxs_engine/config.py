"""
saxs.config -- SAXSConfig dataclass with all analysis parameters.

Ports domain-specific defaults from the MATLAB PolyChar Toolbox,
extended with pyFAI / fabio / sasmodels / lmfit integration fields.
"""
import os

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, Optional, List
import numpy as np


TENSILE_AXIS_CONVENTION = "detector_image_clockwise_deg_v1"


def normalize_tensile_axis(
    value: Any,
    convention: Any,
) -> tuple[float | None, str | None]:
    """Normalize an explicit detector-plane axis without inferring one."""

    if value is None or str(value).strip() == "":
        return None, None
    if str(convention or "").strip() != TENSILE_AXIS_CONVENTION:
        raise ValueError("unsupported_tensile_axis_convention")
    try:
        angle = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("tensile_axis_invalid") from exc
    if not np.isfinite(angle):
        raise ValueError("tensile_axis_nonfinite")
    return float(angle % 180.0), TENSILE_AXIS_CONVENTION


@dataclass
class ConditionPattern:
    """A named regular expression for extracting experimental condition
    values (temperature, strain, time, ...) from file or directory names.

    Attributes
    ----------
    name : str
        Human-readable label (e.g. "PA6-dash-number").
    regex : str
        Regex with exactly **one** capture group.  Applied to ``Path.stem``
        unless ``search_path`` is True (searches full ``Path.parts``).
    unit : str
        Physical unit, for documentation only (e.g. "C", "%", "s").
    search_path : bool
        If True, search the entire ``Path.parts`` tuple (directory-aware).
        If False (default), search only the file stem.
    value_transform : str
        How to convert the captured string: ``"float"`` (default), ``"int"``.
    validator_expr : str
        A Python expression that evaluates to bool, with the captured value
        available as ``x``.  Example: ``"20 < x < 500"``.
        Empty string = no validation.
    lookup_map : str
        Name of a ``SAXSConfig`` attribute (dict) to look up the captured
        string.  If non-empty, the capture group is used as a key into
        ``getattr(cfg, lookup_map)``.  Useful for strain code -> % mappings.
    """

    name: str = ""
    regex: str = ""
    unit: str = ""
    search_path: bool = False
    value_transform: str = "float"
    validator_expr: str = ""
    lookup_map: str = ""


def _default_condition_patterns() -> List[ConditionPattern]:
    """Return the default condition-extraction patterns.

    These replicate the original hard-coded logic in
    ``saxs_engine/io._parse_condition()``.  Users can override
    ``SAXSConfig.condition_patterns`` with their own list.
    """
    return [
        # ---- Strain patterns (matched first for experiment_type="strain") ----
        ConditionPattern(
            name="strain_dash_S_suffix",
            regex=r"-(\d+)-[Ss]_",
            unit="%",
            lookup_map="strain_map",
        ),
        ConditionPattern(
            name="strain_directory_code",
            regex=r"^(\d{3})$",
            unit="%",
            search_path=True,
            lookup_map="strain_map",
        ),
        ConditionPattern(
            name="strain_any_3digit",
            regex=r"(\d{3})",
            unit="%",
            lookup_map="strain_map",
        ),
        ConditionPattern(
            name="strain_directory_percent",
            regex=r"(?<!\d)(-?\d+(?:\.\d+)?)\s*(?:%|pct|percent)\b",
            unit="%",
            search_path=True,
            validator_expr="-5 <= x <= 500",
        ),
        ConditionPattern(
            name="strain_directory_label",
            regex=r"(?:strain|epsilon)[_\-\s]*(-?\d+(?:\.\d+)?)",
            unit="%",
            search_path=True,
            validator_expr="-5 <= x <= 500",
        ),
        # ---- Temperature patterns ----
        ConditionPattern(
            name="temp_dash_number",
            regex=r"-(\d{2,4})-[A-Z_]",
            unit="C",
            validator_expr="20 < x < 500",
        ),
        ConditionPattern(
            name="temp_T_marker",
            regex=r"[T_](\d+\.?\d*)\s*C",
            unit="C",
            validator_expr="20 < x < 500",
        ),
        ConditionPattern(
            name="temp_T_digits",
            regex=r"[Tt]_?(\d{2,4})(?:\.|_|[A-Z]|$)",
            unit="C",
            validator_expr="20 < x < 500",
        ),
        ConditionPattern(
            name="temp_underscore_C",
            regex=r"_(\d+)C",
            unit="C",
            validator_expr="20 < x < 500",
        ),
        ConditionPattern(
            name="temp_2or3_digit",
            regex=r"_(\d{2,3})(?:_[A-Z]|\.)",
            unit="C",
            validator_expr="20 < x < 500",
        ),
        ConditionPattern(
            name="temp_directory_c",
            regex=r"(?<!\d)(-?\d+(?:\.\d+)?)\s*(?:°\s*C|deg\s*C|C)\b",
            unit="C",
            search_path=True,
            validator_expr="-100 < x < 600",
        ),
        ConditionPattern(
            name="temp_directory_label",
            regex=r"(?:temperature|temp)[_\-\s]*(-?\d+(?:\.\d+)?)",
            unit="C",
            search_path=True,
            validator_expr="-100 < x < 600",
        ),
    ]



@dataclass
class SAXSConfig:
    """Master configuration for a SAXS experiment / analysis run."""

    # ---- Experiment identity ----
    experiment_type: str = "static"
    condition_label: str = "Condition"
    condition_unit: str = ""

    # ---- Condition extraction (v1.1: configurable) ----
    condition_patterns: List[ConditionPattern] = field(
        default_factory=_default_condition_patterns
    )
    condition_context: Dict[str, Any] = field(default_factory=dict)
    temperature_range: Tuple[float, float] = (20.0, 500.0)
    warn_on_parse_failure: bool = True

    # ---- Beamline / geometry ----
    wavelength_m: float = 1.541891e-10
    pixel_size_m: float = 75e-6
    sdd_m: float = 0.450
    beam_center_x: float = 255.43
    beam_center_y: float = 549.73

    # ---- Beamstop / direct-beam detection ----
    auto_detect_beamstop: bool = True
    beamstop_pollution_threshold: float = 100.0  # I(min_q)/I(0.2 nm⁻¹) ratio trigger
    min_effective_q_nm1: float = 0.01  # populated at runtime if beamstop detected
    mask_truncated_q_thresh: float = 0.10  # if effective q_min > this, mask may be too aggressive

    # ---- Polarisation ----
    do_polarisation_correction: bool = False
    polarisation_degree: float = 0.0  # 0=unpolarised lab, 0.95-0.99=synchrotron

    # ---- pyFAI calibration ----
    poni_file: str = ""
    detector_name: str = "Pilatus 300k"
    use_pyfai_integration: bool = False

    # ---- Azimuthal integration ----
    n_pt: int = 1000
    q_min: float = 0.05
    q_max: float = 3.0
    chi_halfwidth: float = 15.0
    chi_merid_center: float = 90.0
    chi_equat_center: float = 0.0
    chi_merid_range: Tuple[float, float] = (75, 105)
    chi_equat_range: Tuple[float, float] = (-15, 15)
    n_chi_sectors: int = 36
    # ---- Orientation axis resolution ----
    # A finite value is an explicit detector-plane reference axis (degrees).
    # None enables conservative second-harmonic auto-detection at q*.
    orientation_axis_deg: Optional[float] = None
    orientation_auto_min_strength: float = 0.08
    orientation_auto_min_bins: int = 12
    orientation_auto_min_significance: float = 2.0
    orientation_min_coverage: float = 0.75
    orientation_min_effective_bins: float = 8.0
    orientation_max_axis_drift_deg: float = 20.0

    # ---- Masking ----
    dummy_val: float = -1.5
    ddummy: float = 0.6

    # ---- Background subtraction ----
    background_file: str = ""
    bg_scale_method: str = "transmission"
    bg_scale_value: float = 1.0
    transmission_sample: float = 1.0
    transmission_background: float = 1.0
    sample_thickness_m: float = 1.0

    # ---- Detector correction plugin ----
    # The production registry is intentionally empty. These fields document
    # an explicit future policy without enabling correction by configuration.
    detector_correction_mode: str = "disabled"
    detector_correction_policy_id: str = ""

    # ---- Smoothing ----
    smooth_method: str = "savgol"  # Best for preserving lamellar peak shape
    baseline_method: str = "normalize"  # panel provenance; algorithm mapping remains explicit
    smooth_span: int = 5
    savgol_window: int = 7
    savgol_order: int = 2

    # ---- IDF / correlation function ----
    q_corr_min: float = 0.15
    q_corr_max: float = 2.5  # use full experimental q range
    extrapolate_q0: bool = True
    extrapolate_qinf: bool = True
    n_z_points: int = 2048
    L_search_min: float = 9.0
    L_search_max: float = 50.0
    idf_peak_rel_thresh: float = 0.05
    idf_valley_rel_thresh: float = 0.05
    l1_min_ratio: float = 0.05
    l1_max_ratio: float = 0.95

    # ---- Bragg peak search range ----
    # For lamellar peaks: q ~ 0.3-0.9 nm^-1 (L ~ 7-21 nm)
    # Constrain for strain series to prevent misidentification
    q_bragg_min: float = 0.15   # keep low-q candidates visible for diagnostics
    q_bragg_max: float = 0.9    # static/thermal first-order lamellar window

    # ---- Lorentz fitting ----
    apply_lorentz_full: bool = True
    apply_lorentz_merid: bool = False
    lorentz_fit_method: str = "lmfit"

    # Tanget method quality gate: if tangent thickness < this value (nm)
    # and disagrees with IDF by > 60 %, the tangent is considered unreliable
    # and IDF is used instead.  Typical semi-crystalline lc is 2–8 nm.
    tangent_lc_min_nm: float = 2.0

    # IDF peak assignment: if True, IDF first peak = la (amorphous),
    # second peak = L. If False, first peak = lc (crystalline).
    # For most semi-crystalline polymers (PA6, PE, iPP), lc < la,
    # so the thinner phase measured by tangent/IDF is lc (False).
    idf_first_peak_is_la: bool = False

    # ---- Multi-method voting ----
    # Bragg is the most robust method for lamellar long period.
    # Lorentz and correlation are complementary but more sensitive to noise.
    multi_method_weights: Dict[str, float] = field(default_factory=lambda: {
        "bragg": 0.45, "lorentz": 0.25, "corr_peak": 0.20, "guinier": 0.10,
    })

    # ---- Anisotropy ----
    analysis_priority: str = "anisotropic"
    is_isotropic: bool = False

    # ---- Crystallinity ----
    crystallinity: float = np.nan
    crystallinity_gt_half: bool = False

    # ---- sasmodels lamellar fitting (方案 D) — optional, experimental ----
    use_sasmodels_fit: bool = False

    # ---- In-situ stretching ----
    strain_map: Dict[str, float] = field(default_factory=lambda: {
        "000": 0, "005": 5, "060": 60, "200": 200, "400": 400,
    })
    do_stretching: bool = False
    strain_values: Dict[str, float] = field(default_factory=dict)
    sdd_drift_ppm_per_C: float = 0.0
    beam_center_drift_px_per_C: float = 0.0
    alpha_thermal_expansion: float = 0.0

    # ---- In-situ temperature ----
    temperature_map: Dict[str, float] = field(default_factory=dict)
    do_melt_detection: bool = True
    do_avrami: bool = False
    T_melt_expected: Optional[float] = None

    # ---- Porod analysis ----
    do_porod: bool = True
    q_porod_min: float = 0.8
    q_porod_max: float = 2.5
    delta_rho_sq: float = np.nan

    # ---- Kratky analysis ----
    do_kratky: bool = True

    # ---- sasmodels fitting ----
    do_sasmodels: bool = False
    sasmodels_list: list = field(default_factory=lambda: ["lamellar"])

    # ---- Multi-scale (SAXS+WAXS) ----
    waxs_data_dir: str = ""

    # ---- Output ----
    output_dir: str = ""

    # ---- Reviewer-owned scientific evidence ----
    # Optional serialized ScientificReviewRecord payload.  Consumers must
    # validate it through the shared fail-closed review contract.
    scientific_review: Dict[str, Any] = field(default_factory=dict)

    # ---- Plotting ----
    save_figures: bool = True
    figure_format: str = "pdf"

    # ---- q-resolved orientation reliability diagnostics ----
    # These settings bound non-mutating sensitivity evidence. They do not
    # change the legacy scalar Herman calculation or promote calibration.
    orientation_reliability_enabled: bool = True
    orientation_bootstrap_replicates: int = 256
    orientation_center_offsets_px: Tuple[float, ...] = (-1.0, 0.0, 1.0)
    orientation_mask_dilation_px: Tuple[int, ...] = (1, 2)
    orientation_q_width_scales: Tuple[float, ...] = (0.75, 1.0, 1.25)
    orientation_chi_bin_scales: Tuple[float, ...] = (0.5, 1.0, 2.0)

    # This is the explicit detector-plane projection of the tensile axis. None
    # means no verified tensile reference for table-level Herman. It remains
    # append-only to preserve positional construction of older configurations.
    tensile_axis_deg: Optional[float] = None
    tensile_axis_convention: str | None = None

    # ---- Batch ingestion ----
    # Appended to preserve positional construction of older configurations.
    # None means unlimited. Any configured limit is provenance-visible.
    max_frames_per_condition: Optional[int] = None
    max_total_frames: Optional[int] = None


@dataclass
class ExperimentCondition:
    """Represents one experimental condition (strain/temperature/time point)."""
    label: str = ""
    value: float = np.nan
    condition_key: Any = None
    files: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    param_type: str = ""  # 'temperature', 'strain', 'time', or ''

    @property
    def filepath(self):
        """Convenience: first file path."""
        return self.files[0] if self.files else None

    @property
    def name(self):
        """Convenience: first file name."""
        return os.path.basename(self.filepath) if self.filepath else ""
