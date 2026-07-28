
import logging
logger = logging.getLogger(__name__)
# This legacy compatibility module predates the repository's strict Ruff
# baseline; retain its public names while allowing changed-file verification.
# ruff: noqa: E402, E741, F401, F841

"""
saxs_strain.py — Module 4B: In-situ tensile SAXS analysis.

Four-phase auto-detection, Herman orientation factor, void model,
lamellar+void decomposition, invariant conservation, full parameter tracking.

Reference: SAXS Design Document v1.0, Module 4B.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.integrate import trapezoid
from scipy.signal import find_peaks
from enum import Enum, auto

from .config import SAXSConfig
from .core import (
    bragg_long_period, correlation_function, scattering_invariant,
    lorentz_fit_long_period, analyze_single,
    LongPeriodResult, StructureParams, porod_analysis,
)
from .saxs_quality_contracts import (
    build_detector_quality_report,
    build_orientation_evidence,
    build_series_detector_quality_report,
    build_series_metric_evidence,
    build_series_orientation_evidence,
    sanitize_1d_profile,
)
from .saxs_output_helpers import (
    _data_quality_csv_fields,
    _detector_provenance_csv_fields,
)


def _aligned_source_values(values: Optional[List[str]], count: int) -> tuple[str, ...]:
    """Return source values only when the caller supplied one per frame."""

    if values is None or len(values) != count:
        return ()
    return tuple(str(value or "") for value in values)


def _coerce_strain_value(value) -> float:
    """Return one finite strain value or NaN without inventing an axis value."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


def _source_kwargs(
    source_ids: tuple[str, ...],
    raw_data_refs: tuple[str, ...],
    index: int,
) -> dict[str, str]:
    """Build explicit source kwargs without inventing an unbound source."""

    if not source_ids and not raw_data_refs:
        return {}
    kwargs: dict[str, str] = {}
    if source_ids:
        kwargs["source_id"] = source_ids[index]
    if raw_data_refs:
        kwargs["raw_data_ref"] = raw_data_refs[index]
    return {key: value for key, value in kwargs.items() if value}


class StrainPhase(Enum):
    """Four-phase tensile deformation model."""
    ELASTIC = auto()           # Phase I: elastic deformation
    PLASTIC_VOIDING = auto()   # Phase II: void nucleation & growth
    MICROFIBRILLATION = auto() # Phase III: microfibril formation
    FRACTURE = auto()          # Phase IV: structural failure


