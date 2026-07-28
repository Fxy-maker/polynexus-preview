
"""
saxs_temperature.py — Module 4C: In-situ temperature SAXS analysis.

Melting/crystallization tracking, Gibbs-Thomson analysis,
Avrami crystallization kinetics, thermal expansion correction.

Reference: SAXS Design Document v1.0, Module 4C.
"""

import logging
from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Dict, List, Optional
import numpy as np
from enum import Enum, auto

from .config import SAXSConfig
from .core import (
    bragg_long_period, scattering_invariant,
    analyze_single,
)
from .lc_path_selection import (
    LcCandidate,
    apply_lc_path_decisions,
    select_lc_sequence_path,
)
from .preprocess import apply_thermal_correction
from .saxs_quality_contracts import (
    _as_1d_float_array,
    build_series_detector_quality_report,
    build_guinier_sequence_evidence,
    build_series_metric_evidence,
    build_series_orientation_evidence,
    sanitize_1d_profile,
)
from .saxs_sequence_rescue import build_sequence_rescue_candidates
from .saxs_output_helpers import (
    _data_quality_csv_fields,
    _detector_provenance_csv_fields,
)

logger = logging.getLogger(__name__)


def _aligned_source_values(values: Optional[List[str]], count: int) -> tuple[str, ...]:
    """Return source values only when the caller supplied one per frame."""

    if values is None or len(values) != count:
        return ()
    return tuple(str(value or "") for value in values)


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


def _guinier_metric_frame_payload(point: "TemperaturePointResult") -> dict:
    """Copy existing frame Guinier metric evidence for series aggregation."""

    evidence = getattr(point, "guinier_evidence", None)
    if not isinstance(evidence, Mapping):
        return {}
    metric = evidence.get("metric")
    if not isinstance(metric, Mapping):
        return {}
    return {"guinier": dict(metric)}


_GUINIER_SEQUENCE_INDEX_FIELDS = {
    "frame_source_indices": "Rg_sequence_frame_source_indices",
    "missing_frame_indices": "Rg_sequence_missing_frame_indices",
    "diagnostic_frame_indices": "Rg_sequence_diagnostic_frame_indices",
    "invalid_temperature_indices": "Rg_sequence_invalid_temperature_indices",
    "duplicate_temperature_indices": "Rg_sequence_duplicate_temperature_indices",
    "nonmonotonic_temperature_indices": "Rg_sequence_nonmonotonic_temperature_indices",
    "continuity_break_indices": "Rg_sequence_continuity_break_indices",
    "duplicate_source_index_indices": "Rg_sequence_duplicate_source_index_indices",
    "invalid_source_index_indices": "Rg_sequence_invalid_source_index_indices",
}


def _sequence_indices_csv_value(value: object) -> str | None:
    """Format an emitted sequence index collection without deriving values."""

    if not isinstance(value, (list, tuple)) or not value:
        return None
    return "|".join(str(item) for item in value)


def _guinier_sequence_csv_fields(payload: object) -> dict[str, object]:
    """Project existing sequence integrity facts into stable flat fields."""

    fields: dict[str, object] = {column: None for column in _GUINIER_SEQUENCE_INDEX_FIELDS.values()}
    fields["Rg_sequence_source_index_order_reordered"] = None
    if not isinstance(payload, Mapping):
        return fields

    for source_field, output_field in _GUINIER_SEQUENCE_INDEX_FIELDS.items():
        fields[output_field] = _sequence_indices_csv_value(payload.get(source_field))
    reordered = payload.get("source_index_order_reordered")
    if isinstance(reordered, (bool, np.bool_)):
        fields["Rg_sequence_source_index_order_reordered"] = bool(reordered)
    return fields


class TempPhase(Enum):
    """Thermal process phases."""
    HEATING_SOLID = auto()       # below melting
    MELTING = auto()             # melting range
    MELT = auto()                # fully molten
    COOLING_MELT = auto()        # above crystallization
    CRYSTALLIZATION = auto()     # crystallization range
    COLD_CRYSTALLIZATION = auto() # cold crystallization on heating
    ISOTHERMAL = auto()          # isothermal crystallization


@dataclass
class TemperaturePointResult:
    """Single temperature point analysis result."""
    source_index: int = -1
    temperature_C: float = 0.0
    phase: TempPhase = TempPhase.HEATING_SOLID
    
    # Long period
    L_nm: float = np.nan
    q_star_nm1: float = np.nan
    
    # Structure
    lc_nm: float = np.nan
    la_nm: float = np.nan
    phi_c: float = np.nan
    
    # Invariant
    Q_star: float = np.nan

    # Guinier evidence (kept separate from lamellar structure parameters)
    Rg_nm: float = np.nan
    guinier_level: str = "Unusable"
    guinier_reason_codes: List[str] = field(default_factory=list)
    data_quality_report: Dict = None
    guinier_evidence: Dict = None
    metric_evidence: Dict = None
    detector_quality_report: Dict = None
    raw_detector_quality_report: Dict = None
    orientation_evidence: Dict = None
    
    # Crystallization (if applicable)
    Xc_relative: float = np.nan  # relative crystallinity (0-1)
    
    # Quality
    confidence: float = 0.0
    lc_confidence: float = np.nan
    lc_tangent_nm: float = np.nan
    lc_idf_nm: float = np.nan
    lc_gamma_min_nm: float = np.nan
    lc_candidates: List[LcCandidate] = field(default_factory=list)
    lc_candidate_selected_nm: float = np.nan
    lc_candidate_selected_source: str = ""
    lc_candidate_selected_score: float = np.nan
    lc_candidate_count: int = 0
    lc_effective_nm: float = np.nan
    lc_effective_source: str = ""
    lc_effective_score: float = np.nan
    lc_path_status: str = "diagnostic_only"
    lc_path_reason: str = ""
    method: str = ""
    melting_window_status: str = "undetermined"
    melting_window_reason: str = ""
    lc_reliability_status: str = "diagnostic_only"
    lc_reliability_reason: str = ""
    warnings: List[str] = field(default_factory=list)


