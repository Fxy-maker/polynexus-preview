
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

from dataclasses import dataclass, field, replace
from typing import Dict, List, Mapping, Optional, Tuple
import numpy as np
from scipy.integrate import trapezoid
from scipy.signal import find_peaks
from enum import Enum, auto

from .config import SAXSConfig
from .core import (
    bragg_long_period, correlation_function, scattering_invariant,
    lorentz_fit_long_period, analyze_single,
    LongPeriodResult, SAXSResult, StructureParams, porod_analysis,
)
from .saxs_quality_contracts import (
    DetectorQualityReport,
    QualityLevel,
    _as_1d_float_array,
    build_detector_quality_report,
    build_orientation_evidence,
    build_series_detector_quality_report,
    build_series_metric_evidence,
    build_series_orientation_evidence,
    build_orientation_tracking_evidence,
    metric_evidence_dataframe_fields,
    sanitize_1d_profile,
)
from .saxs_output_helpers import (
    _data_quality_csv_fields,
    _detector_provenance_csv_fields,
)
from .saxs_orientation_tracking import track_orientation_features


def _aligned_source_values(values: Optional[List[str]], count: int) -> tuple[str, ...]:
    """Return source values only when the caller supplied one per frame."""

    if values is None or len(values) != count:
        return ()
    return tuple(str(value or "") for value in values)


def _aligned_source_indices(values, count: int) -> tuple[int, ...]:
    """Accept only an explicit, one-per-frame source-index mapping."""

    if values is None or len(values) != count:
        return ()
    output: list[int] = []
    for value in values:
        if isinstance(value, (bool, np.bool_)):
            return ()
        try:
            index = int(value)
        except (TypeError, ValueError, OverflowError):
            return ()
        if index < 0 or float(value) != float(index):
            return ()
        output.append(index)
    return tuple(output) if len(set(output)) == count else ()


def _tracked_sector_peak(
    sector_data: Mapping[str, object],
    intensity_key: str,
    cfg: SAXSConfig,
    q_anchor: float,
) -> tuple[float, float]:
    if not np.isfinite(q_anchor) or q_anchor <= 0:
        return np.nan, np.nan
    q_values = sector_data.get("q", sector_data.get("q_2d"))
    intensity_values = sector_data.get(intensity_key)
    if q_values is None or intensity_values is None:
        return np.nan, np.nan
    try:
        q_array = np.asarray(q_values, dtype=float)
        intensity_array = np.asarray(intensity_values, dtype=float)
    except (TypeError, ValueError):
        return np.nan, np.nan
    if q_array.ndim != 1 or intensity_array.ndim != 1 or q_array.size != intensity_array.size:
        return np.nan, np.nan
    step_limit = getattr(cfg, "strain_peak_max_relative_step", 0.25)
    try:
        step_limit = float(step_limit)
    except (TypeError, ValueError, OverflowError):
        step_limit = 0.25
    if not np.isfinite(step_limit):
        step_limit = 0.25
    length, q_peak, _ = bragg_long_period(
        q_array,
        intensity_array,
        q_min=float(getattr(cfg, "q_bragg_min", 0.15)),
        q_max=float(getattr(cfg, "q_bragg_max", 0.9)),
        q_anchor=float(q_anchor),
        max_anchor_relative_shift=min(max(step_limit, 0.0), 0.25),
    )
    return float(q_peak), float(length)


def _fail_closed_tracked_lamellar_result(
    saxs_result: SAXSResult,
    *,
    reason: str,
) -> None:
    """Remove feature-dependent values after the series tracker rejects a frame."""

    long_period = saxs_result.long_period
    if long_period is not None:
        long_period.L_best = np.nan
        long_period.L_bragg = np.nan
        long_period.L_lorentz = np.nan
        long_period.L_corr_peak = np.nan
        long_period.L_guinier = np.nan
        long_period.L_confidence = 0.0
        long_period.q_peak_nm1 = np.nan
        long_period.method_used = "tracking_lost" if reason == "tracking_already_lost" else "unavailable"
        long_period.peak_selection_reason = reason

    structure = saxs_result.structure
    if structure is not None:
        for name in (
            "L",
            "lc",
            "la",
            "phi_c",
            "phi_c_invariant",
            "lc_porod_nm",
            "lc_tangent_nm",
            "lc_idf_nm",
            "lc_gamma_min_nm",
            "confidence_lc",
        ):
            setattr(structure, name, np.nan)

    metric_evidence = saxs_result.metric_evidence
    if isinstance(metric_evidence, dict):
        lamellar = metric_evidence.get("lamellar")
        if isinstance(lamellar, dict):
            lamellar["applicable"] = False
            lamellar["valid"] = False
            lamellar["level"] = "Unusable"
            lamellar["value"] = None
            reasons = [
                str(item)
                for item in lamellar.get("reason_codes", ())
                if str(item)
            ]
            if "tracked_feature_unavailable" not in reasons:
                reasons.append("tracked_feature_unavailable")
            if reason not in reasons:
                reasons.append(reason)
            lamellar["reason_codes"] = reasons


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