@dataclass
class StrainPointResult:
    """Single strain point analysis result."""
    strain_pct: float = 0.0
    phase: StrainPhase = StrainPhase.ELASTIC
    
    # Long period
    L_nm: float = np.nan
    q_star_nm1: float = np.nan
    
    # Structure params
    lc_nm: float = np.nan
    la_nm: float = np.nan
    phi_c: float = np.nan
    
    # Invariant
    Q_star: float = np.nan
    Q_star_rel: float = np.nan
    Q_star_normalized: float = np.nan
    
    # Void analysis
    has_voids: bool = False
    phi_void: float = np.nan
    void_ar: float = np.nan       # aspect ratio
    
    # Herman orientation factor
    f_herman: float = np.nan
    f_herman_sub: float = np.nan   # sub-tropical
    f_herman_eq: float = np.nan    # equatorial
    
    # Quality metrics
    confidence: float = 0.0
    method: str = ""
    data_quality_report: Dict = None
    metric_evidence: Dict = None
    detector_quality_report: Dict = None
    raw_detector_quality_report: Dict = None
    orientation_evidence: Dict = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class StrainSeriesResult:
    """Complete in-situ strain SAXS analysis result."""
    strain_points: List[StrainPointResult] = field(default_factory=list)
    phase_boundaries: Dict[StrainPhase, float] = field(default_factory=dict)
    
    # Tracking arrays
    strains: np.ndarray = None
    L_array: np.ndarray = None
    lc_array: np.ndarray = None
    la_array: np.ndarray = None
    Q_star_array: np.ndarray = None
    Q_star_rel_array: np.ndarray = None
    f_herman_array: np.ndarray = None
    phi_void_array: np.ndarray = None
    metric_evidence: Dict = None
    detector_quality_report: Dict = None
    raw_detector_quality_report: Dict = None
    orientation_evidence: Dict = None

    def get_phase_transition(self) -> Dict:
        """Return phase transition strains."""
        return {
            'elastic_to_voiding': self.phase_boundaries.get(StrainPhase.PLASTIC_VOIDING, np.nan),
            'voiding_to_microfibril': self.phase_boundaries.get(StrainPhase.MICROFIBRILLATION, np.nan),
            'microfibril_to_fracture': self.phase_boundaries.get(StrainPhase.FRACTURE, np.nan),
        }

    def to_dataframe(self):
        """Convert to pandas DataFrame for export."""
        import pandas as pd

        def metric_level_summary(payload):
            if not isinstance(payload, dict):
                return None
            pairs = []
            for key in sorted(payload):
                item = payload.get(key)
                if isinstance(item, dict) and item.get('level'):
                    pairs.append(f"{key}:{item['level']}")
            return '|'.join(pairs) or None

        rows = []
        for sp in self.strain_points:
            row = {
                'Strain(%)': sp.strain_pct,
                'Phase': sp.phase.name,
                'L(nm)': round(sp.L_nm, 2) if np.isfinite(sp.L_nm) else None,
                'lc(nm)': round(sp.lc_nm, 2) if np.isfinite(sp.lc_nm) else None,
                'la(nm)': round(sp.la_nm, 2) if np.isfinite(sp.la_nm) else None,
                'phi_c': round(sp.phi_c, 3) if np.isfinite(sp.phi_c) else None,
                'Q_star': f"{sp.Q_star:.4e}" if np.isfinite(sp.Q_star) else None,
                'Q_star_rel': round(sp.Q_star_rel, 4) if np.isfinite(sp.Q_star_rel) else None,
                'Q_star_norm': round(sp.Q_star_normalized, 4) if np.isfinite(sp.Q_star_normalized) else None,
                'f_Herman': round(sp.f_herman, 3) if np.isfinite(sp.f_herman) else None,
                'phi_void': round(sp.phi_void, 3) if np.isfinite(sp.phi_void) else None,
                'void_AR': round(sp.void_ar, 2) if np.isfinite(sp.void_ar) else None,
                'Confidence': round(sp.confidence, 2),
                'Method': sp.method,
                'Metric_evidence_levels': metric_level_summary(sp.metric_evidence),
            }
            row.update(
                _detector_provenance_csv_fields(sp.raw_detector_quality_report)
            )
            row.update(_data_quality_csv_fields(sp.data_quality_report))
            rows.append(row)
        return pd.DataFrame(rows)


# ======================================================================
#  Phase detection
# ======================================================================

def detect_strain_phase(
    strain_pct: float,
    Q_star: float,
    Q_star_ref: float,
    q: np.ndarray,
    I: np.ndarray,
    cfg: SAXSConfig,
) -> StrainPhase:
    """Auto-detect deformation phase from scattering data.

    Phase detection logic (from design doc):
    - Phase I: Q* nearly constant (<5% change), no excess low-q
    - Phase II: Q* starts increasing, excess low-q appears (void nucleation)
    - Phase III: Q* plateaus or decreases slightly, strong anisotropy
    - Phase IV: Q* drops >30%, structure collapse indicators

    Returns the detected phase.
    """
    Q_norm = Q_star / Q_star_ref if Q_star_ref > 0 else 1.0
    
    # Check for excess low-q scattering (void indicator)
    q_low = q[q <= 0.08]
    I_low = I[q <= 0.08]
    if len(q_low) > 3 and len(I_low) > 3:
        # Fit power law in low-q: I ~ q^(-alpha)
        pos = (I_low > 0) & (q_low > 0)
        if np.sum(pos) > 3:
            try:
                p = np.polyfit(np.log(q_low[pos]), np.log(I_low[pos]), 1)
                alpha = -p[0]
            except Exception:
                alpha = 0
                logger.warning("SAXS strain phase low-q power-law fit failed.", exc_info=True)
        else:
            alpha = 0
    else:
        alpha = 0
    
    # Phase classification
    if Q_norm < 0.3 or (strain_pct > 300 and Q_norm < 0.5):
        return StrainPhase.FRACTURE
    elif alpha > 3.5 and Q_norm > 1.05:
        return StrainPhase.MICROFIBRILLATION
    elif alpha > 2.8 or Q_norm > 1.08:
        return StrainPhase.PLASTIC_VOIDING
    else:
        return StrainPhase.ELASTIC