@dataclass
class TempSeriesResult:
    """Complete temperature-dependent SAXS analysis."""
    temp_points: List[TemperaturePointResult] = field(default_factory=list)
    
    # Gibbs-Thomson
    gibbs_thomson: Dict = field(default_factory=dict)
    
    # Avrami kinetics
    avrami: Dict = field(default_factory=dict)
    
    # Tracking arrays
    temperatures: np.ndarray = None
    L_array: np.ndarray = None
    lc_array: np.ndarray = None
    lc_effective_array: np.ndarray = None
    Q_star_array: np.ndarray = None
    Xc_array: np.ndarray = None
    Rg_array: np.ndarray = None
    guinier_level_array: List[str] = field(default_factory=list)
    guinier_sequence_evidence: Dict = None
    detector_quality_report: Dict = None
    raw_detector_quality_report: Dict = None
    orientation_evidence: Dict = None
    metric_evidence: Dict = None
    melting_window_status_array: List[str] = field(default_factory=list)
    lc_reliability_status_array: List[str] = field(default_factory=list)
    lc_path_status_array: List[str] = field(default_factory=list)
    lc_path_reason_array: List[str] = field(default_factory=list)
    lc_candidate_selected_source_array: List[str] = field(default_factory=list)
    lc_candidate_selected_score_array: np.ndarray = None
    sequence_rescue_candidates: List[Dict] = field(default_factory=list)
    
    # Phase transition temperatures
    Tm_onset: float = np.nan
    Tm_peak: float = np.nan
    Tm_end: float = np.nan
    Tc_onset: float = np.nan
    
    experiment_type: str = "heating"  # heating | cooling | isothermal

    def to_dataframe(self):
        """Convert to pandas DataFrame."""
        import pandas as pd
        sequence_payload = self.guinier_sequence_evidence or {}
        sequence_level = sequence_payload.get('level')
        sequence_reasons = sequence_payload.get('reason_codes', [])
        if isinstance(sequence_reasons, (list, tuple)):
            sequence_reasons = '|'.join(str(reason) for reason in sequence_reasons)
        else:
            sequence_reasons = str(sequence_reasons or '')

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
        rescue_by_frame = {
            int(item.get('parameters', {}).get('frame_index')): item
            for item in self.sequence_rescue_candidates
            if isinstance(item, dict)
            and isinstance(item.get('parameters'), dict)
            and item.get('parameters', {}).get('frame_index') is not None
        }
        for tp in self.temp_points:
            frame_index = len(rows)
            rescue = rescue_by_frame.get(frame_index)
            row = {
                'Temperature(C)': tp.temperature_C,
                'source_index': int(tp.source_index) if int(tp.source_index) >= 0 else None,
                'Phase': tp.phase.name,
                'L(nm)': round(tp.L_nm, 2) if np.isfinite(tp.L_nm) else None,
                'lc(nm)': round(tp.lc_nm, 2) if np.isfinite(tp.lc_nm) else None,
                'la(nm)': round(tp.la_nm, 2) if np.isfinite(tp.la_nm) else None,
                'phi_c': round(tp.phi_c, 3) if np.isfinite(tp.phi_c) else None,
                'Q_star': f"{tp.Q_star:.4e}" if np.isfinite(tp.Q_star) else None,
                'Rg(nm)': round(tp.Rg_nm, 3) if np.isfinite(tp.Rg_nm) else None,
                'Rg_level': tp.guinier_level or None,
                'Rg_reason_codes': '|'.join(tp.guinier_reason_codes) if tp.guinier_reason_codes else None,
                'Rg_sequence_level': sequence_level,
                'Rg_sequence_reason_codes': sequence_reasons or None,
                'Metric_evidence_levels': metric_level_summary(tp.metric_evidence),
                'Xc_rel': round(tp.Xc_relative, 3) if np.isfinite(tp.Xc_relative) else None,
                'Confidence': round(tp.confidence, 2),
                'lc_confidence': round(tp.lc_confidence, 2) if np.isfinite(tp.lc_confidence) else None,
                'lc_effective(nm)': round(tp.lc_effective_nm, 2) if np.isfinite(tp.lc_effective_nm) else None,
                'lc_path_status': tp.lc_path_status or None,
                'lc_path_reason': tp.lc_path_reason or None,
                'lc_candidate_source': tp.lc_candidate_selected_source or None,
                'lc_candidate_score': round(tp.lc_candidate_selected_score, 3) if np.isfinite(tp.lc_candidate_selected_score) else None,
                'sequence_rescue_candidate': rescue.get('candidate_id') if rescue else None,
                'melting_window_status': tp.melting_window_status or None,
                'lc_reliability_status': tp.lc_reliability_status or None,
                'lc_reliability_reason': tp.lc_reliability_reason or None,
            }
            row.update(_guinier_sequence_csv_fields(sequence_payload))
            row.update(
                _detector_provenance_csv_fields(tp.raw_detector_quality_report)
            )
            row.update(_data_quality_csv_fields(tp.data_quality_report))
            rows.append(row)
        return pd.DataFrame(rows)


def _temperature_window_margin(temperatures: np.ndarray) -> float:
    finite = _as_1d_float_array(temperatures)
    finite = finite[np.isfinite(finite)]
    if finite.size < 2:
        return 5.0
    diffs = np.diff(np.sort(finite))
    positive = diffs[diffs > 1e-9]
    if positive.size == 0:
        return 5.0
    return max(3.0, float(np.median(positive)) * 0.5)


def _safe_temperature_invariant(
    q: np.ndarray,
    intensity: np.ndarray,
    cfg: SAXSConfig,
    *,
    warning_code: str,
) -> tuple[float, str | None]:
    """Calculate one temperature-frame invariant without aborting the series."""
    try:
        value = float(scattering_invariant(q, intensity, cfg=cfg))
    except Exception:
        logger.warning("SAXS temperature invariant calculation failed: %s", warning_code, exc_info=True)
        return np.nan, warning_code
    if not np.isfinite(value):
        logger.warning("SAXS temperature invariant calculation was non-finite: %s", warning_code)
        return np.nan, warning_code
    return value, None


def _expected_melt_soft_margin(expected_melt_C: float, temperature_margin: float) -> float:
    if not np.isfinite(expected_melt_C):
        return float(max(temperature_margin, 10.0))
    return float(max(temperature_margin, 10.0, abs(expected_melt_C) * 0.05))