def _unavailable_raw_detector_quality_report() -> dict[str, object]:
    """Return raw-detector evidence without attributing sector defects to it."""

    return DetectorQualityReport(
        source_kind="raw_detector",
        reason_codes=("raw_detector_quality_unavailable",),
        level=QualityLevel.DIAGNOSTIC,
    ).to_dict()


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
    q_peak_total_nm1: float = np.nan
    q_peak_meridional_nm1: float = np.nan
    L_meridional_nm: float = np.nan
    q_peak_equatorial_nm1: float = np.nan
    L_equatorial_nm: float = np.nan
    feature_tracking_status: str = "unavailable"
    feature_tracking_reason_codes: List[str] = field(default_factory=list)
    analysis_result: Optional[SAXSResult] = field(default=None, repr=False)
    
    # Structure params
    lc_nm: float = np.nan
    la_nm: float = np.nan
    phi_c: float = np.nan
    
    # Invariant
    invariant_Q: float = np.nan
    invariant_Q_rel: float = np.nan
    # Legacy input aliases retained for detached historical results.
    Q_star: float = np.nan
    Q_star_rel: float = np.nan
    Q_star_normalized: float = np.nan
    
    # Void analysis
    has_voids: bool = False
    phi_void: float = np.nan
    void_ar: float = np.nan       # aspect ratio
    
    # Herman orientation factor
    f_herman: float = np.nan
    f_herman_raw: float = np.nan
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
    q_resolved_orientation_evidence: object = None
    metric_source_channel: str = "total"


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
    invariant_Q_array: np.ndarray = None
    invariant_Q_rel_array: np.ndarray = None
    # Legacy input aliases retained for detached historical results.
    Q_star_array: np.ndarray = None
    Q_star_rel_array: np.ndarray = None
    f_herman_array: np.ndarray = None
    phi_void_array: np.ndarray = None
    metric_evidence: Dict = None
    detector_quality_report: Dict = None
    raw_detector_quality_report: Dict = None
    orientation_evidence: Dict = None
    q_resolved_orientation_evidence: List[object] = field(default_factory=list)
    orientation_tracking_evidence: Dict = None

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
            invariant_Q = (
                sp.invariant_Q if np.isfinite(sp.invariant_Q) else sp.Q_star
            )
            invariant_Q_rel = (
                sp.invariant_Q_rel
                if np.isfinite(sp.invariant_Q_rel)
                else sp.Q_star_rel
            )
            row = {
                'Strain(%)': sp.strain_pct,
                'Phase': sp.phase.name,
                'L(nm)': round(sp.L_nm, 2) if np.isfinite(sp.L_nm) else None,
                'lc(nm)': round(sp.lc_nm, 2) if np.isfinite(sp.lc_nm) else None,
                'la(nm)': round(sp.la_nm, 2) if np.isfinite(sp.la_nm) else None,
                'phi_c': round(sp.phi_c, 3) if np.isfinite(sp.phi_c) else None,
                'invariant_Q': f"{invariant_Q:.4e}" if np.isfinite(invariant_Q) else None,
                'invariant_Q_rel': round(invariant_Q_rel, 4) if np.isfinite(invariant_Q_rel) else None,
                'f_Herman': round(sp.f_herman, 3) if np.isfinite(sp.f_herman) else None,
                'phi_void': round(sp.phi_void, 3) if np.isfinite(sp.phi_void) else None,
                'void_AR': round(sp.void_ar, 2) if np.isfinite(sp.void_ar) else None,
                'Confidence': round(sp.confidence, 2),
                'Method': sp.method,
                'Metric_evidence_levels': metric_level_summary(sp.metric_evidence),
            }
            row.update(metric_evidence_dataframe_fields(sp.metric_evidence))
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
    sanitized = sanitize_1d_profile(q, I)
    q = sanitized.q
    I = sanitized.intensity
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

    def prepare_profile(
        intensity_values: object,
        chi_values: object,
        default_start: float,
        default_end: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        if intensity_values is None:
            return np.asarray([], dtype=float), np.asarray([], dtype=float)
        intensity_array = _as_1d_float_array(intensity_values)
        if chi_values is None:
            chi_array = np.linspace(
                default_start, default_end, intensity_array.size
            )
        else:
            chi_array = _as_1d_float_array(chi_values)
        count = min(intensity_array.size, chi_array.size)
        if count == 0:
            return np.asarray([], dtype=float), np.asarray([], dtype=float)
        chi_pair = chi_array[:count].copy()
        intensity_pair = intensity_array[:count].copy()
        valid = np.isfinite(chi_pair) & np.isfinite(intensity_pair)
        chi_pair = chi_pair[valid]
        intensity_pair = intensity_pair[valid]
        if chi_pair.size > 1 and np.any(np.diff(chi_pair) < 0):
            order = np.argsort(chi_pair, kind="stable")
            chi_pair = chi_pair[order]
            intensity_pair = intensity_pair[order]
        return intensity_pair, chi_pair

    meridional_intensity, meridional_chi = prepare_profile(
        I_meridional, chi_mer, -np.pi / 12, np.pi / 12
    )
    equatorial_intensity, equatorial_chi = prepare_profile(
        I_equatorial, chi_eq, np.pi / 2 - np.pi / 12, np.pi / 2 + np.pi / 12
    )

    # Meridional (along stretch) — sub-tropical region
    if meridional_intensity.size > 5:
        
        # Filter chi to [-15, 15] degrees
        mask = np.abs(meridional_chi) <= np.pi / 12
        if np.sum(mask) > 3:
            chi_f = meridional_chi[mask]
            I_f = meridional_intensity[mask]
            
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
    if equatorial_intensity.size > 5:
        
        mask = np.abs(equatorial_chi - np.pi / 2) <= np.pi / 12
        if np.sum(mask) > 3:
            chi_f = equatorial_chi[mask]
            I_f = equatorial_intensity[mask]
            
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
    data_quality_report: Mapping[str, object] | None = None,
    q_target_nm1: float | None = None,
) -> Dict:
    """Compute Herman factor from sector-integrated data dictionary.

    sector_data: {
        'meridional': {'chi': array, 'I': array, 'q': array},
        'equatorial': {'chi': array, 'I': array, 'q': array},
    }
    """
    if not isinstance(sector_data, dict):
        return _invalid_sector_data_result()

    canonical_keys = ("I_2d", "q_2d", "chi_rad")
    canonical_present = any(key in sector_data for key in canonical_keys)
    if canonical_present and not all(key in sector_data for key in canonical_keys):
        return _invalid_sector_data_result(
            "strain_canonical_sector_payload_invalid"
        )

    if canonical_present:
        try:
            from .saxs_anisotropy import analyze_anisotropy

            I_2d = np.asarray(sector_data["I_2d"], dtype=float)
            q_2d = np.asarray(sector_data["q_2d"], dtype=float)
            chi_rad = np.asarray(sector_data["chi_rad"], dtype=float)
            if (
                I_2d.ndim != 2
                or q_2d.ndim != 1
                or chi_rad.ndim != 1
                or I_2d.shape != (chi_rad.size, q_2d.size)
                or chi_rad.size < 5
                or q_2d.size == 0
                or not np.all(np.isfinite(q_2d))
                or not np.all(np.isfinite(chi_rad))
            ):
                return _invalid_sector_data_result(
                    "strain_canonical_sector_payload_invalid"
                )
            support_count = sector_data.get("support_count")
            if support_count is None:
                image_finite = np.all(np.isfinite(I_2d))
            else:
                try:
                    support = np.asarray(support_count, dtype=float)
                except (TypeError, ValueError):
                    support = np.asarray([], dtype=float)
                image_finite = bool(
                    support.shape == I_2d.shape
                    and np.all(np.isfinite(support))
                    and np.all(support >= 0)
                    and not np.any((support > 0) & ~np.isfinite(I_2d))
                )
            if not image_finite:
                return _invalid_sector_data_result(
                    "strain_canonical_sector_payload_invalid"
                )
            q_1d = np.asarray(sector_data.get("q", q_2d), dtype=float)
            I_1d = np.asarray(
                sector_data["I_full"]
                if "I_full" in sector_data
                else np.nanmean(I_2d, axis=0),
                dtype=float,
            )
            raw_detector_quality = sector_data.get(
                "raw_detector_quality_report"
            )
            if raw_detector_quality is None:
                raw_detector_quality = _unavailable_raw_detector_quality_report()
            orientation = analyze_anisotropy(
                I_2d,
                q_2d,
                chi_rad,
                q_1d,
                I_1d,
                cfg=cfg,
                support_count=support_count,
                raw_detector_quality=raw_detector_quality,
                q_target_nm1=q_target_nm1,
            )
            f_value = float(getattr(orientation, "f_herman", np.nan))
            f_raw = float(getattr(orientation, "f_herman_raw", np.nan))
            orientation_evidence = getattr(orientation, "orientation_evidence", None)
            quality_blockers = _orientation_quality_blockers(data_quality_report)
            if quality_blockers:
                orientation_evidence = _block_orientation_evidence(
                    orientation_evidence,
                    raw_value=f_raw,
                    reason_codes=quality_blockers,
                )
                f_value = np.nan
            raw_detector_quality_report = getattr(
                orientation, "detector_quality_report", None
            )
            if raw_detector_quality_report is None:
                raw_detector_quality_report = raw_detector_quality
            return {
                "f": f_value,
                "f_raw": f_raw,
                "f_sub": float(getattr(orientation, "f_herman_sub", np.nan)),
                "f_eq": float(getattr(orientation, "f_herman_eq", np.nan)),
                "cos2_avg": (2.0 * f_value + 1.0) / 3.0 if np.isfinite(f_value) else np.nan,
                "method": "analyze_anisotropy",
                "detector_quality_report": build_detector_quality_report(
                    I_2d,
                    source_kind="sector_map",
                ).to_dict(),
                "raw_detector_quality_report": raw_detector_quality_report,
                "orientation_evidence": orientation_evidence,
                "q_resolved_orientation_evidence": getattr(
                    orientation, "q_resolved_orientation_evidence", None
                ),
                "orientation_axis_deg": getattr(orientation, "orientation_axis_deg", np.nan),
                "orientation_axis_source": getattr(orientation, "orientation_axis_source", "unavailable"),
                "orientation_axis_strength": getattr(orientation, "orientation_axis_strength", np.nan),
                "orientation_axis_confidence": getattr(orientation, "orientation_axis_confidence", 0.0),
                "principal_scattering_axis_deg": getattr(
                    orientation, "principal_scattering_axis_deg", np.nan
                ),
                "tensile_axis_deg": getattr(orientation, "tensile_axis_deg", np.nan),
                "reference_axis_deg": getattr(orientation, "reference_axis_deg", np.nan),
                "reference_axis_kind": getattr(
                    orientation, "reference_axis_kind", "unknown"
                ),
            }
        except Exception:
            logger.warning("Canonical SAXS orientation payload analysis failed.", exc_info=True)
            return _invalid_sector_data_result(
                "strain_canonical_sector_payload_invalid"
            )

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

    return _legacy_orientation_result(
        herman_orientation_factor(I_mer, I_eq, chi_mer, chi_eq),
        cfg=cfg,
    )


