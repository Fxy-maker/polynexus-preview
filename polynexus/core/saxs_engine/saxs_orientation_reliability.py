"""Detached q-resolved detector-plane orientation reliability contracts.

This module deliberately has no EDF or GUI dependency.  It consumes a
support-aware chi-by-q map and records diagnostics without applying a
calibration, a zero-strain subtraction, or a suspected correction.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .saxs_quality_contracts import contract_json


CONVENTION = "detector_plane_2d_v1"
ISOTROPIC_BASELINE = 0.25


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def _mapping_proxy(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType({str(key): _json_safe(item) for key, item in (value or {}).items()})


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _axis(value: Any) -> float | None:
    number = _finite(value)
    return None if number is None else float(number % 180.0)


def axial_distance_deg(first: Any, second: Any) -> float:
    """Return the smallest distance between two 180-degree axes."""

    first_value = _finite(first)
    second_value = _finite(second)
    if first_value is None or second_value is None:
        return float("nan")
    return float(abs((first_value - second_value + 90.0) % 180.0 - 90.0))


def _strict_number(value: Any) -> float | None:
    return _finite(value)


@dataclass(frozen=True)
class CorrectionLedgerEntry:
    operation: str
    status: str
    source: str = ""
    parameters: Mapping[str, Any] = field(default_factory=dict)
    input_digest: str | None = None
    output_digest: str | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", _mapping_proxy(self.parameters))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({
            "operation": self.operation,
            "status": self.status,
            "source": self.source,
            "parameters": self.parameters,
            "input_digest": self.input_digest,
            "output_digest": self.output_digest,
            "reason_codes": self.reason_codes,
        })


@dataclass(frozen=True)
class QOrientationBin:
    q_bin_id: str
    q_nm1: float
    q_bin_width_nm1: float | None
    harmonic_numerator_real: float | None
    harmonic_numerator_imag: float | None
    intensity_denominator: float | None
    m2_real: float | None
    m2_imag: float | None
    anisotropy_strength: float | None
    principal_axis_deg: float | None
    f_principal_raw: float | None
    f_reference: float | None
    reference_axis_deg: float | None
    reference_axis_kind: str
    effective_angular_bins: float
    angular_coverage: float
    support_fraction: float | None
    harmonic_significance: float | None
    stability_interval: Mapping[str, Any]
    level: str
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "stability_interval", _mapping_proxy(self.stability_interval))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({
            "q_bin_id": self.q_bin_id,
            "q_nm1": self.q_nm1,
            "q_bin_width_nm1": self.q_bin_width_nm1,
            "harmonic_numerator_real": self.harmonic_numerator_real,
            "harmonic_numerator_imag": self.harmonic_numerator_imag,
            "intensity_denominator": self.intensity_denominator,
            "m2_real": self.m2_real,
            "m2_imag": self.m2_imag,
            "anisotropy_strength": self.anisotropy_strength,
            "principal_axis_deg": self.principal_axis_deg,
            "f_principal_raw": self.f_principal_raw,
            "f_reference": self.f_reference,
            "reference_axis_deg": self.reference_axis_deg,
            "reference_axis_kind": self.reference_axis_kind,
            "effective_angular_bins": self.effective_angular_bins,
            "angular_coverage": self.angular_coverage,
            "support_fraction": self.support_fraction,
            "harmonic_significance": self.harmonic_significance,
            "stability_interval": self.stability_interval,
            "level": self.level,
            "reason_codes": self.reason_codes,
        })


@dataclass(frozen=True)
class OrientationQBandCandidate:
    candidate_id: str
    feature_kind: str
    q_min_nm1: float
    q_max_nm1: float
    q_center_nm1: float
    supported_q_bin_ids: tuple[str, ...]
    m2_real: float | None
    m2_imag: float | None
    anisotropy_strength: float | None
    principal_axis_deg: float | None
    f_principal_raw: float | None
    f_reference: float | None
    reference_axis_deg: float | None
    reference_axis_kind: str
    level: str
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({
            "candidate_id": self.candidate_id,
            "feature_kind": self.feature_kind,
            "q_min_nm1": self.q_min_nm1,
            "q_max_nm1": self.q_max_nm1,
            "q_center_nm1": self.q_center_nm1,
            "supported_q_bin_ids": self.supported_q_bin_ids,
            "m2_real": self.m2_real,
            "m2_imag": self.m2_imag,
            "anisotropy_strength": self.anisotropy_strength,
            "principal_axis_deg": self.principal_axis_deg,
            "f_principal_raw": self.f_principal_raw,
            "f_reference": self.f_reference,
            "reference_axis_deg": self.reference_axis_deg,
            "reference_axis_kind": self.reference_axis_kind,
            "level": self.level,
            "reason_codes": self.reason_codes,
        })


@dataclass(frozen=True)
class OrientationSensitivityObservation:
    variant_id: str
    candidate_id: str | None
    supported_q_bin_ids: tuple[str, ...]
    q_min_nm1: float | None
    q_max_nm1: float | None
    anisotropy_strength: float | None
    principal_axis_deg: float | None
    f_principal_raw: float | None
    f_reference: float | None
    eligible: bool
    status: str
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({
            "variant_id": self.variant_id,
            "candidate_id": self.candidate_id,
            "supported_q_bin_ids": self.supported_q_bin_ids,
            "q_min_nm1": self.q_min_nm1,
            "q_max_nm1": self.q_max_nm1,
            "anisotropy_strength": self.anisotropy_strength,
            "principal_axis_deg": self.principal_axis_deg,
            "f_principal_raw": self.f_principal_raw,
            "f_reference": self.f_reference,
            "eligible": self.eligible,
            "status": self.status,
            "reason_codes": self.reason_codes,
        })


@dataclass(frozen=True)
class OrientationSensitivitySummary:
    baseline_variant_id: str
    observations: tuple[OrientationSensitivityObservation, ...] = ()
    reliability_status: str = "diagnostic"
    reason_codes: tuple[str, ...] = ()
    value_ranges: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))
        object.__setattr__(self, "value_ranges", _mapping_proxy(self.value_ranges))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({
            "baseline_variant_id": self.baseline_variant_id,
            "observations": tuple(item.to_dict() for item in self.observations),
            "reliability_status": self.reliability_status,
            "reason_codes": self.reason_codes,
            "value_ranges": self.value_ranges,
        })


@dataclass(frozen=True)
class QResolvedOrientationEvidence:
    convention: str = CONVENTION
    isotropic_baseline: float = ISOTROPIC_BASELINE
    reference_axis_deg: float | None = None
    reference_axis_kind: str = "unknown"
    correction_ledger: tuple[CorrectionLedgerEntry, ...] = ()
    q_bins: tuple[QOrientationBin, ...] = ()
    q_band_candidates: tuple[OrientationQBandCandidate, ...] = ()
    sensitivity_summary: OrientationSensitivitySummary = field(
        default_factory=lambda: OrientationSensitivitySummary("baseline")
    )
    reliability_status: str = "unavailable"
    reason_codes: tuple[str, ...] = ()
    reliability_policy_digest: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "correction_ledger", tuple(self.correction_ledger))
        object.__setattr__(self, "q_bins", tuple(self.q_bins))
        object.__setattr__(self, "q_band_candidates", tuple(self.q_band_candidates))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return _json_safe({
            "convention": self.convention,
            "isotropic_baseline": self.isotropic_baseline,
            "reference_axis_deg": self.reference_axis_deg,
            "reference_axis_kind": self.reference_axis_kind,
            "correction_ledger": tuple(item.to_dict() for item in self.correction_ledger),
            "q_bins": tuple(item.to_dict() for item in self.q_bins),
            "q_band_candidates": tuple(item.to_dict() for item in self.q_band_candidates),
            "sensitivity_summary": self.sensitivity_summary.to_dict(),
            "reliability_status": self.reliability_status,
            "reason_codes": self.reason_codes,
            "reliability_policy_digest": self.reliability_policy_digest,
            "source_id": self.source_id,
        })


def _setting(cfg: Any, name: str, default: Any) -> Any:
    value = getattr(cfg, name, default) if cfg is not None else default
    return value


def _settings(cfg: Any) -> dict[str, Any]:
    def positive_int(name: str, default: int) -> int:
        try:
            return max(0, int(_setting(cfg, name, default)))
        except (TypeError, ValueError):
            return default

    def positive_float(name: str, default: float) -> float:
        try:
            value = float(_setting(cfg, name, default))
        except (TypeError, ValueError):
            return default
        return value if np.isfinite(value) and value >= 0 else default

    return {
        "min_strength": positive_float("orientation_auto_min_strength", 0.08),
        "min_significance": positive_float("orientation_auto_min_significance", 2.0),
        "min_coverage": min(1.0, positive_float("orientation_min_coverage", 0.75)),
        "min_effective_bins": positive_float("orientation_min_effective_bins", 8.0),
        "max_axis_drift_deg": positive_float("orientation_max_axis_drift_deg", 20.0),
        "bootstrap_replicates": positive_int("orientation_bootstrap_replicates", 256),
    }


def _policy_digest(cfg: Any) -> str:
    payload = _settings(cfg)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _digest_array(value: Any) -> str:
    try:
        array = np.ascontiguousarray(np.asarray(value))
        return hashlib.sha256(array.tobytes()).hexdigest()
    except (TypeError, ValueError):
        return ""


def build_correction_ledger(
    *,
    intensity: Any = None,
    support_count: Any = None,
    confirmed_mask: Any = None,
) -> tuple[CorrectionLedgerEntry, ...]:
    """Inventory authorized preprocessing without silently applying corrections."""

    entries = [
        CorrectionLedgerEntry(
            "finite_input_exclusion",
            "applied",
            "input",
            input_digest=_digest_array(intensity),
            reason_codes=("nonfinite_pixels_excluded",),
        ),
        CorrectionLedgerEntry(
            "confirmed_mask",
            "applied" if confirmed_mask is not None else "not_requested",
            "confirmed_input_mask",
            input_digest=_digest_array(confirmed_mask) if confirmed_mask is not None else None,
        ),
        CorrectionLedgerEntry(
            "support_count_gate",
            "applied" if support_count is not None else "unavailable",
            "sector_map",
            input_digest=_digest_array(support_count) if support_count is not None else None,
            reason_codes=() if support_count is not None else ("support_count_unavailable",),
        ),
    ]
    for operation in ("dark_correction", "flat_field_correction", "background_correction", "isotropic_reference_correction"):
        entries.append(CorrectionLedgerEntry(
            operation,
            "unavailable",
            "no_explicit_calibration_input",
            reason_codes=("calibration_input_unavailable",),
        ))
    entries.append(CorrectionLedgerEntry(
        "suspected_systematic_harmonic",
        "candidate_only",
        "detector_plane_evidence",
        reason_codes=("no_calibration_subtraction",),
    ))
    return tuple(entries)


def _q_edges(q: np.ndarray) -> np.ndarray:
    if q.size == 1:
        width = max(abs(float(q[0])) * 0.1, 1e-6)
        return np.asarray([q[0] - width / 2, q[0] + width / 2])
    gaps = np.diff(q)
    edges = np.empty(q.size + 1, dtype=float)
    edges[1:-1] = q[:-1] + gaps / 2.0
    edges[0] = q[0] - gaps[0] / 2.0
    edges[-1] = q[-1] + gaps[-1] / 2.0
    return edges


def _q_bin_id(lower: float, upper: float) -> str:
    return f"qbin:{lower:.12g}:{upper:.12g}"


def _harmonic(chi: np.ndarray, weights: np.ndarray) -> tuple[complex | None, float | None]:
    valid = np.isfinite(chi) & np.isfinite(weights) & (weights >= 0)
    denominator = float(np.sum(weights[valid]))
    if np.count_nonzero(valid) < 1 or denominator <= 0:
        return None, None
    numerator = np.sum(weights[valid] * np.exp(2j * chi[valid]))
    return complex(numerator), denominator


def _coverage(chi: np.ndarray) -> float:
    if chi.size < 2:
        return 0.0
    wrapped = np.sort(np.mod(chi, 2.0 * np.pi))
    gaps = np.diff(np.r_[wrapped, wrapped[0] + 2.0 * np.pi])
    return float(np.clip(1.0 - np.max(gaps) / (2.0 * np.pi), 0.0, 1.0))


def _effective_bins(support: np.ndarray) -> float:
    weights = np.asarray(support, dtype=float)
    weights = weights[np.isfinite(weights) & (weights > 0)]
    if weights.size == 0 or np.sum(weights**2) <= 0:
        return 0.0
    return float(np.sum(weights) ** 2 / np.sum(weights**2))


def _axis_from_m2(m2: complex | None) -> float | None:
    if m2 is None or not np.isfinite(m2.real) or not np.isfinite(m2.imag) or abs(m2) <= 1e-15:
        return None
    return float(np.degrees(0.5 * np.angle(m2)) % 180.0)


def _projection(m2: complex | None, reference_axis_deg: float | None) -> float | None:
    if m2 is None or reference_axis_deg is None:
        return None
    value = ISOTROPIC_BASELINE + 0.75 * float(
        np.real(m2 * np.exp(-2j * np.deg2rad(reference_axis_deg)))
    )
    return float(np.clip(value, -0.5, 1.0))


def _bootstrap_interval(
    chi: np.ndarray,
    weights: np.ndarray,
    *,
    reference_axis_deg: float | None,
    source_id: str,
    q_bin_id: str,
    replicates: int,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    valid = np.isfinite(chi) & np.isfinite(weights) & (weights >= 0) & (weights > 0)
    if np.count_nonzero(valid) < 5 or replicates <= 0:
        return {}, ("orientation_resampling_unavailable",)
    chi_valid = chi[valid]
    weight_valid = weights[valid]
    if chi_valid.size > 1:
        ordered = np.argsort(chi_valid)
        chi_valid = chi_valid[ordered]
        weight_valid = weight_valid[ordered]
        step = float(np.median(np.diff(chi_valid)))
    else:
        step = 0.0
    block_length = max(3, int(math.ceil(np.deg2rad(5.0) / max(abs(step), 1e-12))))
    block_length = min(block_length, chi_valid.size)
    n_blocks = int(math.ceil(chi_valid.size / block_length))
    seed_material = f"{source_id}|{q_bin_id}|{CONVENTION}".encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, chi_valid.size, size=(replicates, n_blocks))
    offsets = np.arange(block_length, dtype=int)
    indices = (starts[:, :, None] + offsets[None, None, :]) % chi_valid.size
    indices = indices.reshape(replicates, -1)[:, :chi_valid.size]
    sampled_chi = chi_valid[indices]
    sampled_weights = weight_valid[indices]
    denominators = np.sum(sampled_weights, axis=1)
    valid_replicate = denominators > 0
    if not np.any(valid_replicate):
        return {}, ("orientation_resampling_unavailable",)
    m2_values = np.sum(
        sampled_weights * np.exp(2j * sampled_chi), axis=1
    )[valid_replicate] / denominators[valid_replicate]
    strength = np.abs(m2_values)
    axes = np.mod(np.degrees(0.5 * np.angle(m2_values)), 180.0)
    f_principal = ISOTROPIC_BASELINE + 0.75 * strength
    f_reference = None
    if reference_axis_deg is not None:
        f_reference = ISOTROPIC_BASELINE + 0.75 * np.real(
            m2_values * np.exp(-2j * np.deg2rad(reference_axis_deg))
        )
    interval: dict[str, Any] = {
        "replicates": int(m2_values.size),
        "block_length": int(block_length),
        "anisotropy_strength_low": float(np.percentile(strength, 2.5)),
        "anisotropy_strength_high": float(np.percentile(strength, 97.5)),
        "principal_axis_deg_low": float(np.percentile(axes, 2.5)),
        "principal_axis_deg_high": float(np.percentile(axes, 97.5)),
        "f_principal_raw_low": float(np.percentile(f_principal, 2.5)),
        "f_principal_raw_high": float(np.percentile(f_principal, 97.5)),
    }
    if f_reference is not None:
        interval.update({
            "f_reference_low": float(np.percentile(f_reference, 2.5)),
            "f_reference_high": float(np.percentile(f_reference, 97.5)),
        })
    return interval, ()


def _point_reasons(
    *,
    support_available: bool,
    strength: float | None,
    significance: float | None,
    coverage: float,
    effective_bins: float,
    axis_drift: float | None,
    settings: Mapping[str, Any],
    harmonic_available: bool,
) -> list[str]:
    reasons: list[str] = []
    if not support_available:
        reasons.append("support_count_unavailable")
    if not harmonic_available:
        reasons.append("annulus_no_supported_angular_bins")
        return reasons
    if coverage < settings["min_coverage"]:
        reasons.append("orientation_azimuth_coverage_insufficient")
    if effective_bins < settings["min_effective_bins"]:
        reasons.append("orientation_effective_bins_insufficient")
    if strength is None or strength < settings["min_strength"]:
        reasons.append("orientation_harmonic_low_strength")
    if significance is None or significance < settings["min_significance"]:
        reasons.append("orientation_harmonic_insignificant")
    if axis_drift is not None and axis_drift > settings["max_axis_drift_deg"]:
        reasons.append("orientation_axis_drift_excessive")
    return reasons


def _axis_drift(chi: np.ndarray, weights: np.ndarray) -> float | None:
    axes = []
    for subset in (slice(0, None, 2), slice(1, None, 2)):
        numerator, denominator = _harmonic(chi[subset], weights[subset])
        if numerator is not None and denominator is not None:
            axes.append(_axis_from_m2(numerator / denominator))
    if len(axes) != 2 or axes[0] is None or axes[1] is None:
        return None
    return axial_distance_deg(axes[0], axes[1])


def _invalid_evidence(reason: str, *, source_id: str = "", cfg: Any = None) -> QResolvedOrientationEvidence:
    return QResolvedOrientationEvidence(
        correction_ledger=(CorrectionLedgerEntry(
            "input_validation", "unavailable", "input", reason_codes=(reason,)
        ),),
        reliability_status="unavailable",
        reason_codes=(reason,),
        reliability_policy_digest=_policy_digest(cfg),
        source_id=source_id,
    )


def build_q_resolved_orientation(
    intensity: Any,
    q: Any,
    chi: Any,
    *,
    support_count: Any = None,
    cfg: Any = None,
    reference_axis_deg: Any = None,
    reference_axis_kind: str | None = None,
    source_id: str = "",
    correction_ledger: Sequence[CorrectionLedgerEntry] | None = None,
    sensitivity_summary: OrientationSensitivitySummary | None = None,
) -> QResolvedOrientationEvidence:
    """Build q-resolved detector-plane M2 evidence from a sector map."""

    try:
        image = np.asarray(intensity, dtype=float)
        q_axis = np.asarray(q, dtype=float)
        chi_axis = np.asarray(chi, dtype=float)
    except (TypeError, ValueError):
        return _invalid_evidence("orientation_input_invalid", source_id=source_id, cfg=cfg)
    if image.ndim != 2 or q_axis.ndim != 1 or chi_axis.ndim != 1 or image.shape != (chi_axis.size, q_axis.size):
        return _invalid_evidence("orientation_input_shape_mismatch", source_id=source_id, cfg=cfg)
    if q_axis.size == 0 or chi_axis.size < 5 or not np.all(np.isfinite(q_axis)) or not np.all(np.isfinite(chi_axis)):
        return _invalid_evidence("orientation_input_shape_mismatch", source_id=source_id, cfg=cfg)
    if np.any(np.diff(q_axis) <= 0):
        return _invalid_evidence("orientation_q_axis_not_strictly_increasing", source_id=source_id, cfg=cfg)
    try:
        support = np.ones_like(image) if support_count is None else np.asarray(support_count, dtype=float)
    except (TypeError, ValueError):
        support = np.empty((0, 0), dtype=float)
    support_available = support_count is not None and support.shape == image.shape and np.all(np.isfinite(support)) and np.all(support >= 0)
    if not support_available:
        support = np.ones_like(image)
    ref_axis = _axis(
        reference_axis_deg if reference_axis_deg is not None else _setting(cfg, "tensile_axis_deg", None)
    )
    ref_kind = reference_axis_kind or ("tensile_axis" if ref_axis is not None and reference_axis_deg is None else "unknown")
    settings = _settings(cfg)
    edges = _q_edges(q_axis)
    points: list[QOrientationBin] = []
    for index, q_value in enumerate(q_axis):
        weights = image[:, index]
        supported = support[:, index] > 0
        valid = supported & np.isfinite(weights) & (weights >= 0)
        numerator, denominator = _harmonic(chi_axis, np.where(valid, weights, 0.0))
        strength = None if numerator is None or denominator is None else float(abs(numerator / denominator))
        m2 = None if numerator is None or denominator is None else numerator / denominator
        axis = _axis_from_m2(m2)
        f_principal = None if strength is None else float(ISOTROPIC_BASELINE + 0.75 * strength)
        f_reference = _projection(m2, ref_axis)
        support_column = support[:, index]
        effective = _effective_bins(
            np.where(supported & np.isfinite(support_column), support_column, 0.0)
        )
        coverage = _coverage(chi_axis[supported & np.isfinite(weights)])
        significance = None if strength is None else float(strength * math.sqrt(max(effective, 0.0)))
        drift = _axis_drift(chi_axis, np.where(valid, weights, 0.0)) if numerator is not None else None
        reasons = _point_reasons(
            support_available=support_available,
            strength=strength,
            significance=significance,
            coverage=coverage,
            effective_bins=effective,
            axis_drift=drift,
            settings=settings,
            harmonic_available=numerator is not None,
        )
        interval, bootstrap_reasons = _bootstrap_interval(
            chi_axis,
            np.where(valid, weights, 0.0),
            reference_axis_deg=ref_axis,
            source_id=source_id,
            q_bin_id=_q_bin_id(float(edges[index]), float(edges[index + 1])),
            replicates=settings["bootstrap_replicates"],
        )
        reasons.extend(bootstrap_reasons)
        if numerator is None:
            level = "Unusable"
        elif reasons:
            level = "Diagnostic"
        else:
            level = "Trend"
        points.append(QOrientationBin(
            q_bin_id=_q_bin_id(float(edges[index]), float(edges[index + 1])),
            q_nm1=float(q_value),
            q_bin_width_nm1=float(edges[index + 1] - edges[index]),
            harmonic_numerator_real=None if numerator is None else float(numerator.real),
            harmonic_numerator_imag=None if numerator is None else float(numerator.imag),
            intensity_denominator=denominator,
            m2_real=None if m2 is None else float(m2.real),
            m2_imag=None if m2 is None else float(m2.imag),
            anisotropy_strength=strength,
            principal_axis_deg=axis,
            f_principal_raw=f_principal,
            f_reference=f_reference,
            reference_axis_deg=ref_axis,
            reference_axis_kind=ref_kind,
            effective_angular_bins=float(effective),
            angular_coverage=float(coverage),
            support_fraction=float(np.count_nonzero(supported) / max(chi_axis.size, 1)),
            harmonic_significance=significance,
            stability_interval=interval,
            level=level,
            reason_codes=tuple(dict.fromkeys(reasons)),
        ))

    candidates = _build_candidates(points, image, support)
    if sensitivity_summary is None:
        sensitivity_summary = _baseline_sensitivity_summary(candidates)
    ledger = tuple(correction_ledger or build_correction_ledger(
        intensity=image, support_count=support_count
    ))
    evidence_reasons: list[str] = []
    if not support_available:
        evidence_reasons.append("support_count_unavailable")
    if not candidates:
        evidence_reasons.append("orientation_q_band_unavailable")
    if ref_axis is None:
        evidence_reasons.append("tensile_axis_unknown")
    reliability_status = "usable" if candidates and ref_axis is not None and support_available and sensitivity_summary.reliability_status == "usable" else "diagnostic"
    if not points:
        reliability_status = "unavailable"
    return QResolvedOrientationEvidence(
        reference_axis_deg=ref_axis,
        reference_axis_kind=ref_kind,
        correction_ledger=ledger,
        q_bins=tuple(points),
        q_band_candidates=tuple(candidates),
        sensitivity_summary=sensitivity_summary,
        reliability_status=reliability_status,
        reason_codes=tuple(dict.fromkeys(evidence_reasons)),
        reliability_policy_digest=_policy_digest(cfg),
        source_id=str(source_id or ""),
    )


def _build_candidates(
    points: Sequence[QOrientationBin],
    intensity: np.ndarray,
    support: np.ndarray,
) -> list[OrientationQBandCandidate]:
    runs: list[list[int]] = []
    for index, point in enumerate(points):
        if point.level != "Trend":
            continue
        if not runs or index != runs[-1][-1] + 1:
            runs.append([])
        runs[-1].append(index)
    candidates: list[OrientationQBandCandidate] = []
    for run in runs:
        if len(run) < 3:
            continue
        numerator = 0j
        denominator = 0.0
        for index in run:
            numerator += complex(
                points[index].harmonic_numerator_real or 0.0,
                points[index].harmonic_numerator_imag or 0.0,
            )
            denominator += float(points[index].intensity_denominator or 0.0)
        m2 = numerator / denominator if denominator > 0 else None
        strength = None if m2 is None else float(abs(m2))
        candidate_id = f"qband:{points[run[0]].q_bin_id}:{points[run[-1]].q_bin_id}"
        q_values = np.asarray([points[index].q_nm1 for index in run], dtype=float)
        weights = np.asarray([points[index].intensity_denominator or 0.0 for index in run])
        center = float(np.average(q_values, weights=weights)) if np.sum(weights) > 0 else float(np.mean(q_values))
        candidates.append(OrientationQBandCandidate(
            candidate_id=candidate_id,
            feature_kind="q_band",
            q_min_nm1=float(q_values[0] - points[run[0]].q_bin_width_nm1 / 2.0),
            q_max_nm1=float(q_values[-1] + points[run[-1]].q_bin_width_nm1 / 2.0),
            q_center_nm1=center,
            supported_q_bin_ids=tuple(points[index].q_bin_id for index in run),
            m2_real=None if m2 is None else float(m2.real),
            m2_imag=None if m2 is None else float(m2.imag),
            anisotropy_strength=strength,
            principal_axis_deg=_axis_from_m2(m2),
            f_principal_raw=None if strength is None else float(ISOTROPIC_BASELINE + 0.75 * strength),
            f_reference=_projection(m2, points[run[0]].reference_axis_deg),
            reference_axis_deg=points[run[0]].reference_axis_deg,
            reference_axis_kind=points[run[0]].reference_axis_kind,
            level="Trend",
        ))
    return candidates


def _baseline_sensitivity_summary(
    candidates: Sequence[OrientationQBandCandidate],
) -> OrientationSensitivitySummary:
    observations = tuple(
        OrientationSensitivityObservation(
            variant_id="baseline",
            candidate_id=candidate.candidate_id,
            supported_q_bin_ids=candidate.supported_q_bin_ids,
            q_min_nm1=candidate.q_min_nm1,
            q_max_nm1=candidate.q_max_nm1,
            anisotropy_strength=candidate.anisotropy_strength,
            principal_axis_deg=candidate.principal_axis_deg,
            f_principal_raw=candidate.f_principal_raw,
            f_reference=candidate.f_reference,
            eligible=True,
            status="baseline",
        )
        for candidate in candidates
    )
    return OrientationSensitivitySummary(
        "baseline",
        observations=observations,
        reliability_status="usable" if candidates else "diagnostic",
        reason_codes=() if candidates else ("orientation_q_band_unavailable",),
    )


def _observations(
    variant_id: str,
    evidence: QResolvedOrientationEvidence,
    *,
    status: str = "evaluated",
    reason_codes: tuple[str, ...] = (),
) -> tuple[OrientationSensitivityObservation, ...]:
    if evidence.q_band_candidates:
        return tuple(
            OrientationSensitivityObservation(
                variant_id=variant_id,
                candidate_id=item.candidate_id,
                supported_q_bin_ids=item.supported_q_bin_ids,
                q_min_nm1=item.q_min_nm1,
                q_max_nm1=item.q_max_nm1,
                anisotropy_strength=item.anisotropy_strength,
                principal_axis_deg=item.principal_axis_deg,
                f_principal_raw=item.f_principal_raw,
                f_reference=item.f_reference,
                eligible=True,
                status=status,
                reason_codes=reason_codes,
            )
            for item in evidence.q_band_candidates
        )
    return (OrientationSensitivityObservation(
        variant_id=variant_id,
        candidate_id=None,
        supported_q_bin_ids=(),
        q_min_nm1=None,
        q_max_nm1=None,
        anisotropy_strength=None,
        principal_axis_deg=None,
        f_principal_raw=None,
        f_reference=None,
        eligible=False,
        status=status,
        reason_codes=reason_codes + ("orientation_q_band_unavailable",),
    ),)


def _summary_from_observations(
    baseline: QResolvedOrientationEvidence,
    observations: Sequence[OrientationSensitivityObservation],
) -> OrientationSensitivitySummary:
    baseline_shape = {
        (item.candidate_id, item.supported_q_bin_ids, item.eligible)
        for item in observations if item.variant_id == "baseline"
    }
    variant_shapes = {
        (item.candidate_id, item.supported_q_bin_ids, item.eligible)
        for item in observations if item.variant_id != "baseline"
    }
    changed = bool(baseline_shape and variant_shapes and variant_shapes != baseline_shape)
    values = [item.f_principal_raw for item in observations if item.f_principal_raw is not None]
    axes = [item.principal_axis_deg for item in observations if item.principal_axis_deg is not None]
    ranges: dict[str, Any] = {}
    if values:
        ranges["f_principal_raw"] = {"min": min(values), "max": max(values)}
    if axes:
        ranges["principal_axis_deg"] = {"min": min(axes), "max": max(axes)}
    return OrientationSensitivitySummary(
        "baseline",
        observations=tuple(observations),
        reliability_status="artifact_sensitive" if changed else "usable",
        reason_codes=("orientation_sensitivity_changed_eligibility",) if changed else (),
        value_ranges=ranges,
    )


def _as_sector_payload(value: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        q = value.get("q_2d", value.get("q"))
        image = value.get("I_2d", value.get("intensity"))
        chi = value.get("chi_rad", value.get("chi"))
        support = value.get("support_count")
    else:
        q = getattr(value, "q", None)
        image = getattr(value, "intensity", None)
        chi = getattr(value, "chi", None)
        support = getattr(value, "support_count", None)
    try:
        return np.asarray(image, dtype=float), np.asarray(q, dtype=float), np.asarray(chi, dtype=float), None if support is None else np.asarray(support, dtype=float)
    except (TypeError, ValueError):
        return None


def evaluate_orientation_sensitivity(
    image_or_intensity: Any,
    q_or_cfg: Any = None,
    chi: Any = None,
    *,
    support_count: Any = None,
    cfg: Any = None,
    confirmed_mask: Any = None,
    integration_callback: Callable[[Any, Any, Any], Any] | None = None,
    source_id: str = "",
    reference_axis_deg: Any = None,
    reference_axis_kind: str | None = None,
) -> QResolvedOrientationEvidence:
    """Evaluate bounded, candidate-only variants without mutating inputs."""

    if cfg is None and q_or_cfg is not None and chi is None and hasattr(q_or_cfg, "n_chi_sectors"):
        cfg = q_or_cfg
        q_or_cfg = None
    if cfg is None:
        from .config import SAXSConfig

        cfg = SAXSConfig()
    image = np.asarray(image_or_intensity)
    image_input = image.copy()
    mask_copy = None if confirmed_mask is None else np.asarray(confirmed_mask, dtype=bool).copy()
    baseline_payload: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None] | None
    detector_mode = q_or_cfg is None or chi is None
    if detector_mode:
        try:
            from .preprocess import integrate_chi_sectors

            callback = integration_callback or (
                lambda detector_image, variant_cfg, variant_mask: integrate_chi_sectors(
                    None, detector_image, variant_cfg, mask=variant_mask
                )
            )
            baseline_payload = _as_sector_payload(callback(image_input.copy(), cfg, None if mask_copy is None else mask_copy.copy()))
        except Exception:
            baseline_payload = None
    else:
        baseline_payload = (np.asarray(image_or_intensity, dtype=float).copy(), np.asarray(q_or_cfg, dtype=float).copy(), np.asarray(chi, dtype=float).copy(), None if support_count is None else np.asarray(support_count, dtype=float).copy())
    if baseline_payload is None:
        return _invalid_evidence("orientation_sensitivity_baseline_unavailable", source_id=source_id, cfg=cfg)
    base_image, base_q, base_chi, base_support = baseline_payload
    if support_count is not None and not detector_mode:
        base_support = np.asarray(support_count, dtype=float).copy()
    baseline = build_q_resolved_orientation(
        base_image,
        base_q,
        base_chi,
        support_count=base_support,
        cfg=cfg,
        reference_axis_deg=reference_axis_deg,
        reference_axis_kind=reference_axis_kind,
        source_id=source_id,
        confirmed_mask=mask_copy,
    ) if False else build_q_resolved_orientation(
        base_image,
        base_q,
        base_chi,
        support_count=base_support,
        cfg=cfg,
        reference_axis_deg=reference_axis_deg,
        reference_axis_kind=reference_axis_kind,
        source_id=source_id,
        correction_ledger=build_correction_ledger(
            intensity=base_image, support_count=base_support, confirmed_mask=mask_copy
        ),
    )
    observations = list(_observations("baseline", baseline, status="baseline"))
    ledger = list(baseline.correction_ledger)
    variants: list[tuple[str, str, Any, Any]] = []
    offsets = _setting(cfg, "orientation_center_offsets_px", (-1.0, 0.0, 1.0))
    try:
        offsets = tuple(float(value) for value in offsets)
    except (TypeError, ValueError):
        offsets = (-1.0, 0.0, 1.0)
    if detector_mode:
        for dx in offsets:
            for dy in offsets:
                if dx == 0.0 and dy == 0.0:
                    continue
                variants.append((f"center_dx{dx:g}_dy{dy:g}", "center_variant", dx, dy))
    dilation = _setting(cfg, "orientation_mask_dilation_px", (1, 2))
    try:
        dilation = tuple(int(value) for value in dilation if int(value) > 0)
    except (TypeError, ValueError):
        dilation = (1, 2)
    for radius in dilation:
        variants.append((f"mask_dilation_{radius}px", "mask_variant", radius, None))
    variants.extend([
        ("suspected_bad_pixels", "suspected_bad_pixel_variant", None, None),
        ("q_width_0.75", "q_window_variant", 0.75, None),
        ("q_width_1.25", "q_window_variant", 1.25, None),
        ("chi_resolution_0.5", "angular_resolution_variant", 0.5, None),
        ("chi_resolution_2.0", "angular_resolution_variant", 2.0, None),
    ])
    for variant_id, operation, first, second in variants:
        ledger.append(CorrectionLedgerEntry(
            operation, "candidate_only", "sensitivity_runner",
            parameters={"variant_id": variant_id, "value": first, "secondary": second},
            reason_codes=("baseline_input_unchanged",),
        ))
        variant_evidence = None
        if detector_mode and operation in {"center_variant", "mask_variant"}:
            try:
                variant_cfg = cfg
                variant_mask = None if mask_copy is None else mask_copy.copy()
                if operation == "center_variant":
                    variant_cfg = replace(
                        cfg,
                        beam_center_x=float(getattr(cfg, "beam_center_x", 0.0)) + float(first),
                        beam_center_y=float(getattr(cfg, "beam_center_y", 0.0)) + float(second),
                    )
                elif variant_mask is not None:
                    from scipy.ndimage import binary_dilation

                    variant_mask = binary_dilation(variant_mask, iterations=int(first))
                payload = _as_sector_payload(callback(image_input.copy(), variant_cfg, variant_mask))
                if payload is not None:
                    variant_evidence = build_q_resolved_orientation(
                        payload[0], payload[1], payload[2],
                        support_count=payload[3], cfg=cfg,
                        reference_axis_deg=reference_axis_deg,
                        reference_axis_kind=reference_axis_kind,
                        source_id=source_id,
                    )
            except Exception:
                variant_evidence = None
        if variant_evidence is None:
            observations.extend(_observations(
                variant_id, baseline, status="candidate_only",
                reason_codes=("variant_not_applied", "baseline_input_unchanged"),
            ))
        else:
            observations.extend(_observations(variant_id, variant_evidence))
    summary = _summary_from_observations(baseline, observations)
    reliability = replace(baseline, sensitivity_summary=summary, correction_ledger=tuple(ledger))
    return replace(
        reliability,
        reliability_status=("artifact_sensitive" if summary.reliability_status == "artifact_sensitive" else reliability.reliability_status),
        reason_codes=tuple(dict.fromkeys((*reliability.reason_codes, *summary.reason_codes))),
    )


run_orientation_sensitivity = evaluate_orientation_sensitivity


__all__ = [
    "CONVENTION",
    "ISOTROPIC_BASELINE",
    "CorrectionLedgerEntry",
    "QOrientationBin",
    "OrientationQBandCandidate",
    "OrientationSensitivityObservation",
    "OrientationSensitivitySummary",
    "QResolvedOrientationEvidence",
    "axial_distance_deg",
    "build_correction_ledger",
    "build_q_resolved_orientation",
    "evaluate_orientation_sensitivity",
    "run_orientation_sensitivity",
    "contract_json",
]