def _coerce_optional_float(value: float | None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


def classify_melting_window_status(
    temperature: float,
    Tm_onset: float,
    Tm_peak: float,
    Tm_end: float,
    temperatures: np.ndarray | None = None,
    expected_melt_C: float = np.nan,
) -> tuple[str, str]:
    """Classify where a frame sits relative to the sequence-derived melting window."""
    temperature = _coerce_optional_float(temperature)
    Tm_onset = _coerce_optional_float(Tm_onset)
    Tm_peak = _coerce_optional_float(Tm_peak)
    Tm_end = _coerce_optional_float(Tm_end)

    if not np.isfinite(temperature):
        return "undetermined", "temperature_unresolved"

    expected_melt_C = _coerce_optional_float(expected_melt_C)
    margin = _temperature_window_margin(temperatures if temperatures is not None else np.asarray([temperature], dtype=float))
    expected_melt_hint_margin = _expected_melt_soft_margin(expected_melt_C, margin)

    if np.isfinite(Tm_end) and temperature > Tm_end + margin:
        return "post_end", "past_sequence_melting_end"

    if not np.isfinite(Tm_onset):
        if np.isfinite(Tm_peak):
            if temperature <= Tm_peak + margin:
                return "near_onset", "melting_onset_unresolved_peak_only"
            if np.isfinite(expected_melt_C) and temperature >= expected_melt_C - expected_melt_hint_margin:
                return "undetermined", "expected_melt_prior_hint"
            return "within_window", "above_peak_with_unresolved_end"
        if np.isfinite(expected_melt_C) and temperature >= expected_melt_C - expected_melt_hint_margin:
            return "undetermined", "expected_melt_prior_hint"
        return "undetermined", "melting_onset_unresolved"

    if temperature < Tm_onset - margin:
        return "outside_window", "below_sequence_melting_onset"

    if temperature <= Tm_onset + margin:
        return "near_onset", "near_sequence_melting_onset"

    if np.isfinite(Tm_end):
        if temperature <= Tm_end:
            return "within_window", "between_sequence_melting_onset_and_end"
        return "post_end", "past_sequence_melting_end"

    if np.isfinite(Tm_peak) and temperature <= Tm_peak + margin:
        return "within_window", "between_sequence_melting_onset_and_peak"

    return "within_window", "above_sequence_melting_onset_with_unresolved_end"


def classify_lc_reliability_status(
    point: TemperaturePointResult,
    *,
    peak_intensity_ratio: float = np.nan,
    q_invariant_ratio: float = np.nan,
    previous_point: Optional[TemperaturePointResult] = None,
) -> tuple[str, str]:
    """Classify whether a frame's lc should be treated as usable, tentative, or diagnostic-only."""
    reasons: List[str] = []

    if not np.isfinite(point.L_nm) or point.L_nm <= 0 or not np.isfinite(point.lc_nm) or point.lc_nm <= 0:
        return "diagnostic_only", "structure_unresolved"

    lc_conf = float(point.lc_confidence) if np.isfinite(point.lc_confidence) else np.nan
    if not np.isfinite(lc_conf):
        lc_conf = 0.0

    minority_fraction = np.nan
    if np.isfinite(point.la_nm) and point.la_nm >= 0 and point.L_nm > 0:
        minority_fraction = min(point.lc_nm, point.la_nm) / point.L_nm

    prev_minority_fraction = np.nan
    lc_ratio_prev = np.nan
    L_ratio_prev = np.nan
    if (
        previous_point is not None
        and np.isfinite(previous_point.lc_nm)
        and previous_point.lc_nm > 0
        and np.isfinite(previous_point.L_nm)
        and previous_point.L_nm > 0
    ):
        lc_ratio_prev = point.lc_nm / previous_point.lc_nm
        L_ratio_prev = point.L_nm / previous_point.L_nm
        if np.isfinite(previous_point.la_nm) and previous_point.la_nm >= 0:
            prev_minority_fraction = min(previous_point.lc_nm, previous_point.la_nm) / previous_point.L_nm

    method_values = [
        float(value)
        for value in (
            getattr(point, "lc_tangent_nm", np.nan),
            getattr(point, "lc_idf_nm", np.nan),
            getattr(point, "lc_gamma_min_nm", np.nan),
        )
        if np.isfinite(value) and value > 0
    ]
    method_count = len(method_values)
    method_spread = np.nan
    if method_count >= 2:
        method_mean = float(np.mean(method_values))
        if method_mean > 0:
            method_spread = float((max(method_values) - min(method_values)) / method_mean)

    q_star = float(point.Q_star) if np.isfinite(point.Q_star) else np.nan
    if np.isfinite(q_star) and (q_star > 50.0 or (0 < q_star < 0.5)):
        reasons.append("q_invariant_anomaly")
    if np.isfinite(minority_fraction) and minority_fraction < 0.15:
        reasons.append("minority_fraction_too_low")
    if lc_conf < 0.2:
        reasons.append("low_lc_confidence")
    elif lc_conf < 0.5:
        reasons.append("limited_lc_confidence")
    if point.warnings:
        reasons.append("frame_analysis_warning")
    if np.isfinite(peak_intensity_ratio):
        if peak_intensity_ratio < 0.50:
            reasons.append("peak_tracking_lost")
        elif peak_intensity_ratio < 0.70:
            reasons.append("peak_tracking_weakened")
    if np.isfinite(q_invariant_ratio):
        if q_invariant_ratio < 0.50:
            reasons.append("sequence_crystallinity_drop")
        elif q_invariant_ratio < 0.70:
            reasons.append("sequence_crystallinity_softening")
    if np.isfinite(lc_ratio_prev) and np.isfinite(L_ratio_prev):
        if lc_ratio_prev < 0.45 and L_ratio_prev > 0.80:
            reasons.append("sequence_continuity_break")
        elif lc_ratio_prev < 0.65 and L_ratio_prev > 0.85 and np.isfinite(prev_minority_fraction) and prev_minority_fraction >= 0.18:
            reasons.append("sequence_continuity_weakened")
    if method_count == 1:
        reasons.append("single_method_fragile")
    elif np.isfinite(method_spread) and method_spread > 0.35:
        reasons.append("method_conflict")

    severe_instability = bool(
        lc_conf < 0.2
        or ("minority_fraction_too_low" in reasons and np.isfinite(minority_fraction) and minority_fraction < 0.12)
        or "peak_tracking_lost" in reasons
        or "sequence_crystallinity_drop" in reasons
        or "sequence_continuity_break" in reasons
    )
    moderate_instability = bool(
        severe_instability
        or "single_method_fragile" in reasons
        or "method_conflict" in reasons
        or "limited_lc_confidence" in reasons
        or "peak_tracking_weakened" in reasons
        or "sequence_crystallinity_softening" in reasons
        or "sequence_continuity_weakened" in reasons
        or "q_invariant_anomaly" in reasons
        or "frame_analysis_warning" in reasons
        or "expected_melt_prior_hint" in reasons
    )

    melting_status = str(point.melting_window_status or "").strip().lower()
    melting_reason = str(point.melting_window_reason or "").strip().lower()
    if melting_status == "post_end":
        reasons.append("post_melting_window")
        return "diagnostic_only", "|".join(reasons)
    if melting_status == "within_window":
        reasons.append("within_melting_window")
        if severe_instability or lc_conf < 0.5 or (np.isfinite(minority_fraction) and minority_fraction < 0.15):
            return "diagnostic_only", "|".join(reasons)
        return "low_confidence", "|".join(reasons)
    if melting_status == "near_onset":
        reasons.append("near_melting_onset")
        if severe_instability or lc_conf < 0.35:
            return "diagnostic_only", "|".join(reasons)
        return "low_confidence", "|".join(reasons)
    if melting_status == "undetermined":
        reasons.append("melting_window_undetermined")
        if "expected_melt_prior_hint" in melting_reason:
            reasons.append("expected_melt_prior_hint")
        if severe_instability:
            return "diagnostic_only", "|".join(reasons)
        if moderate_instability or "expected_melt_prior_hint" in reasons:
            return "low_confidence", "|".join(reasons)

    if severe_instability:
        return "diagnostic_only", "|".join(reasons)
    if moderate_instability:
        return "low_confidence", "|".join(reasons)
    return "usable", "stable_structure_support"


def _first_sustained_threshold_crossing(
    values: np.ndarray,
    threshold: float,
    *,
    min_run: int = 2,
) -> Optional[int]:
    finite = np.asarray(values, dtype=float)
    n_points = len(finite)
    if n_points == 0:
        return None
    for idx in range(1, n_points):
        value = finite[idx]
        if not np.isfinite(value) or value >= threshold:
            continue
        tail = finite[idx:min(n_points, idx + max(min_run, 1))]
        tail = tail[np.isfinite(tail)]
        if tail.size >= min_run and np.all(tail < threshold):
            return idx
        if idx == n_points - 1:
            return idx
    return None


def _build_sequence_support_ratios(
    result: TempSeriesResult,
    I_peak_tracking: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    n_points = len(result.temp_points)
    peak_ratios = np.full(n_points, np.nan)
    q_ratios = np.full(n_points, np.nan)

    outside_indices = [
        idx
        for idx, tp in enumerate(result.temp_points)
        if str(tp.melting_window_status or "").strip().lower() == "outside_window"
    ]

    reference_indices = [idx for idx in outside_indices if np.isfinite(I_peak_tracking[idx]) or np.isfinite(result.Q_star_array[idx])]
    if not reference_indices:
        reference_indices = [
            idx
            for idx in range(n_points)
            if np.isfinite(I_peak_tracking[idx]) or np.isfinite(result.Q_star_array[idx])
        ][: max(1, min(3, n_points))]

    if not reference_indices:
        return peak_ratios, q_ratios

    ref_peak = np.nanmedian(I_peak_tracking[reference_indices])
    ref_q = np.nanmedian(result.Q_star_array[reference_indices])

    for idx in range(n_points):
        if np.isfinite(ref_peak) and ref_peak > 0 and np.isfinite(I_peak_tracking[idx]):
            peak_ratios[idx] = I_peak_tracking[idx] / ref_peak
        if np.isfinite(ref_q) and ref_q > 0 and np.isfinite(result.Q_star_array[idx]):
            q_ratios[idx] = result.Q_star_array[idx] / ref_q

    return peak_ratios, q_ratios


# ======================================================================
#  Temperature phase detection
# ======================================================================

def detect_temperature_phase(
    temperature: float,
    Q_star: float,
    Q_star_solid: float,
    L: float,
    L_solid: float,
    exp_type: str = "heating",
) -> TempPhase:
    """Auto-detect thermal phase from SAXS parameters.

    Key indicators:
    - Q* drops → melting begins
    - L increases → lamellar thickening
    - Bragg peak disappears → fully molten
    - Q* rises → crystallization
    """
    Q_star = _coerce_optional_float(Q_star)
    Q_star_solid = _coerce_optional_float(Q_star_solid)
    L = _coerce_optional_float(L)
    L_solid = _coerce_optional_float(L_solid)

    Q_norm = Q_star / Q_star_solid if Q_star_solid > 0 else 1.0
    
    if exp_type == "heating":
        if Q_norm < 0.05:
            return TempPhase.MELT
        elif Q_norm < 0.5 and Q_norm > 0.05:
            return TempPhase.MELTING
        elif Q_norm > 0.9:
            return TempPhase.HEATING_SOLID
        else:
            # Check if cold crystallization (Q* rises during heating)
            if np.isfinite(L) and np.isfinite(L_solid) and L > L_solid * 1.2:
                return TempPhase.COLD_CRYSTALLIZATION
            return TempPhase.MELTING
    
    elif exp_type == "cooling":
        if Q_norm > 0.9:
            return TempPhase.COOLING_MELT
        elif Q_norm > 0.3:
            return TempPhase.CRYSTALLIZATION
        else:
            return TempPhase.HEATING_SOLID  # fully crystallized
    
    elif exp_type == "isothermal":
        return TempPhase.ISOTHERMAL
    
    return TempPhase.HEATING_SOLID


# ======================================================================
#  Gibbs-Thomson analysis
# ======================================================================

def gibbs_thomson_analysis(
    temperatures: np.ndarray,
    lc_array: np.ndarray,
    Tm_inf: float = None,
) -> Dict:
    """Gibbs-Thomson equation for lamellar thickness vs melting point.

    Tm = Tm_inf * (1 - 2*sigma_e / (delta_Hf * lc))

    Where:
      Tm_inf = equilibrium melting point (K)
      sigma_e = fold surface free energy (J/m^2)
      delta_Hf = heat of fusion per unit volume (J/m^3)
      lc = lamellar thickness (m)

    From SAXS: lc(T) → predicts Tm
    Linearized: Tm = Tm_inf - (2*Tm_inf*sigma_e/delta_Hf) * (1/lc)

    Returns dict with Gibbs-Thomson parameters.
    """
    result = {
        'Tm_inf_K': np.nan,
        'Tm_inf_C': np.nan,
        'sigma_e_over_dHf': np.nan,
        'sigma_e_Jm2': np.nan,
        'R2': np.nan,
        'valid': False,
    }

    temperatures = _as_1d_float_array(temperatures)
    lc_array = _as_1d_float_array(lc_array)
    aligned_count = min(temperatures.size, lc_array.size)
    temperatures = temperatures[:aligned_count]
    lc_array = lc_array[:aligned_count]

    # Filter valid points in melting region
    valid = np.isfinite(lc_array) & (lc_array > 0) & np.isfinite(temperatures)
    if np.sum(valid) < 4:
        return result

    T_valid = temperatures[valid] + 273.15  # to Kelvin
    lc_valid = lc_array[valid]

    # Tm ~ 1/lc relationship
    inv_lc = 1.0 / lc_valid

    try:
        p = np.polyfit(inv_lc, T_valid, 1)
        Tm_inf = p[1]  # intercept -> Tm_inf
        slope = p[0]   # = -2*Tm_inf*sigma_e/delta_Hf

        # R-squared
        T_pred = np.polyval(p, inv_lc)
        ss_res = np.sum((T_valid - T_pred) ** 2)
        ss_tot = np.sum((T_valid - np.mean(T_valid)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        result['Tm_inf_K'] = Tm_inf
        result['Tm_inf_C'] = Tm_inf - 273.15
        result['sigma_e_over_dHf'] = -slope / (2 * Tm_inf) if Tm_inf > 0 else np.nan
        result['R2'] = r2
        result['valid'] = r2 > 0.8

        # If delta_Hf known, estimate sigma_e
        # Typical polymers: delta_Hf ~ 2e8 J/m^3
        delta_Hf_typical = 2.0e8  # J/m^3
        if np.isfinite(result['sigma_e_over_dHf']):
            result['sigma_e_Jm2'] = result['sigma_e_over_dHf'] * delta_Hf_typical
    except Exception:
        logger.warning("SAXS Gibbs-Thomson analysis failed.", exc_info=True)

    return result


# ======================================================================
#  Avrami crystallization kinetics
# ======================================================================

def avrami_kinetics(
    times: np.ndarray,
    Xc_relative: np.ndarray,
    auto_range: bool = True,
) -> Dict:
    """Avrami crystallization kinetics analysis.

    Avrami equation: 1 - Xc = exp(-k * t^n)
    Linearized: ln(-ln(1 - Xc)) = ln(k) + n * ln(t)

    Parameters
    ----------
    times : np.ndarray
        Time array (seconds).
    Xc_relative : np.ndarray
        Relative crystallinity (0 to 1).
    auto_range : bool
        If True, automatically select Xc range [0.05, 0.63] for fitting.

    Returns
    -------
    dict with Avrami parameters n, k, t_half, R2.
    """
    result = {
        'n': np.nan,           # Avrami exponent
        'k_sn': np.nan,        # rate constant (s^-n)
        't_half_s': np.nan,    # half-crystallization time
        'R2': np.nan,
        'valid': False,
        'fit_range': None,
    }

    times = _as_1d_float_array(times)
    Xc_relative = _as_1d_float_array(Xc_relative)
    aligned_count = min(times.size, Xc_relative.size)
    times = times[:aligned_count]
    Xc_relative = Xc_relative[:aligned_count]

    valid = np.isfinite(Xc_relative) & np.isfinite(times) & (times > 0)
    if np.sum(valid) < 5:
        return result

    t_valid = times[valid]
    Xc_valid = Xc_relative[valid]

    # Select range: [0.05, 0.63] for primary crystallization
    if auto_range:
        mask = (Xc_valid >= 0.03) & (Xc_valid <= 0.63)
        if np.sum(mask) < 4:
            mask = (Xc_valid >= 0.01) & (Xc_valid <= 0.80)
    else:
        mask = np.ones(len(Xc_valid), dtype=bool)

    if np.sum(mask) < 4:
        return result

    t_fit = t_valid[mask]
    Xc_fit = Xc_valid[mask]

    # Avoid log issues
    Xc_fit = np.clip(Xc_fit, 1e-6, 1 - 1e-6)

    y = np.log(-np.log(1 - Xc_fit))
    x = np.log(t_fit)

    try:
        p = np.polyfit(x, y, 1)
        n = p[0]
        ln_k = p[1]
        k = np.exp(ln_k)

        # R-squared
        y_pred = np.polyval(p, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # Half-crystallization time
        if k > 0:
            t_half = (np.log(2) / k) ** (1 / n)
        else:
            t_half = np.nan

        result['n'] = n
        result['k_sn'] = k
        result['t_half_s'] = t_half
        result['R2'] = r2
        result['valid'] = r2 > 0.9 and 1.0 <= n <= 4.0
        result['fit_range'] = (float(np.min(t_fit)), float(np.max(t_fit)))
    except Exception:
        logger.warning("SAXS Avrami kinetics fit failed.", exc_info=True)

    return result


def avrami_from_temp_series(
    time_array: np.ndarray,
    temp_array: np.ndarray,
    Xc_array: np.ndarray,
    Tc_target: float,
    tolerance: float = 2.0,
) -> Dict:
    """Extract Avrami kinetics from a temperature series at a specific Tc.

    For isothermal crystallization data embedded in cooling runs.
    """
    time_values = _as_1d_float_array(time_array)
    temperature_values = _as_1d_float_array(temp_array)
    xc_values = _as_1d_float_array(Xc_array)
    aligned_count = min(
        time_values.size,
        temperature_values.size,
        xc_values.size,
    )
    time_values = time_values[:aligned_count]
    temperature_values = temperature_values[:aligned_count]
    xc_values = xc_values[:aligned_count]

    mask = (
        np.isfinite(temperature_values)
        & (np.abs(temperature_values - Tc_target) <= tolerance)
        & np.isfinite(time_values)
        & np.isfinite(xc_values)
    )
    if np.sum(mask) < 5:
        return {'valid': False, 'n': np.nan, 'k_sn': np.nan}

    t_iso = time_values[mask] - time_values[mask][0]  # relative time
    Xc_iso = xc_values[mask]

    return avrami_kinetics(t_iso, Xc_iso)


# ======================================================================
#  Melting point from SAXS (Bragg peak disappearance)
# ======================================================================

def detect_melting_from_saxs(
    temperatures: np.ndarray,
    q_star_array: np.ndarray,
    I_peak_array: np.ndarray,
) -> Dict:
    """Detect melting range from SAXS Bragg peak evolution.

    Tm_onset: first detectable decrease in peak intensity
    Tm_peak: 50% drop in peak intensity
    Tm_end: peak intensity < 1% of initial

    Returns dict with Tm values.
    """
    result = {
        'Tm_onset_C': np.nan,
        'Tm_50pct_C': np.nan,
        'Tm_end_C': np.nan,
        'melting_range_C': np.nan,
    }

    temperature_values = _as_1d_float_array(temperatures)
    peak_intensity_values = _as_1d_float_array(I_peak_array)
    aligned_count = min(temperature_values.size, peak_intensity_values.size)
    temperature_values = temperature_values[:aligned_count]
    peak_intensity_values = peak_intensity_values[:aligned_count]

    valid = np.isfinite(peak_intensity_values) & np.isfinite(temperature_values)
    if np.sum(valid) < 3:
        return result

    T = temperature_values[valid]
    I_pk = peak_intensity_values[valid]
    I_init = np.nanmedian(I_pk[:min(5, len(I_pk))])  # robust initial intensity

    if I_init <= 0:
        return result

    I_norm = I_pk / I_init

    # Tm_onset / midpoint / end should prefer sustained loss rather than a single noisy dip.
    onset_idx = _first_sustained_threshold_crossing(I_norm, 0.95, min_run=2)
    if onset_idx is not None:
        result['Tm_onset_C'] = float(T[onset_idx])

    mid_idx = _first_sustained_threshold_crossing(I_norm, 0.50, min_run=2)
    if mid_idx is not None:
        result['Tm_50pct_C'] = float(T[mid_idx])

    end_idx = _first_sustained_threshold_crossing(I_norm, 0.01, min_run=1)
    if end_idx is not None:
        result['Tm_end_C'] = float(T[end_idx])

    if np.isfinite(result['Tm_end_C']) and np.isfinite(result['Tm_onset_C']):
        result['melting_range_C'] = result['Tm_end_C'] - result['Tm_onset_C']

    return result


# ======================================================================
#  Full temperature series analysis
# ======================================================================

def analyze_temperature_series(
    temperatures: List[float],
    q_list: List[np.ndarray],
    I_list: List[np.ndarray],
    times: Optional[List[float]] = None,
    cfg: Optional[SAXSConfig] = None,
    exp_type: str = "heating",
    Tm_inf: Optional[float] = None,
    thermal_expansion_coeff: Optional[float] = None,
    detector_quality_reports: Optional[List[Dict]] = None,
    source_ids: Optional[List[str]] = None,
    raw_data_refs: Optional[List[str]] = None,
    verbose: bool = False,
) -> TempSeriesResult:
    """Analyze a complete in-situ temperature SAXS experiment.

    Parameters
    ----------
    temperatures : list of float
        Temperature values (C) for each measurement point.
    q_list : list of np.ndarray
        q for each point.
    I_list : list of np.ndarray
        I(q) for each point.
    times : list of float, optional
        Time values (seconds). Required for Avrami kinetics.
    cfg : SAXSConfig, optional
    exp_type : str
        "heating", "cooling", or "isothermal".
    Tm_inf : float, optional
        Equilibrium melting point (C) for Gibbs-Thomson.
    thermal_expansion_coeff : float, optional
        Linear thermal expansion coefficient (1/K).

    Returns
    -------
    TempSeriesResult
    """
    if cfg is None:
        cfg = SAXSConfig()

    n_points = len(temperatures)
    if len(q_list) != n_points or len(I_list) != n_points:
        raise ValueError("temperatures, q_list, I_list must have same length")
    time_axis_length_mismatch = times is not None and len(times) != n_points
    time_axis_invalid_values = False

    if n_points == 0:
        empty = np.asarray([], dtype=float)
        result = TempSeriesResult(experiment_type=exp_type)
        result.temperatures = empty.copy()
        result.L_array = empty.copy()
        result.lc_array = empty.copy()
        result.lc_effective_array = empty.copy()
        result.Q_star_array = empty.copy()
        result.Xc_array = empty.copy()
        result.Rg_array = empty.copy()
        result.lc_candidate_selected_score_array = empty.copy()
        result.guinier_sequence_evidence = build_guinier_sequence_evidence(
            [], [], source_indices=[],
            source_ref="saxs_temperature.guinier_sequence",
        ).to_dict()
        result.metric_evidence = build_series_metric_evidence(
            [],
            metric_names=("guinier", "porod", "kratky", "invariant", "lamellar"),
            source_ref="saxs_temperature.metric_evidence",
            frame_source_indices=[],
            condition_name="temperature_C",
            condition_values=[],
        )
        if time_axis_length_mismatch:
            result.avrami = {
                "valid": False,
                "reason": "temperature_time_axis_length_mismatch",
            }
        return result

    source_ids_aligned = _aligned_source_values(source_ids, n_points)
    raw_data_refs_aligned = _aligned_source_values(raw_data_refs, n_points)

    temps_arr = np.asarray(
        [_coerce_optional_float(value) for value in temperatures],
        dtype=float,
    )

    # Sort by temperature
    sort_idx = np.argsort(temps_arr)
    temps_arr = temps_arr[sort_idx]
    q_sorted = [q_list[i] for i in sort_idx]
    I_sorted = [I_list[i] for i in sort_idx]
    sanitized_sorted = [
        sanitize_1d_profile(q_values, intensity_values)
        for q_values, intensity_values in zip(q_sorted, I_sorted)
    ]
    reports_sorted = (
        [detector_quality_reports[i] for i in sort_idx]
        if detector_quality_reports is not None
        and len(detector_quality_reports) == n_points
        else [None] * n_points
    )

    if times is not None:
        if time_axis_length_mismatch:
            times_arr = np.full(n_points, np.nan, dtype=float)
        else:
            time_values = np.asarray(
                [_coerce_optional_float(value) for value in times],
                dtype=float,
            )
            time_axis_invalid_values = bool(np.any(~np.isfinite(time_values)))
            times_arr = time_values[sort_idx]
    else:
        times_arr = np.arange(n_points, dtype=float)

    result = TempSeriesResult(experiment_type=exp_type)
    if time_axis_length_mismatch:
        result.avrami = {
            "valid": False,
            "reason": "temperature_time_axis_length_mismatch",
        }
    elif time_axis_invalid_values:
        result.avrami = {
            "valid": False,
            "reason": "temperature_time_axis_invalid_values",
        }
    result.temperatures = temps_arr
    result.L_array = np.full(n_points, np.nan)
    result.lc_array = np.full(n_points, np.nan)
    result.Q_star_array = np.full(n_points, np.nan)
    result.Xc_array = np.full(n_points, np.nan)
    result.Rg_array = np.full(n_points, np.nan)
    result.guinier_level_array = ["Unusable"] * n_points

    # Reference: lowest temperature point (solid state)
    ref_idx = 0
    reference_profile = sanitized_sorted[ref_idx]
    Q_solid, reference_invariant_warning = _safe_temperature_invariant(
        reference_profile.q,
        reference_profile.intensity,
        cfg,
        warning_code="temperature_reference_invariant_unavailable",
    )
    reference_long_period_warning = None
    try:
        L_solid, _, _ = bragg_long_period(
            reference_profile.q,
            reference_profile.intensity,
        )
        L_solid = float(L_solid)
        if not np.isfinite(L_solid):
            reference_long_period_warning = "temperature_reference_long_period_unavailable"
            L_solid = np.nan
    except Exception:
        logger.warning(
            "SAXS temperature reference long-period calculation failed.",
            exc_info=True,
        )
        reference_long_period_warning = "temperature_reference_long_period_unavailable"
        L_solid = np.nan

    # Track Bragg peak intensity for melting detection
    I_peak_tracking = np.full(n_points, np.nan)

    for i in range(n_points):
        T = temps_arr[i]
        q = q_sorted[i]
        I = I_sorted[i]  # noqa: E741
        profile = sanitized_sorted[i]

        tp = TemperaturePointResult(source_index=int(sort_idx[i]), temperature_C=float(T))
        tp.raw_detector_quality_report = reports_sorted[i]
        if i == ref_idx:
            for warning_code in (reference_invariant_warning, reference_long_period_warning):
                if warning_code:
                    tp.warnings.append(warning_code)

        # Apply thermal expansion correction
        if thermal_expansion_coeff is not None and np.isfinite(thermal_expansion_coeff):
            try:
                cfg_corrected = apply_thermal_correction(cfg, T)
            except Exception:
                cfg_corrected = cfg
                logger.warning("SAXS thermal expansion correction failed; using original config.", exc_info=True)
        else:
            cfg_corrected = cfg

        # ---- Core analysis ----
        try:
            source_kwargs = _source_kwargs(
                source_ids_aligned,
                raw_data_refs_aligned,
                int(sort_idx[i]),
            )
            saxs_result = analyze_single(q, I, cfg_corrected, **source_kwargs)
            lp = saxs_result.long_period
            struct = saxs_result.structure
            
            tp.L_nm = lp.L_best
            tp.q_star_nm1 = 2 * np.pi / lp.L_best if np.isfinite(lp.L_best) and lp.L_best > 0 else np.nan
            tp.method = lp.method_used
            tp.confidence = lp.L_confidence
            
            tp.lc_nm = struct.lc
            tp.la_nm = struct.la
            tp.phi_c = struct.phi_c
            tp.lc_confidence = struct.confidence_lc
            tp.lc_tangent_nm = getattr(struct, "lc_tangent_nm", np.nan)
            tp.lc_idf_nm = getattr(struct, "lc_idf_nm", np.nan)
            tp.lc_gamma_min_nm = getattr(struct, "lc_gamma_min_nm", np.nan)
            tp.data_quality_report = getattr(saxs_result, "data_quality_report", None)
            tp.guinier_evidence = getattr(saxs_result, "guinier_evidence", None)
            tp.metric_evidence = getattr(saxs_result, "metric_evidence", None)
            tp.detector_quality_report = getattr(saxs_result, "detector_quality_report", None)
            tp.orientation_evidence = getattr(saxs_result, "orientation_evidence", None)
            if isinstance(tp.guinier_evidence, dict):
                try:
                    rg_value = float(tp.guinier_evidence.get("rg_nm", np.nan))
                except (TypeError, ValueError):
                    rg_value = np.nan
                tp.Rg_nm = rg_value if np.isfinite(rg_value) else np.nan
                tp.guinier_level = str(tp.guinier_evidence.get("level", "Unusable") or "Unusable")
                reason_codes = tp.guinier_evidence.get("reason_codes", [])
                if isinstance(reason_codes, (list, tuple)):
                    tp.guinier_reason_codes = [str(reason) for reason in reason_codes]
            result.Rg_array[i] = tp.Rg_nm
            result.guinier_level_array[i] = tp.guinier_level

            # Track Bragg peak intensity
            q_star = tp.q_star_nm1
            if np.isfinite(q_star) and profile.q.size:
                idx = np.argmin(np.abs(profile.q - q_star))
                I_peak_tracking[i] = (
                    profile.intensity[idx]
                    if idx < len(profile.intensity)
                    else np.nan
                )
        except Exception as e:
            tp.warnings.append(f"Core analysis: {e}")
            logger.warning("SAXS temperature frame core analysis failed.", exc_info=True)

        # ---- Invariant ----
        Q_star, invariant_warning = _safe_temperature_invariant(
            profile.q,
            profile.intensity,
            cfg_corrected,
            warning_code="temperature_frame_invariant_unavailable",
        )
        tp.Q_star = Q_star
        if invariant_warning:
            tp.warnings.append(invariant_warning)
        result.Q_star_array[i] = Q_star

        # ---- Relative crystallinity ----
        if exp_type in ("cooling", "isothermal"):
            # For crystallization: Xc = (Q - Q_melt) / (Q_solid - Q_melt)
            Q_max = np.nanmax(result.Q_star_array[:i+1])
            Q_min = np.nanmin(result.Q_star_array[:i+1])
            if Q_max > Q_min:
                tp.Xc_relative = (Q_star - Q_min) / (Q_max - Q_min)
                tp.Xc_relative = np.clip(tp.Xc_relative, 0, 1)
        elif exp_type == "heating":
            # For melting: Xc decreases
            if Q_solid > 0:
                tp.Xc_relative = Q_star / Q_solid
                tp.Xc_relative = np.clip(tp.Xc_relative, 0, 1)

        result.Xc_array[i] = tp.Xc_relative

        # ---- Phase detection ----
        phase = detect_temperature_phase(T, Q_star, Q_solid, tp.L_nm, L_solid, exp_type)
        tp.phase = phase

        result.temp_points.append(tp)
        result.L_array[i] = tp.L_nm
        result.lc_array[i] = tp.lc_nm

    frame_metric_evidence = []
    for point in result.temp_points:
        frame_metrics = (
            dict(point.metric_evidence)
            if isinstance(point.metric_evidence, Mapping)
            else {}
        )
        frame_metrics.update(_guinier_metric_frame_payload(point))
        frame_metric_evidence.append(frame_metrics)
    result.metric_evidence = build_series_metric_evidence(
        frame_metric_evidence,
        metric_names=("guinier", "porod", "kratky", "invariant", "lamellar"),
        source_ref="saxs_temperature.metric_evidence",
        frame_source_indices=[point.source_index for point in result.temp_points],
        condition_name="temperature_C",
        condition_values=result.temperatures,
    )
    detector_quality = build_series_detector_quality_report(
        [point.detector_quality_report for point in result.temp_points],
        source_ref="saxs_temperature.detector_quality_report",
    )
    orientation = build_series_orientation_evidence(
        [point.orientation_evidence for point in result.temp_points],
        source_ref="saxs_temperature.orientation_evidence",
    )
    if detector_quality is not None:
        result.detector_quality_report = detector_quality
    raw_detector_quality = build_series_detector_quality_report(
        [point.raw_detector_quality_report for point in result.temp_points],
        source_ref="saxs_temperature.raw_detector_quality_report",
    )
    if raw_detector_quality is not None:
        result.raw_detector_quality_report = raw_detector_quality
    if orientation is not None:
        result.orientation_evidence = orientation
    result.guinier_sequence_evidence = build_guinier_sequence_evidence(
        result.temperatures,
        [point.guinier_evidence for point in result.temp_points],
        source_indices=[point.source_index for point in result.temp_points],
        source_ref="saxs_temperature.guinier_sequence",
    ).to_dict()

    # ---- Post-analysis ----

    # Melting detection
    melting = detect_melting_from_saxs(temps_arr, result.L_array, I_peak_tracking)
    result.Tm_onset = melting.get('Tm_onset_C', np.nan)
    result.Tm_peak = melting.get('Tm_50pct_C', np.nan)
    result.Tm_end = melting.get('Tm_end_C', np.nan)

    result.melting_window_status_array = ["undetermined"] * len(result.temp_points)
    result.lc_reliability_status_array = ["diagnostic_only"] * len(result.temp_points)
    for idx, tp in enumerate(result.temp_points):
        window_status, window_reason = classify_melting_window_status(
            tp.temperature_C,
            result.Tm_onset,
            result.Tm_peak,
            result.Tm_end,
            result.temperatures,
            _coerce_optional_float(getattr(cfg, "T_melt_expected", None)) if cfg is not None else np.nan,
        )
        tp.melting_window_status = window_status
        tp.melting_window_reason = window_reason
        result.melting_window_status_array[idx] = window_status

    peak_ratios, q_ratios = _build_sequence_support_ratios(result, I_peak_tracking)
    previous_point: Optional[TemperaturePointResult] = None
    for idx, tp in enumerate(result.temp_points):
        lc_status, lc_reason = classify_lc_reliability_status(
            tp,
            peak_intensity_ratio=peak_ratios[idx],
            q_invariant_ratio=q_ratios[idx],
            previous_point=previous_point,
        )
        tp.lc_reliability_status = lc_status
        tp.lc_reliability_reason = lc_reason
        result.lc_reliability_status_array[idx] = lc_status
        previous_point = tp

    path_decisions = select_lc_sequence_path(result.temp_points)
    apply_lc_path_decisions(result.temp_points, path_decisions)

    result.lc_effective_array = np.asarray([tp.lc_effective_nm for tp in result.temp_points], dtype=float)
    result.lc_path_status_array = [str(tp.lc_path_status or "") for tp in result.temp_points]
    result.lc_path_reason_array = [str(tp.lc_path_reason or "") for tp in result.temp_points]
    result.lc_candidate_selected_source_array = [str(tp.lc_candidate_selected_source or "") for tp in result.temp_points]
    result.lc_candidate_selected_score_array = np.asarray(
        [float(tp.lc_candidate_selected_score) if np.isfinite(tp.lc_candidate_selected_score) else np.nan for tp in result.temp_points],
        dtype=float,
    )
    result.sequence_rescue_candidates = [
        candidate.to_dict()
        for candidate in build_sequence_rescue_candidates(
            result.temp_points,
            axis_name="temperature",
        )
    ]

    lc_for_gibbs_thomson = result.lc_effective_array
    if not np.any(np.isfinite(lc_for_gibbs_thomson)):
        lc_for_gibbs_thomson = result.lc_array

    # Gibbs-Thomson prefers the sequence-selected path when available, but
    # falls back to the raw core output if no effective path survives.
    result.gibbs_thomson = gibbs_thomson_analysis(
        temps_arr,
        lc_for_gibbs_thomson,
        Tm_inf,
    )

    # Avrami kinetics (for cooling/isothermal)
    if (
        not time_axis_length_mismatch
        and not time_axis_invalid_values
        and exp_type in ("cooling", "isothermal")
        and len(times_arr) > 5
    ):
        result.avrami = avrami_kinetics(times_arr, result.Xc_array)

    if verbose:
        print(f"Temperature series: {n_points} points, {exp_type}")
        print(f"T range: {temps_arr[0]:.0f} - {temps_arr[-1]:.0f} C")
        print(f"Tm_onset: {result.Tm_onset:.1f} C" if np.isfinite(result.Tm_onset) else "Tm not detected")
        if result.gibbs_thomson.get('valid'):
            print(f"Gibbs-Thomson Tm_inf: {result.gibbs_thomson['Tm_inf_C']:.1f} C, R2={result.gibbs_thomson['R2']:.3f}")

    return result