# ======================================================================
#  Herman orientation factor
# ======================================================================

def herman_orientation_factor(
    I_meridional: np.ndarray,
    I_equatorial: np.ndarray,
    chi_mer: np.ndarray = None,
    chi_eq: np.ndarray = None,
) -> Dict:
    """Compute Herman orientation factor from sector-integrated intensities.

    For polymers with lamellar stacks:
      f = (3<cos^2(phi)> - 1) / 2

    where <cos^2(phi)> = integral(I(chi)*cos^2(chi)*sin(chi) dchi)
                        / integral(I(chi)*sin(chi) dchi)

    f = 1.0  -> perfect orientation along reference direction
    f = 0.0  -> random orientation
    f = -0.5 -> perfect orientation perpendicular

    Reference: Design Document Module 4B & Module 5
    """
    result = {'f': np.nan, 'f_sub': np.nan, 'f_eq': np.nan,
              'cos2_avg': np.nan, 'method': 'none'}

    # Meridional (along stretch) — sub-tropical region
    if I_meridional is not None and len(I_meridional) > 5:
        n = len(I_meridional)
        if chi_mer is None:
            chi_mer = np.linspace(-np.pi/12, np.pi/12, n)  # +/- 15 deg
        
        # Filter chi to [-15, 15] degrees
        mask = (np.abs(chi_mer) <= np.pi / 12)
        if np.sum(mask) > 3:
            chi_f = chi_mer[mask]
            I_f = I_meridional[mask]
            
            cos2_chi = np.cos(chi_f) ** 2
            sin_abs = np.abs(np.sin(chi_f))
            
            numerator = trapezoid(I_f * cos2_chi * sin_abs, chi_f)
            denominator = trapezoid(I_f * sin_abs, chi_f)
            
            if denominator > 0:
                cos2_avg = numerator / denominator
                f = (3 * cos2_avg - 1) / 2
                result['cos2_avg'] = cos2_avg
                result['f_sub'] = f
                result['f'] = f  # meridional is primary for lamellar
                result['method'] = 'azimuthal_integral'

    # Equatorial (perpendicular to stretch)
    if I_equatorial is not None and len(I_equatorial) > 5:
        n = len(I_equatorial)
        if chi_eq is None:
            chi_eq = np.linspace(np.pi/2 - np.pi/12, np.pi/2 + np.pi/12, n)
        
        mask = (np.abs(chi_eq - np.pi/2) <= np.pi / 12)
        if np.sum(mask) > 3:
            chi_f = chi_eq[mask]
            I_f = I_equatorial[mask]
            
            cos2_chi = np.cos(chi_f) ** 2
            sin_abs = np.abs(np.sin(chi_f))
            
            numerator = trapezoid(I_f * cos2_chi * sin_abs, chi_f)
            denominator = trapezoid(I_f * sin_abs, chi_f)
            
            if denominator > 0:
                cos2_avg = numerator / denominator
                result['f_eq'] = (3 * cos2_avg - 1) / 2

    return result