def _orientation_quality_blockers(
    report: Mapping[str, object] | None,
) -> tuple[str, ...]:
    """Return only the radial-1D quality gate that blocks 2D transport."""

    if not isinstance(report, Mapping):
        return ()

    level = str(report.get("level") or "").strip().lower()
    return ("orientation_input_quality_unusable",) if level == "unusable" else ()


def _block_orientation_evidence(
    evidence: Mapping[str, object] | None,
    *,
    raw_value: float,
    reason_codes: tuple[str, ...],
) -> dict:
    """Keep raw fit evidence while removing a blocked effective value."""

    payload = dict(evidence) if isinstance(evidence, Mapping) else {}
    fit_evidence = dict(payload.get("fit_evidence") or {})
    if np.isfinite(raw_value):
        fit_evidence["f_herman_raw"] = float(raw_value)
    fit_evidence.pop("f_herman", None)
    payload["value"] = dict(fit_evidence)
    payload["fit_evidence"] = fit_evidence
    physical_checks = dict(payload.get("physical_checks") or {})
    physical_checks["orientation_reliability_status"] = "blocked"
    physical_checks["orientation_reliability_reason_codes"] = list(reason_codes)
    payload["physical_checks"] = physical_checks
    payload["level"] = "Unusable"
    payload["applicable"] = False
    payload["reason_codes"] = tuple(
        dict.fromkeys(
            list(payload.get("reason_codes") or ())
            + ["orientation_reliability_blocked", *reason_codes]
        )
    )
    return payload