def herman_from_sector_data(
    sector_data: Dict[str, Dict],
    q_range: Tuple[float, float] = None,
    cfg: Optional[SAXSConfig] = None,
) -> Dict:
    """Compute Herman factor from sector-integrated data dictionary.

    sector_data: {
        'meridional': {'chi': array, 'I': array, 'q': array},
        'equatorial': {'chi': array, 'I': array, 'q': array},
    }
    """
    if not isinstance(sector_data, dict):
        return _invalid_sector_data_result()

    if all(key in sector_data for key in ("I_2d", "q_2d", "chi_rad")):
        try:
            from .saxs_anisotropy import analyze_anisotropy

            I_2d = np.asarray(sector_data["I_2d"], dtype=float)
            q_2d = np.asarray(sector_data["q_2d"], dtype=float)
            chi_rad = np.asarray(sector_data["chi_rad"], dtype=float)
            q_1d = np.asarray(sector_data.get("q", q_2d), dtype=float)
            I_1d = np.asarray(
                sector_data.get("I_full", np.nanmean(I_2d, axis=0)),
                dtype=float,
            )
            orientation = analyze_anisotropy(
                I_2d,
                q_2d,
                chi_rad,
                q_1d,
                I_1d,
                cfg=cfg,
            )
            f_value = float(getattr(orientation, "f_herman", np.nan))
            return {
                "f": f_value,
                "f_sub": float(getattr(orientation, "f_herman_sub", np.nan)),
                "f_eq": float(getattr(orientation, "f_herman_eq", np.nan)),
                "cos2_avg": (2.0 * f_value + 1.0) / 3.0 if np.isfinite(f_value) else np.nan,
                "method": "analyze_anisotropy",
                "detector_quality_report": getattr(
                    orientation, "detector_quality_report", None
                ),
                "orientation_evidence": getattr(orientation, "orientation_evidence", None),
                "orientation_axis_deg": getattr(orientation, "orientation_axis_deg", np.nan),
                "orientation_axis_source": getattr(orientation, "orientation_axis_source", "unavailable"),
                "orientation_axis_strength": getattr(orientation, "orientation_axis_strength", np.nan),
                "orientation_axis_confidence": getattr(orientation, "orientation_axis_confidence", 0.0),
            }
        except Exception:
            logger.warning("Canonical SAXS orientation payload analysis failed.", exc_info=True)

    mer_data = sector_data.get('meridional', {})
    eq_data = sector_data.get('equatorial', {})
    if not isinstance(mer_data, dict) or not isinstance(eq_data, dict):
        return _invalid_sector_data_result()

    I_mer = mer_data.get('I', None)
    I_eq = eq_data.get('I', None)
    chi_mer = mer_data.get('chi', None)
    chi_eq = eq_data.get('chi', None)

    # If q_range specified, integrate over that q range
    if q_range is not None and 'q' in mer_data:
        q_mer = mer_data['q']
        mask = (q_mer >= q_range[0]) & (q_mer <= q_range[1])
        if np.sum(mask) > 0:
            I_mer = np.array([np.mean(I_mer[:, mask], axis=1)]) if I_mer.ndim > 1 else I_mer[mask]

    return herman_orientation_factor(I_mer, I_eq, chi_mer, chi_eq)


def _invalid_sector_data_result(
    reason: str = "strain_sector_data_invalid",
) -> Dict:
    """Return explicit Unusable orientation evidence for malformed sectors."""

    detector = build_detector_quality_report(
        np.empty((0, 0), dtype=float),
        source_kind="sector_map",
    )
    evidence = build_orientation_evidence(
        {},
        detector,
        applicability="supported",
        source_ref="saxs_strain.herman_from_sector_data",
    ).to_dict()
    reason_codes = list(evidence.get("reason_codes") or ())
    reason_codes.append(reason)
    evidence["reason_codes"] = tuple(dict.fromkeys(reason_codes))
    physical_checks = dict(evidence.get("physical_checks") or {})
    physical_checks["input_validation_reason"] = reason
    evidence["physical_checks"] = physical_checks
    return {
        "f": np.nan,
        "f_sub": np.nan,
        "f_eq": np.nan,
        "cos2_avg": np.nan,
        "method": "unavailable",
        "reason_codes": (reason,),
        "detector_quality_report": detector.to_dict(),
        "orientation_evidence": evidence,
    }


# ======================================================================
#  Void analysis
# ======================================================================

def detect_voids(
    q: np.ndarray,
    I: np.ndarray,
    cfg: SAXSConfig,
) -> Dict:
    """Detect and characterize voids/scattering inhomogeneities.

    Voids produce excess low-q scattering following a power law or Guinier regime.
    For ellipsoidal voids, the scattering can be decomposed as:
        I_total(q) = I_lamellar(q) + I_void(q)

    Returns dict with void indicators.
    """
    result = {
        'has_voids': False,
        'phi_void': np.nan,
        'void_ar': np.nan,        # aspect ratio
        'void_Rg': np.nan,        # radius of gyration (nm)
        'excess_low_q': np.nan,
        'method': 'none',
    }

    # 1. Porod slope check: ideal 2-phase system has slope -4
    porod = porod_analysis(q, I, cfg)
    slope = porod.get('slope', np.nan)
    if np.isfinite(slope) and slope > -3.5:
        result['has_voids'] = True
        result['method'] = 'porod_deviation'

    # 2. Low-q excess: compare observed I(q) vs Guinier extrapolation
    q_low = q[q <= 0.1]
    I_low = I[q <= 0.1]
    if len(q_low) >= 5:
        pos = (I_low > 0) & (q_low > 1e-6)
        if np.sum(pos) >= 5:
            # Guinier: I(q) = I(0) * exp(-q^2 * Rg^2 / 3)
            try:
                p = np.polyfit(q_low[pos]**2, np.log(I_low[pos]), 1)
                I0 = np.exp(p[1])
                Rg2 = -3 * p[0]
                result['void_Rg'] = np.sqrt(Rg2) if Rg2 > 0 else np.nan
            except Exception:
                logger.warning("SAXS void Guinier fit failed.", exc_info=True)

    # 3. Estimate void volume fraction from invariant ratio
    Q_total = trapezoid(I * q**2, q)
    if np.isfinite(Q_total) and Q_total > 0:
        # Excess invariant in low-q beyond lamellar contribution
        q_mid = q[(q >= 0.08) & (q <= 0.3)]
        if len(q_mid) > 3:
            # In two-phase system, Q ~ phi*(1-phi)*(delta_rho)^2
            # Void fraction estimation requires absolute intensity calibration
            result['excess_low_q'] = Q_total

    return result


# ======================================================================
#  Full strain series analysis
# ======================================================================