def _legacy_orientation_result(
    legacy: Mapping[str, object],
    *,
    cfg: Optional[SAXSConfig] = None,
) -> Dict:
    """Keep legacy Herman output diagnostic without promoting it to final."""

    f_raw = float(legacy.get("f", np.nan))
    detector = build_detector_quality_report(
        np.empty((0, 0), dtype=float),
        source_kind="sector_map",
    )
    raw_detector_quality = _unavailable_raw_detector_quality_report()
    reasons = ["legacy_orientation_unavailable"]
    try:
        tensile_axis = float(getattr(cfg, "tensile_axis_deg", np.nan))
    except (TypeError, ValueError):
        tensile_axis = np.nan
    if not np.isfinite(tensile_axis):
        reasons.append("tensile_axis_unknown")
    evidence = build_orientation_evidence(
        {
            "f_herman_raw": f_raw,
            "orientation_reliability_status": "unavailable",
            "orientation_reliability_reason_codes": reasons,
        },
        detector,
        applicability="supported",
        source_ref="saxs_strain.legacy_sector_adapter",
    ).to_dict()
    fit_evidence = dict(evidence.get("fit_evidence") or {})
    fit_evidence.update(
        {
            "feature_kind": "legacy_orientation",
            "orientation_axis_source": "legacy_sector_adapter",
            "orientation_axis_deg": None,
            "orientation_axis_strength": None,
            "orientation_axis_confidence": 0.0,
            "principal_scattering_axis_deg": None,
            "tensile_axis_deg": (
                float(tensile_axis) if np.isfinite(tensile_axis) else None
            ),
            "reference_axis_deg": None,
            "reference_axis_kind": "legacy_principal_axis",
            "orientation_vector_kind": "legacy_principal_axis",
            "herman_convention": "detector_plane_2d_v1",
            "isotropic_baseline": 0.25,
            "q_star_candidate": None,
            "selected_q_range_nm1": None,
        }
    )
    evidence["value"] = dict(fit_evidence)
    evidence["fit_evidence"] = fit_evidence
    evidence_reasons = list(evidence.get("reason_codes") or ())
    evidence_reasons.extend(reasons)
    evidence["reason_codes"] = tuple(dict.fromkeys(evidence_reasons))
    evidence["applicable"] = False
    physical_checks = dict(evidence.get("physical_checks") or {})
    physical_checks["orientation_reliability_status"] = "unavailable"
    physical_checks["orientation_reliability_reason_codes"] = reasons
    evidence["physical_checks"] = physical_checks
    return {
        "f": np.nan,
        "f_raw": f_raw,
        "f_sub": float(legacy.get("f_sub", np.nan)),
        "f_eq": float(legacy.get("f_eq", np.nan)),
        "cos2_avg": float(legacy.get("cos2_avg", np.nan)),
        "method": "legacy_sector_adapter",
        "detector_quality_report": detector.to_dict(),
        "raw_detector_quality_report": raw_detector_quality,
        "orientation_evidence": evidence,
    }


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
        "f_raw": np.nan,
        "f_sub": np.nan,
        "f_eq": np.nan,
        "cos2_avg": np.nan,
        "method": "unavailable",
        "reason_codes": (reason,),
        "detector_quality_report": detector.to_dict(),
        "raw_detector_quality_report": _unavailable_raw_detector_quality_report(),
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
    sanitized = sanitize_1d_profile(q, I)
    q = sanitized.q
    I = sanitized.intensity
    result = {
        'has_voids': False,
        'phi_void': np.nan,
        'void_ar': np.nan,        # aspect ratio
        'void_Rg': np.nan,        # radius of gyration (nm)
        'excess_low_q': np.nan,
        'method': 'none',
        'reason': 'absolute_contrast_required',
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
    frame_source_indices: Optional[List[int]] = None,
    q_pyfai_list: Optional[List[np.ndarray]] = None,
    I_pyfai_list: Optional[List[np.ndarray]] = None,
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
    frame_source_indices_aligned = _aligned_source_indices(frame_source_indices, n_points)
    frame_source_indices_invalid = (
        frame_source_indices is not None and not frame_source_indices_aligned
    )

    # Normalize strains
    strains_arr = np.asarray(
        [_coerce_strain_value(value) for value in strains],
        dtype=float,
    )
    sanitized_profiles = []
    try:
        q_floor = float(getattr(cfg, "q_min", np.nan))
    except (TypeError, ValueError, OverflowError):
        q_floor = np.nan
    for q_values, intensity_values in zip(q_list, I_list):
        profile = sanitize_1d_profile(q_values, intensity_values)
        if np.isfinite(q_floor) and q_floor > 0:
            keep = profile.q >= q_floor
            if np.any(~keep):
                profile = type(profile)(
                    profile.q[keep],
                    profile.intensity[keep],
                    profile.original_point_count,
                    profile.aligned_point_count,
                    int(np.count_nonzero(keep)),
                    tuple(profile.actions) + ("configured_q_min_applied",),
                )
        sanitized_profiles.append(profile)

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
    result.invariant_Q_array = np.full(n_points, np.nan)
    result.invariant_Q_rel_array = np.full(n_points, np.nan)
    result.f_herman_array = np.full(n_points, np.nan)
    result.phi_void_array = np.full(n_points, np.nan)

    phase_boundaries = {}
    previous_q_peak = np.nan
    tracking_has_seed = False
    tracking_lost = False

    for i in range(n_points):
        strain = strains_arr[i]
        q = q_list[i]
        I = I_list[i]
        profile = sanitized_profiles[i]

        sp = StrainPointResult(strain_pct=float(strain))
        frame_cfg = replace(cfg)
        q_anchor = float(previous_q_peak) if tracking_has_seed else None
        tracking_locked_out = tracking_lost
        # Invariant, Porod, Guinier, Kratky, long-period and structure
        # metrics are always derived from the full scattering profile.
        # Sector data below is an orientation-only input.
        sp.metric_source_channel = "total"
        if not np.isfinite(strain):
            sp.warnings.append("Invalid strain axis value; retained as NaN")
        if detector_quality_reports is not None and len(detector_quality_reports) == n_points:
            sp.raw_detector_quality_report = detector_quality_reports[i]

        # ---- Core analysis (strain-aware) ----
        try:
            # Use strain-aware peak search (constrain around reference)
            if np.isfinite(result.L_array[0]) and result.L_array[0] > 2 and result.L_array[0] < 50:
                q_ref_0 = 2 * np.pi / result.L_array[0]
                frame_cfg = replace(
                    frame_cfg,
                    q_bragg_min=max(0.25, q_ref_0 * 0.50),
                    q_bragg_max=min(1.5, q_ref_0 * 1.50),
                    q_corr_min=max(0.10, q_ref_0 * 0.40),
                    q_corr_max=min(2.0, q_ref_0 * 1.60),
                )
            # else: use cfg defaults (already 0.30-1.2)
            
            source_kwargs = _source_kwargs(source_ids_aligned, raw_data_refs_aligned, i)
            q_pyfai = (
                q_pyfai_list[i]
                if q_pyfai_list is not None and len(q_pyfai_list) == n_points
                else None
            )
            I_pyfai = (
                I_pyfai_list[i]
                if I_pyfai_list is not None and len(I_pyfai_list) == n_points
                else None
            )
            saxs_result = analyze_single(
                q,
                I,
                frame_cfg,
                q_anchor=q_anchor,
                q_pyfai=q_pyfai,
                I_pyfai=I_pyfai,
                **source_kwargs,
            )
            lp = saxs_result.long_period
            struct = saxs_result.structure

            sp.analysis_result = saxs_result
            if (
                not tracking_has_seed
                and str(getattr(lp, "peak_selection_reason", "none"))
                != "best_credible_lamellar"
            ):
                lp.q_peak_nm1 = np.nan
                lp.L_bragg = np.nan
                lp.L_best = np.nan
                lp.method_used = "unseeded"
            if tracking_locked_out:
                lp.q_peak_nm1 = np.nan
                lp.L_bragg = np.nan
                lp.L_best = np.nan
                lp.method_used = "tracking_lost"
                lp.peak_selection_reason = "tracking_already_lost"
            sp.q_peak_total_nm1 = float(getattr(lp, "q_peak_nm1", np.nan))
            if np.isfinite(sp.q_peak_total_nm1) and sp.q_peak_total_nm1 > 0:
                tracking_has_seed = True
                previous_q_peak = sp.q_peak_total_nm1
                sp.L_nm = 2 * np.pi / sp.q_peak_total_nm1
                sp.q_star_nm1 = sp.q_peak_total_nm1
                sp.feature_tracking_status = "seeded" if q_anchor is None else "tracked"
            else:
                if tracking_has_seed:
                    tracking_lost = True
                sp.L_nm = np.nan
                sp.q_star_nm1 = np.nan
                sp.feature_tracking_status = (
                    "tracking_lost" if tracking_has_seed else "unseeded"
                )
                sp.feature_tracking_reason_codes.extend(
                    [
                        "tracked_feature_unavailable",
                        str(getattr(lp, "peak_selection_reason", "none")),
                    ]
                )
                _fail_closed_tracked_lamellar_result(
                    saxs_result,
                    reason=str(getattr(lp, "peak_selection_reason", "none")),
                )
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
            failure_reason = "core_analysis_failed"
            if tracking_has_seed:
                tracking_lost = True
                sp.feature_tracking_status = "tracking_lost"
            else:
                sp.feature_tracking_status = "unseeded"
            sp.feature_tracking_reason_codes.extend(
                ["tracked_feature_unavailable", failure_reason]
            )
            sp.method = failure_reason
            sp.analysis_result = SAXSResult(
                q=profile.q,
                I=profile.intensity,
                I_smooth=profile.intensity,
                long_period=LongPeriodResult(
                    method_used=failure_reason,
                    peak_selection_reason=failure_reason,
                ),
                structure=StructureParams(),
                metric_evidence={
                    "lamellar": {
                        "applicable": False,
                        "valid": False,
                        "level": "Unusable",
                        "value": None,
                        "reason_codes": [
                            "tracked_feature_unavailable",
                            failure_reason,
                        ],
                    }
                },
                validation_summary=(
                    f"strain_core_analysis_failed:{type(e).__name__}"
                ),
            )
            logger.warning("SAXS strain frame core analysis failed.", exc_info=True)

        # ---- Invariant ----
        Q_star = scattering_invariant(
            profile.q,
            profile.intensity,
            cfg=frame_cfg,
        )
        sp.invariant_Q = Q_star
        sp.invariant_Q_rel = (
            Q_star / Q_ref
            if np.isfinite(Q_star) and np.isfinite(Q_ref) and Q_ref > 0
            else np.nan
        )
        result.invariant_Q_array[i] = Q_star
        result.invariant_Q_rel_array[i] = sp.invariant_Q_rel

        # ---- Phase detection ----
        phase = detect_strain_phase(
            strain,
            Q_star,
            Q_ref,
            profile.q,
            profile.intensity,
            frame_cfg,
        )
        sp.phase = phase

        # Track phase boundaries
        if np.isfinite(strain) and phase not in phase_boundaries:
            phase_boundaries[phase] = strain

        # ---- Void analysis ----
        void = detect_voids(profile.q, profile.intensity, frame_cfg)
        sp.has_voids = void['has_voids']
        sp.phi_void = void['phi_void']
        sp.void_ar = void['void_ar']
        result.phi_void_array[i] = void['phi_void'] if np.isfinite(void['phi_void']) else np.nan

        # ---- Herman orientation factor ----
        if sector_data_list is not None and i < len(sector_data_list):
            sd = sector_data_list[i]
            if sd is not None:
                (
                    sp.q_peak_meridional_nm1,
                    sp.L_meridional_nm,
                ) = _tracked_sector_peak(
                    sd, "I_merid", frame_cfg, sp.q_peak_total_nm1
                )
                (
                    sp.q_peak_equatorial_nm1,
                    sp.L_equatorial_nm,
                ) = _tracked_sector_peak(
                    sd, "I_equat", frame_cfg, sp.q_peak_total_nm1
                )
                if not np.isfinite(sp.q_peak_total_nm1):
                    herman = _invalid_sector_data_result(
                        "tracked_feature_unavailable"
                    )
                else:
                    try:
                        herman = herman_from_sector_data(
                            sd,
                            cfg=frame_cfg,
                            data_quality_report=sp.data_quality_report,
                            q_target_nm1=sp.q_peak_total_nm1,
                        )
                    except Exception:
                        logger.warning(
                            "SAXS strain sector payload failed closed.",
                            exc_info=True,
                        )
                        herman = _invalid_sector_data_result()
                sp.f_herman = herman.get('f', np.nan)
                sp.f_herman_raw = herman.get('f_raw', sp.f_herman)
                sp.f_herman_sub = herman.get('f_sub', np.nan)
                sp.f_herman_eq = herman.get('f_eq', np.nan)
                if herman.get("detector_quality_report") is not None:
                    sp.detector_quality_report = herman["detector_quality_report"]
                if (
                    sp.raw_detector_quality_report is None
                    and herman.get("raw_detector_quality_report") is not None
                ):
                    sp.raw_detector_quality_report = herman[
                        "raw_detector_quality_report"
                    ]
                if herman.get("orientation_evidence") is not None:
                    sp.orientation_evidence = herman["orientation_evidence"]
                if herman.get("q_resolved_orientation_evidence") is not None:
                    sp.q_resolved_orientation_evidence = herman[
                        "q_resolved_orientation_evidence"
                    ]
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
    result.q_resolved_orientation_evidence = [
        point.q_resolved_orientation_evidence
        for point in result.strain_points
    ]
    if any(item is not None for item in result.q_resolved_orientation_evidence):
        tracking_frames = [
            {
                "frame_source_index": (
                    None
                    if frame_source_indices_invalid
                    else frame_source_indices_aligned[index]
                    if frame_source_indices_aligned
                    else (
                        sector_data_list[index].get("frame_source_index")
                        if sector_data_list is not None
                        and index < len(sector_data_list)
                        and isinstance(sector_data_list[index], Mapping)
                        else None
                    )
                ),
                "condition_value": result.strains[index],
                "q_resolved_orientation_evidence": evidence,
            }
            for index, evidence in enumerate(result.q_resolved_orientation_evidence)
        ]
        tracking = track_orientation_features(
            tracking_frames,
            frame_source_indices=(
                frame_source_indices_aligned
                if frame_source_indices_aligned
                else None
            ),
            max_axis_drift_deg=float(getattr(cfg, "orientation_max_axis_drift_deg", 20.0)),
        )
        result.orientation_tracking_evidence = build_orientation_tracking_evidence(
            tracking
        )
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

    strain_values = _as_1d_float_array(strains)
    q_values = _as_1d_float_array(Q_star_array)
    aligned_count = min(strain_values.size, q_values.size)
    strain_values = strain_values[:aligned_count]
    q_values = q_values[:aligned_count]
    tolerance_value = _coerce_strain_value(tolerance)

    valid = np.isfinite(q_values) & np.isfinite(strain_values)
    if np.sum(valid) < 2:
        return result

    Q_valid = q_values[valid]
    strains_valid = strain_values[valid]

    Q_mean = np.mean(Q_valid)
    Q_std = np.std(Q_valid)
    result['Q_mean'] = Q_mean
    result['Q_std'] = Q_std
    result['Q_cv'] = Q_std / Q_mean if Q_mean > 0 else np.nan

    # Check if within tolerance
    result['conserved'] = result['Q_cv'] < tolerance_value

    # Find max deviation
    deviations = np.abs(Q_valid - Q_mean) / Q_mean
    max_idx = np.argmax(deviations)
    result['max_deviation'] = deviations[max_idx]
    result['max_dev_strain'] = strains_valid[max_idx]

    return result