def analyze_strain_series(
    strains: List[float],
    q_list: List[np.ndarray],
    I_list: List[np.ndarray],
    sector_data_list: Optional[List[Dict]] = None,
    cfg: Optional[SAXSConfig] = None,
    verbose: bool = False,
    detector_quality_reports: Optional[List[Dict]] = None,
    source_ids: Optional[List[str]] = None,
    raw_data_refs: Optional[List[str]] = None,
) -> StrainSeriesResult:
    """Analyze a complete in-situ tensile SAXS experiment.

    Parameters
    ----------
    strains : list of float
        Strain values (%) for each measurement point.
    q_list : list of np.ndarray
        Scattering vector q for each strain point.
    I_list : list of np.ndarray
        Intensity I(q) for each strain point.
    sector_data_list : list of dict, optional
        Sector-integrated data for each point (for Herman factor).
    cfg : SAXSConfig, optional
        Configuration object.

    Returns
    -------
    StrainSeriesResult with full analysis.
    """
    if cfg is None:
        cfg = SAXSConfig()

    n_points = len(strains)
    if len(q_list) != n_points or len(I_list) != n_points:
        raise ValueError("strains, q_list, I_list must have same length")

    source_ids_aligned = _aligned_source_values(source_ids, n_points)
    raw_data_refs_aligned = _aligned_source_values(raw_data_refs, n_points)

    # Normalize strains
    strains_arr = np.asarray(
        [_coerce_strain_value(value) for value in strains],
        dtype=float,
    )
    sanitized_profiles = [
        sanitize_1d_profile(q_values, intensity_values)
        for q_values, intensity_values in zip(q_list, I_list)
    ]

    # Reference: first point (unstretched)
    if sanitized_profiles:
        reference_profile = sanitized_profiles[0]
        Q_ref = scattering_invariant(
            reference_profile.q,
            reference_profile.intensity,
            cfg=cfg,
        )
    else:
        Q_ref = np.nan

    result = StrainSeriesResult()
    result.strains = strains_arr
    result.L_array = np.full(n_points, np.nan)
    result.lc_array = np.full(n_points, np.nan)
    result.la_array = np.full(n_points, np.nan)
    result.Q_star_array = np.full(n_points, np.nan)
    result.Q_star_rel_array = np.full(n_points, np.nan)
    result.f_herman_array = np.full(n_points, np.nan)
    result.phi_void_array = np.full(n_points, np.nan)

    phase_boundaries = {}

    for i in range(n_points):
        strain = strains_arr[i]
        q = q_list[i]
        I = I_list[i]
        profile = sanitized_profiles[i]

        sp = StrainPointResult(strain_pct=float(strain))
        if not np.isfinite(strain):
            sp.warnings.append("Invalid strain axis value; retained as NaN")
        if detector_quality_reports is not None and len(detector_quality_reports) == n_points:
            sp.raw_detector_quality_report = detector_quality_reports[i]

        # ---- Core analysis (strain-aware) ----
        try:
            # Use strain-aware peak search (constrain around reference)
            if np.isfinite(result.L_array[0]) and result.L_array[0] > 2 and result.L_array[0] < 50:
                q_ref_0 = 2 * np.pi / result.L_array[0]
                cfg.q_bragg_min = max(0.25, q_ref_0 * 0.50)
                cfg.q_bragg_max = min(1.5, q_ref_0 * 1.50)
                cfg.q_corr_min = max(0.10, q_ref_0 * 0.40)
                cfg.q_corr_max = min(2.0, q_ref_0 * 1.60)
            # else: use cfg defaults (already 0.30-1.2)
            
            source_kwargs = _source_kwargs(source_ids_aligned, raw_data_refs_aligned, i)
            saxs_result = analyze_single(q, I, cfg, **source_kwargs)
            lp = saxs_result.long_period
            struct = saxs_result.structure
            
            sp.L_nm = lp.L_best
            sp.q_star_nm1 = 2 * np.pi / lp.L_best if np.isfinite(lp.L_best) and lp.L_best > 0 else np.nan
            sp.method = lp.method_used
            sp.confidence = lp.L_confidence
            
            sp.lc_nm = struct.lc
            sp.la_nm = struct.la
            sp.phi_c = struct.phi_c
            sp.data_quality_report = getattr(saxs_result, "data_quality_report", None)
            sp.metric_evidence = getattr(saxs_result, "metric_evidence", None)
            sp.detector_quality_report = getattr(saxs_result, "detector_quality_report", None)
            sp.orientation_evidence = getattr(saxs_result, "orientation_evidence", None)
        except Exception as e:
            sp.warnings.append(f"Core analysis: {e}")
            logger.warning("SAXS strain frame core analysis failed.", exc_info=True)

        # ---- Invariant ----
        Q_star = scattering_invariant(
            profile.q,
            profile.intensity,
            cfg=cfg,
        )
        sp.Q_star = Q_star
        sp.Q_star_rel = Q_star / Q_ref if Q_ref > 0 else 1.0
        sp.Q_star_normalized = sp.Q_star_rel
        result.Q_star_array[i] = Q_star
        result.Q_star_rel_array[i] = sp.Q_star_rel

        # ---- Phase detection ----
        phase = detect_strain_phase(
            strain,
            Q_star,
            Q_ref,
            profile.q,
            profile.intensity,
            cfg,
        )
        sp.phase = phase

        # Track phase boundaries
        if np.isfinite(strain) and phase not in phase_boundaries:
            phase_boundaries[phase] = strain

        # ---- Void analysis ----
        void = detect_voids(profile.q, profile.intensity, cfg)
        sp.has_voids = void['has_voids']
        sp.phi_void = void['phi_void']
        sp.void_ar = void['void_ar']
        result.phi_void_array[i] = void['phi_void'] if np.isfinite(void['phi_void']) else np.nan

        # ---- Herman orientation factor ----
        if sector_data_list is not None and i < len(sector_data_list):
            sd = sector_data_list[i]
            if sd is not None:
                try:
                    herman = herman_from_sector_data(sd, cfg=cfg)
                except Exception:
                    logger.warning(
                        "SAXS strain sector payload failed closed.",
                        exc_info=True,
                    )
                    herman = _invalid_sector_data_result()
                sp.f_herman = herman.get('f', np.nan)
                sp.f_herman_sub = herman.get('f_sub', np.nan)
                sp.f_herman_eq = herman.get('f_eq', np.nan)
                if herman.get("detector_quality_report") is not None:
                    sp.detector_quality_report = herman["detector_quality_report"]
                if herman.get("orientation_evidence") is not None:
                    sp.orientation_evidence = herman["orientation_evidence"]
                result.f_herman_array[i] = sp.f_herman

        result.strain_points.append(sp)
        result.L_array[i] = sp.L_nm
        result.lc_array[i] = sp.lc_nm
        result.la_array[i] = sp.la_nm

    result.metric_evidence = build_series_metric_evidence(
        [point.metric_evidence for point in result.strain_points],
        metric_names=("porod", "kratky", "invariant", "lamellar"),
        source_ref="saxs_strain.metric_evidence",
        condition_name="strain_pct",
        condition_values=result.strains,
    )
    detector_quality = build_series_detector_quality_report(
        [point.detector_quality_report for point in result.strain_points],
        source_ref="saxs_strain.detector_quality_report",
    )
    orientation = build_series_orientation_evidence(
        [point.orientation_evidence for point in result.strain_points],
        source_ref="saxs_strain.orientation_evidence",
    )
    if detector_quality is not None:
        result.detector_quality_report = detector_quality
    raw_detector_quality = build_series_detector_quality_report(
        [point.raw_detector_quality_report for point in result.strain_points],
        source_ref="saxs_strain.raw_detector_quality_report",
    )
    if raw_detector_quality is not None:
        result.raw_detector_quality_report = raw_detector_quality
    if orientation is not None:
        result.orientation_evidence = orientation
    result.phase_boundaries = phase_boundaries

    if verbose:
        print(f"Strain series: {n_points} points")
        print(f"Phase boundaries: {phase_boundaries}")
        if np.any(np.isfinite(result.L_array)):
            print(f"L range: {np.nanmin(result.L_array):.1f} - {np.nanmax(result.L_array):.1f} nm")

    return result


# ======================================================================
#  Invariant conservation check
# ======================================================================

def check_invariant_conservation(
    strains: np.ndarray,
    Q_star_array: np.ndarray,
    tolerance: float = 0.05,
) -> Dict:
    """Verify invariant conservation during deformation.

    In an ideal isochoric two-phase deformation, Q* should remain constant.
    Significant deviations indicate void formation or structural changes.

    Returns dict with conservation metrics.
    """
    result = {
        'Q_mean': np.nan,
        'Q_std': np.nan,
        'Q_cv': np.nan,           # coefficient of variation
        'conserved': False,
        'max_deviation': np.nan,
        'max_dev_strain': np.nan,
    }

    valid = np.isfinite(Q_star_array)
    if np.sum(valid) < 2:
        return result

    Q_valid = Q_star_array[valid]
    strains_valid = strains[valid]

    Q_mean = np.mean(Q_valid)
    Q_std = np.std(Q_valid)
    result['Q_mean'] = Q_mean
    result['Q_std'] = Q_std
    result['Q_cv'] = Q_std / Q_mean if Q_mean > 0 else np.nan

    # Check if within tolerance
    result['conserved'] = result['Q_cv'] < tolerance

    # Find max deviation
    deviations = np.abs(Q_valid - Q_mean) / Q_mean
    max_idx = np.argmax(deviations)
    result['max_deviation'] = deviations[max_idx]
    result['max_dev_strain'] = strains_valid[max_idx]

    return result
