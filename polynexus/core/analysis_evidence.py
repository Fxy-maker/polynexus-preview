from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from .saxs_symptom_detector import detect_saxs_symptoms, symptom_bridge_lines
from .ir_engine.names import normalize_ir_polymer_name


@dataclass(frozen=True)
class EvidenceConstraint:
    name: str
    kind: str
    source: str
    severity: str
    description: str
    field: str | None = None
    rationale: str | None = None
    triggered: bool = False
    observed: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnalysisEvidence:
    technique: str
    summary: str = ""
    fit_evidence: dict[str, Any] = field(default_factory=dict)
    physical_evidence: dict[str, Any] = field(default_factory=dict)
    residual_evidence: dict[str, Any] = field(default_factory=dict)
    feature_evidence: dict[str, Any] = field(default_factory=dict)
    signal_evidence: dict[str, Any] = field(default_factory=dict)
    peak_evidence: dict[str, Any] = field(default_factory=dict)
    assignment_evidence: dict[str, Any] = field(default_factory=dict)
    reference_evidence: dict[str, Any] = field(default_factory=dict)
    background_evidence: dict[str, Any] = field(default_factory=dict)
    phase_evidence: dict[str, Any] = field(default_factory=dict)
    transform_evidence: dict[str, Any] = field(default_factory=dict)
    structure_evidence: dict[str, Any] = field(default_factory=dict)
    raw_structure_evidence: dict[str, Any] = field(default_factory=dict)
    batch_evidence: dict[str, Any] = field(default_factory=dict)
    condition_evidence: dict[str, Any] = field(default_factory=dict)
    stability_evidence: dict[str, Any] = field(default_factory=dict)
    symptoms: list[dict[str, Any]] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    confidence_signals: list[dict[str, Any]] = field(default_factory=list)
    actionable_symptoms: list[str] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    constraint_summary: dict[str, Any] = field(default_factory=dict)
    cross_validation: dict[str, Any] = field(default_factory=dict)
    source_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _clamp_unit(value: float | None, default: float = 0.0) -> float:
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def _mean_finite(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None]
    if not finite:
        return None
    return sum(finite) / len(finite)


def _relative_spread(values: list[Any]) -> float | None:
    finite = [float(value) for value in values if _clean_float(value) is not None]
    if len(finite) < 2:
        return None
    scale = max(max(abs(value) for value in finite), 1e-9)
    return (max(finite) - min(finite)) / scale


def _condition_values(output: dict[str, Any], batch_rows: list[dict[str, Any]], label: str) -> list[float]:
    values: list[float] = []
    if batch_rows:
        for row in batch_rows:
            if not isinstance(row, dict):
                continue
            value = _clean_float(row.get("condition_value"))
            if value is None and label == "temperature":
                value = _clean_float(row.get("temperature_C"))
            if value is None and label == "strain":
                value = _clean_float(row.get("strain_pct"))
            if value is not None:
                values.append(value)
        return values

    for key in ("condition_value", "temperature_C", "strain_pct"):
        value = _clean_float(output.get(key))
        if value is not None:
            values.append(value)
            break
    return values


def _inverse_ratio_score(value: float | None, limit: float) -> float | None:
    if value is None or limit <= 0:
        return None
    return _clamp_unit(1.0 - abs(float(value)) / float(limit), default=0.0)


def _numeric_distribution(values: list[Any], *, source: str = "") -> dict[str, Any] | None:
    finite = [float(value) for value in values if _clean_float(value) is not None]
    if not finite:
        return None
    arr = np.asarray(finite, dtype=float)
    p25, p50, p75 = np.percentile(arr, [25, 50, 75])
    summary: dict[str, Any] = {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "p25": float(p25),
        "median": float(p50),
        "mean": float(np.mean(arr)),
        "p75": float(p75),
        "max": float(np.max(arr)),
        "std": float(np.std(arr)),
    }
    spread = _relative_spread(finite)
    if spread is not None:
        summary["spread"] = float(spread)
    if source:
        summary["source"] = source
    return summary


def _inventory(*constraints: EvidenceConstraint) -> list[EvidenceConstraint]:
    return list(constraints)


def physical_constraint_inventory(technique: str) -> list[EvidenceConstraint]:
    key = str(technique or "").upper()
    if key == "SAXS":
        return _inventory(
            EvidenceConstraint(
                name="beamstop_contamination",
                kind="hard_fail",
                source="SAXS",
                severity="ERROR",
                description="Beam-stop contamination can invalidate low-q interpretation.",
                field="beam_stop_contaminated",
                rationale="low-q / q* evidence is not reliable when the beamstop intrudes.",
            ),
            EvidenceConstraint(
                name="mask_truncated",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="Effective q-min is truncated and reduces low-q confidence.",
                field="mask_truncated",
                rationale="Long-period evidence becomes weaker when q-range is cut.",
            ),
            EvidenceConstraint(
                name="low_peak_snr",
                kind="evidence_only",
                source="SAXS",
                severity="INFO",
                description="Lamellar peak SNR is a confidence signal, not a hard gate.",
                field="q_peak_snr",
                rationale="Use it to weight confidence, not to replace the fit score.",
            ),
            EvidenceConstraint(
                name="l_consistency",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="Bragg and correlation long-period estimates should stay close.",
                field="L_bragg",
                rationale="Cross-check long-period estimates before acceptance.",
            ),
            EvidenceConstraint(
                name="fit_regions_unstable",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="Peak/correlation fit regions look numerically unstable and often produce misleading figures.",
                field="fit_regions",
                rationale="When multiple fit regions fail together, AI should stop tuning and ask the core path to stabilize first.",
            ),
            EvidenceConstraint(
                name="correlation_over_oscillation",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="Correlation or IDF curves oscillate too densely to support a trustworthy lamellar interpretation.",
                field="fit_regions",
                rationale="Dense oscillation usually means q-range, smoothing, or preprocessing is dominating the shape.",
            ),
            EvidenceConstraint(
                name="missing_condition_axis",
                kind="hard_fail",
                source="SAXS",
                severity="ERROR",
                description="In-situ SAXS series is missing reliable condition values, so trend plots are not scientifically trustworthy.",
                field="condition_value",
                rationale="If the temperature/strain axis is unknown, the agent should not optimize toward that sequence trend.",
            ),
            EvidenceConstraint(
                name="strain_axis_low_confidence",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="The strain axis is present but still low-confidence.",
                field="condition_confidence",
                rationale="Sequence interpretation should remain provisional until the strain axis stabilizes.",
            ),
            EvidenceConstraint(
                name="strain_sequence_nonmonotonic",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="The strain sequence is not strictly monotonic.",
                field="strain_pct",
                rationale="Stretching order must be clear before a trend is interpreted.",
            ),
            EvidenceConstraint(
                name="strain_duplicate_frames",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="Duplicate strain frames weaken sequence continuity.",
                field="condition_value",
                rationale="Duplicate conditions can fake smooth trends.",
            ),
            EvidenceConstraint(
                name="low_q_void_dominant",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="Low-q void or upturn evidence dominates the strain chain.",
                field="phi_void",
                rationale="Void-dominated low-q shapes should be separated before lamellar trends are trusted.",
            ),
            EvidenceConstraint(
                name="strain_void_lamellar_conflict",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="Void growth conflicts with the lamellar long-period interpretation under strain.",
                field="Q_star_rel",
                rationale="A single lamellar explanation is too weak when void evidence rises at the same time.",
            ),
            EvidenceConstraint(
                name="lamellar_anchor_lost_under_strain",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="The lamellar anchor is unstable across the strain series.",
                field="L_bragg",
                rationale="The strain trend needs a stable L anchor before comparison across frames.",
            ),
            EvidenceConstraint(
                name="qstar_rel_without_lamellar_support",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="Q* relative values are present, but lamellar support is weak.",
                field="Q_star_rel",
                rationale="Q* normalization should not outrun the long-period evidence chain.",
            ),
            EvidenceConstraint(
                name="orientation_shift_breaks_lamellar_comparison",
                kind="soft_warn",
                source="SAXS",
                severity="WARN",
                description="Orientation changes are large enough to weaken frame-to-frame lamellar comparison.",
                field="f_Herman",
                rationale="Changing orientation can move the apparent lamellar support even when Q* still looks tidy.",
            ),
        )
    if key == "DSC":
        return _inventory(
            EvidenceConstraint(
                name="quality_floor",
                kind="hard_fail",
                source="DSC",
                severity="ERROR",
                description="Low DSC quality score should not be promoted as a valid candidate.",
                field="quality_score",
                rationale="File-level fits need a minimum quality gate.",
            ),
            EvidenceConstraint(
                name="multi_scan_inconsistent",
                kind="evidence_only",
                source="DSC",
                severity="INFO",
                description="Aggregate scan metrics matter more than one local fit score.",
                field="scan_r_squared",
                rationale="Use the file-level median as the main evidence stream.",
            ),
            EvidenceConstraint(
                name="baseline_sensitive_result",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="Baseline-sensitive DSC output should stay provisional until drift-like residuals settle.",
                field="quality_score",
                rationale="A plausible number is not enough when the thermal baseline is still steering the result.",
            ),
            EvidenceConstraint(
                name="Tg_without_DCp_step",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="A reported Tg without a visible Cp-step should stay evidence-limited.",
                field="Tg_C",
                rationale="Tg claims should be supported by a measurable heat-capacity step.",
            ),
            EvidenceConstraint(
                name="Tg_outside_supported_window",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="Tg outside the configured search window should not be promoted as stable.",
                field="Tg_C",
                rationale="A glass-transition claim needs to stay inside the search bounds that produced it.",
            ),
            EvidenceConstraint(
                name="melting_without_supported_event",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="Reported melting should map to a supported thermal event, not only a fitted scalar.",
                field="Tm_peak_C",
                rationale="Tm should remain anchored to an actual endothermic event.",
            ),
            EvidenceConstraint(
                name="cold_crystallization_conflicts_with_melting",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="Cold crystallisation should stay thermally separated from melting on heating scans.",
                field="Tcc_peak_C",
                rationale="Overlapping event windows weaken the thermodynamic interpretation.",
            ),
            EvidenceConstraint(
                name="event_polarity_conflict",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="Event polarity should match the exo-up convention used by the scan.",
                field="peak_components",
                rationale="A sign mismatch means the event is not yet physically consistent.",
            ),
            EvidenceConstraint(
                name="peak_components_too_sparse",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="Too few supported peak components make DSC conclusions fragile.",
                field="peak_components",
                rationale="Thermal claims need at least one supported event component.",
            ),
            EvidenceConstraint(
                name="peak_width_nonphysical",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="Non-physical DSC event widths usually indicate unstable windows or baseline handling.",
                field="peak_components",
                rationale="Event widths should stay positive and within a realistic thermal window.",
            ),
            EvidenceConstraint(
                name="multi_scan_inconsistent",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="Different scans disagree too much to support a stable file-level DSC conclusion.",
                field="scan_r_squared",
                rationale="File-level confidence should fall when valid scans diverge sharply.",
            ),
            EvidenceConstraint(
                name="crystallinity_without_event_support",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="Crystallinity estimates should stay tied to supported thermal events.",
                field="Xc_pct",
                rationale="Xc should not outrun the melt / cold-crystallisation evidence chain.",
            ),
            EvidenceConstraint(
                name="dsc_baseline_sensitive_xc",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="DSC crystallinity is sensitive to baseline or integration boundaries.",
                field="baseline_sensitivity_pct",
                rationale="Xc should be downgraded when small baseline changes materially alter enthalpy.",
            ),
            EvidenceConstraint(
                name="quality_score_without_event_support",
                kind="soft_warn",
                source="DSC",
                severity="WARN",
                description="A good DSC score is not enough when there is no supported thermal event underneath it.",
                field="quality_score",
                rationale="Fit quality should confirm event support, not replace it.",
            ),
        )
    if key == "WAXS":
        return _inventory(
            EvidenceConstraint(
                name="peak_visibility",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Missing sharp peaks weaken crystallinity claims.",
                field="n_peaks",
                rationale="Crystallinity should be supported by visible peak structure.",
            ),
            EvidenceConstraint(
                name="temperature_axis_missing",
                kind="hard_fail",
                source="WAXS",
                severity="ERROR",
                description="In-situ WAXS sequence is missing a reliable temperature axis.",
                field="temperature_missing_count",
                rationale="Temperature trends cannot be trusted if the axis itself is missing or incomplete.",
            ),
            EvidenceConstraint(
                name="temperature_axis_low_confidence",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="The temperature axis is present but still low-confidence.",
                field="condition_confidence",
                rationale="Sequence interpretation should remain provisional until the temperature axis stabilizes.",
            ),
            EvidenceConstraint(
                name="temperature_sequence_nonmonotonic",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Temperature sequence is not strictly monotonic.",
                field="temperature_monotonic",
                rationale="Heating or cooling order must be clear before a trend is interpreted.",
            ),
            EvidenceConstraint(
                name="temperature_duplicate_frames",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Duplicate temperature frames weaken sequence continuity.",
                field="temperature_duplicate_count",
                rationale="Duplicate conditions can fake smooth trends.",
            ),
            EvidenceConstraint(
                name="peak_count_insufficient",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Too few resolved peaks make phase and size claims fragile.",
                field="n_peaks",
                rationale="A stable crystal family usually needs at least two resolved peaks.",
            ),
            EvidenceConstraint(
                name="peak_family_unstable",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Peak positions or widths drift too much for a stable crystal family.",
                field="peaks",
                rationale="Peak positions and widths should move together rather than fragmenting into unrelated components.",
            ),
            EvidenceConstraint(
                name="amorphous_partition_unstable",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Crystallinity depends too much on amorphous partitioning.",
                field="Xc_method",
                rationale="Peak-area crystallinity should not dominate when the amorphous split is still fragile.",
            ),
            EvidenceConstraint(
                name="peak_width_nonphysical",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Peak widths look implausible for a physical crystal family.",
                field="peaks",
                rationale="Zero, negative, or absurdly broad widths usually indicate a bad fit.",
            ),
            EvidenceConstraint(
                name="offset_sensitive_solution",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="The fit appears sensitive to a non-zero 2θ offset.",
                field="two_theta_offset",
                rationale="A material offset should be resolved before claiming a stable crystal geometry.",
            ),
            EvidenceConstraint(
                name="crystallinity_without_peak_support",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Crystallinity is being claimed without enough peak support.",
                field="Xc_pct",
                rationale="Xc should be backed by a stable peak family, not only by fit smoothness.",
            ),
            EvidenceConstraint(
                name="size_without_multi_peak_support",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Scherrer size is not trustworthy without at least two resolved peaks.",
                field="D_Scherrer_nm",
                rationale="Crystallite size needs more than one peak to be a robust estimate.",
            ),
            EvidenceConstraint(
                name="scherrer_trend_without_multi_peak_support",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Scherrer trend is not trustworthy without repeated multi-peak support.",
                field="D_trend_support_score",
                rationale="Temperature-dependent crystallite size should stay tied to repeated resolved peaks.",
            ),
            EvidenceConstraint(
                name="scherrer_jump_single_frame",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Scherrer size jumps too sharply in a single frame.",
                field="D_jump_single_frame_count",
                rationale="A paper-grade D trend should not hinge on a single unstable frame.",
            ),
            EvidenceConstraint(
                name="scherrer_dominated_by_peak_width_noise",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Scherrer trend is dominated by peak-width noise rather than a stable trend.",
                field="D_slope_distribution",
                rationale="When width noise dominates, the size trend is not yet robust enough for interpretation.",
            ),
            EvidenceConstraint(
                name="scherrer_instrument_broadening_unresolved",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Instrument broadening is not clearly modeled, so Scherrer size remains provisional.",
                field="instrument_broadening_present",
                rationale="Scherrer size should be interpreted with instrument broadening in mind.",
            ),
            EvidenceConstraint(
                name="scherrer_conflicts_with_peak_family_tracking",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Scherrer trend conflicts with unstable peak-family tracking.",
                field="FWHM_values_by_family",
                rationale="Size claims need the same peak families to stay trackable across temperature.",
            ),
            EvidenceConstraint(
                name="scherrer_unphysical_temperature_trend",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Scherrer trend oscillates too much to be treated as a physical temperature trend.",
                field="D_values_nm",
                rationale="A physically meaningful size trend should not bounce frame to frame without support.",
            ),
            EvidenceConstraint(
                name="fit_quality_vs_phys",
                kind="soft_warn",
                source="WAXS",
                severity="WARN",
                description="Fit score is not sufficient without physical support.",
                field="r_squared",
                rationale="A fit-only score can overstate confidence.",
            ),
        )
    if key == "IR":
        return _inventory(
            EvidenceConstraint(
                name="assignment_confidence",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Polymer assignment confidence should be tracked explicitly.",
                field="polymer_score",
                rationale="Peak matching needs a confidence layer, not just raw fit.",
            ),
            EvidenceConstraint(
                name="key_band_support_insufficient",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Reference-band coverage is too weak to support a stable polymer call.",
                field="n_peaks",
                rationale="The agent should not promote a polymer assignment when key bands are still missing.",
            ),
            EvidenceConstraint(
                name="assignment_without_characteristic_bands",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Assignment exists, but characteristic bands are not yet consistently matched.",
                field="assignment_confidence",
                rationale="Assignment confidence should agree with key-band coverage.",
            ),
            EvidenceConstraint(
                name="baseline_sensitive_assignment",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Polymer assignment depends too much on baseline or normalization settings.",
                field="baseline_method",
                rationale="Baseline stability should be resolved before the agent tries to strengthen the call.",
            ),
            EvidenceConstraint(
                name="baseline_drift_low_wn",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="The low-wavenumber edge is drifting and should be stabilized first.",
                field="residual_type",
                rationale="Low-wavenumber drift usually points to baseline instability.",
            ),
            EvidenceConstraint(
                name="baseline_drift_high_wn",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="The high-wavenumber edge is drifting and should be stabilized first.",
                field="residual_type",
                rationale="High-wavenumber drift usually points to normalization instability.",
            ),
            EvidenceConstraint(
                name="key_band_mismatch",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Characteristic bands are locally mismatched against the observed spectrum.",
                field="residual_type",
                rationale="Band identity should stabilize before the polymer call is promoted.",
            ),
            EvidenceConstraint(
                name="crowded_band_underfit",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Crowded bands are not being separated cleanly enough for a stable assignment.",
                field="residual_type",
                rationale="Crowded bands need a separation pass before the conclusion is strengthened.",
            ),
            EvidenceConstraint(
                name="over_smoothed_weak_bands",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Weak bands are likely being smoothed away before they can support the assignment.",
                field="residual_type",
                rationale="Over-smoothing can erase the weak bands needed for a credible call.",
            ),
            EvidenceConstraint(
                name="normalization_bias",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Normalization is biasing the relative band balance.",
                field="residual_type",
                rationale="Normalization should stabilize before peak thresholds are adjusted again.",
            ),
            EvidenceConstraint(
                name="noise_dominant",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="The residual is dominated by noise rather than a localized mismatch.",
                field="residual_type",
                rationale="Noise-dominant spectra should be smoothed before band thresholds are changed.",
            ),
            EvidenceConstraint(
                name="weak_peak_only_support",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Peak detection alone is not enough to support a confident IR conclusion.",
                field="n_peaks",
                rationale="The evidence needs matching reference bands, not just a visible peak count.",
            ),
            EvidenceConstraint(
                name="overcrowded_band_separation_unstable",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Crowded bands or wide fit windows make the local band separation unstable.",
                field="peak_distance",
                rationale="The next tuning round should narrow the band separation problem before pushing confidence up.",
            ),
            EvidenceConstraint(
                name="polymer_score_without_assignment_support",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Polymer score is present but not backed by enough assigned peaks or key bands.",
                field="polymer_score",
                rationale="A score alone should not override weak assignment support.",
            ),
            EvidenceConstraint(
                name="crystallinity_index_without_band_support",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="Crystallinity index is being reported without enough supporting bands.",
                field="Xc_pct",
                rationale="IR crystallinity should stay tentative until the band support chain is stable.",
            ),
            EvidenceConstraint(
                name="ir_xc_uncalibrated",
                kind="soft_warn",
                source="IR",
                severity="WARN",
                description="IR crystallinity is an uncalibrated band index.",
                field="Xc_calibration_status",
                rationale="Uncalibrated IR ratios should stay diagnostic and not be compared as calibrated crystallinity.",
            ),
            EvidenceConstraint(
                name="peak_structure",
                kind="evidence_only",
                source="IR",
                severity="INFO",
                description="Peak count and band coverage are evidence signals.",
                field="n_peaks",
                rationale="Use them as supporting evidence for the assignment path.",
            ),
        )
    if key == "NMR":
        return _inventory(
            EvidenceConstraint(
                name="fit_quality",
                kind="soft_warn",
                source="NMR",
                severity="WARN",
                description="Low-quality deconvolution should reduce confidence.",
                field="quality_metrics.fit_quality",
                rationale="Fit quality should be visible to the orchestrator.",
            ),
            EvidenceConstraint(
                name="peak_snr",
                kind="evidence_only",
                source="NMR",
                severity="INFO",
                description="Median SNR is a supporting confidence signal.",
                field="median_snr",
                rationale="Use it to contextualize line-shape and assignment reliability.",
            ),
            EvidenceConstraint(
                name="nmr_low_peak_count",
                kind="soft_warn",
                source="NMR",
                severity="WARN",
                description="Too few resolved NMR peaks to support strong assignment confidence.",
                field="n_peaks",
                rationale="Assignments and Xc estimates need enough resolved peak support.",
            ),
            EvidenceConstraint(
                name="nmr_low_snr",
                kind="soft_warn",
                source="NMR",
                severity="WARN",
                description="Median NMR SNR is too low for strong assignment confidence.",
                field="median_snr",
                rationale="Low SNR makes peak detection, deconvolution, and assignment fragile.",
            ),
            EvidenceConstraint(
                name="nmr_broad_linewidth",
                kind="soft_warn",
                source="NMR",
                severity="WARN",
                description="NMR linewidth is broad enough to weaken peak separation and phase assignment.",
                field="mean_fwhm_ppm",
                rationale="Broad peaks make crystalline/amorphous peak partitioning less reliable.",
            ),
            EvidenceConstraint(
                name="nmr_weak_assignment",
                kind="soft_warn",
                source="NMR",
                severity="WARN",
                description="Detected NMR peaks are not backed by enough assignments or database matches.",
                field="n_matches",
                rationale="Peak-derived conclusions should stay provisional when assignments are sparse.",
            ),
            EvidenceConstraint(
                name="nmr_solvent_risk",
                kind="soft_warn",
                source="NMR",
                severity="WARN",
                description="One or more NMR peaks overlap likely solvent regions.",
                field="peak_possible_solvent",
                rationale="Solvent-like peaks can inflate or mislead assignment evidence.",
            ),
            EvidenceConstraint(
                name="nmr_xc_assignment_missing",
                kind="soft_warn",
                source="NMR",
                severity="WARN",
                description="NMR crystallinity requires crystalline/amorphous peak assignment support.",
                field="Xc_method",
                rationale="Solid-state NMR Xc should not be promoted before phase assignments are explicit.",
            ),
            EvidenceConstraint(
                name="nmr_xc_assignment_limited",
                kind="soft_warn",
                source="NMR",
                severity="WARN",
                description="NMR Xc is present without crystalline/amorphous phase assignment support.",
                field="Xc_method",
                rationale="Assignment-limited Xc should not enter Joint as strong crystallinity evidence.",
            ),
        )
    return []


def _match_constraint_value(output: dict[str, Any], field: str | None) -> Any:
    if not field:
        return None
    current: Any = output
    for part in field.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _non_empty_mapping(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if value in (None, "", [], {}):
            continue
        out[key] = value
    return out


def _nmr_peak_rows(output: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx in range(10):
        ppm = _clean_float(output.get(f"peak_{idx}_ppm"))
        assignment = str(output.get(f"peak_{idx}_assignment") or "").strip()
        phase = str(output.get(f"peak_{idx}_phase") or "").strip().lower()
        if ppm is None and not assignment and not phase:
            continue
        rows.append(
            _non_empty_mapping(
                [
                    ("index", idx),
                    ("ppm", ppm),
                    ("assignment", assignment or None),
                    ("phase", phase or None),
                    ("snr", _clean_float(output.get(f"peak_{idx}_snr"))),
                    ("fwhm_ppm", _clean_float(output.get(f"peak_{idx}_fwhm_ppm"))),
                    ("area", _clean_float(output.get(f"peak_{idx}_area"))),
                    ("delta_ppm", _clean_float(output.get(f"peak_{idx}_delta_ppm"))),
                    ("possible_solvent", str(output.get(f"peak_{idx}_possible_solvent") or "").strip() or None),
                ]
            )
        )
    return rows


def _nmr_symptoms_from_constraints(constraints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = {
        "nmr_low_peak_count",
        "nmr_low_snr",
        "nmr_broad_linewidth",
        "nmr_weak_assignment",
        "nmr_solvent_risk",
        "nmr_xc_assignment_missing",
        "nmr_xc_assignment_limited",
    }
    symptoms: list[dict[str, Any]] = []
    for item in constraints:
        name = str(item.get("name", "") or "").strip()
        if name not in names or not item.get("triggered"):
            continue
        symptoms.append(
            _non_empty_mapping(
                [
                    ("name", name),
                    ("severity", item.get("severity") or "WARN"),
                    ("summary", item.get("description")),
                    ("target", item.get("field") or name),
                    ("observed", item.get("observed")),
                ]
            )
        )
    return symptoms


def _nmr_symptom_bridge_lines(symptom: dict[str, Any] | None) -> list[str]:
    if not isinstance(symptom, dict):
        return []
    name = str(symptom.get("name", "") or "").strip()
    mapping = {
        "nmr_low_peak_count": "nmr_low_peak_count -> review peak threshold and deconvolution settings before trusting assignments",
        "nmr_low_snr": "nmr_low_snr -> review baseline correction and peak threshold before trusting assignments",
        "nmr_broad_linewidth": "nmr_broad_linewidth -> review baseline, apodization, and peak fitting before trusting phase assignment",
        "nmr_weak_assignment": "nmr_weak_assignment -> add or verify peak assignments before promoting structural conclusions",
        "nmr_solvent_risk": "nmr_solvent_risk -> exclude likely solvent peaks before using assignment evidence",
        "nmr_xc_assignment_missing": "nmr_xc_assignment_missing -> assign crystalline and amorphous peaks before trusting NMR Xc",
        "nmr_xc_assignment_limited": "nmr_xc_assignment_limited -> keep NMR Xc diagnostic until crystalline and amorphous peaks are assigned",
    }
    return [mapping[name]] if name in mapping else []


def _dsc_scan_rows(scan_r_squared: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(scan_r_squared, dict):
        scan_r_squared = [scan_r_squared]
    if not isinstance(scan_r_squared, list):
        return rows
    for item in scan_r_squared:
        if not isinstance(item, dict):
            continue
        row = _non_empty_mapping(
            [
                ("scan", item.get("scan")),
                ("label", str(item.get("label", "") or "").strip() or None),
                ("r_squared", _clean_float(item.get("r_squared"))),
                ("fit_rmse", _clean_float(item.get("fit_rmse"))),
                ("quality_score", _clean_float(item.get("quality_score"))),
                ("n_fit_regions", item.get("n_fit_regions")),
            ]
        )
        if row:
            rows.append(row)
    return rows


def _dsc_peak_component_rows(peak_components: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(peak_components, list):
        return rows
    for item in peak_components:
        if not isinstance(item, dict):
            continue
        row = _non_empty_mapping(
            [
                ("type", str(item.get("type", "") or "").strip() or None),
                ("peak_C", _clean_float(item.get("peak_C"))),
                ("onset_C", _clean_float(item.get("onset_C"))),
                ("end_C", _clean_float(item.get("end_C"))),
                ("enthalpy_Jg", _clean_float(item.get("enthalpy_Jg"))),
                ("fraction", _clean_float(item.get("fraction"))),
                ("sigma_C", _clean_float(item.get("sigma_C", item.get("sigma")))),
                ("amplitude", _clean_float(item.get("amplitude", item.get("amp")))),
            ]
        )
        if row:
            rows.append(row)
    return rows


def _extract_nested_mapping(value: Any, *keys: str) -> dict[str, Any]:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _shape_tuple(value: Any) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    out: list[int] = []
    for item in value:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            return ()
    return tuple(out)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_ir_temperature_2d(output: dict[str, Any], validation: dict[str, Any] | None = None) -> bool:
    validation = dict(validation or {})
    submodule_id = str(validation.get("submodule_id", "") or "").strip().lower()
    if submodule_id == "ir.temperature_2d":
        return True
    matrix_shape = _shape_tuple(output.get("matrix_shape"))
    dynamic_shape = _shape_tuple(output.get("dynamic_shape"))
    sync_shape = _shape_tuple(output.get("sync_shape"))
    async_shape = _shape_tuple(output.get("async_shape"))
    if matrix_shape and dynamic_shape and sync_shape and async_shape:
        return True
    return any(key in output for key in ("sync_cross_peak_count", "async_cross_peak_count", "n_frames", "stage_counts"))


def _ir_temperature_2d_metrics(output: dict[str, Any], validation: dict[str, Any] | None = None) -> dict[str, Any]:
    validation = dict(validation or {})
    stage_counts = output.get("stage_counts", {})
    if not isinstance(stage_counts, dict):
        stage_counts = {}
    matrix_shape = _shape_tuple(output.get("matrix_shape"))
    dynamic_shape = _shape_tuple(output.get("dynamic_shape"))
    sync_shape = _shape_tuple(output.get("sync_shape"))
    async_shape = _shape_tuple(output.get("async_shape"))

    n_frames = _safe_int(output.get("n_frames"), 0)
    n_bands_tracked = _safe_int(output.get("n_bands_tracked"), 0)
    temperature_missing_count = _safe_int(output.get("temperature_missing_count"), 0)
    time_missing_count = _safe_int(output.get("time_missing_count"), 0)
    time_estimated_count = _safe_int(output.get("time_estimated_count"), 0)
    hold_time_missing_count = _safe_int(output.get("hold_time_missing_count"), 0)
    hold_time_estimated_count = _safe_int(output.get("hold_time_estimated_count"), 0)
    transition_count = _safe_int(output.get("transition_count", output.get("n_transitions")), 0)
    sync_cross_peak_count = _safe_int(output.get("sync_cross_peak_count"), 0)
    async_cross_peak_count = _safe_int(output.get("async_cross_peak_count"), 0)
    cross_peak_count = _safe_int(output.get("cross_peak_count"), sync_cross_peak_count + async_cross_peak_count)
    assigned_cross_peak_count = _safe_int(output.get("assigned_cross_peak_count"), 0)
    unassigned_cross_peak_count = _safe_int(output.get("unassigned_cross_peak_count"), 0)
    async_with_sync_support_count = _safe_int(output.get("async_with_sync_support_count"), 0)
    band_index_series_count = _safe_int(output.get("band_index_series_count"), 0)
    band_index_transition_candidate_count = _safe_int(output.get("band_index_transition_candidate_count"), 0)
    band_index_transition_support_band_count = _safe_int(output.get("band_index_transition_support_band_count"), 0)
    band_index_transition_consensus_frame = _safe_int(output.get("band_index_transition_consensus_frame"), -1)
    band_index_transition_frame_spread = _clean_float(output.get("band_index_transition_frame_spread"))
    band_index_transition_support_ratio = _clean_float(output.get("band_index_transition_support_ratio"))
    band_index_transition_single_frame_only = bool(output.get("band_index_transition_single_frame_only", False))
    band_index_transition_reproducible = bool(output.get("band_index_transition_reproducible", False))
    band_index_transition_denominator_unstable = bool(output.get("band_index_transition_denominator_unstable", False))
    band_index_transition_max_jump = _clean_float(output.get("band_index_transition_max_jump_cm1"))
    band_index_transition_median_jump = _clean_float(output.get("band_index_transition_median_jump_cm1"))
    band_index_transition_max_jump_ratio = _clean_float(output.get("band_index_transition_max_jump_ratio"))
    band_tracking_missing_key_band = bool(output.get("band_tracking_missing_key_band", False))
    band_index_transition_support_keys = output.get("band_index_transition_support_keys", [])
    if not isinstance(band_index_transition_support_keys, list):
        band_index_transition_support_keys = []
    low_confidence_frame_count = _safe_int(output.get("low_confidence_frame_count"), 0)
    low_confidence_frame_ratio = _clean_float(output.get("low_confidence_frame_ratio"))
    frame_assignment_confidence_mean = _clean_float(output.get("frame_assignment_confidence_mean"))
    frame_polymer_score_mean = _clean_float(output.get("frame_polymer_score_mean"))
    frame_key_band_support_mean = _clean_float(output.get("frame_key_band_support_mean"))

    heating_monotonic = bool(output.get("heating_monotonic", False))
    cooling_monotonic = bool(output.get("cooling_monotonic", False))
    hold_monotonic = bool(output.get("hold_monotonic", False))
    sequence_order_source = str(output.get("sequence_order_source", validation.get("sequence_order_source", "")) or "").strip()
    temperature_min = _clean_float(output.get("temperature_min_C"))
    temperature_max = _clean_float(output.get("temperature_max_C"))
    neg_fraction = _clean_float(output.get("neg_fraction"))
    nan_fraction = _clean_float(output.get("nan_fraction", output.get("matrix_nan_fraction")))
    dynamic_rms = _clean_float(output.get("dynamic_rms"))
    dynamic_signal_rms = _clean_float(output.get("dynamic_signal_rms", dynamic_rms))
    max_sync_abs = _clean_float(output.get("max_sync_abs"))
    max_async_abs = _clean_float(output.get("max_async_abs"))
    top_sync_diagonal_distance = _clean_float(output.get("top_sync_diagonal_distance_cm1"))
    top_async_diagonal_distance = _clean_float(output.get("top_async_diagonal_distance_cm1"))
    top_sync_assigned = bool(output.get("top_sync_assigned", False))
    top_async_assigned = bool(output.get("top_async_assigned", False))
    top_async_has_sync_support = bool(output.get("top_async_has_sync_support", False))
    noda_rule_interpretation_ready = bool(output.get("noda_rule_interpretation_ready", False))
    frame_intensity_scale_spread = _clean_float(output.get("frame_intensity_scale_spread"))
    wavenumber_grid_consistent = bool(output.get("wavenumber_grid_consistent", True))

    stage_total = 0
    for value in stage_counts.values():
        stage_total += _safe_int(value, 0)

    sequence_axis_ready = bool(
        n_frames >= 3
        and stage_total == n_frames
        and temperature_missing_count == 0
        and heating_monotonic
        and cooling_monotonic
        and hold_monotonic
        and temperature_min is not None
        and temperature_max is not None
    )
    matrix_shapes_consistent = bool(
        matrix_shape
        and dynamic_shape
        and sync_shape
        and async_shape
        and len(matrix_shape) == 2
        and len(dynamic_shape) == 2
        and len(sync_shape) == 2
        and len(async_shape) == 2
        and matrix_shape == dynamic_shape
        and sync_shape[0] == sync_shape[1]
        and async_shape[0] == async_shape[1]
        and matrix_shape[1] == sync_shape[0] == async_shape[0]
    )

    sequence_axis_score = _clamp_unit(
        (0.52 if n_frames >= 3 else 0.18)
        + (0.14 if stage_total == n_frames and stage_total > 0 else 0.0)
        + (0.10 if temperature_missing_count == 0 else 0.0)
        + (0.07 if time_missing_count == 0 else 0.0)
        + (0.06 if heating_monotonic else 0.0)
        + (0.06 if cooling_monotonic else 0.0)
        + (0.03 if hold_monotonic else 0.0)
        + (0.03 if sequence_order_source else 0.0)
        - min(time_estimated_count, 5) * 0.01,
        default=0.0,
    )
    matrix_quality_score = 0.38
    if matrix_shapes_consistent:
        matrix_quality_score += 0.18
    if neg_fraction is not None:
        matrix_quality_score += 0.24 * max(0.0, 1.0 - min(neg_fraction, 0.50) / 0.50)
    if dynamic_signal_rms is not None:
        matrix_quality_score += 0.18 * min(dynamic_signal_rms / 0.05, 1.0)
    if nan_fraction is not None:
        matrix_quality_score += 0.08 * max(0.0, 1.0 - min(nan_fraction, 0.30) / 0.30)
    if wavenumber_grid_consistent:
        matrix_quality_score += 0.08
    if frame_intensity_scale_spread is not None:
        matrix_quality_score += 0.04 * max(0.0, 1.0 - min(frame_intensity_scale_spread, 1.0))
    matrix_quality_score = _clamp_unit(matrix_quality_score, default=0.0)
    cos_signal_score = _clamp_unit(
        0.45 * min(sync_cross_peak_count / 12.0, 1.0)
        + 0.35 * min(async_cross_peak_count / 12.0, 1.0)
        + 0.10 * min((max_sync_abs or 0.0) / 0.02, 1.0)
        + 0.10 * min((max_async_abs or 0.0) / 0.02, 1.0),
        default=0.0,
    )
    band_tracking_score = _clamp_unit(
        0.35
        + (0.12 if band_index_series_count >= 3 else 0.0)
        + (0.14 if band_index_transition_support_band_count >= 2 else 0.0)
        + (0.12 if band_index_transition_reproducible else 0.0)
        + (0.10 if not band_index_transition_single_frame_only else 0.0)
        + (0.08 if transition_count > 0 else 0.0)
        - (0.12 if band_tracking_missing_key_band else 0.0)
        - (0.10 if band_index_transition_denominator_unstable else 0.0),
        default=0.0,
    )
    interpretation_ready = bool(
        sequence_axis_ready
        and matrix_quality_score >= 0.60
        and sync_cross_peak_count > 0
        and async_cross_peak_count > 0
        and (band_index_transition_reproducible or band_index_transition_support_band_count >= 2)
    )
    paper_conclusion_ready = bool(
        interpretation_ready
        and transition_count > 0
        and neg_fraction is not None
        and neg_fraction <= 0.30
        and band_index_transition_reproducible
    )

    return {
        "submodule_id": str(validation.get("submodule_id", "") or "").strip() or "ir.temperature_2d",
        "stage_counts": stage_counts,
        "matrix_shape": matrix_shape,
        "dynamic_shape": dynamic_shape,
        "sync_shape": sync_shape,
        "async_shape": async_shape,
        "n_frames": n_frames,
        "n_bands_tracked": n_bands_tracked,
        "temperature_missing_count": temperature_missing_count,
        "time_missing_count": time_missing_count,
        "time_estimated_count": time_estimated_count,
        "hold_time_missing_count": hold_time_missing_count,
        "hold_time_estimated_count": hold_time_estimated_count,
        "transition_count": transition_count,
        "transition_temperatures_C": str(output.get("transition_temperatures_C", "") or "").strip(),
        "sync_cross_peak_count": sync_cross_peak_count,
        "async_cross_peak_count": async_cross_peak_count,
        "cross_peak_count": cross_peak_count,
        "assigned_cross_peak_count": assigned_cross_peak_count,
        "unassigned_cross_peak_count": unassigned_cross_peak_count,
        "async_with_sync_support_count": async_with_sync_support_count,
        "band_index_series_count": band_index_series_count,
        "band_index_transition_candidate_count": band_index_transition_candidate_count,
        "band_index_transition_support_band_count": band_index_transition_support_band_count,
        "band_index_transition_consensus_frame": band_index_transition_consensus_frame,
        "band_index_transition_frame_spread": band_index_transition_frame_spread,
        "band_index_transition_support_ratio": band_index_transition_support_ratio,
        "band_index_transition_single_frame_only": band_index_transition_single_frame_only,
        "band_index_transition_reproducible": band_index_transition_reproducible,
        "band_index_transition_denominator_unstable": band_index_transition_denominator_unstable,
        "band_index_transition_max_jump_cm1": band_index_transition_max_jump,
        "band_index_transition_median_jump_cm1": band_index_transition_median_jump,
        "band_index_transition_max_jump_ratio": band_index_transition_max_jump_ratio,
        "band_tracking_missing_key_band": band_tracking_missing_key_band,
        "band_index_transition_support_keys": band_index_transition_support_keys,
        "low_confidence_frame_count": low_confidence_frame_count,
        "low_confidence_frame_ratio": low_confidence_frame_ratio,
        "frame_assignment_confidence_mean": frame_assignment_confidence_mean,
        "frame_polymer_score_mean": frame_polymer_score_mean,
        "frame_key_band_support_mean": frame_key_band_support_mean,
        "sequence_order_source": sequence_order_source,
        "heating_monotonic": heating_monotonic,
        "cooling_monotonic": cooling_monotonic,
        "hold_monotonic": hold_monotonic,
        "temperature_min_C": temperature_min,
        "temperature_max_C": temperature_max,
        "T_range_C": str(output.get("T_range_C", "") or "").strip(),
        "neg_fraction": neg_fraction,
        "nan_fraction": nan_fraction,
        "dynamic_rms": dynamic_rms,
        "dynamic_signal_rms": dynamic_signal_rms,
        "max_sync_abs": max_sync_abs,
        "max_async_abs": max_async_abs,
        "frame_intensity_scale_spread": frame_intensity_scale_spread,
        "wavenumber_grid_consistent": wavenumber_grid_consistent,
        "top_sync_cross_peak_cm1": str(output.get("top_sync_cross_peak_cm1", "") or "").strip(),
        "top_async_cross_peak_cm1": str(output.get("top_async_cross_peak_cm1", "") or "").strip(),
        "top_sync_diagonal_distance_cm1": top_sync_diagonal_distance,
        "top_async_diagonal_distance_cm1": top_async_diagonal_distance,
        "top_sync_assigned": top_sync_assigned,
        "top_async_assigned": top_async_assigned,
        "top_async_has_sync_support": top_async_has_sync_support,
        "noda_rule_interpretation_ready": noda_rule_interpretation_ready,
        "sequence_axis_ready": sequence_axis_ready,
        "matrix_shapes_consistent": matrix_shapes_consistent,
        "sequence_axis_score": sequence_axis_score,
        "matrix_quality_score": matrix_quality_score,
        "cos_signal_score": cos_signal_score,
        "band_tracking_score": band_tracking_score,
        "interpretation_ready": interpretation_ready,
        "paper_conclusion_ready": paper_conclusion_ready,
    }


def _ir_temperature_2d_symptoms_from_constraints(
    constraints: list[dict[str, Any]],
    output: dict[str, Any],
    residual: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, Any]]:
    triggered = {
        str(item.get("name", "") or "").strip(): item
        for item in constraints
        if isinstance(item, dict) and item.get("triggered")
    }
    metrics = _ir_temperature_2d_metrics(output, validation)
    symptom_list: list[dict[str, Any]] = []

    def add(name: str, summary: str, target_params: list[str], observed: dict[str, Any], expected: list[str]) -> None:
        item = triggered.get(name)
        if not item:
            return
        symptom_list.append(
            {
                "name": name,
                "severity": str(item.get("severity", "") or "").strip() or "WARN",
                "source": "IR_temperature_2d",
                "summary": summary,
                "target_params": target_params,
                "observed": observed,
                "expected_evidence_change": expected,
            }
        )

    add(
        "sequence_axis_incomplete",
        "The 2D IR sequence axis is incomplete, so perturbation ordering is not yet trustworthy.",
        ["temperature_axis_source", "time_axis_source"],
        {
            "n_frames": metrics.get("n_frames"),
            "stage_counts": metrics.get("stage_counts"),
            "temperature_missing_count": metrics.get("temperature_missing_count"),
            "time_missing_count": metrics.get("time_missing_count"),
            "heating_monotonic": metrics.get("heating_monotonic"),
            "cooling_monotonic": metrics.get("cooling_monotonic"),
            "hold_monotonic": metrics.get("hold_monotonic"),
        },
        [
            "temperature/time axis recovery should become complete",
            "heating/cooling/hold ordering should stabilize",
        ],
    )
    add(
        "temperature_axis_missing",
        "The 2D IR sequence does not yet have a reliable temperature axis.",
        ["temperature_axis_source", "sequence_order_source"],
        {
            "temperature_missing_count": metrics.get("temperature_missing_count"),
            "sequence_order_source": metrics.get("sequence_order_source"),
            "stage_counts": metrics.get("stage_counts"),
        },
        [
            "temperature recovery should become explicit",
            "the sequence axis should no longer depend on guessed order",
        ],
    )
    add(
        "stage_order_ambiguous",
        "Heating, hold, and cooling are not in a clean order yet.",
        ["stage_sequence", "sequence_order_source"],
        {
            "heating_monotonic": metrics.get("heating_monotonic"),
            "cooling_monotonic": metrics.get("cooling_monotonic"),
            "hold_monotonic": metrics.get("hold_monotonic"),
            "sequence_order_source": metrics.get("sequence_order_source"),
        },
        [
            "stage ordering should become monotonic and explicit",
            "mixed sequence directions should not be interpreted as real transitions",
        ],
    )
    add(
        "hold_time_missing_or_estimated",
        "Hold-time values are missing or only estimated, so the hold segment is less trustworthy.",
        ["time_axis_source", "hold_time_source"],
        {
            "time_missing_count": metrics.get("time_missing_count"),
            "hold_time_missing_count": metrics.get("hold_time_missing_count"),
            "hold_time_estimated_count": metrics.get("hold_time_estimated_count"),
        },
        [
            "hold times should be recovered explicitly",
            "estimated hold segments should not drive the conclusion",
        ],
    )
    add(
        "matrix_shape_inconsistent",
        "The 2D IR matrix and correlation shapes are inconsistent.",
        ["matrix_shape", "sync_shape", "async_shape"],
        {
            "matrix_shape": metrics.get("matrix_shape"),
            "dynamic_shape": metrics.get("dynamic_shape"),
            "sync_shape": metrics.get("sync_shape"),
            "async_shape": metrics.get("async_shape"),
        },
        [
            "dynamic and correlation shapes should agree",
            "2D-COS maps should be square and aligned with the tracked axis",
        ],
    )
    add(
        "negative_matrix_fraction_high",
        "The absorbance matrix contains too many non-positive values.",
        ["baseline_method", "mute_zone", "matrix_recovery"],
        {
            "neg_fraction": metrics.get("neg_fraction"),
            "nan_fraction": metrics.get("nan_fraction"),
            "dynamic_rms": metrics.get("dynamic_rms"),
        },
        [
            "baseline over-subtraction should weaken",
            "dynamic matrix sign balance should move toward a stable range",
        ],
    )
    add(
        "matrix_nan_fraction_high",
        "The 2D IR matrix contains too many NaN values.",
        ["matrix_recovery", "interpolation_grid"],
        {
            "nan_fraction": metrics.get("nan_fraction"),
            "wavenumber_grid_consistent": metrics.get("wavenumber_grid_consistent"),
        },
        [
            "spectral interpolation should become complete",
            "matrix holes should be filled before 2D-COS interpretation",
        ],
    )
    add(
        "wavenumber_grid_inconsistent",
        "The per-frame wavenumber grids are not aligned to a shared axis.",
        ["wavenumber_grid", "matrix_shape"],
        {
            "wavenumber_grid_consistent": metrics.get("wavenumber_grid_consistent"),
            "sequence_order_source": metrics.get("sequence_order_source"),
        },
        [
            "all frames should share the same wavenumber grid",
            "grid alignment should be fixed before cross-peak ranking",
        ],
    )
    add(
        "frame_intensity_scale_unstable",
        "The frame-to-frame intensity scale is drifting too much.",
        ["normalization_method", "baseline_method", "frame_scale"],
        {
            "frame_intensity_scale_spread": metrics.get("frame_intensity_scale_spread"),
            "dynamic_rms": metrics.get("dynamic_rms"),
        },
        [
            "frame scale should stabilize across the series",
            "normalization should stop erasing the temperature trend",
        ],
    )
    add(
        "weak_cos_signal",
        "2D-COS signal is too weak for stable synchronous/asynchronous interpretation.",
        ["baseline_method", "matrix_recovery", "transition_review"],
        {
            "sync_cross_peak_count": metrics.get("sync_cross_peak_count"),
            "async_cross_peak_count": metrics.get("async_cross_peak_count"),
            "dynamic_rms": metrics.get("dynamic_rms"),
            "top_sync_cross_peak_cm1": metrics.get("top_sync_cross_peak_cm1"),
            "top_async_cross_peak_cm1": metrics.get("top_async_cross_peak_cm1"),
        },
        [
            "sync and async cross peaks should become repeatable",
            "cross-peak ranking should stabilize",
        ],
    )
    add(
        "cross_peak_near_diagonal",
        "The strongest 2D-COS cross peak is still too close to the diagonal.",
        ["cross_peak_exclusion_cm1", "cross_peak_threshold"],
        {
            "top_sync_diagonal_distance_cm1": metrics.get("top_sync_diagonal_distance_cm1"),
            "top_async_diagonal_distance_cm1": metrics.get("top_async_diagonal_distance_cm1"),
        },
        [
            "top cross peaks should move away from the diagonal band",
            "self-correlation leakage should weaken",
        ],
    )
    add(
        "cross_peak_without_band_assignment",
        "The leading 2D-COS peaks do not yet map cleanly onto reference bands.",
        ["assignment_tolerance_cm1", "cross_peak_exclusion_cm1"],
        {
            "assigned_cross_peak_count": metrics.get("assigned_cross_peak_count"),
            "unassigned_cross_peak_count": metrics.get("unassigned_cross_peak_count"),
            "top_sync_assigned": metrics.get("top_sync_assigned"),
            "top_async_assigned": metrics.get("top_async_assigned"),
        },
        [
            "assigned cross-peak count should rise",
            "top peaks should align with known bands before interpretation is promoted",
        ],
    )
    add(
        "async_peak_without_sync_support",
        "The asynchronous peak does not yet have enough synchronous support.",
        ["cross_peak_exclusion_cm1", "assignment_tolerance_cm1"],
        {
            "async_with_sync_support_count": metrics.get("async_with_sync_support_count"),
            "top_async_has_sync_support": metrics.get("top_async_has_sync_support"),
        },
        [
            "async peaks should be backed by a stable sync pair",
            "Noda-order interpretation should stop depending on isolated async peaks",
        ],
    )
    add(
        "noda_rule_not_applicable",
        "The current 2D-COS evidence is not yet strong enough for Noda-rule interpretation.",
        ["sequence_axis_source", "assignment_tolerance_cm1", "cross_peak_exclusion_cm1"],
        {
            "noda_rule_interpretation_ready": metrics.get("noda_rule_interpretation_ready"),
            "top_async_has_sync_support": metrics.get("top_async_has_sync_support"),
            "assigned_cross_peak_count": metrics.get("assigned_cross_peak_count"),
        },
        [
            "Noda-rule interpretation should wait until sync/async support becomes explicit",
            "the perturbation ordering and peak assignment chain should become complete",
        ],
    )
    add(
        "insufficient_perturbation_frames",
        "There are not enough perturbation frames to support stable 2D-COS interpretation.",
        ["n_frames", "stage_sequence"],
        {
            "n_frames": metrics.get("n_frames"),
            "stage_counts": metrics.get("stage_counts"),
        },
        [
            "more frames should be present before paper-ready interpretation",
            "the perturbation series should have enough change points",
        ],
    )
    add(
        "transition_candidate_present",
        "A temperature-dependent transition candidate is present in the tracked bands.",
        ["transition_review", "band_tracking"],
        {
            "transition_count": metrics.get("transition_count"),
            "transition_temperatures_C": metrics.get("transition_temperatures_C"),
        },
        [
            "transition candidate should be verified against the raw sequence",
            "cross-peak interpretation should stay evidence-only until stable",
        ],
    )
    add(
        "band_index_jump_single_frame",
        "The band-index transition is still dominated by a single-frame jump.",
        ["band_tracking", "transition_review"],
        {
            "band_index_transition_support_band_count": metrics.get("band_index_transition_support_band_count"),
            "band_index_transition_frame_spread": metrics.get("band_index_transition_frame_spread"),
            "band_index_transition_max_jump_cm1": metrics.get("band_index_transition_max_jump_cm1"),
            "band_index_transition_max_jump_ratio": metrics.get("band_index_transition_max_jump_ratio"),
        },
        [
            "transition support should span more than one band index series",
            "single-frame spikes should stop dominating the transition readout",
        ],
    )
    add(
        "band_index_denominator_unstable",
        "The band-index denominator looks unstable, so the transition may be amplified by a weak local baseline.",
        ["band_tracking", "transition_review"],
        {
            "band_index_transition_denominator_unstable": metrics.get("band_index_transition_denominator_unstable"),
            "band_index_transition_max_jump_ratio": metrics.get("band_index_transition_max_jump_ratio"),
        },
        [
            "the band-index scale should be more balanced",
            "local denominator effects should stop dominating the transition shape",
        ],
    )
    add(
        "transition_single_frame_only",
        "The transition is only supported by a single-frame event so far.",
        ["band_tracking", "transition_review"],
        {
            "band_index_transition_support_band_count": metrics.get("band_index_transition_support_band_count"),
            "band_index_transition_frame_spread": metrics.get("band_index_transition_frame_spread"),
            "band_index_transition_reproducible": metrics.get("band_index_transition_reproducible"),
        },
        [
            "transition support should cover multiple band indices",
            "the transition should persist across adjacent frames",
        ],
    )
    add(
        "band_tracking_missing_key_band",
        "One or more tracked transition bands are still missing from the band-index chain.",
        ["band_tracking", "reference_band_chain"],
        {
            "band_index_series_count": metrics.get("band_index_series_count"),
            "band_index_transition_support_keys": metrics.get("band_index_transition_support_keys"),
        },
        [
            "the key band-index series should be present before transition claims are strengthened",
            "band tracking should cover all expected reference bands",
        ],
    )
    add(
        "temperature_trend_not_reproducible",
        "The temperature trend is not yet reproducible across the tracked band indices.",
        ["band_tracking", "transition_review"],
        {
            "band_index_transition_support_band_count": metrics.get("band_index_transition_support_band_count"),
            "band_index_transition_reproducible": metrics.get("band_index_transition_reproducible"),
            "band_index_transition_support_ratio": metrics.get("band_index_transition_support_ratio"),
        },
        [
            "the same transition should be supported by multiple tracked bands",
            "trend direction should stay consistent across the series",
        ],
    )
    return symptom_list


def _ir_temperature_2d_symptom_bridge_lines(
    symptom: dict[str, Any] | None,
    output: dict[str, Any] | None = None,
) -> list[str]:
    if not isinstance(symptom, dict):
        return []

    output = dict(output or {})
    name = str(symptom.get("name", "") or "").strip().lower()
    targets = symptom.get("target_params", [])
    if not isinstance(targets, list):
        targets = []
    target_text = " / ".join(str(item).strip() for item in targets if str(item).strip())

    bridge_map = {
        "sequence_axis_incomplete": "sequence_axis_incomplete -> recover temperature/time ordering before promoting the 2D map",
        "temperature_axis_missing": "temperature_axis_missing -> recover an explicit temperature axis before treating the sequence as real perturbation data",
        "stage_order_ambiguous": "stage_order_ambiguous -> separate heating, hold, and cooling before reading the trend",
        "hold_time_missing_or_estimated": "hold_time_missing_or_estimated -> recover the hold segment timing before using it as evidence",
        "matrix_shape_inconsistent": "matrix_shape_inconsistent -> make the dynamic matrix and 2D-COS shapes line up first",
        "negative_matrix_fraction_high": "negative_matrix_fraction_high -> reduce baseline over-subtraction before trusting the 2D map",
        "matrix_nan_fraction_high": "matrix_nan_fraction_high -> fill the matrix holes before interpreting 2D-COS peaks",
        "wavenumber_grid_inconsistent": "wavenumber_grid_inconsistent -> align every frame to the same wavenumber grid before cross-peak ranking",
        "frame_intensity_scale_unstable": "frame_intensity_scale_unstable -> stabilize frame intensity scaling before promoting the transition",
        "dynamic_signal_too_weak": "dynamic_signal_too_weak -> recover a stronger dynamic signal before trusting the cross-peak map",
        "weak_cos_signal": "weak_cos_signal -> stabilize the sync/async peaks before drawing transitions from them",
        "cross_peak_near_diagonal": "cross_peak_near_diagonal -> push the leading cross peaks away from the diagonal before reading them as real coupling",
        "cross_peak_without_band_assignment": "cross_peak_without_band_assignment -> recover reference-band assignment before using the cross-peak map for mechanism claims",
        "async_peak_without_sync_support": "async_peak_without_sync_support -> require a matching synchronous pair before trusting async ordering",
        "noda_rule_not_applicable": "noda_rule_not_applicable -> keep Noda-rule interpretation disabled until sync/async support and assignment both hold",
        "band_index_jump_single_frame": "band_index_jump_single_frame -> require multi-band support before calling the transition real",
        "band_index_denominator_unstable": "band_index_denominator_unstable -> stabilize the band-index scale before trusting the transition magnitude",
        "transition_single_frame_only": "transition_single_frame_only -> keep the transition tentative until adjacent frames support it",
        "band_tracking_missing_key_band": "band_tracking_missing_key_band -> recover the missing tracked bands before strengthening the conclusion",
        "temperature_trend_not_reproducible": "temperature_trend_not_reproducible -> require the same trend to repeat across multiple tracked bands",
        "insufficient_perturbation_frames": "insufficient_perturbation_frames -> gather more perturbation frames before paper-ready interpretation",
        "transition_candidate_present": "transition_candidate_present -> keep the transition as evidence-only until the sequence and matrix stay stable",
    }

    lead = bridge_map.get(name)
    if not lead:
        summary = str(symptom.get("summary", "") or "").strip()
        if target_text:
            lead = f"{name} -> {target_text}"
        elif summary:
            lead = f"{name} -> {summary}"
        else:
            return []

    lines = [lead]
    expected = symptom.get("expected_evidence_change", [])
    if not isinstance(expected, list):
        expected = []
    lines.extend(f"expected evidence change: {str(item).strip()}" for item in expected if str(item).strip())
    quality_flag = str(output.get("quality_flag", "") or "").strip()
    validation_summary = str(output.get("validation_summary", "") or "").strip()
    if quality_flag:
        lines.append(f"current quality_flag: {quality_flag}")
    if validation_summary and validation_summary != "All checks passed":
        lines.append(f"current validation_summary: {validation_summary}")
    return lines


def _waxs_peak_metrics(output: dict[str, Any]) -> dict[str, Any]:
    raw_peaks = output.get("peaks")
    peaks: list[dict[str, Any]] = []

    if isinstance(raw_peaks, list):
        for peak in raw_peaks:
            if not isinstance(peak, dict):
                continue
            center = _clean_float(peak.get("two_theta", peak.get("center")))
            width = _clean_float(peak.get("fwhm_deg", peak.get("fwhm")))
            area = _clean_float(peak.get("area"))
            peaks.append(
                {
                    "center": center,
                    "width": width,
                    "area": area,
                    "hkl": str(peak.get("hkl", "") or "").strip(),
                }
            )

    if not peaks:
        centers = output.get("peak_centers")
        if isinstance(centers, list):
            for center in centers:
                peaks.append({"center": _clean_float(center), "width": None, "area": None, "hkl": ""})

    centers = [item["center"] for item in peaks if item.get("center") is not None]
    widths = [item["width"] for item in peaks if item.get("width") is not None]
    areas = [item["area"] for item in peaks if item.get("area") is not None]
    sorted_centers = sorted(centers)
    gaps = [b - a for a, b in zip(sorted_centers, sorted_centers[1:]) if b > a]
    peak_gap_spread = _relative_spread(gaps)
    peak_width_spread = _relative_spread(widths)
    area_ratio = None
    positive_areas = [float(value) for value in areas if value is not None and float(value) > 0]
    if len(positive_areas) >= 2:
        area_ratio = max(positive_areas) / max(min(positive_areas), 1e-9)

    return {
        "peaks": peaks,
        "peak_count": len(centers),
        "peak_positions": centers,
        "peak_widths": widths,
        "peak_areas": areas,
        "peak_gap_spread": peak_gap_spread,
        "peak_width_spread": peak_width_spread,
        "peak_area_ratio": area_ratio,
    }


def _ir_peak_records(output: dict[str, Any]) -> list[dict[str, Any]]:
    raw_peaks = output.get("peaks")
    peaks: list[dict[str, Any]] = []

    if isinstance(raw_peaks, list) and raw_peaks:
        for peak in raw_peaks:
            if not isinstance(peak, dict):
                continue
            peaks.append(
                {
                    "wavenumber": _clean_float(peak.get("wavenumber")),
                    "height": _clean_float(peak.get("height")),
                    "prominence": _clean_float(peak.get("prominence")),
                    "fwhm_cm1": _clean_float(peak.get("fwhm_cm1", peak.get("fwhm"))),
                    "area": _clean_float(peak.get("area")),
                    "assignment": str(peak.get("assignment", "") or "").strip(),
                    "ref_wavenumber": _clean_float(peak.get("ref_wavenumber")),
                }
            )
        return peaks

    for index in range(1, 21):
        prefix = f"peak_{index}_"
        found_any = False
        wavenumber = _clean_float(output.get(f"{prefix}cm1"))
        height = _clean_float(output.get(f"{prefix}height"))
        area = _clean_float(output.get(f"{prefix}area"))
        width = _clean_float(output.get(f"{prefix}fwhm_cm1"))
        prominence = _clean_float(output.get(f"{prefix}prominence", output.get(f"{prefix}peak_prominence")))
        assignment = str(output.get(f"{prefix}assignment", "") or "").strip()
        ref_wavenumber = _clean_float(output.get(f"{prefix}ref_wavenumber", output.get(f"{prefix}ref_cm1")))
        if wavenumber is not None:
            found_any = True
        if height is not None:
            found_any = True
        if prominence is not None:
            found_any = True
        if area is not None:
            found_any = True
        if width is not None:
            found_any = True
        if assignment:
            found_any = True
        if ref_wavenumber is not None:
            found_any = True
        if not found_any:
            continue
        peaks.append(
            {
                "wavenumber": wavenumber,
                "height": height,
                "prominence": prominence,
                "fwhm_cm1": width,
                "area": area,
                "assignment": assignment,
                "ref_wavenumber": ref_wavenumber,
            }
        )

    if not peaks:
        centers = output.get("peak_centers")
        if isinstance(centers, list):
            for center in centers:
                peaks.append(
                    {
                        "wavenumber": _clean_float(center),
                        "height": None,
                        "prominence": None,
                        "fwhm_cm1": None,
                        "area": None,
                        "assignment": "",
                        "ref_wavenumber": None,
                    }
                )

    return peaks


def _ir_xc_calibration_status(output: dict[str, Any]) -> str | None:
    status = str(output.get("Xc_calibration_status") or "").strip()
    if status:
        return status

    method = str(output.get("Xc_method") or "").strip().lower()
    if method.endswith("_uncalibrated") or method == "band_ratio":
        return "uncalibrated_index"
    if output.get("Xc_pct") is None and not method:
        return "unavailable"
    return None


def _ir_band_support_metrics(output: dict[str, Any], validation: dict[str, Any] | None = None) -> dict[str, Any]:
    validation = dict(validation or {})
    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}

    raw_peaks = _ir_peak_records(output)
    peak_widths = [
        _clean_float(peak.get("fwhm_cm1"))
        for peak in raw_peaks
        if _clean_float(peak.get("fwhm_cm1")) is not None
    ]
    assigned_peak_count = sum(
        1
        for peak in raw_peaks
        if str(peak.get("assignment", "") or "").strip().lower() not in {"", "unknown"}
    )

    polymer_db = output.get("polymer_peaks_db")
    if not isinstance(polymer_db, dict):
        polymer_db = _extract_nested_mapping(config_snapshot, "polymer_peaks_db")
    polymer_name = str(output.get("polymer_name", output.get("polymer", "")) or "").strip()
    polymer_key = normalize_ir_polymer_name(polymer_name)
    characteristic_bands = polymer_db.get(polymer_key, []) if isinstance(polymer_db, dict) else []

    reference_band_records: list[dict[str, Any]] = []
    reference_bands_payload = validation.get("ir_reference_bands", {})
    if isinstance(reference_bands_payload, dict):
        payload_bands = reference_bands_payload.get("bands", [])
        if isinstance(payload_bands, list):
            for band in payload_bands:
                if not isinstance(band, dict):
                    continue
                ref_wn = _clean_float(band.get("wavenumber"))
                if ref_wn is None:
                    continue
                reference_band_records.append(
                    _non_empty_mapping(
                        [
                            ("ref_wavenumber", ref_wn),
                            ("assignment", str(band.get("assignment", "") or "").strip() or None),
                            ("intensity", str(band.get("intensity", "") or "").strip() or None),
                            ("crystallinity_sensitive", bool(band.get("crystallinity_sensitive", False))),
                        ]
                    )
                )

    if not reference_band_records and isinstance(characteristic_bands, list) and characteristic_bands:
        for band in characteristic_bands:
            if not isinstance(band, (list, tuple)) or not band:
                continue
            ref_wn = _clean_float(band[0])
            assignment = str(band[1] if len(band) > 1 else "",).strip()
            intensity = str(band[2] if len(band) > 2 else "",).strip()
            cryst = bool(band[3]) if len(band) > 3 else False
            if ref_wn is None:
                continue
            reference_band_records.append(
                _non_empty_mapping(
                    [
                        ("ref_wavenumber", ref_wn),
                        ("assignment", assignment or "unknown"),
                        ("intensity", intensity or None),
                        ("crystallinity_sensitive", cryst),
                    ]
                )
            )

    band_hit_count = 0
    band_missing_count = 0
    for band in reference_band_records:
        ref_wn = _clean_float(band.get("ref_wavenumber"))
        if ref_wn is None:
            continue
        matched = False
        for peak in raw_peaks:
            peak_wn = _clean_float(peak.get("wavenumber"))
            if peak_wn is None:
                continue
            if abs(peak_wn - ref_wn) <= 18.0:
                matched = True
                break
        if matched:
            band_hit_count += 1
        else:
            band_missing_count += 1

    peak_width_spread = _relative_spread(peak_widths) if len(peak_widths) >= 2 else None
    baseline_method = str(output.get("baseline_method", config_snapshot.get("baseline_method", "")) or "").strip().lower()
    normalization_method = str(output.get("normalization_method", config_snapshot.get("normalization_method", "")) or "").strip().lower()
    peak_distance = _clean_float(output.get("peak_distance", config_snapshot.get("peak_distance")))
    peak_fit_window = _clean_float(output.get("peak_fit_window_cm1", config_snapshot.get("peak_fit_window_cm1")))
    assignment_confidence = _clean_float(output.get("assignment_confidence", output.get("polymer_score")))
    polymer_score = _clean_float(output.get("polymer_score"))
    x_pct = _clean_float(output.get("Xc_pct"))
    x_method = str(output.get("Xc_method") or "").strip()
    x_calibration_status = _ir_xc_calibration_status(output)

    return {
        "peak_count": len(raw_peaks),
        "assigned_peak_count": assigned_peak_count,
        "peak_width_spread": peak_width_spread,
        "baseline_method": baseline_method,
        "normalization_method": normalization_method,
        "peak_distance": peak_distance,
        "peak_fit_window_cm1": peak_fit_window,
        "assignment_confidence": assignment_confidence,
        "polymer_score": polymer_score,
        "Xc_pct": x_pct,
        "Xc_method": x_method,
        "Xc_calibration_status": x_calibration_status,
        "reference_band_count": len(reference_band_records),
        "reference_band_hit_count": band_hit_count,
        "reference_band_missing_count": band_missing_count,
        "characteristic_band_support_ok": bool(reference_band_records and band_hit_count >= 3 and band_missing_count == 0),
    }


def _ir_symptom_bridge_lines(symptom: dict[str, Any] | None, output: dict[str, Any] | None = None) -> list[str]:
    if not isinstance(symptom, dict):
        return []

    output = dict(output or {})
    name = str(symptom.get("name", "") or "").strip().lower()
    targets = symptom.get("target_params", [])
    if not isinstance(targets, list):
        targets = []
    target_text = " / ".join(str(item).strip() for item in targets if str(item).strip())

    if name == "key_band_support_insufficient":
        lead = "key_band_support_insufficient -> keep the polymer call tentative until reference bands are recovered"
    elif name == "assignment_without_characteristic_bands":
        lead = "assignment_without_characteristic_bands -> verify characteristic bands before accepting the assignment"
    elif name == "baseline_sensitive_assignment":
        lead = "baseline_sensitive_assignment -> stabilize baseline_method / normalization_method before another round"
    elif name == "weak_peak_only_support":
        lead = "weak_peak_only_support -> peak count alone is not enough; wait for band support"
    elif name == "overcrowded_band_separation_unstable":
        lead = "overcrowded_band_separation_unstable -> narrow peak_fit_window_cm1 and separate crowded bands first"
    elif name == "baseline_drift_low_wn":
        lead = "baseline_drift_low_wn -> stabilize baseline_method before changing peak thresholds"
    elif name == "baseline_drift_high_wn":
        lead = "baseline_drift_high_wn -> stabilize normalization_method before changing peak thresholds"
    elif name == "baseline_drift_low_t":
        lead = "baseline_drift_low_t -> stabilize baseline_type before changing event thresholds"
    elif name == "baseline_drift_high_t":
        lead = "baseline_drift_high_t -> stabilize baseline_type before changing event thresholds"
    elif name == "melting_peak_shift":
        lead = "melting_peak_shift -> re-center Tm/Tc windows before changing peak_function"
    elif name == "tg_step_missing":
        lead = "tg_step_missing -> re-check Tg support and DCp before trusting Tg"
    elif name == "cold_crystallization_overlap":
        lead = "cold_crystallization_overlap -> separate Tcc from the melting window first"
    elif name == "event_window_too_narrow":
        lead = "event_window_too_narrow -> widen the event window before re-fitting"
    elif name == "event_window_too_wide":
        lead = "event_window_too_wide -> narrow the event window before trusting the fit"
    elif name == "exo_up_down_confusion":
        lead = "exo_up_down_confusion -> verify exo_up and signed enthalpy convention"
    elif name == "multi_event_underfit":
        lead = "multi_event_underfit -> allow multiple thermal events or components"
    elif name == "segment_split_issue":
        lead = "segment_split_issue -> check whether the scan was split at the wrong point"
    elif name == "noise_dominant":
        lead = "noise_dominant -> stabilize preprocessing and smoothing before another attempt"
    elif name == "crystallinity_index_without_band_support":
        lead = "crystallinity_index_without_band_support -> keep Xc tentative until band support is stable"
    elif name == "ir_xc_uncalibrated":
        lead = "ir_xc_uncalibrated -> treat IR Xc as a diagnostic band index until a calibration curve is available"
    else:
        summary = str(symptom.get("summary", "") or "").strip()
        if target_text:
            lead = f"{name} -> {target_text}"
        elif summary:
            lead = f"{name} -> {summary}"
        else:
            return []

    expected = symptom.get("expected_evidence_change", [])
    if not isinstance(expected, list):
        expected = []
    lines = [lead]
    lines.extend(f"expected evidence change: {str(item).strip()}" for item in expected if str(item).strip())
    quality_flag = str(output.get("quality_flag", "") or "").strip()
    validation_summary = str(output.get("validation_summary", "") or "").strip()
    if quality_flag:
        lines.append(f"current quality_flag: {quality_flag}")
    if validation_summary and validation_summary != "All checks passed":
        lines.append(f"current validation_summary: {validation_summary}")
    return lines


def _ir_symptoms_from_constraints(
    constraints: list[dict[str, Any]],
    output: dict[str, Any],
    residual: dict[str, Any],
    validation: dict[str, Any],
) -> list[dict[str, Any]]:
    symptom_list: list[dict[str, Any]] = []
    triggered = {
        str(item.get("name", "") or "").strip(): item
        for item in constraints
        if isinstance(item, dict) and item.get("triggered")
    }

    support = _ir_band_support_metrics(output, validation)
    peak_count = support.get("peak_count")
    assigned_peak_count = support.get("assigned_peak_count")
    reference_band_count = support.get("reference_band_count")
    reference_band_hit_count = support.get("reference_band_hit_count")
    reference_band_missing_count = support.get("reference_band_missing_count")
    peak_width_spread = support.get("peak_width_spread")
    baseline_method = str(support.get("baseline_method", "") or "").strip().lower()
    normalization_method = str(support.get("normalization_method", "") or "").strip().lower()
    peak_distance = _clean_float(support.get("peak_distance"))
    peak_fit_window = _clean_float(support.get("peak_fit_window_cm1"))
    assignment_confidence = _clean_float(support.get("assignment_confidence"))
    residual_type = str(output.get("residual_type", "") or "").strip()

    def add(symptom: dict[str, Any] | None) -> None:
        if isinstance(symptom, dict) and symptom.get("name"):
            symptom_list.append(symptom)

    if "key_band_support_insufficient" in triggered:
        add(
            {
                "name": "key_band_support_insufficient",
                "severity": "warning",
                "source": "IR",
                "summary": "Reference-band coverage is too weak to support a stable polymer call.",
                "target_params": ["assignment_tolerance_cm1", "peak_fit_window_cm1"],
                "observed": {
                    "reference_band_count": reference_band_count,
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                },
                "expected_evidence_change": [
                    "reference_band_hit_count should rise",
                    "reference_band_missing_count should drop to 0",
                ],
            }
        )
    if "assignment_without_characteristic_bands" in triggered:
        add(
            {
                "name": "assignment_without_characteristic_bands",
                "severity": "warning",
                "source": "IR",
                "summary": "Assignment exists, but characteristic bands are not yet consistently matched.",
                "target_params": ["assignment_tolerance_cm1", "peak_fit_window_cm1"],
                "observed": {
                    "assignment_confidence": assignment_confidence,
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                },
                "expected_evidence_change": [
                    "assignment_confidence should align with key-band coverage",
                    "paper_conclusion_ready should remain false until the chain is stable",
                ],
            }
        )
    if "baseline_sensitive_assignment" in triggered:
        add(
            {
                "name": "baseline_sensitive_assignment",
                "severity": "warning",
                "source": "IR",
                "summary": "Polymer assignment depends too much on baseline or normalization settings.",
                "target_params": ["baseline_method", "normalization_method", "smooth_window"],
                "observed": {
                    "baseline_method": baseline_method or None,
                    "normalization_method": normalization_method or None,
                    "peak_width_spread": peak_width_spread,
                },
                "expected_evidence_change": [
                    "baseline_method should settle on a stable choice",
                    "peak widths should become less spread out",
                ],
            }
        )
    if "weak_peak_only_support" in triggered:
        add(
            {
                "name": "weak_peak_only_support",
                "severity": "warning",
                "source": "IR",
                "summary": "Peak detection alone is not enough to support a confident IR conclusion.",
                "target_params": ["peak_height_min", "peak_prominence_min", "peak_distance"],
                "observed": {
                    "peak_count": peak_count,
                    "assigned_peak_count": assigned_peak_count,
                    "reference_band_hit_count": reference_band_hit_count,
                },
                "expected_evidence_change": [
                    "reference_band_hit_count should reach a stable minimum",
                    "assigned_peak_count should rise with real characteristic bands",
                ],
            }
        )
    if "overcrowded_band_separation_unstable" in triggered:
        add(
            {
                "name": "overcrowded_band_separation_unstable",
                "severity": "warning",
                "source": "IR",
                "summary": "Crowded bands or wide fit windows make the local band separation unstable.",
                "target_params": ["peak_distance", "peak_fit_window_cm1"],
                "observed": {
                    "peak_count": peak_count,
                    "peak_distance": peak_distance,
                    "peak_fit_window_cm1": peak_fit_window,
                    "peak_width_spread": peak_width_spread,
                },
                "expected_evidence_change": [
                    "peak distance should better separate nearby bands",
                    "peak_fit_window_cm1 should narrow around the active peak",
                ],
            }
        )
    if "polymer_score_without_assignment_support" in triggered:
        add(
            {
                "name": "polymer_score_without_assignment_support",
                "severity": "warning",
                "source": "IR",
                "summary": "Polymer score is present but not backed by enough assigned peaks or key bands.",
                "target_params": ["assignment_confidence", "peak_fit_window_cm1"],
                "observed": {
                    "polymer_score": _clean_float(support.get("polymer_score")),
                    "reference_band_hit_count": reference_band_hit_count,
                    "assigned_peak_count": assigned_peak_count,
                },
                "expected_evidence_change": [
                    "reference_band_hit_count should reach 3 or more",
                    "assigned_peak_count should rise to a stable band family",
                ],
            }
        )
    if "crystallinity_index_without_band_support" in triggered:
        add(
            {
                "name": "crystallinity_index_without_band_support",
                "severity": "warning",
                "source": "IR",
                "summary": "Crystallinity index is being reported without enough supporting bands.",
                "target_params": ["crystallinity_band", "crystallinity_ref_band"],
                "observed": {
                    "Xc_pct": _clean_float(support.get("Xc_pct")),
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                },
                "expected_evidence_change": [
                    "reference_band_missing_count should drop to zero",
                    "Xc should only be promoted when the band support chain is stable",
                ],
            }
        )
    if "ir_xc_uncalibrated" in triggered:
        add(
            {
                "name": "ir_xc_uncalibrated",
                "severity": "warning",
                "source": "IR",
                "summary": "IR crystallinity is an uncalibrated band index and should remain diagnostic.",
                "target_params": ["crystallinity_band", "crystallinity_ref_band"],
                "observed": {
                    "Xc_pct": _clean_float(support.get("Xc_pct")),
                    "Xc_method": support.get("Xc_method"),
                    "Xc_calibration_status": support.get("Xc_calibration_status"),
                },
                "expected_evidence_change": [
                    "Xc_calibration_status should become calibrated before entering paper-ready conclusions",
                    "calibrated reference bands or an external calibration curve should be recorded",
                ],
            }
        )

    if "baseline_drift_low_wn" in triggered:
        add(
            {
                "name": "baseline_drift_low_wn",
                "severity": "warning",
                "source": "IR",
                "summary": "The low-wavenumber edge is drifting and should be stabilized first.",
                "target_params": ["baseline_method", "smooth_window"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "low-wavenumber residuals should weaken",
                    "baseline method should settle before peak thresholds move again",
                ],
            }
        )
    if "baseline_drift_high_wn" in triggered:
        add(
            {
                "name": "baseline_drift_high_wn",
                "severity": "warning",
                "source": "IR",
                "summary": "The high-wavenumber edge is drifting and should be stabilized first.",
                "target_params": ["baseline_method", "normalization_method"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "high-wavenumber residuals should weaken",
                    "normalization should stop steering the conclusion",
                ],
            }
        )
    if "key_band_mismatch" in triggered:
        add(
            {
                "name": "key_band_mismatch",
                "severity": "warning",
                "source": "IR",
                "summary": "Characteristic bands are locally mismatched against the observed spectrum.",
                "target_params": ["peak_fit_window_cm1", "peak_prominence_min", "peak_height_min"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "key-band hits should rise",
                    "assignment confidence should better match band support",
                ],
            }
        )
    if "crowded_band_underfit" in triggered:
        add(
            {
                "name": "crowded_band_underfit",
                "severity": "warning",
                "source": "IR",
                "summary": "Crowded bands are not being separated cleanly enough.",
                "target_params": ["peak_distance", "lineshape"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "peak families should separate more cleanly",
                    "peak widths should become easier to compare",
                ],
            }
        )
    if "over_smoothed_weak_bands" in triggered:
        add(
            {
                "name": "over_smoothed_weak_bands",
                "severity": "warning",
                "source": "IR",
                "summary": "Weak bands are likely being smoothed away.",
                "target_params": ["smooth_window", "peak_height_min"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "weak bands should reappear",
                    "peak count should stay useful without over-promoting noise",
                ],
            }
        )
    if "normalization_bias" in triggered:
        add(
            {
                "name": "normalization_bias",
                "severity": "warning",
                "source": "IR",
                "summary": "Normalization is biasing the relative band balance.",
                "target_params": ["normalization_method", "baseline_method"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "band balance should become more stable",
                    "assignment confidence should stop jumping with scaling changes",
                ],
            }
        )
    if "noise_dominant" in triggered:
        add(
            {
                "name": "noise_dominant",
                "severity": "warning",
                "source": "IR",
                "summary": "The residual is dominated by noise rather than a localized mismatch.",
                "target_params": ["smooth_window"],
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": [
                    "sign flips should drop",
                    "weak-band recovery should become more stable",
                ],
            }
        )

    return symptom_list


def _waxs_structure_metrics(
    output: dict[str, Any],
    *,
    peak_metrics: dict[str, Any] | None = None,
    config_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    peak_metrics = peak_metrics if isinstance(peak_metrics, dict) else _waxs_peak_metrics(output)
    config_snapshot = config_snapshot if isinstance(config_snapshot, dict) else {}

    peak_count = _clean_float(peak_metrics.get("peak_count"))
    peak_width_spread = _clean_float(peak_metrics.get("peak_width_spread"))
    peak_area_ratio = _clean_float(peak_metrics.get("peak_area_ratio"))
    width_values = [value for value in peak_metrics.get("peak_widths", []) if _clean_float(value) is not None]
    mean_peak_width = _mean_finite([_clean_float(value) for value in width_values])

    x_pct = _clean_float(output.get("Xc_pct"))
    scherrer = _clean_float(output.get("D_Scherrer_nm"))
    scherrer_uncertainty = _clean_float(output.get("D_uncertainty_nm"))
    wh_size = _clean_float(output.get("D_WH_nm"))
    wh_size_uncertainty = _clean_float(output.get("D_WH_uncertainty_nm"))
    wh_strain = _clean_float(output.get("epsilon_WH_pct"))
    wh_strain_uncertainty = _clean_float(output.get("epsilon_WH_uncertainty_pct"))
    wh_fit_r_squared = _clean_float(output.get("WH_fit_r_squared"))
    size_reliability_status = str(output.get("size_reliability_status", "") or "").strip() or None
    instrument_broadening_model = str(output.get("instrument_broadening_model", "") or "").strip() or None
    scherrer_peak_records = output.get("scherrer_peak_records")
    if not isinstance(scherrer_peak_records, list):
        scherrer_peak_records = []
    offset = _clean_float(output.get("two_theta_offset"))
    if offset is None:
        offset = _clean_float(config_snapshot.get("two_theta_offset"))

    crystal_system = str(output.get("crystal_system", "") or "").strip()
    unit_cell_params = output.get("unit_cell_params", config_snapshot.get("unit_cell_params", {}))
    unit_cell_present = bool(unit_cell_params)
    crystallinity_method = str(
        output.get("crystallinity_method", output.get("Xc_method", config_snapshot.get("crystallinity_method", "")))
        or ""
    ).strip()

    peak_support_ok = peak_count is not None and peak_count >= 2
    offset_ok = offset is None or abs(offset) <= 0.05
    width_ok = peak_width_spread is None or peak_width_spread <= 0.45
    offset_score = _inverse_ratio_score(abs(offset), 0.08) if offset is not None else 1.0
    structure_support_score = _clamp_unit(
        0.40 * (1.0 if peak_support_ok else 0.28)
        + 0.20 * (offset_score if offset_score is not None else 0.0)
        + 0.20 * (1.0 if width_ok else 0.42)
        + 0.20 * (1.0 if unit_cell_present or crystal_system else 0.45),
        default=0.0,
    )
    fit_only_pass = bool(x_pct is not None and x_pct > 0)
    physical_support_pass = bool(
        peak_support_ok
        and offset_ok
        and width_ok
        and (scherrer is None or scherrer > 0)
    )
    paper_ready_candidate = bool(
        fit_only_pass
        and physical_support_pass
        and structure_support_score >= 0.72
        and peak_area_ratio is not None
        and peak_area_ratio <= 6.0
    )

    return _non_empty_mapping(
        [
            ("peak_count_detected", peak_count),
            ("peak_count_fitted", peak_count),
            ("dominant_peak_positions", peak_metrics.get("peak_positions") if peak_metrics.get("peak_positions") else None),
            ("mean_peak_width_deg", mean_peak_width),
            ("peak_width_spread", peak_width_spread),
            ("peak_area_ratio", peak_area_ratio),
            ("crystallinity_method", crystallinity_method or None),
            ("crystallinity_estimate_pct", x_pct),
            ("crystal_system", crystal_system or None),
            ("unit_cell_params_present", unit_cell_present or None),
            ("scherrer_size_nm", scherrer),
            ("scherrer_size_uncertainty_nm", scherrer_uncertainty),
            ("williamson_hall_size_nm", wh_size),
            ("williamson_hall_size_uncertainty_nm", wh_size_uncertainty),
            ("williamson_hall_strain_pct", wh_strain),
            ("williamson_hall_strain_uncertainty_pct", wh_strain_uncertainty),
            ("WH_fit_r_squared", wh_fit_r_squared),
            ("size_reliability_status", size_reliability_status),
            ("instrument_broadening_model", instrument_broadening_model),
            ("scherrer_peak_record_count", len(scherrer_peak_records) if scherrer_peak_records else None),
            ("two_theta_offset", offset),
            ("structure_support_score", round(structure_support_score, 3)),
            ("fit_only_pass", fit_only_pass),
            ("physical_support_pass", physical_support_pass),
            ("paper_ready_candidate", paper_ready_candidate),
        ]
    )


def _waxs_symptoms_from_constraints(
    constraints: list[dict[str, Any]],
    output: dict[str, Any],
    validation: dict[str, Any],
    residual: dict[str, Any],
) -> list[dict[str, Any]]:
    symptom_specs: dict[str, tuple[str, list[str]]] = {
        "temperature_axis_missing": (
            "The temperature axis is missing or incomplete for this WAXS sequence.",
            ["condition_confidence", "temperature_missing_count"],
        ),
        "temperature_axis_low_confidence": (
            "The temperature axis is present but still low-confidence.",
            ["condition_confidence", "condition_continuity_score"],
        ),
        "temperature_sequence_nonmonotonic": (
            "The temperature sequence is not strictly monotonic.",
            ["temperature_values", "sequence_order_source"],
        ),
        "temperature_duplicate_frames": (
            "Duplicate temperature frames weaken sequence continuity.",
            ["temperature_duplicate_count", "temperature_values"],
        ),
        "peak_visibility": (
            "No resolved sharp peak support is visible yet.",
            ["peak_distance", "max_peaks"],
        ),
        "peak_count_insufficient": (
            "Too few resolved peaks to support stable phase or size claims.",
            ["peak_distance", "max_peaks"],
        ),
        "peak_family_unstable": (
            "Peak spacing or peak widths drift too much for a stable peak family.",
            ["peak_distance", "peak_function"],
        ),
        "peak_family_identity_swap": (
            "Peak identity appears to swap between frames instead of staying continuous.",
            ["peak_family_assignment_method", "peak_distance"],
        ),
        "peak_family_track_fragmented": (
            "Peak family tracks are fragmented and need continuity recovery.",
            ["peak_family_continuity_score", "peak_family_assignment_method"],
        ),
        "peak_family_missing_too_many_frames": (
            "Too many frames are missing from the peak family tracks.",
            ["peak_family_missing_frame_count", "peak_family_missing_ratio"],
        ),
        "peak_position_drift_unphysical": (
            "Peak family position drift is too large to be treated as a stable family.",
            ["peak_position_drift_per_family", "peak_family_continuity_score"],
        ),
        "peak_width_trend_unstable": (
            "Peak widths drift too much to keep the family assignment stable.",
            ["peak_width_drift_per_family", "peak_family_continuity_score"],
        ),
        "phase_transition_without_peak_family_support": (
            "A transition was detected without enough peak-family support.",
            ["peak_family_count", "peak_family_continuity_score"],
        ),
        "crystallinity_trend_without_peak_support": (
            "Xc trend is being interpreted without enough peak support behind it.",
            ["Xc_peak_support_ratio", "Xc_trend_support_score"],
        ),
        "crystallinity_jump_single_frame": (
            "Xc changes too sharply in a single frame to be treated as a stable trend.",
            ["crystallinity_jump_single_frame_count", "Xc_values"],
        ),
        "crystallinity_background_driven": (
            "Xc appears too sensitive to background partitioning or missing peak support.",
            ["Xc_background_sensitivity", "frame_low_conf_count"],
        ),
        "crystallinity_trend_conflicts_with_peak_area": (
            "Xc trend conflicts with the peak-area trend and needs review.",
            ["Xc_values", "peak_area_sum"],
        ),
        "crystallinity_outside_physical_range": (
            "Xc values go outside the physical range and should not be promoted.",
            ["Xc_values"],
        ),
        "melting_trend_without_peak_disappearance": (
            "Melting-like Xc drop does not line up with peak disappearance.",
            ["peak_family_tracks", "peak_disappearance_temperatures"],
        ),
        "cold_crystallization_without_new_peak_support": (
            "Cold-crystallisation-like Xc rise does not line up with new peak birth.",
            ["new_peak_birth_temperatures", "Xc_transition_candidates"],
        ),
        "amorphous_partition_unstable": (
            "Crystallinity still depends too much on the amorphous partition.",
            ["background_method", "amorphous_subtraction", "amorphous_n_peaks"],
        ),
        "peak_width_nonphysical": (
            "Peak widths look too broad or degenerate for a paper-grade WAXS fit.",
            ["peak_function", "smooth_window"],
        ),
        "offset_sensitive_solution": (
            "2theta offset is still steering the solution and should be checked first.",
            ["two_theta_offset"],
        ),
        "crystallinity_without_peak_support": (
            "Xc is being reported without enough peak support behind it.",
            ["peak_distance", "max_peaks", "amorphous_subtraction"],
        ),
        "size_without_multi_peak_support": (
            "Scherrer size needs at least two resolved peaks to stay trustworthy.",
            ["peak_distance", "max_peaks"],
        ),
        "scherrer_trend_without_multi_peak_support": (
            "Scherrer trend is being interpreted without repeated multi-peak support.",
            ["D_support_peak_count", "D_support_family_count"],
        ),
        "scherrer_jump_single_frame": (
            "Scherrer size changes too abruptly in a single frame.",
            ["D_jump_single_frame_count", "D_jump_single_frame_indices"],
        ),
        "scherrer_dominated_by_peak_width_noise": (
            "Scherrer trend is being driven more by peak-width noise than by a stable size change.",
            ["D_slope_distribution", "FWHM_values_by_family"],
        ),
        "scherrer_instrument_broadening_unresolved": (
            "Instrument broadening is not clearly modeled for the Scherrer result.",
            ["instrument_broadening_present", "caglioti_U", "caglioti_V", "caglioti_W"],
        ),
        "scherrer_conflicts_with_peak_family_tracking": (
            "Scherrer trend does not agree with the peak-family tracking story.",
            ["peak_family_continuity_score", "FWHM_values_by_family"],
        ),
        "scherrer_unphysical_temperature_trend": (
            "Scherrer trend is too oscillatory to be treated as physically stable.",
            ["D_values_nm", "D_trend_monotonicity"],
        ),
        "fit_quality_vs_phys": (
            "Fit score and physical support still need to agree before trust rises.",
            ["peak_function", "amorphous_subtraction"],
        ),
    }

    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}

    symptom_list: list[dict[str, Any]] = []
    triggered = {
        str(item.get("name", "") or "").strip(): item
        for item in constraints
        if isinstance(item, dict) and item.get("triggered")
    }

    for name, item in triggered.items():
        spec = symptom_specs.get(name)
        if not spec:
            continue
        summary, target_params = spec
        observed = item.get("observed")

        if name == "offset_sensitive_solution" and _clean_float(observed) is None:
            observed = _clean_float(output.get("two_theta_offset", config_snapshot.get("two_theta_offset")))
        if name == "amorphous_partition_unstable" and observed is None:
            observed = {
                "Xc_method": output.get("Xc_method"),
                "amorphous_subtraction": output.get("amorphous_subtraction", config_snapshot.get("amorphous_subtraction")),
                "amorphous_n_peaks": output.get("amorphous_n_peaks", config_snapshot.get("amorphous_n_peaks")),
            }

        symptom_list.append(
            {
                "name": name,
                "summary": summary,
                "severity": str(item.get("severity", "") or "").strip() or "WARN",
                "source": "WAXS",
                "target_params": target_params,
                "observed": observed,
            }
        )

    waxs_residual_symptom_map: dict[str, tuple[str, list[str], list[str]]] = {
        "peak_position_bias": (
            "Peak positions are shifted relative to the observed profile.",
            ["two_theta_offset", "peak_function", "peak_distance"],
            ["peak positions should converge", "residual_type should move toward random"],
        ),
        "peak_count_underfit": (
            "The current peak family misses supported structure.",
            ["peak_distance", "max_peaks"],
            ["peak count should rise", "supporting peak regions should narrow"],
        ),
        "peak_count_overfit": (
            "The current peak family is too crowded for the observed structure.",
            ["max_peaks", "peak_distance"],
            ["peak count should fall", "peak family should simplify"],
        ),
        "amorphous_background_bias": (
            "Crystallinity is still too sensitive to halo/background partitioning.",
            ["background_method", "amorphous_subtraction", "amorphous_n_peaks"],
            ["background-related residuals should weaken", "crystallinity should stop depending on halo shape"],
        ),
        "peak_width_mismatch": (
            "Peak shoulders and cores disagree, suggesting a shape mismatch.",
            ["peak_function", "smooth_window"],
            ["shoulders and peak core should agree better", "peak widths should stabilize"],
        ),
        "low_angle_background_drift": (
            "Low-angle background is still drifting near the beamstop region.",
            ["background_method", "amorphous_subtraction", "two_theta_offset"],
            ["low-angle residuals should weaken", "max_residual_region should move away from beamstop"],
        ),
    }

    residual_type = str(residual.get("residual_type", "") or "").strip().lower()
    if residual_type in waxs_residual_symptom_map:
        summary, target_params, expected_change = waxs_residual_symptom_map[residual_type]
        symptom_list.append(
            {
                "name": residual_type,
                "summary": summary,
                "severity": "WARN",
                "source": "WAXS_residual",
                "target_params": target_params,
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": expected_change,
            }
        )

    return symptom_list


def _build_saxs_stability_evidence(
    output: dict[str, Any],
    *,
    symptoms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    symptom_names = {
        str(item.get("name", "")).strip()
        for item in (symptoms or [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }

    quality_score = _clean_float(output.get("quality_score"))
    l_confidence = _clean_float(output.get("L_confidence"))
    lc_confidence = _clean_float(output.get("lc_confidence"))
    q_peak_snr = _clean_float(output.get("q_peak_snr"))
    q_peak_diff_pct = _clean_float(output.get("q_peak_diff_pct"))
    if q_peak_diff_pct is None:
        q_peak_diff_pct = _clean_float(output.get("pyfai_q_peak_diff_pct"))

    parameter_terms = [
        _clamp_unit(quality_score, default=0.0) if quality_score is not None else None,
        _clamp_unit(l_confidence, default=0.0) if l_confidence is not None else None,
        _clamp_unit(lc_confidence, default=0.0) if lc_confidence is not None else None,
        _clamp_unit(q_peak_snr / 5.0, default=0.0) if q_peak_snr is not None else None,
    ]
    parameter_stability_score = _mean_finite(parameter_terms)
    if parameter_stability_score is None:
        parameter_stability_score = 0.5
    if output.get("beam_stop_contaminated"):
        parameter_stability_score -= 0.08
    if output.get("mask_truncated"):
        parameter_stability_score -= 0.04
    if output.get("Q_star_valid") is False:
        parameter_stability_score -= 0.05
    if "beamstop_or_low_q_contamination" in symptom_names:
        parameter_stability_score -= 0.04
    if "low_q_void_dominant" in symptom_names:
        parameter_stability_score -= 0.03
    parameter_stability_score = _clamp_unit(parameter_stability_score, default=0.0)

    l_spread = _relative_spread(
        [
            _clean_float(output.get("L_bragg")),
            _clean_float(output.get("L_corr_peak", output.get("L_corr"))),
            _clean_float(output.get("L_nm", output.get("L_best"))),
        ]
    )
    lc_spread = _relative_spread(
        [
            _clean_float(output.get("lc_tangent_nm")),
            _clean_float(output.get("lc_gamma_min_nm")),
            _clean_float(output.get("lc_idf_nm")),
        ]
    )
    phi_spread = _relative_spread(
        [
            _clean_float(output.get("phi_c")),
            _clean_float(output.get("phi_c_invariant")),
        ]
    )
    agreement_terms = [
        _inverse_ratio_score(l_spread, 0.10),
        _inverse_ratio_score(lc_spread, 0.15),
        _inverse_ratio_score(phi_spread, 0.12),
        _inverse_ratio_score(abs(q_peak_diff_pct) if q_peak_diff_pct is not None else None, 5.0),
    ]
    method_agreement_score = _mean_finite(agreement_terms)
    if method_agreement_score is None:
        method_agreement_score = 0.5
    if "multi_method_disagreement" in symptom_names:
        method_agreement_score -= 0.08
    if "gamma_tangent_unstable" in symptom_names:
        method_agreement_score -= 0.05
    method_agreement_score = _clamp_unit(method_agreement_score, default=0.0)

    batch_frames_raw = output.get("batch_frames")
    try:
        batch_frames = int(batch_frames_raw) if batch_frames_raw is not None else 0
    except (TypeError, ValueError):
        batch_frames = 0
    condition_label = str(output.get("condition_label", "") or "").strip().lower()
    condition_continuity_score = _clean_float(output.get("condition_continuity_score"))
    condition_confidence = _clean_float(output.get("condition_confidence"))
    missing_frames_raw = output.get("condition_missing_frames")
    try:
        missing_frames = int(missing_frames_raw) if missing_frames_raw is not None else 0
    except (TypeError, ValueError):
        missing_frames = 0
    coverage_score = None
    if batch_frames > 0:
        coverage_score = _clamp_unit(1.0 - (missing_frames / max(batch_frames, 1)), default=0.0)
    batch_terms = [condition_continuity_score, condition_confidence, coverage_score]
    batch_continuity_score = _mean_finite(batch_terms)
    if batch_continuity_score is None:
        batch_continuity_score = 1.0 if batch_frames <= 1 else 0.5
    if "condition_axis_missing" in symptom_names:
        batch_continuity_score = min(batch_continuity_score, 0.15)
    elif "condition_axis_unstable" in symptom_names:
        batch_continuity_score = min(batch_continuity_score, 0.55)
    if "batch_mixed_samples" in symptom_names:
        batch_continuity_score -= 0.12
    if "temperature_calibration_fallback_active" in symptom_names:
        parameter_stability_score -= 0.03
        batch_continuity_score -= 0.06
    if "diagnostic_lc_frames_present" in symptom_names:
        parameter_stability_score -= 0.06
        method_agreement_score -= 0.05
    if "temperature_sequence_near_melting_window" in symptom_names:
        method_agreement_score -= 0.03
    if "lc_unreliable_without_melting_proof" in symptom_names:
        method_agreement_score -= 0.08
        batch_continuity_score -= 0.03
    if "batch_summary_conflicts_with_frame_evidence" in symptom_names:
        method_agreement_score -= 0.08
        batch_continuity_score -= 0.08
    if "thickness_chain_unreliable" in symptom_names:
        method_agreement_score -= 0.10
        batch_continuity_score -= 0.04
    if "strain_void_lamellar_conflict" in symptom_names:
        method_agreement_score -= 0.08
    if "lamellar_anchor_lost_under_strain" in symptom_names:
        method_agreement_score -= 0.10
        batch_continuity_score -= 0.03
    if "qstar_rel_without_lamellar_support" in symptom_names:
        method_agreement_score -= 0.06
    if "orientation_shift_breaks_lamellar_comparison" in symptom_names:
        method_agreement_score -= 0.08
    if condition_label == "strain":
        strain_status = str(output.get("strain_reliability_status", "") or "").strip().lower()
        phase_ambiguous_frame_count = _safe_int(output.get("phase_ambiguous_frame_count"), default=0)
        frame_low_conf_count = _safe_int(output.get("frame_low_conf_count"), default=0)
        void_dominant_frame_count = _safe_int(output.get("void_dominant_frame_count"), default=0)
        effective_param_ratio = _clean_float(output.get("effective_param_ratio"))
        if strain_status == "diagnostic_only":
            parameter_stability_score -= 0.12
            batch_continuity_score -= 0.05
        elif strain_status == "low_confidence":
            parameter_stability_score -= 0.06
        if phase_ambiguous_frame_count > 0:
            method_agreement_score -= 0.06
        if void_dominant_frame_count > 0:
            method_agreement_score -= 0.05
        if frame_low_conf_count > 0:
            batch_continuity_score -= 0.04
        if effective_param_ratio is not None and effective_param_ratio < 0.55:
            batch_continuity_score -= 0.05
    batch_continuity_score = _clamp_unit(batch_continuity_score, default=0.0)

    stability_score = _clamp_unit(
        0.45 * parameter_stability_score
        + 0.35 * method_agreement_score
        + 0.20 * batch_continuity_score,
        default=0.0,
    )

    flags: list[str] = []
    if parameter_stability_score < 0.55:
        flags.append("parameter_stability_low")
    if method_agreement_score < 0.60:
        flags.append("method_agreement_low")
    if batch_continuity_score < 0.65:
        flags.append("batch_continuity_low")
    if stability_score < 0.60:
        flags.append("stability_low")
    if condition_label == "strain":
        strain_status = str(output.get("strain_reliability_status", "") or "").strip().lower()
        if strain_status == "low_confidence":
            flags.append("strain_reliability_low")
        elif strain_status == "diagnostic_only":
            flags.append("strain_reliability_diagnostic")
        if _safe_int(output.get("phase_ambiguous_frame_count"), default=0) > 0:
            flags.append("phase_ambiguous")
        if _safe_int(output.get("void_dominant_frame_count"), default=0) > 0:
            flags.append("void_dominant")

    return _non_empty_mapping(
        [
            ("stability_score", round(stability_score, 3)),
            ("parameter_stability_score", round(parameter_stability_score, 3)),
            ("method_agreement_score", round(method_agreement_score, 3)),
            ("batch_continuity_score", round(batch_continuity_score, 3)),
            ("stability_flags", flags),
            ("l_method_relative_spread", round(float(l_spread), 4) if l_spread is not None else None),
            ("lc_method_relative_spread", round(float(lc_spread), 4) if lc_spread is not None else None),
            ("phi_method_relative_spread", round(float(phi_spread), 4) if phi_spread is not None else None),
            ("condition_continuity_score", condition_continuity_score),
            ("condition_frame_coverage", round(float(coverage_score), 3) if coverage_score is not None else None),
            ("strain_reliability_status", str(output.get("strain_reliability_status", "") or "").strip() or None),
            ("strain_reliability_reason", str(output.get("strain_reliability_reason", "") or "").strip() or None),
            ("phase_ambiguous_frame_count", _safe_int(output.get("phase_ambiguous_frame_count"), default=0) if output.get("phase_ambiguous_frame_count") is not None else None),
            ("frame_low_conf_count", _safe_int(output.get("frame_low_conf_count"), default=0) if output.get("frame_low_conf_count") is not None else None),
            ("void_dominant_frame_count", _safe_int(output.get("void_dominant_frame_count"), default=0) if output.get("void_dominant_frame_count") is not None else None),
            ("effective_param_ratio", _clean_float(output.get("effective_param_ratio"))),
        ]
    )


def symptom_action_hints(
    technique: str,
    residual_type: str,
    output_parameters: dict[str, Any] | None = None,
) -> list[str]:
    technique_key = str(technique or "").upper()
    residual_key = str(residual_type or "").strip().lower()
    output = dict(output_parameters or {})

    mapping: dict[str, dict[str, tuple[list[str], list[str]]]] = {
        "WAXS": {
            "peak_position_bias": (
                ["two_theta_offset", "peak_function", "peak_distance"],
                ["peak positions should converge", "residual_type should move toward random"],
            ),
            "peak_count_underfit": (
                ["peak_distance", "max_peaks"],
                ["peak count should rise", "supporting peak regions should narrow"],
            ),
            "peak_count_overfit": (
                ["max_peaks", "peak_distance"],
                ["peak count should fall", "peak family should simplify"],
            ),
            "amorphous_background_bias": (
                ["background_method", "amorphous_subtraction", "amorphous_n_peaks"],
                ["background-related residuals should weaken", "crystallinity should stop depending on halo shape"],
            ),
            "peak_width_mismatch": (
                ["peak_function", "smooth_window"],
                ["shoulders and peak core should agree better", "peak widths should stabilize"],
            ),
            "low_angle_background_drift": (
                ["background_method", "amorphous_subtraction", "two_theta_offset"],
                ["low-angle residuals should weaken", "max_residual_region should move away from beamstop"],
            ),
            "peak_mismatch": (
                ["peak_function", "peak_distance", "two_theta_offset"],
                ["residual_type should move toward random", "max_residual_region should shrink"],
            ),
            "background_drift": (
                ["background_method", "amorphous_subtraction", "smooth_window"],
                ["background-related residuals should weaken", "summary should lose drift wording"],
            ),
            "noise": (
                ["smooth_window", "max_peaks"],
                ["residual_type should move toward random", "peak positions should stay stable"],
            ),
        },
        "SAXS": {
            "peak_mismatch": (
                ["savgol_window", "q_bragg_min", "q_bragg_max"],
                ["residual_type should move toward random", "Bragg-region fit should stabilize"],
            ),
            "background_drift": (
                ["savgol_window", "q_corr_min", "q_corr_max"],
                ["L_bragg and L_corr should move closer", "validation_summary should calm down"],
            ),
            "noise": (
                ["savgol_window", "savgol_order"],
                ["residual_type should move toward random", "q_peak_snr should stabilize"],
            ),
        },
        "DSC": {
            "peak_shift": (
                ["Tm_search_low_C", "Tm_search_high_C", "peak_function"],
                ["Tm_peak_C should align better", "validation_summary should calm down"],
            ),
            "baseline_drift": (
                ["baseline_type", "smooth_window"],
                ["baseline-related warnings should weaken", "residual summary should lose drift wording"],
            ),
            "baseline_drift_low_t": (
                ["baseline_type", "smooth_window"],
                ["low-temperature baseline support should stabilize", "residual summary should lose drift wording"],
            ),
            "baseline_drift_high_t": (
                ["baseline_type", "smooth_window"],
                ["high-temperature baseline support should stabilize", "residual summary should lose drift wording"],
            ),
            "melting_peak_shift": (
                ["Tm_search_low_C", "Tm_search_high_C", "peak_function"],
                ["Tm_peak_C should align better", "melting window should re-center"],
            ),
            "tg_step_missing": (
                ["Tg_search_low_C", "Tg_search_high_C", "baseline_type"],
                ["Tg support should become clearer", "DCp should stop looking flat"],
            ),
            "cold_crystallization_overlap": (
                ["Tc_search_low_C", "Tc_search_high_C", "Tm_search_low_C"],
                ["Tcc and Tm should separate more cleanly", "event windows should stop overlapping"],
            ),
            "event_window_too_narrow": (
                ["Tm_search_low_C", "Tm_search_high_C", "Tc_search_low_C", "Tc_search_high_C"],
                ["event support should widen", "edge truncation should weaken"],
            ),
            "event_window_too_wide": (
                ["Tm_search_low_C", "Tm_search_high_C", "Tc_search_low_C", "Tc_search_high_C"],
                ["event support should tighten", "broad windows should stop swallowing noise"],
            ),
            "exo_up_down_confusion": (
                ["exo_up", "baseline_type"],
                ["polarity should align with the scan convention", "signed enthalpy should stop contradicting the event"],
            ),
            "multi_event_underfit": (
                ["peak_function", "max_melting_peak_width_C"],
                ["multiple events should be represented explicitly", "single-peak forcing should weaken"],
            ),
            "segment_split_issue": (
                ["smooth_window", "peak_function"],
                ["scan segmentation should be checked", "the event should stop being split across fragments"],
            ),
            "noise": (
                ["smooth_window", "peak_prominence_ratio"],
                ["residual_type should move toward random", "scan_r_squared should stabilize"],
            ),
            "noise_dominant": (
                ["smooth_window", "peak_prominence_ratio"],
                ["residual_type should move toward random", "noise should stop dominating the event"],
            ),
        },
        "IR": {
            "baseline_drift_low_wn": (
                ["baseline_method", "smooth_window"],
                ["low-wavenumber residuals should weaken", "baseline method should settle first"],
            ),
            "baseline_drift_high_wn": (
                ["baseline_method", "normalization_method"],
                ["high-wavenumber residuals should weaken", "normalization should stop steering the conclusion"],
            ),
            "key_band_mismatch": (
                ["peak_fit_window_cm1", "peak_prominence_min", "peak_height_min"],
                ["key-band hits should rise", "assignment confidence should better match band support"],
            ),
            "crowded_band_underfit": (
                ["peak_distance", "lineshape"],
                ["crowded bands should separate more cleanly", "peak widths should become easier to compare"],
            ),
            "over_smoothed_weak_bands": (
                ["smooth_window", "peak_height_min"],
                ["weak bands should reappear", "peak count should stay useful without over-promoting noise"],
            ),
            "normalization_bias": (
                ["normalization_method", "baseline_method"],
                ["band balance should become more stable", "assignment confidence should stop jumping"],
            ),
            "noise_dominant": (
                ["smooth_window"],
                ["sign flips should drop", "weak-band recovery should become more stable"],
            ),
            "peak_mismatch": (
                ["peak_height_min", "peak_prominence_min", "peak_fit_window_cm1"],
                ["peak identity should stabilize", "residual summary should lose mismatch wording"],
            ),
            "background_drift": (
                ["baseline_method", "normalization_method"],
                ["baseline-related warnings should weaken", "residual summary should lose drift wording"],
            ),
            "noise": (
                ["smooth_window", "peak_distance"],
                ["residual_type should move toward random", "peak count should stay stable"],
            ),
        },
        "NMR": {
            "peak_mismatch": (
                ["baseline_method", "peak_distance_ppm", "peak_height_min"],
                ["peak assignment should stabilize", "residual summary should lose mismatch wording"],
            ),
            "background_drift": (
                ["baseline_method", "apodization"],
                ["baseline-related warnings should weaken", "residual summary should lose drift wording"],
            ),
            "noise": (
                ["baseline_method", "peak_height_min"],
                ["residual_type should move toward random", "median_snr should stay stable"],
            ),
        },
    }

    spec = mapping.get(technique_key, {}).get(residual_key)
    if not spec:
        return []

    actions, evidence = spec
    hints = [f"{residual_key} -> {' / '.join(actions)}"]
    hints.extend(f"expected evidence change: {item}" for item in evidence)

    quality_flag = str(output.get("quality_flag", "") or "").strip()
    validation_summary = str(output.get("validation_summary", "") or "").strip()
    if quality_flag:
        hints.append(f"current quality_flag: {quality_flag}")
    if validation_summary and validation_summary != "All checks passed":
        hints.append(f"current validation_summary: {validation_summary}")

    return hints


def evaluate_physical_constraints(
    technique: str,
    output_parameters: dict[str, Any] | None = None,
    residual_pattern: dict[str, Any] | None = None,
    validation_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    output = dict(output_parameters or {})
    residual = dict(residual_pattern or {})
    validation = dict(validation_context or {})
    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}
    technique_key = str(technique or "").upper()
    residual_key = str(residual.get("residual_type", "") or "").strip().lower()
    is_ir_temperature_2d = technique_key == "IR" and _is_ir_temperature_2d(output, validation)
    ir_2d_metrics = _ir_temperature_2d_metrics(output, validation) if is_ir_temperature_2d else {}
    ir_support = _ir_band_support_metrics(output, validation) if technique_key == "IR" else {}
    evaluated: list[dict[str, Any]] = []

    batch_rows = output.get("_batch_data") if isinstance(output.get("_batch_data"), list) else []

    for item in physical_constraint_inventory(technique_key):
        observed = _match_constraint_value(output, item.field)
        triggered = False

        if item.name == "beamstop_contamination":
            triggered = bool(observed)
        elif item.name == "mask_truncated":
            triggered = bool(observed)
        elif item.name == "low_peak_snr":
            snr = _clean_float(observed)
            triggered = snr is not None and snr < 3.0
            observed = snr
        elif item.name == "l_consistency":
            l_bragg = _clean_float(output.get("L_bragg"))
            l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
            if l_bragg is None or l_corr is None:
                triggered = False
            else:
                rel = abs(l_bragg - l_corr) / max(abs(l_bragg), abs(l_corr), 1e-9)
                observed = {"L_bragg": l_bragg, "L_corr": l_corr, "rel_diff": rel}
                triggered = rel > 0.03
        elif item.name == "fit_regions_unstable":
            fit_regions = output.get("fit_regions")
            if isinstance(fit_regions, list) and fit_regions:
                failing = []
                for region in fit_regions:
                    if not isinstance(region, dict):
                        continue
                    region_r2 = _clean_float(region.get("r_squared"))
                    region_rmse = _clean_float(region.get("rmse"))
                    label = str(region.get("region", "") or region.get("name", "") or "unknown").strip()
                    if (region_r2 is not None and region_r2 < 0.25) or (region_rmse is not None and region_rmse > 0.35):
                        failing.append(
                            {
                                "region": label,
                                "r_squared": region_r2,
                                "rmse": region_rmse,
                            }
                        )
                observed = {"failing_regions": failing, "total_regions": len(fit_regions)}
                triggered = len(failing) >= 2
        elif item.name == "correlation_over_oscillation":
            fit_regions = output.get("fit_regions")
            oscillation_flags = []
            if isinstance(fit_regions, list):
                for region in fit_regions:
                    if not isinstance(region, dict):
                        continue
                    label = str(region.get("region", "") or region.get("name", "") or "").strip().lower()
                    if label not in {"correlation", "idf", "correlation_function"}:
                        continue
                    peak_count = _clean_float(region.get("peak_count"))
                    zero_crossings = _clean_float(region.get("zero_crossings"))
                    if (peak_count is not None and peak_count >= 8) or (zero_crossings is not None and zero_crossings >= 10):
                        oscillation_flags.append(
                            {
                                "region": label,
                                "peak_count": peak_count,
                                "zero_crossings": zero_crossings,
                            }
                        )
            observed = {"oscillation_regions": oscillation_flags}
            triggered = bool(oscillation_flags)
        elif item.name == "missing_condition_axis":
            condition_value = _clean_float(output.get("condition_value"))
            if condition_value is None:
                condition_value = _clean_float(output.get("temperature_C"))
            if condition_value is None:
                condition_value = _clean_float(output.get("strain_pct"))
            condition_label = str(output.get("condition_label", "") or "").strip().lower()
            raw_file = str(output.get("file", "") or "").strip().lower()
            observed = {
                "condition_value": condition_value,
                "condition_label": condition_label,
                "file": raw_file,
            }
            triggered = (
                condition_label in {"temperature", "strain"}
                and condition_value is None
                and raw_file.startswith("check-")
            )
        elif item.name == "strain_axis_low_confidence":
            condition_label = str(output.get("condition_label", "") or "").strip().lower()
            strain_confidence = _clean_float(output.get("strain_axis_confidence", output.get("condition_confidence")))
            if strain_confidence is None:
                strain_confidence = _clean_float(output.get("condition_confidence"))
            observed = {
                "condition_label": condition_label,
                "strain_axis_confidence": strain_confidence,
                "condition_continuity_score": _clean_float(output.get("condition_continuity_score")),
            }
            triggered = condition_label == "strain" and strain_confidence is not None and strain_confidence < 0.70
        elif item.name == "strain_sequence_nonmonotonic":
            strain_values = _condition_values(output, batch_rows, "strain")
            observed = {
                "strain_values": strain_values,
                "sequence_direction": "unknown",
            }
            if len(strain_values) >= 2:
                increasing = all(b >= a for a, b in zip(strain_values, strain_values[1:]))
                decreasing = all(b <= a for a, b in zip(strain_values, strain_values[1:]))
                if increasing:
                    observed["sequence_direction"] = "increasing"
                elif decreasing:
                    observed["sequence_direction"] = "decreasing"
                else:
                    observed["sequence_direction"] = "mixed"
            triggered = bool(strain_values) and observed.get("sequence_direction") == "mixed"
        elif item.name == "strain_duplicate_frames":
            strain_values = _condition_values(output, batch_rows, "strain")
            duplicates = max(0, len(strain_values) - len({str(value) for value in strain_values}))
            observed = {
                "strain_values": strain_values,
                "strain_duplicate_count": duplicates,
            }
            triggered = duplicates > 0
        elif item.name == "low_q_void_dominant":
            has_voids = bool(output.get("has_voids")) or _safe_int(output.get("has_voids_row_count"), default=0) > 0
            phi_void = _clean_float(output.get("phi_void_mean", output.get("phi_void")))
            phi_void_span = _clean_float(output.get("phi_void_span"))
            porod_slope = _clean_float(output.get("porod_slope_mean", output.get("porod_slope")))
            q_star_valid = output.get("Q_star_valid")
            if porod_slope is not None and porod_slope > -3.5:
                has_voids = True
            observed = {
                "has_voids": has_voids,
                "phi_void": phi_void,
                "phi_void_span": phi_void_span,
                "porod_slope": porod_slope,
                "Q_star_valid": q_star_valid,
            }
            triggered = has_voids and (
                (phi_void is not None and phi_void >= 0.02)
                or (phi_void_span is not None and phi_void_span >= 0.015)
                or (porod_slope is not None and porod_slope > -3.5)
                or bool(output.get("beam_stop_contaminated"))
                or bool(output.get("mask_truncated"))
                or q_star_valid is False
            )
        elif item.name == "strain_void_lamellar_conflict":
            has_voids = bool(output.get("has_voids")) or _safe_int(output.get("has_voids_row_count"), default=0) > 0
            phi_void = _clean_float(output.get("phi_void_mean", output.get("phi_void")))
            q_star_rel = _clean_float(output.get("Q_star_rel_mean", output.get("Q_star_rel", output.get("Q_rel"))))
            q_star_rel_span = _clean_float(output.get("Q_star_rel_span"))
            l_bragg = _clean_float(output.get("L_bragg"))
            l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
            l_best = _clean_float(output.get("L_best", output.get("L_nm")))
            l_spread = _relative_spread([value for value in (l_bragg, l_corr, l_best) if value is not None])
            porod_slope = _clean_float(output.get("porod_slope_mean", output.get("porod_slope")))
            void_proxy = has_voids or bool(output.get("beam_stop_contaminated")) or bool(output.get("mask_truncated")) or output.get("Q_star_valid") is False
            if porod_slope is not None and porod_slope > -3.5:
                void_proxy = True
            observed = {
                "has_voids": has_voids,
                "phi_void": phi_void,
                "Q_star_rel": q_star_rel,
                "Q_star_rel_span": q_star_rel_span,
                "L_bragg": l_bragg,
                "L_corr": l_corr,
                "L_best": l_best,
                "l_spread": l_spread,
                "porod_slope": porod_slope,
            }
            triggered = condition_label == "strain" and (
                void_proxy
                and (
                    (phi_void is not None and phi_void >= 0.02)
                    or (q_star_rel_span is not None and q_star_rel_span >= 0.05)
                    or (l_spread is not None and l_spread > 0.05)
                    or (porod_slope is not None and porod_slope > -3.5)
                    or bool(output.get("beam_stop_contaminated"))
                    or bool(output.get("mask_truncated"))
                    or output.get("Q_star_valid") is False
                )
            )
        elif item.name == "lamellar_anchor_lost_under_strain":
            has_voids = bool(output.get("has_voids")) or _safe_int(output.get("has_voids_row_count"), default=0) > 0
            l_bragg = _clean_float(output.get("L_bragg"))
            l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
            l_best = _clean_float(output.get("L_best", output.get("L_nm")))
            l_values = [value for value in (l_bragg, l_corr, l_best) if value is not None]
            l_spread = _relative_spread(l_values)
            void_proxy = has_voids or bool(output.get("beam_stop_contaminated")) or bool(output.get("mask_truncated")) or output.get("Q_star_valid") is False
            observed = {
                "has_voids": has_voids,
                "L_bragg": l_bragg,
                "L_corr": l_corr,
                "L_best": l_best,
                "l_spread": l_spread,
                "Q_star_valid": output.get("Q_star_valid"),
            }
            triggered = condition_label == "strain" and (
                len(l_values) < 2
                or l_spread is None
                or l_spread > 0.08
            ) and (
                void_proxy
            )
        elif item.name == "qstar_rel_without_lamellar_support":
            q_star_rel = _clean_float(output.get("Q_star_rel_mean", output.get("Q_star_rel", output.get("Q_rel"))))
            q_star_rel_span = _clean_float(output.get("Q_star_rel_span"))
            l_bragg = _clean_float(output.get("L_bragg"))
            l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
            l_best = _clean_float(output.get("L_best", output.get("L_nm")))
            l_values = [value for value in (l_bragg, l_corr, l_best) if value is not None]
            l_spread = _relative_spread(l_values)
            observed = {
                "Q_star_rel": q_star_rel,
                "Q_star_rel_span": q_star_rel_span,
                "L_bragg": l_bragg,
                "L_corr": l_corr,
                "L_best": l_best,
                "l_spread": l_spread,
            }
            triggered = condition_label == "strain" and q_star_rel is not None and (
                len(l_values) < 2
                or l_spread is None
                or l_spread > 0.08
                or (q_star_rel_span is not None and q_star_rel_span > 0.05)
            )
        elif item.name == "orientation_shift_breaks_lamellar_comparison":
            f_herman = _clean_float(output.get("f_Herman_mean", output.get("f_Herman", output.get("f_herman"))))
            f_herman_span = _clean_float(output.get("f_Herman_span"))
            q_star_rel_span = _clean_float(output.get("Q_star_rel_span"))
            observed = {
                "f_Herman": f_herman,
                "f_Herman_span": f_herman_span,
                "Q_star_rel_span": q_star_rel_span,
            }
            triggered = condition_label == "strain" and f_herman is not None and (
                f_herman_span is not None and f_herman_span > 0.35
            ) and (
                q_star_rel_span is None or q_star_rel_span > 0.03
            )
        elif item.name == "quality_floor":
            quality = _clean_float(observed)
            triggered = quality is not None and quality < 0.5
            observed = quality
        elif item.name == "multi_scan_consistency":
            triggered = bool(output.get("scan_r_squared"))
            observed = output.get("scan_r_squared")
        elif item.name == "peak_visibility":
            n_peaks = _clean_float(observed)
            triggered = n_peaks is not None and n_peaks <= 0
            observed = n_peaks
        elif item.name == "peak_structure":
            n_peaks = _clean_float(observed)
            triggered = n_peaks is not None and n_peaks > 0
            observed = n_peaks
        elif item.name == "fit_quality_vs_phys":
            r2 = _clean_float(observed)
            quality = _clean_float(output.get("quality_score"))
            if r2 is not None and quality is not None:
                triggered = abs(r2 - quality) > 0.05
                observed = {"r_squared": r2, "quality_score": quality}
        elif item.name == "assignment_confidence":
            score = _clean_float(observed)
            triggered = score is not None and score < 0.7
            observed = score
        elif item.name == "fit_quality":
            fit_quality = None
            if isinstance(output.get("quality_metrics"), dict):
                fit_quality = _clean_float(output["quality_metrics"].get("fit_quality"))
            if fit_quality is None:
                fit_quality = _clean_float(output.get("quality_fit_quality"))
            triggered = fit_quality is not None and fit_quality < 1.0
            observed = fit_quality
        elif item.name == "peak_snr":
            snr = _clean_float(observed)
            triggered = snr is not None and snr < 5.0
            observed = snr
        elif item.name == "nmr_low_peak_count":
            n_peaks = _clean_float(observed)
            triggered = n_peaks is not None and n_peaks < 2
            observed = n_peaks
        elif item.name == "nmr_low_snr":
            snr = _clean_float(observed)
            triggered = snr is not None and snr < 5.0
            observed = snr
        elif item.name == "nmr_broad_linewidth":
            linewidth = _clean_float(observed)
            triggered = linewidth is not None and linewidth > 20.0
            observed = linewidth
        elif item.name == "nmr_weak_assignment":
            peak_rows = _nmr_peak_rows(output)
            assigned_count = sum(1 for row in peak_rows if row.get("assignment"))
            match_count = _clean_float(output.get("n_matches"))
            n_peaks = _clean_float(output.get("n_peaks"))
            observed = {"assigned_peak_count": assigned_count, "n_matches": match_count, "n_peaks": n_peaks}
            triggered = bool(
                (peak_rows and n_peaks is not None and n_peaks > 0 and assigned_count == 0)
                or (match_count is not None and match_count <= 0)
            )
        elif item.name == "nmr_solvent_risk":
            peak_rows = _nmr_peak_rows(output)
            solvent_peaks = [
                {"index": row.get("index"), "possible_solvent": row.get("possible_solvent")}
                for row in peak_rows
                if row.get("possible_solvent")
            ]
            observed = solvent_peaks
            triggered = bool(solvent_peaks)
        elif item.name == "nmr_xc_assignment_missing":
            peak_rows = _nmr_peak_rows(output)
            phases = {str(row.get("phase", "") or "").lower() for row in peak_rows if row.get("phase")}
            xc_method = str(output.get("Xc_method") or "").strip()
            needs_assignment = xc_method == "requires_crystalline_amorphous_assignment" and output.get("Xc_pct") is None
            has_crystalline = bool(phases & {"c", "crystalline"})
            has_amorphous = bool(phases & {"a", "amorphous"})
            observed = {"Xc_method": xc_method or None, "phases": sorted(phases)}
            triggered = bool(needs_assignment and not (has_crystalline and has_amorphous))
        elif item.name == "nmr_xc_assignment_limited":
            peak_rows = _nmr_peak_rows(output)
            phases = {str(row.get("phase", "") or "").lower() for row in peak_rows if row.get("phase")}
            xc_method = str(output.get("Xc_method") or "").strip()
            phase_count = _clean_float(output.get("phase_assignment_count"))
            if phase_count is not None and phase_count <= 0:
                phases = set()
            has_crystalline = bool(phases & {"c", "crystalline"})
            has_amorphous = bool(phases & {"a", "amorphous"})
            observed = {
                "Xc_method": xc_method or None,
                "Xc_pct": _clean_float(output.get("Xc_pct")),
                "phase_assignment_count": phase_count,
                "phases": sorted(phases),
            }
            triggered = bool(
                output.get("Xc_pct") is not None
                and xc_method == "requires_crystalline_amorphous_assignment"
                and not (has_crystalline and has_amorphous)
            )
        elif technique_key == "IR" and not is_ir_temperature_2d and item.name in {
            "key_band_support_insufficient",
            "assignment_without_characteristic_bands",
            "baseline_sensitive_assignment",
            "baseline_drift_low_wn",
            "baseline_drift_high_wn",
            "key_band_mismatch",
            "crowded_band_underfit",
            "over_smoothed_weak_bands",
            "normalization_bias",
            "noise_dominant",
            "weak_peak_only_support",
            "overcrowded_band_separation_unstable",
            "polymer_score_without_assignment_support",
            "crystallinity_index_without_band_support",
            "ir_xc_uncalibrated",
        }:
            peak_count = _clean_float(ir_support.get("peak_count"))
            assigned_peak_count = _clean_float(ir_support.get("assigned_peak_count"))
            peak_width_spread = _clean_float(ir_support.get("peak_width_spread"))
            baseline_method = str(ir_support.get("baseline_method", "") or "").strip().lower()
            normalization_method = str(ir_support.get("normalization_method", "") or "").strip().lower()
            peak_distance = _clean_float(ir_support.get("peak_distance"))
            peak_fit_window = _clean_float(ir_support.get("peak_fit_window_cm1"))
            assignment_confidence = _clean_float(ir_support.get("assignment_confidence"))
            polymer_score = _clean_float(ir_support.get("polymer_score"))
            reference_band_count = int(ir_support.get("reference_band_count") or 0)
            reference_band_hit_count = int(ir_support.get("reference_band_hit_count") or 0)
            reference_band_missing_count = int(ir_support.get("reference_band_missing_count") or 0)
            x_pct = _clean_float(ir_support.get("Xc_pct"))
            x_method = str(ir_support.get("Xc_method") or "").strip()
            x_calibration_status = str(ir_support.get("Xc_calibration_status") or "").strip()

            if item.name == "key_band_support_insufficient":
                observed = {
                    "reference_band_count": reference_band_count,
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                }
                triggered = reference_band_count > 0 and (
                    reference_band_hit_count < 3 or reference_band_missing_count > 0
                )
            elif item.name == "assignment_without_characteristic_bands":
                observed = {
                    "assignment_confidence": assignment_confidence,
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                }
                triggered = assignment_confidence is not None and assignment_confidence < 0.8 and (
                    reference_band_hit_count < 3 or reference_band_missing_count > 0
                )
            elif item.name == "baseline_sensitive_assignment":
                observed = {
                    "baseline_method": baseline_method or None,
                    "normalization_method": normalization_method or None,
                    "peak_width_spread": peak_width_spread,
                }
                triggered = (
                    baseline_method in {"als", "mute_zone", "none"}
                    or normalization_method in {"none", "peak"}
                    or (peak_width_spread is not None and peak_width_spread > 0.4)
                )
            elif item.name == "baseline_drift_low_wn":
                observed = {
                    "residual_type": residual_key or None,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                }
                triggered = residual_key == "baseline_drift_low_wn"
            elif item.name == "baseline_drift_high_wn":
                observed = {
                    "residual_type": residual_key or None,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                }
                triggered = residual_key == "baseline_drift_high_wn"
            elif item.name == "key_band_mismatch":
                observed = {
                    "residual_type": residual_key or None,
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                }
                triggered = residual_key in {"key_band_mismatch", "peak_mismatch"} and (
                    assignment_confidence is None
                    or assignment_confidence < 0.9
                    or reference_band_hit_count < 3
                    or reference_band_missing_count > 0
                )
            elif item.name == "crowded_band_underfit":
                observed = {
                    "residual_type": residual_key or None,
                    "peak_count": peak_count,
                    "peak_distance": peak_distance,
                    "peak_fit_window_cm1": peak_fit_window,
                    "peak_width_spread": peak_width_spread,
                }
                triggered = residual_key == "crowded_band_underfit" or (
                    residual_key == "peak_mismatch"
                    and (
                        (peak_count is not None and peak_count >= 8)
                        or (peak_distance is not None and peak_distance < 10.0)
                        or (peak_fit_window is not None and peak_fit_window > 50.0)
                        or (peak_width_spread is not None and peak_width_spread > 0.45)
                    )
                )
            elif item.name == "over_smoothed_weak_bands":
                observed = {
                    "residual_type": residual_key or None,
                    "peak_count": peak_count,
                    "peak_width_spread": peak_width_spread,
                }
                triggered = residual_key == "over_smoothed_weak_bands"
            elif item.name == "normalization_bias":
                observed = {
                    "residual_type": residual_key or None,
                    "baseline_method": baseline_method or None,
                    "normalization_method": normalization_method or None,
                }
                triggered = residual_key == "normalization_bias"
            elif item.name == "noise_dominant":
                observed = {
                    "residual_type": residual_key or None,
                    "peak_count": peak_count,
                    "peak_width_spread": peak_width_spread,
                }
                triggered = residual_key in {"noise_dominant", "noise"}
            elif item.name == "weak_peak_only_support":
                observed = {
                    "peak_count": peak_count,
                    "assigned_peak_count": assigned_peak_count,
                    "reference_band_hit_count": reference_band_hit_count,
                }
                triggered = (
                    peak_count is not None
                    and peak_count > 0
                    and reference_band_hit_count < 2
                    and (assignment_confidence is None or assignment_confidence < 0.85)
                )
            elif item.name == "overcrowded_band_separation_unstable":
                observed = {
                    "peak_count": peak_count,
                    "peak_distance": peak_distance,
                    "peak_fit_window_cm1": peak_fit_window,
                    "peak_width_spread": peak_width_spread,
                }
                triggered = (
                    (peak_distance is not None and peak_distance < 10.0)
                    or (peak_fit_window is not None and peak_fit_window > 50.0)
                    or (peak_count is not None and peak_count >= 8)
                    or (peak_width_spread is not None and peak_width_spread > 0.45)
                )
            elif item.name == "polymer_score_without_assignment_support":
                observed = {
                    "polymer_score": polymer_score,
                    "reference_band_hit_count": reference_band_hit_count,
                    "assigned_peak_count": assigned_peak_count,
                }
                triggered = polymer_score is not None and polymer_score < 0.85 and (
                    reference_band_hit_count < 3 or assigned_peak_count < 4
                )
            elif item.name == "crystallinity_index_without_band_support":
                observed = {
                    "Xc_pct": x_pct,
                    "reference_band_hit_count": reference_band_hit_count,
                    "reference_band_missing_count": reference_band_missing_count,
                }
                triggered = x_pct is not None and x_pct > 0 and (
                    reference_band_hit_count < 2 or reference_band_missing_count > 0
                )
            elif item.name == "ir_xc_uncalibrated":
                observed = {
                    "Xc_pct": x_pct,
                    "Xc_method": x_method or None,
                    "Xc_calibration_status": x_calibration_status or None,
                }
                triggered = (
                    x_calibration_status == "uncalibrated_index"
                    or x_method.lower().endswith("_uncalibrated")
                )
        elif technique_key == "DSC" and item.name in {
            "baseline_sensitive_result",
            "Tg_without_DCp_step",
            "Tg_outside_supported_window",
            "melting_without_supported_event",
            "cold_crystallization_conflicts_with_melting",
            "event_polarity_conflict",
            "peak_components_too_sparse",
            "peak_width_nonphysical",
            "multi_scan_inconsistent",
            "crystallinity_without_event_support",
            "dsc_baseline_sensitive_xc",
            "quality_score_without_event_support",
        }:
            peak_rows = _dsc_peak_component_rows(output.get("peak_components"))
            scan_rows = _dsc_scan_rows(output.get("scan_r_squared"))
            scan_mode = str(output.get("scan_mode", output.get("technique", "")) or "").strip().lower()
            quality_flags = output.get("quality_flags")
            if isinstance(quality_flags, dict):
                quality_flag_text = " ".join(f"{key}:{value}" for key, value in quality_flags.items())
            elif isinstance(quality_flags, list):
                quality_flag_text = " ".join(str(value) for value in quality_flags)
            else:
                quality_flag_text = str(quality_flags or "")
            quality_flag_text = quality_flag_text.strip().lower()
            dtg = _clean_float(output.get("DTg_C"))
            dcp = _clean_float(output.get("DCp_JgK"))
            tg_c = _clean_float(output.get("Tg_C"))
            tm_peak = _clean_float(output.get("Tm_peak_C"))
            tm_onset = _clean_float(output.get("Tm_onset_C"))
            tcc_peak = _clean_float(output.get("Tcc_peak_C"))
            tcc_onset = _clean_float(output.get("Tcc_onset_C"))
            tc_peak = _clean_float(output.get("Tc_peak_C"))
            dhm = _clean_float(output.get("DHm_Jg"))
            dhcc = _clean_float(output.get("DHcc_Jg"))
            xc_pct = _clean_float(output.get("Xc_pct"))
            baseline_sensitive = _clean_float(output.get("baseline_sensitivity_pct"))
            boundary_sensitive = _clean_float(output.get("integration_boundary_sensitivity_pct"))
            quality = _clean_float(output.get("quality_score"))
            min_event_enthalpy = _clean_float(output.get("min_event_enthalpy_Jg", config_snapshot.get("min_event_enthalpy_Jg")))
            max_melt_width = _clean_float(
                output.get("max_melting_peak_width_C", config_snapshot.get("max_melting_peak_width_C"))
            )
            if max_melt_width is None:
                max_melt_width = 50.0
            tg_window_low = _clean_float(output.get("Tg_search_low_C", config_snapshot.get("Tg_search_low_C")))
            tg_window_high = _clean_float(output.get("Tg_search_high_C", config_snapshot.get("Tg_search_high_C")))
            exo_up = config_snapshot.get("exo_up", output.get("exo_up"))
            supported_components = [
                row for row in peak_rows
                if _clean_float(row.get("peak_C")) is not None
                and _clean_float(row.get("enthalpy_Jg")) is not None
                and abs(_clean_float(row.get("enthalpy_Jg")) or 0.0) >= max(0.0, float(min_event_enthalpy or 0.0))
            ]
            supported_melting_components = [
                row for row in supported_components
                if str(row.get("type", "") or "").strip().lower() in {"melting", "deconv_melting"}
            ]

            def _near_event(
                event_type: set[str],
                center_c: float | None,
                tolerance_c: float = 12.0,
            ) -> list[dict[str, Any]]:
                if center_c is None:
                    return []
                matched: list[dict[str, Any]] = []
                for row in peak_rows:
                    row_type = str(row.get("type", "") or "").strip().lower()
                    peak_c = _clean_float(row.get("peak_C"))
                    if row_type not in event_type or peak_c is None:
                        continue
                    if abs(peak_c - center_c) <= tolerance_c:
                        matched.append(row)
                return matched

            if item.name == "baseline_sensitive_result":
                observed = {
                    "residual_type": residual_key or None,
                    "quality_flags": quality_flag_text or None,
                    "fit_rmse": _clean_float(output.get("fit_rmse")),
                }
                triggered = residual_key in {
                    "baseline_drift",
                    "baseline_drift_low_t",
                    "baseline_drift_high_t",
                    "segment_split_issue",
                } or "baseline" in quality_flag_text or (quality is not None and quality < 0.55)
            elif item.name == "Tg_without_DCp_step":
                observed = {
                    "Tg_C": tg_c,
                    "DTg_C": dtg,
                    "DCp_JgK": dcp,
                }
                triggered = tg_c is not None and (
                    dcp is None
                    or abs(dcp) < 0.005
                    or dtg is None
                    or dtg <= 0
                )
            elif item.name == "Tg_outside_supported_window":
                observed = {
                    "Tg_C": tg_c,
                    "Tg_search_low_C": tg_window_low,
                    "Tg_search_high_C": tg_window_high,
                }
                triggered = (
                    tg_c is not None
                    and tg_window_low is not None
                    and tg_window_high is not None
                    and (tg_c < tg_window_low or tg_c > tg_window_high)
                )
            elif item.name == "melting_without_supported_event":
                melt_rows = _near_event({"melting", "deconv_melting"}, tm_peak, tolerance_c=18.0)
                observed = {
                    "Tm_peak_C": tm_peak,
                    "DHm_Jg": dhm,
                    "supported_melting_component_count": len(supported_melting_components),
                    "supported_components": melt_rows,
                }
                triggered = tm_peak is not None and (
                    not melt_rows or dhm is None or dhm <= 0
                    or len(supported_melting_components) < 1
                )
            elif item.name == "cold_crystallization_conflicts_with_melting":
                gap_to_melt_onset = None
                if tcc_peak is not None and tm_onset is not None:
                    gap_to_melt_onset = tm_onset - tcc_peak
                observed = {
                    "Tcc_peak_C": tcc_peak,
                    "Tcc_onset_C": tcc_onset,
                    "Tm_onset_C": tm_onset,
                    "Tm_peak_C": tm_peak,
                    "gap_to_melt_onset_C": gap_to_melt_onset,
                }
                triggered = (
                    tcc_peak is not None
                    and (
                        (tm_onset is not None and tcc_peak >= tm_onset - 5.0)
                        or (tm_peak is not None and abs(tm_peak - tcc_peak) < 15.0)
                    )
                )
            elif item.name == "event_polarity_conflict":
                conflicting_types: list[str] = []
                signed_conflicts: list[dict[str, Any]] = []
                peak_types = {
                    str(row.get("type", "") or "").strip().lower()
                    for row in peak_rows
                    if str(row.get("type", "") or "").strip()
                }
                exo_up_known = isinstance(exo_up, bool)
                exo_sign = 1.0 if exo_up is True else -1.0
                if exo_up_known:
                    for row in supported_components or peak_rows:
                        row_type = str(row.get("type", "") or "").strip().lower()
                        enthalpy = _clean_float(row.get("enthalpy_Jg"))
                        if enthalpy is None:
                            continue
                        if row_type in {"melting", "deconv_melting"} and enthalpy * exo_sign > 0:
                            signed_conflicts.append({"type": row_type, "enthalpy_Jg": enthalpy})
                        if row_type in {"crystallisation", "crystallization", "cold_crystallisation", "cold_crystallization", "recrystallisation", "recrystallization"} and enthalpy * exo_sign < 0:
                            signed_conflicts.append({"type": row_type, "enthalpy_Jg": enthalpy})
                if scan_mode == "heating":
                    if tc_peak is not None:
                        conflicting_types.append("cooling_crystallisation_present_on_heating")
                    if "crystallisation" in peak_types:
                        conflicting_types.append("crystallisation_component_on_heating")
                elif scan_mode == "cooling":
                    if tm_peak is not None:
                        conflicting_types.append("melting_present_on_cooling")
                    if {"melting", "deconv_melting"} & peak_types:
                        conflicting_types.append("melting_component_on_cooling")
                observed = {
                    "scan_mode": scan_mode or None,
                    "exo_up": exo_up if exo_up is not None else None,
                    "exo_up_known": exo_up_known,
                    "peak_types": sorted(peak_types),
                    "conflicting_types": conflicting_types,
                    "signed_conflicts": signed_conflicts,
                }
                triggered = bool(conflicting_types or signed_conflicts)
            elif item.name == "peak_components_too_sparse":
                thermal_claims = [
                    value
                    for value in (tg_c, tm_peak, tc_peak, tcc_peak, xc_pct)
                    if value is not None
                ]
                observed = {
                    "peak_component_count": len(peak_rows),
                    "supported_component_count": len(supported_components),
                    "n_peaks": _safe_int(output.get("n_peaks"), default=len(peak_rows)),
                    "thermal_claim_count": len(thermal_claims),
                }
                triggered = bool(thermal_claims) and len(supported_components) < 1
            elif item.name == "peak_width_nonphysical":
                invalid_rows: list[dict[str, Any]] = []
                for row in peak_rows:
                    row_type = str(row.get("type", "") or "").strip().lower()
                    onset = _clean_float(row.get("onset_C"))
                    end = _clean_float(row.get("end_C"))
                    sigma_c = _clean_float(row.get("sigma_C"))
                    width = None
                    invalid = False
                    if onset is not None and end is not None:
                        width = end - onset
                        if width <= 0 or width < 1.0:
                            invalid = True
                        if row_type in {"melting", "deconv_melting"} and width > max_melt_width:
                            invalid = True
                        if width > 80.0:
                            invalid = True
                    if sigma_c is not None and sigma_c <= 0:
                        invalid = True
                    if invalid:
                        bad = dict(row)
                        if width is not None:
                            bad["width_C"] = width
                        invalid_rows.append(bad)
                observed = {
                    "max_melting_peak_width_C": max_melt_width,
                    "invalid_components": invalid_rows,
                }
                triggered = bool(invalid_rows)
            elif item.name == "multi_scan_inconsistent":
                r2_values = [row.get("r_squared") for row in scan_rows if _clean_float(row.get("r_squared")) is not None]
                quality_values = [
                    row.get("quality_score")
                    for row in scan_rows
                    if _clean_float(row.get("quality_score")) is not None
                ]
                r2_spread = _relative_spread(r2_values)
                quality_spread = _relative_spread(quality_values)
                min_r2 = min((float(value) for value in r2_values), default=None)
                max_r2 = max((float(value) for value in r2_values), default=None)
                observed = {
                    "scan_count": len(scan_rows),
                    "r_squared_spread": r2_spread,
                    "quality_spread": quality_spread,
                    "min_r_squared": min_r2,
                    "max_r_squared": max_r2,
                }
                triggered = bool(
                    scan_rows
                    and (
                        (r2_spread is not None and r2_spread > 0.06)
                        or (quality_spread is not None and quality_spread > 0.10)
                        or (min_r2 is not None and max_r2 is not None and (max_r2 - min_r2) > 0.08)
                    )
                )
            elif item.name == "crystallinity_without_event_support":
                melt_rows = _near_event({"melting", "deconv_melting"}, tm_peak, tolerance_c=18.0)
                observed = {
                    "Xc_pct": xc_pct,
                    "DHm_Jg": dhm,
                    "DHcc_Jg": dhcc,
                    "supported_melting_components": melt_rows,
                }
                triggered = xc_pct is not None and xc_pct > 0 and (
                    dhm is None
                    or dhm <= 0
                    or not melt_rows
                    or len(supported_melting_components) < 1
                )
            elif item.name == "dsc_baseline_sensitive_xc":
                observed = {
                    "Xc_pct": xc_pct,
                    "baseline_sensitivity_pct": baseline_sensitive,
                    "integration_boundary_sensitivity_pct": boundary_sensitive,
                }
                triggered = xc_pct is not None and (
                    (baseline_sensitive is not None and baseline_sensitive >= 10.0)
                    or (boundary_sensitive is not None and boundary_sensitive >= 8.0)
                )
            elif item.name == "quality_score_without_event_support":
                event_count = len(supported_components)
                observed = {
                    "quality_score": quality,
                    "peak_component_count": event_count,
                    "Tm_peak_C": tm_peak,
                    "Tc_peak_C": tc_peak,
                    "Tcc_peak_C": tcc_peak,
                }
                triggered = quality is not None and quality >= 0.75 and (
                    event_count < 1
                    or (tm_peak is None and tc_peak is None and tcc_peak is None and tg_c is None)
                )
        elif technique_key == "WAXS" and item.name in {
            "temperature_axis_missing",
            "temperature_axis_low_confidence",
            "temperature_sequence_nonmonotonic",
            "temperature_duplicate_frames",
            "peak_count_insufficient",
            "peak_family_unstable",
            "peak_family_identity_swap",
            "peak_family_track_fragmented",
            "peak_family_missing_too_many_frames",
            "peak_position_drift_unphysical",
            "peak_width_trend_unstable",
            "phase_transition_without_peak_family_support",
            "crystallinity_trend_without_peak_support",
            "crystallinity_jump_single_frame",
            "crystallinity_background_driven",
            "crystallinity_trend_conflicts_with_peak_area",
            "crystallinity_outside_physical_range",
            "melting_trend_without_peak_disappearance",
            "cold_crystallization_without_new_peak_support",
            "amorphous_partition_unstable",
            "peak_width_nonphysical",
            "offset_sensitive_solution",
            "crystallinity_without_peak_support",
            "size_without_multi_peak_support",
        }:
            waxs_metrics = _waxs_peak_metrics(output)
            peak_count = waxs_metrics.get("peak_count")
            peak_widths = waxs_metrics.get("peak_widths", [])
            peak_gap_spread = waxs_metrics.get("peak_gap_spread")
            peak_width_spread = waxs_metrics.get("peak_width_spread")
            x_method = str(output.get("Xc_method", "") or "").strip().lower()
            x_pct = _clean_float(output.get("Xc_pct"))
            two_theta_offset = _clean_float(output.get("two_theta_offset"))
            if two_theta_offset is None:
                two_theta_offset = _clean_float(config_snapshot.get("two_theta_offset"))
            temperature_missing_count = _safe_int(output.get("temperature_missing_count"), 0)
            temperature_duplicate_count = _safe_int(output.get("temperature_duplicate_count"), 0)
            temperature_monotonic = bool(output.get("temperature_monotonic", False))
            temperature_axis_confidence = _clean_float(output.get("temperature_axis_confidence", output.get("condition_confidence")))
            family_count = _safe_int(output.get("peak_family_count"), 0)
            family_continuity = _clean_float(output.get("peak_family_continuity_score"))
            family_missing_count = _safe_int(output.get("peak_family_missing_frame_count"), 0)
            family_missing_ratio = _clean_float(output.get("peak_family_missing_ratio"))
            family_swap_count = _safe_int(output.get("peak_family_identity_swap_count"), 0)
            family_fragmented_count = _safe_int(output.get("peak_family_fragmented_count"), 0)
            position_drift_map = output.get("peak_position_drift_per_family")
            width_drift_map = output.get("peak_width_drift_per_family")
            d_values = output.get("D_values_nm", [])
            if not isinstance(d_values, list):
                d_values = []
            d_support_peak_count = _safe_int(output.get("D_support_peak_count"), 0)
            d_support_family_count = _safe_int(output.get("D_support_family_count"), 0)
            d_trend_support_score = _clean_float(output.get("D_trend_support_score"))
            d_monotonicity = str(output.get("D_trend_monotonicity", "") or "").strip().lower()
            d_jump_count = _safe_int(output.get("D_jump_single_frame_count"), 0)
            d_jump_indices = output.get("D_jump_single_frame_indices", [])
            if not isinstance(d_jump_indices, list):
                d_jump_indices = []
            d_confidence_by_frame = output.get("D_confidence_by_frame", [])
            if not isinstance(d_confidence_by_frame, list):
                d_confidence_by_frame = []
            fwhm_values_by_family = output.get("FWHM_values_by_family", {})
            if not isinstance(fwhm_values_by_family, dict):
                fwhm_values_by_family = {}
            instrument_broadening_present = bool(output.get("instrument_broadening_present"))
            max_fwhm_drift = None
            width_drift_values = []
            if isinstance(width_drift_map, dict) and width_drift_map:
                width_drift_values = [_clean_float(value) for value in width_drift_map.values()]
                width_drift_values = [value for value in width_drift_values if value is not None]
                if width_drift_values:
                    max_fwhm_drift = max(width_drift_values)
            xc_values = output.get("Xc_values", [])
            xc_support_score = _clean_float(output.get("Xc_trend_support_score"))
            xc_background_sensitivity = _clean_float(output.get("Xc_background_sensitivity"))
            xc_peak_support_ratio = _clean_float(output.get("Xc_peak_support_ratio"))
            xc_monotonicity = str(output.get("Xc_trend_monotonicity", "") or "").strip().lower()
            xc_jump_count = _safe_int(output.get("crystallinity_jump_single_frame_count"), 0)
            xc_jump_indices = output.get("crystallinity_jump_single_frame_indices", [])
            if not isinstance(xc_jump_indices, list):
                xc_jump_indices = []
            transition_support_score = _clean_float(output.get("transition_support_score"))
            transition_candidate_count = _safe_int(output.get("transition_candidate_count"), 0)
            transition_candidates = output.get("Xc_transition_candidates", [])
            if not isinstance(transition_candidates, list):
                transition_candidates = []
            if transition_candidate_count <= 0 and transition_candidates:
                transition_candidate_count = len(transition_candidates)
            max_position_drift = None
            max_width_drift = None
            frame_records = output.get("frame_evidence", [])
            if not isinstance(frame_records, list):
                frame_records = []
            peak_area_series = []
            x_c_series = []
            for row in frame_records:
                if not isinstance(row, dict):
                    continue
                area = _clean_float(row.get("peak_area_sum"))
                if area is not None and np.isfinite(area):
                    peak_area_series.append(area)
                x_val = _clean_float(row.get("Xc_pct"))
                if x_val is not None and np.isfinite(x_val):
                    x_c_series.append(x_val)
            if isinstance(position_drift_map, dict) and position_drift_map:
                pos_values = [_clean_float(value) for value in position_drift_map.values()]
                pos_values = [value for value in pos_values if value is not None]
                if pos_values:
                    max_position_drift = max(pos_values)
            if isinstance(width_drift_map, dict) and width_drift_map:
                width_values = [_clean_float(value) for value in width_drift_map.values()]
                width_values = [value for value in width_values if value is not None]
                if width_values:
                    max_width_drift = max(width_values)

            if item.name == "temperature_axis_missing":
                triggered = temperature_missing_count > 0
                observed = {
                    "temperature_missing_count": temperature_missing_count,
                    "temperature_values": output.get("temperature_values", []),
                }
            elif item.name == "temperature_axis_low_confidence":
                triggered = temperature_axis_confidence is not None and temperature_axis_confidence < 0.70
                observed = {
                    "condition_confidence": temperature_axis_confidence,
                    "condition_continuity_score": _clean_float(output.get("condition_continuity_score")),
                }
            elif item.name == "temperature_sequence_nonmonotonic":
                triggered = not temperature_monotonic
                observed = {
                    "temperature_monotonic": temperature_monotonic,
                    "temperature_values": output.get("temperature_values", []),
                }
            elif item.name == "temperature_duplicate_frames":
                triggered = temperature_duplicate_count > 0
                observed = {
                    "temperature_duplicate_count": temperature_duplicate_count,
                    "temperature_values": output.get("temperature_values", []),
                }
            elif item.name == "peak_count_insufficient":
                triggered = peak_count is not None and peak_count < 2
                observed = {"peak_count": peak_count, "peak_positions": waxs_metrics.get("peak_positions", [])}
            elif item.name == "peak_family_unstable":
                width_trigger = peak_width_spread is not None and peak_width_spread > 0.45
                gap_trigger = peak_count is not None and peak_count >= 3 and peak_gap_spread is not None and peak_gap_spread > 0.35
                triggered = width_trigger or gap_trigger
                observed = {
                    "peak_count": peak_count,
                    "peak_gap_spread": peak_gap_spread,
                    "peak_width_spread": peak_width_spread,
                }
            elif item.name == "peak_family_identity_swap":
                triggered = family_swap_count > 0
                observed = {
                    "peak_family_identity_swap_count": family_swap_count,
                    "peak_family_continuity_score": family_continuity,
                }
            elif item.name == "peak_family_track_fragmented":
                triggered = family_fragmented_count > 0 or (
                    family_continuity is not None and family_continuity < 0.72
                )
                observed = {
                    "peak_family_fragmented_count": family_fragmented_count,
                    "peak_family_continuity_score": family_continuity,
                }
            elif item.name == "peak_family_missing_too_many_frames":
                triggered = (
                    (family_missing_ratio is not None and family_missing_ratio > 0.30)
                    or family_missing_count >= 2
                )
                observed = {
                    "peak_family_missing_frame_count": family_missing_count,
                    "peak_family_missing_ratio": family_missing_ratio,
                }
            elif item.name == "peak_position_drift_unphysical":
                triggered = max_position_drift is not None and max_position_drift > 0.85
                observed = {
                    "peak_position_drift_per_family": position_drift_map,
                    "max_position_drift_deg": max_position_drift,
                }
            elif item.name == "peak_width_trend_unstable":
                triggered = max_width_drift is not None and max_width_drift > 0.55
                observed = {
                    "peak_width_drift_per_family": width_drift_map,
                    "max_width_drift_deg": max_width_drift,
                }
            elif item.name == "phase_transition_without_peak_family_support":
                transition_count = _safe_int(output.get("n_transitions"), 0)
                triggered = transition_count > 0 and (
                    family_count < 2
                    or (family_continuity is not None and family_continuity < 0.55)
                    or (transition_support_score is not None and transition_support_score < 0.55)
                )
                observed = {
                    "n_transitions": transition_count,
                    "peak_family_count": family_count,
                    "peak_family_continuity_score": family_continuity,
                    "transition_support_score": transition_support_score,
                    "transition_candidate_count": transition_candidate_count,
                }
            elif item.name == "crystallinity_trend_without_peak_support":
                triggered = (
                    xc_support_score is not None and xc_support_score < 0.52
                ) or (
                    xc_peak_support_ratio is not None and xc_peak_support_ratio < 0.60
                )
                observed = {
                    "Xc_trend_support_score": xc_support_score,
                    "Xc_peak_support_ratio": xc_peak_support_ratio,
                    "Xc_trend_monotonicity": xc_monotonicity,
                }
            elif item.name == "crystallinity_jump_single_frame":
                triggered = xc_jump_count > 0
                observed = {
                    "crystallinity_jump_single_frame_count": xc_jump_count,
                    "crystallinity_jump_single_frame_indices": xc_jump_indices,
                }
            elif item.name == "crystallinity_background_driven":
                triggered = (
                    xc_background_sensitivity is not None and xc_background_sensitivity > 0.45
                ) or (
                    xc_support_score is not None and xc_support_score < 0.45
                )
                observed = {
                    "Xc_background_sensitivity": xc_background_sensitivity,
                    "Xc_trend_support_score": xc_support_score,
                }
            elif item.name == "crystallinity_trend_conflicts_with_peak_area":
                area_delta_sum = None
                if len(peak_area_series) >= 2:
                    area_delta_sum = float(peak_area_series[-1] - peak_area_series[0])
                xc_delta = None
                if len(x_c_series) >= 2:
                    xc_delta = float(x_c_series[-1] - x_c_series[0])
                triggered = (
                    area_delta_sum is not None
                    and xc_delta is not None
                    and area_delta_sum * xc_delta < 0
                    and abs(xc_delta) > 0.02
                )
                observed = {
                    "peak_area_start_end_delta": area_delta_sum,
                    "Xc_start_end_delta": xc_delta,
                }
            elif item.name == "crystallinity_outside_physical_range":
                invalid_xc = [
                    value
                    for value in (xc_values if isinstance(xc_values, list) else [])
                    if _clean_float(value) is not None and (_clean_float(value) < 0 or _clean_float(value) > 95.0)
                ]
                triggered = bool(invalid_xc)
                observed = {"invalid_Xc_values": invalid_xc}
            elif item.name == "melting_trend_without_peak_disappearance":
                xc_start = _clean_float(output.get("Xc_initial_pct"))
                xc_end = _clean_float(output.get("Xc_final_pct"))
                disappearance_count = len(output.get("peak_disappearance_temperatures", []) or [])
                triggered = (
                    xc_start is not None
                    and xc_end is not None
                    and xc_end < xc_start - 0.02
                    and disappearance_count <= 0
                )
                observed = {
                    "Xc_initial_pct": xc_start,
                    "Xc_final_pct": xc_end,
                    "peak_disappearance_temperatures": output.get("peak_disappearance_temperatures", []),
                }
            elif item.name == "cold_crystallization_without_new_peak_support":
                xc_start = _clean_float(output.get("Xc_initial_pct"))
                xc_end = _clean_float(output.get("Xc_final_pct"))
                birth_count = len(output.get("new_peak_birth_temperatures", []) or [])
                triggered = (
                    xc_start is not None
                    and xc_end is not None
                    and xc_end > xc_start + 0.02
                    and birth_count <= 0
                )
                observed = {
                    "Xc_initial_pct": xc_start,
                    "Xc_final_pct": xc_end,
                    "new_peak_birth_temperatures": output.get("new_peak_birth_temperatures", []),
                }
            elif item.name == "amorphous_partition_unstable":
                triggered = x_method in {"peak_area", "no_sharp_peak"} or (
                    x_pct is not None and peak_count is not None and peak_count < 2 and x_pct > 0
                )
                observed = {
                    "Xc_method": output.get("Xc_method"),
                    "amorphous_subtraction": output.get("amorphous_subtraction", config_snapshot.get("amorphous_subtraction")),
                    "amorphous_n_peaks": output.get("amorphous_n_peaks", config_snapshot.get("amorphous_n_peaks")),
                }
            elif item.name == "peak_width_nonphysical":
                invalid_widths = [
                    width
                    for width in peak_widths
                    if width is None or width <= 0 or width > 6.0
                ]
                triggered = bool(invalid_widths)
                observed = {"peak_widths": peak_widths, "invalid_widths": invalid_widths}
            elif item.name == "offset_sensitive_solution":
                triggered = two_theta_offset is not None and abs(two_theta_offset) > 0.05
                observed = {"two_theta_offset": two_theta_offset}
            elif item.name == "crystallinity_without_peak_support":
                triggered = x_pct is not None and x_pct > 0 and peak_count is not None and peak_count < 2
                observed = {
                    "Xc_pct": x_pct,
                    "peak_count": peak_count,
                    "Xc_method": output.get("Xc_method"),
                }
            elif item.name == "size_without_multi_peak_support":
                size = _clean_float(observed)
                triggered = size is not None and size > 0 and peak_count is not None and peak_count < 2
                observed = {"D_Scherrer_nm": size, "peak_count": peak_count}
            elif item.name == "scherrer_trend_without_multi_peak_support":
                triggered = (
                    (d_support_peak_count < 2 and any(_clean_float(value) is not None for value in d_values))
                    or (d_support_family_count < 2 and len(d_values) >= 2)
                    or (d_trend_support_score is not None and d_trend_support_score < 0.60)
                )
                observed = {
                    "D_support_peak_count": d_support_peak_count,
                    "D_support_family_count": d_support_family_count,
                    "D_trend_support_score": d_trend_support_score,
                }
            elif item.name == "scherrer_jump_single_frame":
                triggered = d_jump_count > 0
                observed = {
                    "D_jump_single_frame_count": d_jump_count,
                    "D_jump_single_frame_indices": d_jump_indices,
                }
            elif item.name == "scherrer_dominated_by_peak_width_noise":
                triggered = (
                    (d_trend_support_score is not None and d_trend_support_score < 0.55)
                    or (max_fwhm_drift is not None and max_fwhm_drift > 0.40)
                )
                observed = {
                    "D_trend_support_score": d_trend_support_score,
                    "max_peak_width_drift_deg": max_fwhm_drift,
                    "D_slope_distribution": output.get("D_slope_distribution"),
                }
            elif item.name == "scherrer_instrument_broadening_unresolved":
                triggered = (
                    d_support_peak_count > 0
                    and not instrument_broadening_present
                )
                observed = {
                    "instrument_broadening_present": instrument_broadening_present,
                    "config_snapshot": config_snapshot,
                }
            elif item.name == "scherrer_conflicts_with_peak_family_tracking":
                triggered = (
                    (family_swap_count > 0 or family_fragmented_count > 0 or (family_continuity is not None and family_continuity < 0.65))
                    and (d_support_peak_count > 0 or d_support_family_count > 0)
                )
                observed = {
                    "peak_family_continuity_score": family_continuity,
                    "peak_family_identity_swap_count": family_swap_count,
                    "peak_family_fragmented_count": family_fragmented_count,
                    "D_confidence_by_frame": d_confidence_by_frame[:3],
                }
            elif item.name == "scherrer_unphysical_temperature_trend":
                triggered = (
                    d_monotonicity == "mixed"
                    and (d_trend_support_score is not None and d_trend_support_score < 0.65)
                ) or (
                    d_jump_count >= 2
                )
                observed = {
                    "D_trend_monotonicity": d_monotonicity,
                    "D_values_nm": d_values,
                    "D_jump_single_frame_count": d_jump_count,
                }

        if validation.get("cross_validation") and item.name in {"l_consistency", "multi_scan_consistency", "multi_scan_inconsistent"}:
            observed = validation.get("cross_validation")

        evaluated.append(
            {
                **item.to_dict(),
                "triggered": triggered,
                "observed": observed,
            }
        )

    if is_ir_temperature_2d:
        sequence_ready = bool(ir_2d_metrics.get("sequence_axis_ready"))
        matrix_shapes_consistent = bool(ir_2d_metrics.get("matrix_shapes_consistent"))
        n_frames = _safe_int(ir_2d_metrics.get("n_frames"), 0)
        temperature_missing_count = _safe_int(ir_2d_metrics.get("temperature_missing_count"), 0)
        time_missing_count = _safe_int(ir_2d_metrics.get("time_missing_count"), 0)
        hold_time_missing_count = _safe_int(ir_2d_metrics.get("hold_time_missing_count"), 0)
        hold_time_estimated_count = _safe_int(ir_2d_metrics.get("hold_time_estimated_count"), 0)
        heating_monotonic = bool(ir_2d_metrics.get("heating_monotonic"))
        cooling_monotonic = bool(ir_2d_metrics.get("cooling_monotonic"))
        hold_monotonic = bool(ir_2d_metrics.get("hold_monotonic"))
        sequence_order_source = str(ir_2d_metrics.get("sequence_order_source", "") or "").strip()
        neg_fraction = _clean_float(ir_2d_metrics.get("neg_fraction"))
        nan_fraction = _clean_float(ir_2d_metrics.get("nan_fraction"))
        dynamic_rms = _clean_float(ir_2d_metrics.get("dynamic_rms"))
        dynamic_signal_rms = _clean_float(ir_2d_metrics.get("dynamic_signal_rms", dynamic_rms))
        frame_intensity_scale_spread = _clean_float(ir_2d_metrics.get("frame_intensity_scale_spread"))
        wavenumber_grid_consistent = bool(ir_2d_metrics.get("wavenumber_grid_consistent", True))
        sync_cross_peak_count = _safe_int(ir_2d_metrics.get("sync_cross_peak_count"), 0)
        async_cross_peak_count = _safe_int(ir_2d_metrics.get("async_cross_peak_count"), 0)
        cross_peak_count = _safe_int(ir_2d_metrics.get("cross_peak_count"), 0)
        assigned_cross_peak_count = _safe_int(ir_2d_metrics.get("assigned_cross_peak_count"), 0)
        unassigned_cross_peak_count = _safe_int(ir_2d_metrics.get("unassigned_cross_peak_count"), 0)
        async_with_sync_support_count = _safe_int(ir_2d_metrics.get("async_with_sync_support_count"), 0)
        top_sync_diagonal_distance = _clean_float(ir_2d_metrics.get("top_sync_diagonal_distance_cm1"))
        top_async_diagonal_distance = _clean_float(ir_2d_metrics.get("top_async_diagonal_distance_cm1"))
        top_sync_assigned = bool(ir_2d_metrics.get("top_sync_assigned", False))
        top_async_assigned = bool(ir_2d_metrics.get("top_async_assigned", False))
        top_async_has_sync_support = bool(ir_2d_metrics.get("top_async_has_sync_support", False))
        noda_rule_interpretation_ready = bool(ir_2d_metrics.get("noda_rule_interpretation_ready", False))
        transition_count = _safe_int(ir_2d_metrics.get("transition_count"), 0)

        evaluated.extend(
            [
                {
                    "name": "sequence_axis_incomplete",
                    "kind": "hard_fail",
                    "source": "IR_temperature_2d",
                    "severity": "ERROR",
                    "description": "The 2D IR sequence axis is incomplete, so perturbation ordering is not yet trustworthy.",
                    "field": "n_frames",
                    "rationale": "2D-COS interpretation depends on a stable temperature/time ordering.",
                    "triggered": not sequence_ready,
                    "observed": {
                        "n_frames": n_frames,
                        "stage_counts": ir_2d_metrics.get("stage_counts"),
                        "temperature_missing_count": temperature_missing_count,
                        "time_missing_count": time_missing_count,
                        "heating_monotonic": heating_monotonic,
                        "cooling_monotonic": cooling_monotonic,
                        "hold_monotonic": hold_monotonic,
                        "sequence_order_source": sequence_order_source,
                    },
                },
                {
                    "name": "temperature_axis_missing",
                    "kind": "hard_fail",
                    "source": "IR_temperature_2d",
                    "severity": "ERROR",
                    "description": "The temperature axis is missing or incomplete for this 2D IR sequence.",
                    "field": "temperature_missing_count",
                    "rationale": "A missing temperature axis means the perturbation ordering is not physically anchored.",
                    "triggered": temperature_missing_count > 0,
                    "observed": {
                        "temperature_missing_count": temperature_missing_count,
                        "sequence_order_source": sequence_order_source,
                        "stage_counts": ir_2d_metrics.get("stage_counts"),
                    },
                },
                {
                    "name": "stage_order_ambiguous",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "Heating, hold, and cooling are not in a clean monotonic order.",
                    "field": "stage_counts",
                    "rationale": "Mixed perturbation direction weakens any synchronous/asynchronous ordering claim.",
                    "triggered": not (heating_monotonic and cooling_monotonic and hold_monotonic),
                    "observed": {
                        "heating_monotonic": heating_monotonic,
                        "cooling_monotonic": cooling_monotonic,
                        "hold_monotonic": hold_monotonic,
                        "sequence_order_source": sequence_order_source,
                    },
                },
                {
                    "name": "hold_time_missing_or_estimated",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "Hold-segment timing is missing or only estimated.",
                    "field": "time_missing_count",
                    "rationale": "Uncertain hold timing weakens any plateau or transition interpretation.",
                    "triggered": hold_time_missing_count > 0 or hold_time_estimated_count > 0,
                    "observed": {
                        "time_missing_count": time_missing_count,
                        "hold_time_missing_count": hold_time_missing_count,
                        "hold_time_estimated_count": hold_time_estimated_count,
                    },
                },
                {
                    "name": "insufficient_perturbation_frames",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "There are not enough perturbation frames for stable 2D-COS interpretation.",
                    "field": "n_frames",
                    "rationale": "Too few frames can produce attractive maps with weak physical support.",
                    "triggered": n_frames < 5,
                    "observed": {
                        "n_frames": n_frames,
                        "stage_counts": ir_2d_metrics.get("stage_counts"),
                    },
                },
                {
                    "name": "matrix_shape_inconsistent",
                    "kind": "hard_fail",
                    "source": "IR_temperature_2d",
                    "severity": "ERROR",
                    "description": "The 2D IR matrix and correlation shapes are inconsistent.",
                    "field": "matrix_shape",
                    "rationale": "The dynamic matrix and sync/async maps must agree before interpretation.",
                    "triggered": not matrix_shapes_consistent,
                    "observed": {
                        "matrix_shape": ir_2d_metrics.get("matrix_shape"),
                        "dynamic_shape": ir_2d_metrics.get("dynamic_shape"),
                        "sync_shape": ir_2d_metrics.get("sync_shape"),
                        "async_shape": ir_2d_metrics.get("async_shape"),
                    },
                },
                {
                    "name": "negative_matrix_fraction_high",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "The absorbance matrix contains a high fraction of non-positive values.",
                    "field": "neg_fraction",
                    "rationale": "High negativity often means baseline over-subtraction or clipping.",
                    "triggered": neg_fraction is not None and neg_fraction > 0.30,
                    "observed": {
                        "neg_fraction": neg_fraction,
                        "nan_fraction": nan_fraction,
                        "dynamic_rms": dynamic_rms,
                    },
                },
                {
                    "name": "matrix_nan_fraction_high",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "The absorbance matrix still contains too many NaN values.",
                    "field": "nan_fraction",
                    "rationale": "Matrix holes make 2D-COS peaks unstable and harder to trust.",
                    "triggered": nan_fraction is not None and nan_fraction > 0.01,
                    "observed": {
                        "nan_fraction": nan_fraction,
                        "wavenumber_grid_consistent": wavenumber_grid_consistent,
                    },
                },
                {
                    "name": "wavenumber_grid_inconsistent",
                    "kind": "hard_fail",
                    "source": "IR_temperature_2d",
                    "severity": "ERROR",
                    "description": "The per-frame wavenumber grids are not aligned to a shared matrix axis.",
                    "field": "wavenumber_grid_consistent",
                    "rationale": "Cross-peaks cannot be trusted when frame grids do not align.",
                    "triggered": not wavenumber_grid_consistent,
                    "observed": {
                        "wavenumber_grid_consistent": wavenumber_grid_consistent,
                        "matrix_shape": ir_2d_metrics.get("matrix_shape"),
                    },
                },
                {
                    "name": "frame_intensity_scale_unstable",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "Frame-to-frame intensity scaling is drifting too much.",
                    "field": "frame_intensity_scale_spread",
                    "rationale": "Large frame-scale drift often means baseline or normalization artifacts dominate the trend.",
                    "triggered": frame_intensity_scale_spread is not None and frame_intensity_scale_spread > 0.85,
                    "observed": {
                        "frame_intensity_scale_spread": frame_intensity_scale_spread,
                        "dynamic_rms": dynamic_signal_rms,
                    },
                },
                {
                    "name": "dynamic_signal_too_weak",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "The dynamic signal is too weak to support a robust 2D-COS interpretation.",
                    "field": "dynamic_signal_rms",
                    "rationale": "When the dynamic signal is tiny, cross-peaks may mainly reflect amplified noise.",
                    "triggered": dynamic_signal_rms is not None and dynamic_signal_rms < 0.005,
                    "observed": {
                        "dynamic_signal_rms": dynamic_signal_rms,
                        "sync_cross_peak_count": sync_cross_peak_count,
                        "async_cross_peak_count": async_cross_peak_count,
                    },
                },
                {
                    "name": "weak_cos_signal",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "2D-COS signal is too weak for stable synchronous/asynchronous interpretation.",
                    "field": "sync_cross_peak_count",
                    "rationale": "A visible sync/async signal is required before promoting transition claims.",
                    "triggered": (
                        sync_cross_peak_count <= 0
                        or async_cross_peak_count <= 0
                        or (dynamic_signal_rms is not None and dynamic_signal_rms < 0.005)
                    ),
                    "observed": {
                        "sync_cross_peak_count": sync_cross_peak_count,
                        "async_cross_peak_count": async_cross_peak_count,
                        "dynamic_rms": dynamic_signal_rms,
                    },
                },
                {
                    "name": "cross_peak_near_diagonal",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "The strongest 2D-COS cross peak sits too close to the diagonal.",
                    "field": "top_async_diagonal_distance_cm1",
                    "rationale": "A near-diagonal cross peak is often not distinct enough for a stable interpretation.",
                    "triggered": (
                        (top_sync_diagonal_distance is not None and top_sync_diagonal_distance < 45.0)
                        or (top_async_diagonal_distance is not None and top_async_diagonal_distance < 45.0)
                    ),
                    "observed": {
                        "top_sync_diagonal_distance_cm1": top_sync_diagonal_distance,
                        "top_async_diagonal_distance_cm1": top_async_diagonal_distance,
                    },
                },
                {
                    "name": "cross_peak_without_band_assignment",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "The leading cross peaks are not assigned cleanly to reference bands.",
                    "field": "assigned_cross_peak_count",
                    "rationale": "Unassigned peaks can be useful for diagnosis, but they should not carry the final mechanistic story.",
                    "triggered": (
                        cross_peak_count > 0
                        and (assigned_cross_peak_count <= 0 or unassigned_cross_peak_count >= assigned_cross_peak_count)
                    ),
                    "observed": {
                        "cross_peak_count": cross_peak_count,
                        "assigned_cross_peak_count": assigned_cross_peak_count,
                        "unassigned_cross_peak_count": unassigned_cross_peak_count,
                        "top_sync_assigned": top_sync_assigned,
                        "top_async_assigned": top_async_assigned,
                    },
                },
                {
                    "name": "async_peak_without_sync_support",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "The asynchronous peak is not backed by enough synchronous support.",
                    "field": "async_with_sync_support_count",
                    "rationale": "Async peaks are weaker evidence when they are not paired with a stable synchronous relationship.",
                    "triggered": async_cross_peak_count > 0 and (async_with_sync_support_count <= 0 or not top_async_has_sync_support),
                    "observed": {
                        "async_cross_peak_count": async_cross_peak_count,
                        "async_with_sync_support_count": async_with_sync_support_count,
                        "top_async_has_sync_support": top_async_has_sync_support,
                    },
                },
                {
                    "name": "noda_rule_not_applicable",
                    "kind": "soft_warn",
                    "source": "IR_temperature_2d",
                    "severity": "WARN",
                    "description": "Noda-rule interpretation is not yet supported by the current evidence chain.",
                    "field": "noda_rule_interpretation_ready",
                    "rationale": "Do not promote sequence-order claims until sync/async support and band assignment both hold.",
                    "triggered": async_cross_peak_count > 0 and not noda_rule_interpretation_ready,
                    "observed": {
                        "noda_rule_interpretation_ready": noda_rule_interpretation_ready,
                        "assigned_cross_peak_count": assigned_cross_peak_count,
                        "top_async_has_sync_support": top_async_has_sync_support,
                    },
                },
                {
                    "name": "transition_candidate_present",
                    "kind": "evidence_only",
                    "source": "IR_temperature_2d",
                    "severity": "INFO",
                    "description": "A temperature-dependent transition candidate is present in the tracked bands.",
                    "field": "transition_count",
                    "rationale": "Treat this as evidence only until the matrix quality is stable.",
                    "triggered": transition_count > 0,
                    "observed": {
                        "transition_count": transition_count,
                        "transition_temperatures_C": ir_2d_metrics.get("transition_temperatures_C"),
                    },
                },
            ]
        )

    return evaluated


def summarize_constraints(constraints: list[dict[str, Any]] | None) -> dict[str, Any]:
    items = constraints if isinstance(constraints, list) else []
    inventory = {"hard_fail": 0, "soft_warn": 0, "evidence_only": 0}
    triggered_by_kind = {"hard_fail": [], "soft_warn": [], "evidence_only": []}

    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "") or "").strip()
        if kind not in inventory:
            continue
        inventory[kind] += 1
        if item.get("triggered"):
            name = str(item.get("name", "") or "").strip()
            if name:
                triggered_by_kind[kind].append(name)

    status = "ok"
    if triggered_by_kind["hard_fail"]:
        status = "hard_fail"
    elif triggered_by_kind["soft_warn"]:
        status = "soft_warn"
    elif triggered_by_kind["evidence_only"]:
        status = "evidence_only"

    triggered_counts = {
        kind: len(names)
        for kind, names in triggered_by_kind.items()
    }

    return {
        "status": status,
        "inventory": inventory,
        "triggered_total": sum(triggered_counts.values()),
        "triggered_counts": triggered_counts,
        "triggered_names": triggered_by_kind,
    }


def build_analysis_evidence(
    technique: str,
    output_parameters: dict[str, Any] | None = None,
    residual_pattern: dict[str, Any] | None = None,
    validation_context: dict[str, Any] | None = None,
) -> AnalysisEvidence:
    output = dict(output_parameters or {})
    residual = dict(residual_pattern or {})
    validation = dict(validation_context or {})
    technique_key = str(technique or "").upper()
    is_ir_temperature_2d = technique_key == "IR" and _is_ir_temperature_2d(output, validation)

    fit_evidence: dict[str, Any] = {}
    physical_evidence: dict[str, Any] = {}
    residual_evidence: dict[str, Any] = {}
    feature_evidence: dict[str, Any] = {}
    signal_evidence: dict[str, Any] = {}
    peak_evidence: dict[str, Any] = {}
    assignment_evidence: dict[str, Any] = {}
    reference_evidence: dict[str, Any] = {}
    background_evidence: dict[str, Any] = {}
    phase_evidence: dict[str, Any] = {}
    transform_evidence: dict[str, Any] = {}
    structure_evidence: dict[str, Any] = {}
    raw_structure_evidence: dict[str, Any] = {}
    batch_evidence: dict[str, Any] = {}
    condition_evidence: dict[str, Any] = {}
    stability_evidence: dict[str, Any] = {}
    symptoms: list[dict[str, Any]] = []
    risk_flags: list[str] = []
    confidence_signals: list[dict[str, Any]] = []
    actionable_symptoms: list[str] = []

    r_squared = _clean_float(output.get("r_squared"))
    quality_score = _clean_float(output.get("quality_score"))
    fit_rmse = _clean_float(output.get("fit_rmse"))
    quality_flag = str(output.get("quality_flag", "") or "").strip()
    validation_summary = str(output.get("validation_summary", "") or "").strip()
    residual_type = str(residual.get("residual_type", "") or "").strip()
    residual_summary = str(residual.get("summary", "") or "").strip()

    if r_squared is not None:
        fit_evidence["r_squared"] = r_squared
    if quality_score is not None:
        fit_evidence["quality_score"] = quality_score
    if fit_rmse is not None:
        fit_evidence["fit_rmse"] = fit_rmse
    if quality_flag:
        physical_evidence["quality_flag"] = quality_flag
        if quality_flag != "OK":
            risk_flags.append(quality_flag)
    if validation_summary:
        physical_evidence["validation_summary"] = validation_summary

    residual_evidence.update(
        {
            "residual_type": residual_type or "unknown",
            "summary": residual_summary,
            "max_residual_region": residual.get("max_residual_region", "unknown"),
            "rmse": _clean_float(residual.get("rmse")),
            "r_squared": _clean_float(residual.get("r_squared")),
            "peak_regions": residual.get("peak_regions", []),
        }
    )

    if technique_key in {"WAXS", "SAXS"}:
        for key in (
            "L_bragg",
            "L_lorentz",
            "L_corr_peak",
            "L_nm",
            "L_best",
            "L_confidence",
            "q_peak_snr",
            "Q_star",
            "Q_star_rel",
            "Q_star_valid",
            "has_voids",
            "phi_void",
            "void_AR",
            "f_Herman",
            "f_herman",
            "porod_slope",
        ):
            if key in output:
                physical_evidence[key] = output.get(key)
        for key in ("beam_stop_contaminated", "mask_truncated", "condition_value", "condition_label", "temperature_C", "strain_pct"):
            if key in output:
                physical_evidence[key] = output.get(key)
        if output.get("fit_regions") is not None:
            feature_evidence["fit_regions"] = output.get("fit_regions", [])
        if output.get("quality_score") is not None:
            confidence_signals.append({"name": "quality_score", "value": quality_score, "source": technique_key})
        if output.get("q_peak_snr") is not None:
            confidence_signals.append({"name": "q_peak_snr", "value": _clean_float(output.get("q_peak_snr")), "source": technique_key})
        if output.get("L_confidence") is not None:
            confidence_signals.append({"name": "L_confidence", "value": _clean_float(output.get("L_confidence")), "source": technique_key})
        if output.get("pyfai_q_peak_diff_pct") is not None:
            confidence_signals.append({"name": "pyfai_q_peak_diff_pct", "value": _clean_float(output.get("pyfai_q_peak_diff_pct")), "source": "cross_validation"})

    if technique_key == "SAXS":
        signal_evidence = _non_empty_mapping(
            [
                ("q_peak_snr", _clean_float(output.get("q_peak_snr"))),
                ("Q_star", _clean_float(output.get("Q_star"))),
                ("Q_star_valid", output.get("Q_star_valid")),
                ("beam_stop_contaminated", output.get("beam_stop_contaminated")),
                ("mask_truncated", output.get("mask_truncated")),
                ("quality_flag", quality_flag or None),
                ("validation_summary", validation_summary or None),
            ]
        )

        peak_evidence = _non_empty_mapping(
            [
                ("L_bragg", _clean_float(output.get("L_bragg"))),
                ("L_lorentz", _clean_float(output.get("L_lorentz"))),
                ("L_pyfai_nm", _clean_float(output.get("L_pyfai_nm"))),
                ("q_peak_diff_pct", _clean_float(output.get("q_peak_diff_pct"))),
                ("fit_regions", output.get("fit_regions") if isinstance(output.get("fit_regions"), list) else None),
            ]
        )

        transform_evidence = _non_empty_mapping(
            [
                ("L_corr_peak", _clean_float(output.get("L_corr_peak", output.get("L_corr")))),
                ("lc_tangent_nm", _clean_float(output.get("lc_tangent_nm"))),
                ("lc_gamma_min_nm", _clean_float(output.get("lc_gamma_min_nm"))),
                ("lc_idf_nm", _clean_float(output.get("lc_idf_nm"))),
                ("phi_c_invariant", _clean_float(output.get("phi_c_invariant"))),
            ]
        )

        structure_evidence = _non_empty_mapping(
            [
                ("L_nm", _clean_float(output.get("L_nm", output.get("L_best")))),
                ("L_best", _clean_float(output.get("L_best", output.get("L_nm")))),
                ("L_confidence", _clean_float(output.get("L_confidence"))),
                ("lc_nm", _clean_float(output.get("lc_nm"))),
                ("la_nm", _clean_float(output.get("la_nm"))),
                ("phi_c", _clean_float(output.get("phi_c"))),
                ("lc_confidence", _clean_float(output.get("lc_confidence"))),
                ("lc_nm_raw", _clean_float(output.get("lc_nm_raw"))),
                ("la_nm_raw", _clean_float(output.get("la_nm_raw"))),
                ("Xc_raw", _clean_float(output.get("Xc_raw"))),
                ("Q_star_abs", _clean_float(output.get("Q_star_abs", output.get("Q_star")))),
                ("Q_star_rel", _clean_float(output.get("Q_star_rel", output.get("Q_rel")))),
                ("Q_star_rel_mean", _clean_float(output.get("Q_star_rel_mean"))),
                ("Q_star_rel_span", _clean_float(output.get("Q_star_rel_span"))),
                ("has_voids", output.get("has_voids")),
                ("phi_void", _clean_float(output.get("phi_void"))),
                ("phi_void_mean", _clean_float(output.get("phi_void_mean"))),
                ("phi_void_span", _clean_float(output.get("phi_void_span"))),
                ("void_detected_frames", _safe_int(output.get("void_detected_frames"), default=0) if output.get("void_detected_frames") is not None else None),
                ("void_AR", _clean_float(output.get("void_AR"))),
                ("f_Herman", _clean_float(output.get("f_Herman", output.get("f_herman")))),
                ("f_Herman_mean", _clean_float(output.get("f_Herman_mean"))),
                ("f_Herman_span", _clean_float(output.get("f_Herman_span"))),
                ("porod_slope", _clean_float(output.get("porod_slope"))),
                ("porod_slope_mean", _clean_float(output.get("porod_slope_mean"))),
                ("porod_slope_span", _clean_float(output.get("porod_slope_span"))),
                ("lc_nm_effective", _clean_float(output.get("lc_nm_effective"))),
                ("la_nm_effective", _clean_float(output.get("la_nm_effective"))),
                ("Xc_effective", _clean_float(output.get("Xc_effective"))),
                ("lamellar_interpretation_mode", str(output.get("lamellar_interpretation_mode", "") or "").strip() or None),
                ("effective_param_reason", str(output.get("effective_param_reason", "") or "").strip() or None),
                ("melting_window_status", str(output.get("melting_window_status", "") or "").strip() or None),
                ("melting_window_reason", str(output.get("melting_window_reason", "") or "").strip() or None),
                ("lc_reliability_status", str(output.get("lc_reliability_status", "") or "").strip() or None),
                ("lc_reliability_reason", str(output.get("lc_reliability_reason", "") or "").strip() or None),
                ("lc_nm_calibrated", _clean_float(output.get("lc_nm_calibrated"))),
                ("la_nm_calibrated", _clean_float(output.get("la_nm_calibrated"))),
                ("Xc_calibrated", _clean_float(output.get("Xc_calibrated"))),
                ("lc_confidence_calibrated", _clean_float(output.get("lc_confidence_calibrated"))),
                ("lc_method", str(output.get("lc_method", "") or "").strip() or None),
                ("calibrated_fallback_active", output.get("calibrated_fallback_active")),
                ("calibrated_fallback_reason", str(output.get("calibrated_fallback_reason", "") or "").strip() or None),
                ("calibration_skipped_reason", str(output.get("calibration_skipped_reason", "") or "").strip() or None),
                ("fallback_applied_fields", output.get("fallback_applied_fields") if isinstance(output.get("fallback_applied_fields"), list) else None),
                ("sasmodels_R2", _clean_float(output.get("sasmodels_R2"))),
                ("sasmodels_model_used", str(output.get("sasmodels_model_used", "") or "").strip() or None),
            ]
        )

        raw_snapshot = output.get("raw_snapshot")
        if isinstance(raw_snapshot, dict) and raw_snapshot:
            raw_long_period = _extract_nested_mapping(raw_snapshot, "long_period")
            raw_structure = _extract_nested_mapping(raw_snapshot, "structure")
            raw_structure_evidence = _non_empty_mapping(
                [
                    ("L_nm_raw", _clean_float(raw_structure.get("L"))),
                    ("lc_nm_raw", _clean_float(raw_structure.get("lc"))),
                    ("la_nm_raw", _clean_float(raw_structure.get("la"))),
                    ("Xc_raw", _clean_float(raw_structure.get("phi_c"))),
                    ("lc_confidence_raw", _clean_float(raw_structure.get("confidence_lc"))),
                    ("Q_star_raw", _clean_float(raw_structure.get("Q_invariant"))),
                    ("L_best_raw", _clean_float(raw_long_period.get("L_best"))),
                    ("raw_structure_available", True),
                ]
            )
            if raw_structure_evidence:
                feature_evidence["raw_structure_evidence"] = raw_structure_evidence

        batch_rows = output.get("_batch_data")
        if isinstance(batch_rows, list) and batch_rows:
            batch_evidence = _non_empty_mapping(
                [
                    ("batch_frames", int(output.get("batch_frames")) if output.get("batch_frames") is not None else None),
                    ("condition_label", str(output.get("condition_label", "") or "").strip() or None),
                    ("condition_range", str(output.get("condition_range", "") or "").strip() or None),
                    ("batch_calibration_summary", output.get("batch_calibration_summary") if isinstance(output.get("batch_calibration_summary"), dict) else None),
                    ("batch_structure_summary", output.get("batch_structure_summary") if isinstance(output.get("batch_structure_summary"), dict) else None),
                    ("sample_files", [str(row.get("file")) for row in batch_rows[:6] if isinstance(row, dict) and str(row.get("file", "")).strip()]),
                    (
                        "frame_condition_values",
                        [
                            {
                                "file": str(row.get("file", "") or "").strip(),
                                "condition_value": _clean_float(row.get("condition_value")),
                                "temperature_C": _clean_float(row.get("temperature_C")),
                                "strain_pct": _clean_float(row.get("strain_pct")),
                                "melting_window_status": str(row.get("melting_window_status", "") or "").strip() or None,
                                "lc_reliability_status": str(row.get("lc_reliability_status", "") or "").strip() or None,
                            }
                            for row in batch_rows[:8]
                            if isinstance(row, dict)
                        ],
                    ),
                ]
            )

        condition_label = str(output.get("condition_label", "") or "").strip()
        condition_value = _clean_float(output.get("condition_value"))
        temperature_c = _clean_float(output.get("temperature_C"))
        strain_pct = _clean_float(output.get("strain_pct"))
        condition_source = str(output.get("condition_source", "") or "").strip()
        condition_source_key = str(output.get("condition_source_key", "") or "").strip()
        condition_source_text = str(output.get("condition_source_text", "") or "").strip()
        condition_confidence = _clean_float(output.get("condition_confidence"))
        condition_missing_frames = output.get("condition_missing_frames")
        condition_continuity_score = _clean_float(output.get("condition_continuity_score"))
        if (
            condition_label
            or condition_value is not None
            or temperature_c is not None
            or strain_pct is not None
            or condition_source
            or condition_source_key
            or condition_source_text
            or condition_confidence is not None
            or condition_missing_frames not in (None, [], {})
            or condition_continuity_score is not None
        ):
            condition_evidence = _non_empty_mapping(
                [
                    ("condition_label", condition_label or None),
                    ("condition_value", condition_value),
                    ("temperature_C", temperature_c),
                    ("strain_pct", strain_pct),
                    ("condition_source", condition_source or None),
                    ("condition_source_key", condition_source_key or None),
                    ("condition_source_text", condition_source_text or None),
                    ("condition_confidence", condition_confidence),
                    ("condition_missing_frames", condition_missing_frames),
                    ("condition_continuity_score", condition_continuity_score),
                ]
            )

            strain_values = _condition_values(output, batch_rows if isinstance(batch_rows, list) else [], "strain")
            if strain_values or condition_label.lower() == "strain" or strain_pct is not None:
                strain_missing_count = output.get("strain_missing_count")
                if strain_missing_count is None and isinstance(batch_rows, list):
                    strain_missing_count = sum(
                        1
                        for row in batch_rows
                        if isinstance(row, dict)
                        and _clean_float(row.get("strain_pct")) is None
                        and _clean_float(row.get("condition_value")) is None
                    )
                strain_duplicate_count = output.get("strain_duplicate_count")
                if strain_duplicate_count is None and strain_values:
                    strain_duplicate_count = max(0, len(strain_values) - len({str(value) for value in strain_values}))
                strain_axis_confidence = _clean_float(output.get("strain_axis_confidence", output.get("condition_confidence")))
                if strain_axis_confidence is None:
                    strain_axis_confidence = condition_confidence

                if strain_values:
                    strain_array = np.asarray(strain_values, dtype=float)
                    strain_min = float(np.min(strain_array))
                    strain_max = float(np.max(strain_array))
                    if strain_array.size >= 2:
                        diffs = np.diff(strain_array)
                        increasing = bool(np.all(diffs >= 0))
                        decreasing = bool(np.all(diffs <= 0))
                        if increasing:
                            sequence_direction = "increasing"
                        elif decreasing:
                            sequence_direction = "decreasing"
                        else:
                            sequence_direction = "mixed"
                        strain_step_median = float(np.median(diffs))
                        strain_step_spread = _relative_spread(diffs.tolist()) if diffs.size >= 2 else None
                    else:
                        sequence_direction = "unknown"
                        strain_step_median = None
                        strain_step_spread = None
                    strain_monotonic = sequence_direction in {"increasing", "decreasing"}
                else:
                    strain_min = strain_max = None
                    strain_step_median = None
                    strain_step_spread = None
                    sequence_direction = str(output.get("sequence_direction", "") or "").strip().lower() or "unknown"
                    strain_monotonic = bool(output.get("strain_monotonic", False))

                strain_axis_evidence = _non_empty_mapping(
                    [
                        ("condition_label", condition_label or None),
                        ("condition_unit", str(output.get("condition_unit", "") or "").strip() or None),
                        ("condition_source", condition_source or None),
                        ("condition_source_key", condition_source_key or None),
                        ("condition_source_text", condition_source_text or None),
                        ("condition_confidence", condition_confidence),
                        ("condition_missing_frames", condition_missing_frames),
                        ("condition_continuity_score", condition_continuity_score),
                        ("strain_values", strain_values if strain_values else None),
                        ("strain_min_pct", strain_min),
                        ("strain_max_pct", strain_max),
                        ("strain_missing_count", _clean_float(strain_missing_count)),
                        ("strain_duplicate_count", _clean_float(strain_duplicate_count)),
                        ("strain_monotonic", strain_monotonic),
                        ("strain_step_median_pct", strain_step_median),
                        ("strain_step_spread", strain_step_spread),
                        ("sequence_order_source", str(output.get("sequence_order_source", "") or "").strip() or None),
                        ("sequence_direction", sequence_direction),
                        ("strain_axis_confidence", strain_axis_confidence),
                    ]
                )
                if strain_axis_evidence:
                    feature_evidence["sequence_evidence"] = strain_axis_evidence
                    feature_evidence["condition_evidence"] = strain_axis_evidence
                    condition_evidence = strain_axis_evidence
                    confidence_signals.append(
                        {
                            "name": "strain_axis_confidence",
                            "value": strain_axis_confidence,
                            "source": "SAXS_strain",
                        }
                    )

        if condition_label.lower() == "strain":
            strain_structure_evidence = _non_empty_mapping(
                [
                    ("Q_star_rel", _clean_float(output.get("Q_star_rel", output.get("Q_rel")))),
                    ("Q_star_rel_mean", _clean_float(output.get("Q_star_rel_mean"))),
                    ("Q_star_rel_span", _clean_float(output.get("Q_star_rel_span"))),
                    ("has_voids", output.get("has_voids")),
                    ("void_detected_frames", _safe_int(output.get("void_detected_frames"), default=0) if output.get("void_detected_frames") is not None else None),
                    ("phi_void", _clean_float(output.get("phi_void"))),
                    ("phi_void_mean", _clean_float(output.get("phi_void_mean"))),
                    ("phi_void_span", _clean_float(output.get("phi_void_span"))),
                    ("void_AR", _clean_float(output.get("void_AR"))),
                    ("f_Herman", _clean_float(output.get("f_Herman", output.get("f_herman")))),
                    ("f_Herman_mean", _clean_float(output.get("f_Herman_mean"))),
                    ("f_Herman_span", _clean_float(output.get("f_Herman_span"))),
                    ("porod_slope", _clean_float(output.get("porod_slope"))),
                    ("porod_slope_mean", _clean_float(output.get("porod_slope_mean"))),
                    ("porod_slope_span", _clean_float(output.get("porod_slope_span"))),
                ]
            )
            if strain_structure_evidence:
                feature_evidence["strain_structure_evidence"] = strain_structure_evidence

            phase_distribution = output.get("phase_distribution")
            phase_boundary_candidates = output.get("phase_boundary_candidates")
            phase_evidence = _non_empty_mapping(
                [
                    ("dominant_phase", str(output.get("dominant_phase", "") or "").strip() or None),
                    ("phase_distribution", phase_distribution if isinstance(phase_distribution, dict) and phase_distribution else None),
                    ("phase_boundary_candidates", phase_boundary_candidates if isinstance(phase_boundary_candidates, list) and phase_boundary_candidates else None),
                    ("phase_support_mean", _clean_float(output.get("phase_support_mean"))),
                    ("phase_support_span", _clean_float(output.get("phase_support_span"))),
                    ("phase_ambiguous_frame_count", _safe_int(output.get("phase_ambiguous_frame_count"), default=0) if output.get("phase_ambiguous_frame_count") is not None else None),
                    ("frame_low_conf_count", _safe_int(output.get("frame_low_conf_count"), default=0) if output.get("frame_low_conf_count") is not None else None),
                    ("void_dominant_frame_count", _safe_int(output.get("void_dominant_frame_count"), default=0) if output.get("void_dominant_frame_count") is not None else None),
                    ("effective_param_ratio", _clean_float(output.get("effective_param_ratio"))),
                    ("strain_reliability_status", str(output.get("strain_reliability_status", "") or "").strip() or None),
                    ("strain_reliability_reason", str(output.get("strain_reliability_reason", "") or "").strip() or None),
                    ("paper_figure_candidate", output.get("paper_figure_candidate")),
                    ("paper_conclusion_candidate", output.get("paper_conclusion_candidate")),
                    ("paper_conclusion_ready", output.get("paper_conclusion_ready")),
                ]
            )
            if phase_evidence:
                feature_evidence["phase_evidence"] = phase_evidence
                feature_evidence["strain_phase_evidence"] = phase_evidence
                if isinstance(strain_structure_evidence, dict):
                    strain_structure_evidence = dict(strain_structure_evidence)
                    strain_structure_evidence["dominant_phase"] = str(output.get("dominant_phase", "") or "").strip() or None
                    strain_structure_evidence["phase_support_mean"] = _clean_float(output.get("phase_support_mean"))
                    strain_structure_evidence["phase_support_span"] = _clean_float(output.get("phase_support_span"))
                    strain_structure_evidence["phase_ambiguous_frame_count"] = _safe_int(output.get("phase_ambiguous_frame_count"), default=0) if output.get("phase_ambiguous_frame_count") is not None else None
                    strain_structure_evidence["frame_low_conf_count"] = _safe_int(output.get("frame_low_conf_count"), default=0) if output.get("frame_low_conf_count") is not None else None
                    strain_structure_evidence["void_dominant_frame_count"] = _safe_int(output.get("void_dominant_frame_count"), default=0) if output.get("void_dominant_frame_count") is not None else None
                    strain_structure_evidence["effective_param_ratio"] = _clean_float(output.get("effective_param_ratio"))
                    strain_structure_evidence["strain_reliability_status"] = str(output.get("strain_reliability_status", "") or "").strip() or None
                    strain_structure_evidence["strain_reliability_reason"] = str(output.get("strain_reliability_reason", "") or "").strip() or None
                    strain_structure_evidence["paper_figure_candidate"] = output.get("paper_figure_candidate")
                    strain_structure_evidence["paper_conclusion_candidate"] = output.get("paper_conclusion_candidate")
                    strain_structure_evidence["paper_conclusion_ready"] = output.get("paper_conclusion_ready")
                    feature_evidence["strain_structure_evidence"] = strain_structure_evidence
                    if isinstance(structure_evidence, dict):
                        structure_evidence = dict(structure_evidence)
                        structure_evidence["dominant_phase"] = strain_structure_evidence.get("dominant_phase")
                        structure_evidence["phase_support_mean"] = strain_structure_evidence.get("phase_support_mean")
                        structure_evidence["phase_support_span"] = strain_structure_evidence.get("phase_support_span")
                        structure_evidence["phase_ambiguous_frame_count"] = strain_structure_evidence.get("phase_ambiguous_frame_count")
                        structure_evidence["frame_low_conf_count"] = strain_structure_evidence.get("frame_low_conf_count")
                        structure_evidence["void_dominant_frame_count"] = strain_structure_evidence.get("void_dominant_frame_count")
                        structure_evidence["effective_param_ratio"] = strain_structure_evidence.get("effective_param_ratio")
                        structure_evidence["strain_reliability_status"] = strain_structure_evidence.get("strain_reliability_status")
                        structure_evidence["strain_reliability_reason"] = strain_structure_evidence.get("strain_reliability_reason")
                        structure_evidence["paper_figure_candidate"] = strain_structure_evidence.get("paper_figure_candidate")
                        structure_evidence["paper_conclusion_candidate"] = strain_structure_evidence.get("paper_conclusion_candidate")
                        structure_evidence["paper_conclusion_ready"] = strain_structure_evidence.get("paper_conclusion_ready")
                        feature_evidence["structure_evidence"] = structure_evidence

        if signal_evidence:
            feature_evidence.setdefault("signal_evidence", signal_evidence)
        if peak_evidence:
            feature_evidence.setdefault("peak_evidence", peak_evidence)
        if transform_evidence:
            feature_evidence.setdefault("transform_evidence", transform_evidence)
        if structure_evidence:
            feature_evidence.setdefault("structure_evidence", structure_evidence)
        if raw_structure_evidence:
            feature_evidence.setdefault("raw_structure_evidence", raw_structure_evidence)
        if batch_evidence:
            feature_evidence.setdefault("batch_evidence", batch_evidence)
        if condition_evidence:
            feature_evidence.setdefault("condition_evidence", condition_evidence)

    if technique_key == "DSC":
        config_snapshot = validation.get("config_snapshot", {}) if isinstance(validation.get("config_snapshot", {}), dict) else {}
        peak_components = _dsc_peak_component_rows(output.get("peak_components"))
        scan_rows = _dsc_scan_rows(output.get("scan_r_squared"))
        scan_mode = str(output.get("scan_mode", output.get("technique", "")) or "").strip().lower()
        baseline_corr = str(output.get("baseline_corr", config_snapshot.get("baseline_corr", "")) or "").strip() or None
        exo_up = config_snapshot.get("exo_up", output.get("exo_up"))
        tg_method = str(output.get("Tg_method", config_snapshot.get("Tg_method", "")) or "").strip() or None
        tg_low = _clean_float(output.get("Tg_search_low_C", config_snapshot.get("Tg_search_low_C")))
        tg_high = _clean_float(output.get("Tg_search_high_C", config_snapshot.get("Tg_search_high_C")))
        tm_low = _clean_float(output.get("Tm_search_low_C", config_snapshot.get("Tm_search_low_C")))
        tm_high = _clean_float(output.get("Tm_search_high_C", config_snapshot.get("Tm_search_high_C")))
        tc_low = _clean_float(output.get("Tc_search_low_C", config_snapshot.get("Tc_search_low_C")))
        tc_high = _clean_float(output.get("Tc_search_high_C", config_snapshot.get("Tc_search_high_C")))
        peak_function = str(output.get("peak_function", config_snapshot.get("peak_function", "")) or "").strip() or None
        peak_prominence_ratio = _clean_float(output.get("peak_prominence_ratio", config_snapshot.get("peak_prominence_ratio")))
        min_event_enthalpy = _clean_float(output.get("min_event_enthalpy_Jg", config_snapshot.get("min_event_enthalpy_Jg")))
        max_melting_peak_width = _clean_float(output.get("max_melting_peak_width_C", config_snapshot.get("max_melting_peak_width_C")))
        dhm0 = _clean_float(output.get("DHm0_Jg", config_snapshot.get("user_DHm0", config_snapshot.get("crystallinity_std"))))
        dhm0_source = str(output.get("DHm0_source") or config_snapshot.get("DHm0_source") or "").strip() or None
        baseline_sensitivity = _clean_float(output.get("baseline_sensitivity_pct"))
        boundary_sensitivity = _clean_float(output.get("integration_boundary_sensitivity_pct"))
        dhm_mean = _clean_float(output.get("DHm_Jg_mean"))
        dhm_std = _clean_float(output.get("DHm_Jg_std"))
        dhcc_mean = _clean_float(output.get("DHcc_Jg_mean"))
        dhcc_std = _clean_float(output.get("DHcc_Jg_std"))
        xc_mean = _clean_float(output.get("Xc_pct_mean"))
        xc_std = _clean_float(output.get("Xc_pct_std"))
        xc_ci95 = _clean_float(output.get("Xc_pct_ci95"))
        baseline_variant_count = _safe_int(output.get("baseline_variant_count"), default=0)
        integration_variant_count = _safe_int(output.get("integration_variant_count"), default=0)
        xc_reliability_status = "usable"
        if (baseline_sensitivity is not None and baseline_sensitivity >= 10.0) or (
            boundary_sensitivity is not None and boundary_sensitivity >= 8.0
        ) or (
            xc_ci95 is not None and xc_ci95 >= 8.0
        ):
            xc_reliability_status = "low_confidence"
        if baseline_variant_count == 1 or integration_variant_count == 1:
            xc_reliability_status = "low_confidence"
        if dhm0 is None or dhm0_source == "missing":
            xc_reliability_status = "diagnostic_only"
        supported_components = [
            row for row in peak_components
            if _clean_float(row.get("peak_C")) is not None
            and _clean_float(row.get("enthalpy_Jg")) is not None
            and abs(_clean_float(row.get("enthalpy_Jg")) or 0.0) >= max(0.0, float(min_event_enthalpy or 0.0))
        ]
        supported_melting_components = [row for row in supported_components if str(row.get("type", "") or "").strip().lower() in {"melting", "deconv_melting"}]
        supported_crystallization_components = [row for row in supported_components if str(row.get("type", "") or "").strip().lower() in {"crystallisation", "crystallization", "cold_crystallisation", "cold_crystallization", "recrystallisation", "recrystallization"}]
        thermal_event_evidence = _non_empty_mapping(
            [
                ("scan_mode", scan_mode or None),
                ("exo_up", exo_up if exo_up is not None else None),
                ("Tg_C", _clean_float(output.get("Tg_C"))),
                ("Tg_method", tg_method),
                ("Tg_search_low_C", tg_low),
                ("Tg_search_high_C", tg_high),
                ("DTg_C", _clean_float(output.get("DTg_C"))),
                ("DCp_JgK", _clean_float(output.get("DCp_JgK"))),
                ("Tm_onset_C", _clean_float(output.get("Tm_onset_C"))),
                ("Tm_peak_C", _clean_float(output.get("Tm_peak_C"))),
                ("Tm_end_C", _clean_float(output.get("Tm_end_C"))),
                ("Tm_search_low_C", tm_low),
                ("Tm_search_high_C", tm_high),
                ("Tc_onset_C", _clean_float(output.get("Tc_onset_C"))),
                ("Tc_peak_C", _clean_float(output.get("Tc_peak_C"))),
                ("Tc_end_C", _clean_float(output.get("Tc_end_C"))),
                ("Tc_search_low_C", tc_low),
                ("Tc_search_high_C", tc_high),
                ("Tcc_onset_C", _clean_float(output.get("Tcc_onset_C"))),
                ("Tcc_peak_C", _clean_float(output.get("Tcc_peak_C"))),
                ("DHm_Jg", _clean_float(output.get("DHm_Jg"))),
                ("DHc_Jg", _clean_float(output.get("DHc_Jg"))),
                ("DHcc_Jg", _clean_float(output.get("DHcc_Jg"))),
                ("peak_components", peak_components if peak_components else None),
                ("supported_event_count", len(supported_components)),
                ("supported_melting_event_count", len(supported_melting_components)),
                ("supported_crystallization_event_count", len(supported_crystallization_components)),
                ("n_peaks", _safe_int(output.get("n_peaks"), default=len(peak_components))),
            ]
        )
        scan_evidence = _non_empty_mapping(
            [
                ("scan_mode", scan_mode or None),
                ("scan_r_squared", scan_rows if scan_rows else None),
                ("scan_r_squared_median", _clean_float(_mean_finite([row.get("r_squared") for row in scan_rows]))),
                ("scan_r_squared_spread", _relative_spread([row.get("r_squared") for row in scan_rows])),
                ("scan_count", len(scan_rows)),
                ("r_squared_method", str(output.get("r_squared_method", "") or "").strip() or None),
            ]
        )
        baseline_evidence = _non_empty_mapping(
            [
                ("baseline_corr", baseline_corr),
                ("smooth_window", _clean_float(output.get("smooth_window", config_snapshot.get("smooth_window")))),
                ("exo_up", exo_up if exo_up is not None else None),
                ("Tg_method", tg_method),
                ("peak_function", peak_function),
                ("quality_flags", output.get("quality_flags")),
                ("validation_summary", validation_summary or None),
                ("residual_type", residual_type or None),
                ("residual_summary", residual_summary or None),
                ("peak_prominence_ratio", peak_prominence_ratio),
                ("min_event_enthalpy_Jg", min_event_enthalpy),
                ("baseline_sensitivity_pct", baseline_sensitivity),
                ("integration_boundary_sensitivity_pct", boundary_sensitivity),
            ]
        )
        crystallinity_evidence = _non_empty_mapping(
            [
                ("Xc_pct", _clean_float(output.get("Xc_pct"))),
                ("Xc_method", str(output.get("Xc_method", "") or "").strip() or None),
                ("DHm0_Jg", dhm0),
                ("DHm0_source", dhm0_source),
                ("DHm_Jg", _clean_float(output.get("DHm_Jg"))),
                ("DHm_Jg_mean", dhm_mean),
                ("DHm_Jg_std", dhm_std),
                ("DHcc_Jg", _clean_float(output.get("DHcc_Jg"))),
                ("DHcc_Jg_mean", dhcc_mean),
                ("DHcc_Jg_std", dhcc_std),
                ("Xc_pct_mean", xc_mean),
                ("Xc_pct_std", xc_std),
                ("Xc_pct_ci95", xc_ci95),
                ("baseline_sensitivity_pct", baseline_sensitivity),
                ("integration_boundary_sensitivity_pct", boundary_sensitivity),
                ("baseline_variant_count", baseline_variant_count if baseline_variant_count > 0 else None),
                ("integration_variant_count", integration_variant_count if integration_variant_count > 0 else None),
                ("Xc_reliability_status", xc_reliability_status),
            ]
        )
        peak_evidence = _non_empty_mapping(
            [
                ("peak_components", peak_components if peak_components else None),
                ("peak_component_types", sorted({str(row.get("type", "") or "").strip().lower() for row in peak_components if str(row.get("type", "") or "").strip()} ) or None),
                ("peak_component_count", len(peak_components)),
                ("supported_component_count", len(supported_components)),
                ("supported_melting_component_count", len(supported_melting_components)),
                ("supported_crystallization_component_count", len(supported_crystallization_components)),
                ("Tm_peak_C", _clean_float(output.get("Tm_peak_C"))),
                ("Tm_onset_C", _clean_float(output.get("Tm_onset_C"))),
                ("Tm_end_C", _clean_float(output.get("Tm_end_C"))),
                ("Tc_peak_C", _clean_float(output.get("Tc_peak_C"))),
                ("Tcc_peak_C", _clean_float(output.get("Tcc_peak_C"))),
                ("max_melting_peak_width_C", max_melting_peak_width),
            ]
        )
        feature_evidence["scan_evidence"] = scan_evidence
        feature_evidence["thermal_event_evidence"] = thermal_event_evidence
        feature_evidence["baseline_evidence"] = baseline_evidence
        feature_evidence["crystallinity_evidence"] = crystallinity_evidence
        feature_evidence["peak_evidence"] = peak_evidence
        feature_evidence["peak_components"] = peak_components if peak_components else output.get("peak_components", [])
        for key in (
            "Tm_peak_C",
            "Tm_onset_C",
            "Tm_end_C",
            "Tc_peak_C",
            "Tc_onset_C",
            "Tc_end_C",
            "Tcc_peak_C",
            "Tcc_onset_C",
            "Tg_C",
            "Tg_method",
            "DTg_C",
            "DCp_JgK",
            "Xc_pct",
            "Xc_method",
            "DHm_Jg",
            "DHc_Jg",
            "DHcc_Jg",
            "quality_score",
            "scan_r_squared",
            "scan_mode",
            "r_squared_method",
            "n_peaks",
            "peak_function",
        ):
            if key in output:
                feature_evidence[key] = output.get(key)
        if output.get("quality_flags") is not None:
            physical_evidence["quality_flags"] = output.get("quality_flags")
        if output.get("scan_r_squared") is not None:
            confidence_signals.append({"name": "scan_r_squared", "value": output.get("scan_r_squared"), "source": "DSC"})
        if output.get("quality_score") is not None:
            confidence_signals.append({"name": "quality_score", "value": _clean_float(output.get("quality_score")), "source": "DSC"})
        if scan_rows:
            confidence_signals.append(
                {
                    "name": "scan_r_squared_median",
                    "value": _clean_float(_mean_finite([row.get("r_squared") for row in scan_rows])),
                    "source": "DSC",
                }
            )
        quality_flags_payload = output.get("quality_flags")
        if isinstance(quality_flags_payload, dict):
            quality_flag_text = " ".join(f"{key}:{value}" for key, value in quality_flags_payload.items()).strip().lower()
        elif isinstance(quality_flags_payload, list):
            quality_flag_text = " ".join(str(value) for value in quality_flags_payload).strip().lower()
        else:
            quality_flag_text = str(quality_flags_payload or "").strip().lower()
        event_support_score = _clamp_unit(
            0.45 * _clamp_unit(len(supported_components) / max(len(peak_components), 1))
            + 0.25 * _clamp_unit((_clean_float(output.get("quality_score")) or 0.0))
            + 0.30 * _clamp_unit(1.0 - (_relative_spread([row.get("r_squared") for row in scan_rows]) or 0.0))
        )
        baseline_stability_score = _clamp_unit(
            0.45
            + (0.12 if baseline_corr and baseline_corr not in {"auto", "none", "unknown"} else 0.0)
            + (0.10 if exo_up is not None else 0.0)
            + (0.10 if residual_type not in {"baseline_drift", "baseline_drift_low_t", "baseline_drift_high_t"} else -0.15)
            + (0.10 if quality_score is not None and quality_score >= 0.75 else 0.0)
            - (0.10 if "baseline" in quality_flag_text else 0.0)
        )
        thermodynamic_consistency_score = _clamp_unit(
            0.4 * (1.0 if (tg_c := _clean_float(output.get("Tg_C"))) is not None else 0.0)
            + 0.2 * (1.0 if _clean_float(output.get("Tm_peak_C")) is not None else 0.0)
            + 0.2 * (1.0 if _clean_float(output.get("Tc_peak_C")) is not None or _clean_float(output.get("Tcc_peak_C")) is not None else 0.0)
            + 0.2 * event_support_score
        )
        scan_r_squared_median = _clean_float(_mean_finite([row.get("r_squared") for row in scan_rows]))
        scan_r_squared_spread = _relative_spread([row.get("r_squared") for row in scan_rows])
        supported_event_fraction = (len(supported_components) / max(len(peak_components), 1)) if peak_components else None
        structure_support_score = _clamp_unit(
            0.35 * event_support_score
            + 0.20 * baseline_stability_score
            + 0.20 * thermodynamic_consistency_score
            + 0.15 * _clamp_unit(scan_r_squared_median)
            + 0.10 * _clamp_unit(1.0 - (scan_r_squared_spread or 0.0))
        )
        event_support_evidence = _non_empty_mapping(
            [
                ("event_support_score", event_support_score),
                ("baseline_stability_score", baseline_stability_score),
                ("thermodynamic_consistency_score", thermodynamic_consistency_score),
                ("supported_component_count", len(supported_components)),
                ("supported_event_fraction", (len(supported_components) / max(len(peak_components), 1)) if peak_components else None),
                ("scan_r_squared_median", _clean_float(_mean_finite([row.get("r_squared") for row in scan_rows]))),
                ("scan_r_squared_spread", _relative_spread([row.get("r_squared") for row in scan_rows])),
            ]
        )
        if event_support_evidence:
            feature_evidence["event_support_evidence"] = event_support_evidence
            confidence_signals.extend(
                [
                    {"name": "event_support_score", "value": event_support_score, "source": "DSC"},
                    {"name": "baseline_stability_score", "value": baseline_stability_score, "source": "DSC"},
                    {"name": "thermodynamic_consistency_score", "value": thermodynamic_consistency_score, "source": "DSC"},
                ]
            )

    if technique_key == "IR" and is_ir_temperature_2d:
        temperature_2d_metrics = _ir_temperature_2d_metrics(output, validation)
        signal_evidence = _non_empty_mapping(
            [
                ("submodule_id", temperature_2d_metrics.get("submodule_id")),
                ("n_frames", temperature_2d_metrics.get("n_frames")),
                ("n_bands_tracked", temperature_2d_metrics.get("n_bands_tracked")),
                ("stage_counts", temperature_2d_metrics.get("stage_counts")),
                ("sequence_order_source", temperature_2d_metrics.get("sequence_order_source")),
                ("T_range_C", temperature_2d_metrics.get("T_range_C")),
                ("temperature_min_C", temperature_2d_metrics.get("temperature_min_C")),
                ("temperature_max_C", temperature_2d_metrics.get("temperature_max_C")),
                ("temperature_missing_count", temperature_2d_metrics.get("temperature_missing_count")),
                ("time_missing_count", temperature_2d_metrics.get("time_missing_count")),
                ("time_estimated_count", temperature_2d_metrics.get("time_estimated_count")),
            ]
        )
        peak_evidence = _non_empty_mapping(
            [
                ("dynamic_shape", temperature_2d_metrics.get("dynamic_shape")),
                ("sync_shape", temperature_2d_metrics.get("sync_shape")),
                ("async_shape", temperature_2d_metrics.get("async_shape")),
                ("matrix_shape", temperature_2d_metrics.get("matrix_shape")),
                ("dynamic_rms", temperature_2d_metrics.get("dynamic_rms")),
                ("dynamic_signal_rms", temperature_2d_metrics.get("dynamic_signal_rms")),
                ("neg_fraction", temperature_2d_metrics.get("neg_fraction")),
                ("nan_fraction", temperature_2d_metrics.get("nan_fraction")),
                ("wavenumber_grid_consistent", temperature_2d_metrics.get("wavenumber_grid_consistent")),
                ("frame_intensity_scale_spread", temperature_2d_metrics.get("frame_intensity_scale_spread")),
                ("max_sync_abs", temperature_2d_metrics.get("max_sync_abs")),
                ("max_async_abs", temperature_2d_metrics.get("max_async_abs")),
            ]
        )
        transform_evidence = _non_empty_mapping(
            [
                ("sync_cross_peak_count", temperature_2d_metrics.get("sync_cross_peak_count")),
                ("async_cross_peak_count", temperature_2d_metrics.get("async_cross_peak_count")),
                ("cross_peak_count", temperature_2d_metrics.get("cross_peak_count")),
                ("assigned_cross_peak_count", temperature_2d_metrics.get("assigned_cross_peak_count")),
                ("unassigned_cross_peak_count", temperature_2d_metrics.get("unassigned_cross_peak_count")),
                ("async_with_sync_support_count", temperature_2d_metrics.get("async_with_sync_support_count")),
                ("top_sync_cross_peak_cm1", temperature_2d_metrics.get("top_sync_cross_peak_cm1") or None),
                ("top_async_cross_peak_cm1", temperature_2d_metrics.get("top_async_cross_peak_cm1") or None),
                ("top_sync_diagonal_distance_cm1", temperature_2d_metrics.get("top_sync_diagonal_distance_cm1")),
                ("top_async_diagonal_distance_cm1", temperature_2d_metrics.get("top_async_diagonal_distance_cm1")),
                ("top_sync_assigned", temperature_2d_metrics.get("top_sync_assigned")),
                ("top_async_assigned", temperature_2d_metrics.get("top_async_assigned")),
                ("top_async_has_sync_support", temperature_2d_metrics.get("top_async_has_sync_support")),
                ("noda_rule_interpretation_ready", temperature_2d_metrics.get("noda_rule_interpretation_ready")),
                ("transition_count", temperature_2d_metrics.get("transition_count")),
                ("transition_temperatures_C", temperature_2d_metrics.get("transition_temperatures_C") or None),
            ]
        )
        structure_evidence = _non_empty_mapping(
            [
                ("sequence_axis_ready", temperature_2d_metrics.get("sequence_axis_ready")),
                ("matrix_shapes_consistent", temperature_2d_metrics.get("matrix_shapes_consistent")),
                ("sequence_axis_score", temperature_2d_metrics.get("sequence_axis_score")),
                ("matrix_quality_score", temperature_2d_metrics.get("matrix_quality_score")),
                ("cos_signal_score", temperature_2d_metrics.get("cos_signal_score")),
                ("band_tracking_score", temperature_2d_metrics.get("band_tracking_score")),
                ("interpretation_ready", temperature_2d_metrics.get("interpretation_ready")),
                ("paper_conclusion_ready", temperature_2d_metrics.get("paper_conclusion_ready")),
            ]
        )
        for key, value in temperature_2d_metrics.items():
            if key in {"stage_counts"}:
                continue
            feature_evidence[key] = value
        feature_evidence["sequence_evidence"] = signal_evidence
        feature_evidence["matrix_evidence"] = peak_evidence
        feature_evidence["peak_evidence"] = peak_evidence
        feature_evidence["transform_evidence"] = transform_evidence
        feature_evidence["cos_evidence"] = transform_evidence
        feature_evidence["interpretation_evidence"] = structure_evidence
        feature_evidence["band_tracking_evidence"] = _non_empty_mapping(
            [
                ("band_index_series_count", temperature_2d_metrics.get("band_index_series_count")),
                ("band_index_transition_candidate_count", temperature_2d_metrics.get("band_index_transition_candidate_count")),
                ("band_index_transition_support_band_count", temperature_2d_metrics.get("band_index_transition_support_band_count")),
                ("band_index_transition_consensus_frame", temperature_2d_metrics.get("band_index_transition_consensus_frame")),
                ("band_index_transition_frame_spread", temperature_2d_metrics.get("band_index_transition_frame_spread")),
                ("band_index_transition_support_ratio", temperature_2d_metrics.get("band_index_transition_support_ratio")),
                ("band_index_transition_single_frame_only", temperature_2d_metrics.get("band_index_transition_single_frame_only")),
                ("band_index_transition_reproducible", temperature_2d_metrics.get("band_index_transition_reproducible")),
                ("band_index_transition_denominator_unstable", temperature_2d_metrics.get("band_index_transition_denominator_unstable")),
                ("band_index_transition_max_jump_cm1", temperature_2d_metrics.get("band_index_transition_max_jump_cm1")),
                ("band_index_transition_median_jump_cm1", temperature_2d_metrics.get("band_index_transition_median_jump_cm1")),
                ("band_index_transition_max_jump_ratio", temperature_2d_metrics.get("band_index_transition_max_jump_ratio")),
                ("band_tracking_missing_key_band", temperature_2d_metrics.get("band_tracking_missing_key_band")),
                ("band_index_transition_support_keys", temperature_2d_metrics.get("band_index_transition_support_keys") or None),
            ]
        )
        feature_evidence["single_frame_evidence"] = _non_empty_mapping(
            [
                ("low_confidence_frame_count", temperature_2d_metrics.get("low_confidence_frame_count")),
                ("low_confidence_frame_ratio", temperature_2d_metrics.get("low_confidence_frame_ratio")),
                ("frame_assignment_confidence_mean", temperature_2d_metrics.get("frame_assignment_confidence_mean")),
                ("frame_polymer_score_mean", temperature_2d_metrics.get("frame_polymer_score_mean")),
                ("frame_key_band_support_mean", temperature_2d_metrics.get("frame_key_band_support_mean")),
            ]
        )
        feature_evidence["temperature_2d_evidence"] = _non_empty_mapping(
            [
                ("sequence_axis_score", temperature_2d_metrics.get("sequence_axis_score")),
                ("matrix_quality_score", temperature_2d_metrics.get("matrix_quality_score")),
                ("cos_signal_score", temperature_2d_metrics.get("cos_signal_score")),
                ("band_tracking_score", temperature_2d_metrics.get("band_tracking_score")),
                ("interpretation_ready", temperature_2d_metrics.get("interpretation_ready")),
                ("paper_conclusion_ready", temperature_2d_metrics.get("paper_conclusion_ready")),
                ("low_confidence_frame_ratio", temperature_2d_metrics.get("low_confidence_frame_ratio")),
            ]
        )
        confidence_signals.extend(
            [
                {"name": "sequence_axis_score", "value": temperature_2d_metrics.get("sequence_axis_score"), "source": "IR_temperature_2d"},
                {"name": "matrix_quality_score", "value": temperature_2d_metrics.get("matrix_quality_score"), "source": "IR_temperature_2d"},
                {"name": "cos_signal_score", "value": temperature_2d_metrics.get("cos_signal_score"), "source": "IR_temperature_2d"},
            ]
        )
    elif technique_key == "IR":
        for key in (
            "polymer_name",
            "polymer_score",
            "assignment_confidence",
            "Xc_pct",
            "Xc_method",
            "Xc_calibration_status",
            "n_peaks",
            "r_squared",
        ):
            if key in output:
                feature_evidence[key] = output.get(key)
        if output.get("polymer_score") is not None:
            confidence_signals.append({"name": "polymer_score", "value": _clean_float(output.get("polymer_score")), "source": "IR"})

        peak_positions: list[float] = []
        peak_heights: list[float] = []
        peak_prominences: list[float] = []
        peak_widths: list[float] = []
        peak_assignments: list[str] = []
        assigned_peaks: list[dict[str, Any]] = []
        unassigned_peaks: list[dict[str, Any]] = []
        peak_support_count = 0
        assigned_peak_count = 0
        matched_peak_count = 0
        key_band_hits: list[dict[str, Any]] = []
        key_band_missing: list[dict[str, Any]] = []

        raw_peaks = _ir_peak_records(output)
        if raw_peaks:
            for peak in raw_peaks:
                wn = _clean_float(peak.get("wavenumber"))
                height = _clean_float(peak.get("height"))
                prominence = _clean_float(peak.get("prominence"))
                width = _clean_float(peak.get("fwhm_cm1"))
                assignment = str(peak.get("assignment", "") or "").strip()
                ref_wn = _clean_float(peak.get("ref_wavenumber"))
                if wn is not None:
                    peak_positions.append(wn)
                if height is not None:
                    peak_heights.append(height)
                if prominence is not None:
                    peak_prominences.append(prominence)
                if width is not None:
                    peak_widths.append(width)
                if assignment:
                    peak_assignments.append(assignment)
                peak_record = _non_empty_mapping(
                    [
                        ("wavenumber", wn),
                        ("height", height),
                        ("prominence", prominence),
                        ("fwhm_cm1", width),
                        ("area", _clean_float(peak.get("area"))),
                        ("assignment", assignment or None),
                        ("ref_wavenumber", ref_wn),
                    ]
                )
                if assignment and assignment.lower() != "unknown":
                    assigned_peak_count += 1
                    if peak_record:
                        assigned_peaks.append(peak_record)
                elif peak_record:
                    unassigned_peaks.append(peak_record)
                if ref_wn is not None or (assignment and assignment.lower() != "unknown"):
                    matched_peak_count += 1
                if height is not None and height > 0:
                    peak_support_count += 1

        polymer_db = output.get("polymer_peaks_db")
        if not isinstance(polymer_db, dict):
            polymer_db = _extract_nested_mapping(validation.get("config_snapshot", {}), "polymer_peaks_db")
        polymer_name = str(output.get("polymer_name", output.get("polymer", "")) or "").strip()
        polymer_key = normalize_ir_polymer_name(polymer_name)
        characteristic_bands = polymer_db.get(polymer_key, [])
        reference_band_records: list[dict[str, Any]] = []
        reference_bands_payload = validation.get("ir_reference_bands", {})
        if isinstance(reference_bands_payload, dict):
            payload_bands = reference_bands_payload.get("bands", [])
            if isinstance(payload_bands, list):
                for band in payload_bands:
                    if not isinstance(band, dict):
                        continue
                    ref_wn = _clean_float(band.get("wavenumber"))
                    if ref_wn is None:
                        continue
                    reference_band_records.append(
                        _non_empty_mapping(
                            [
                                ("ref_wavenumber", ref_wn),
                                ("assignment", str(band.get("assignment", "") or "").strip() or None),
                                ("intensity", str(band.get("intensity", "") or "").strip() or None),
                                ("crystallinity_sensitive", bool(band.get("crystallinity_sensitive", False))),
                            ]
                        )
                    )
        if not reference_band_records and isinstance(characteristic_bands, list) and characteristic_bands:
            for band in characteristic_bands:
                if not isinstance(band, (list, tuple)) or not band:
                    continue
                ref_wn = _clean_float(band[0])
                assignment = str(band[1] if len(band) > 1 else "",).strip()
                intensity = str(band[2] if len(band) > 2 else "",).strip()
                cryst = bool(band[3]) if len(band) > 3 else False
                if ref_wn is None:
                    continue
                reference_band_records.append(
                    _non_empty_mapping(
                        [
                            ("ref_wavenumber", ref_wn),
                            ("assignment", assignment or "unknown"),
                            ("intensity", intensity or None),
                            ("crystallinity_sensitive", cryst),
                        ]
                    )
                )

        if reference_band_records:
            for band in reference_band_records:
                ref_wn = _clean_float(band.get("ref_wavenumber"))
                assignment = str(band.get("assignment", "") or "").strip()
                intensity = str(band.get("intensity", "") or "").strip()
                cryst = bool(band.get("crystallinity_sensitive", False))
                if ref_wn is None:
                    continue
                matched_peak = None
                for peak in raw_peaks:
                    peak_wn = _clean_float(peak.get("wavenumber"))
                    if peak_wn is None:
                        continue
                    if abs(peak_wn - ref_wn) <= 18.0:
                        matched_peak = {
                            "ref_wavenumber": ref_wn,
                            "observed_wavenumber": peak_wn,
                            "assignment": assignment or str(peak.get("assignment", "") or "").strip() or "unknown",
                            "intensity": intensity or None,
                            "crystallinity_sensitive": cryst,
                            "delta_cm1": abs(peak_wn - ref_wn),
                        }
                        break
                if matched_peak is not None:
                    key_band_hits.append(matched_peak)
                else:
                    key_band_missing.append(
                        {
                            "ref_wavenumber": ref_wn,
                            "assignment": assignment or "unknown",
                            "intensity": intensity or None,
                            "crystallinity_sensitive": cryst,
                        }
                    )

        baseline_method = str(output.get("baseline_method", validation.get("config_snapshot", {}).get("baseline_method", "")) or "").strip()
        normalization_method = str(output.get("normalization_method", validation.get("config_snapshot", {}).get("normalization_method", "")) or "").strip()
        smooth_window = _clean_float(output.get("smooth_window", validation.get("config_snapshot", {}).get("smooth_window")))
        peak_distance = _clean_float(output.get("peak_distance", validation.get("config_snapshot", {}).get("peak_distance")))
        peak_fit_window = _clean_float(output.get("peak_fit_window_cm1", validation.get("config_snapshot", {}).get("peak_fit_window_cm1")))
        assignment_tolerance = _clean_float(output.get("assignment_tolerance_cm1", validation.get("config_snapshot", {}).get("assignment_tolerance_cm1")))
        wn_min = _clean_float(output.get("wavenumber_min_cm1"))
        wn_max = _clean_float(output.get("wavenumber_max_cm1"))
        wn_span = None
        if wn_min is not None and wn_max is not None:
            wn_span = abs(wn_max - wn_min)
        x_calibration_status = _ir_xc_calibration_status(output)

        if peak_positions:
            peak_prominence_distribution = _numeric_distribution(peak_prominences, source="prominence")
            if peak_prominence_distribution is None and peak_heights:
                peak_prominence_distribution = _numeric_distribution(peak_heights, source="height_proxy")
            peak_evidence = _non_empty_mapping(
                [
                    ("peak_count", len(peak_positions)),
                    ("peak_positions", peak_positions),
                    ("peak_heights", peak_heights if peak_heights else None),
                    ("peak_prominence_distribution", peak_prominence_distribution),
                    ("peak_widths", peak_widths if peak_widths else None),
                    ("peak_assignments", peak_assignments if peak_assignments else None),
                    ("assigned_peak_count", assigned_peak_count),
                    ("unassigned_peak_count", len(unassigned_peaks)),
                    ("matched_peak_count", matched_peak_count),
                    ("peak_support_count", peak_support_count),
                    ("assigned_peaks", assigned_peaks if assigned_peaks else None),
                    ("unassigned_peaks", unassigned_peaks if unassigned_peaks else None),
                ]
            )
        if peak_evidence:
            peak_evidence = dict(peak_evidence)
            peak_evidence["peak_count"] = int(len(peak_positions))
            if peak_evidence.get("peak_widths") and len(peak_evidence.get("peak_widths", [])) >= 2:
                peak_evidence["peak_width_spread"] = _relative_spread(peak_evidence.get("peak_widths", []))
            feature_evidence["peak_evidence"] = peak_evidence
            peak_evidence = peak_evidence
            confidence_signals.append({"name": "peak_count", "value": len(peak_positions), "source": "IR"})

        baseline_evidence = _non_empty_mapping(
            [
                ("baseline_method", baseline_method or None),
                ("normalization_method", normalization_method or None),
                ("smooth_window", smooth_window),
                ("peak_distance", peak_distance),
                ("peak_fit_window_cm1", peak_fit_window),
                ("assignment_tolerance_cm1", assignment_tolerance),
            ]
        )
        if baseline_evidence:
            baseline_evidence = dict(baseline_evidence)
            feature_evidence["baseline_evidence"] = baseline_evidence
            background_evidence = baseline_evidence

        assignment_evidence = _non_empty_mapping(
            [
                ("polymer_name", polymer_name or None),
                ("polymer_score", _clean_float(output.get("polymer_score"))),
                ("assignment_confidence", _clean_float(output.get("assignment_confidence", output.get("polymer_score")))),
                ("assigned_peaks", assigned_peaks if assigned_peaks else None),
                ("unassigned_peaks", unassigned_peaks if unassigned_peaks else None),
                ("assigned_peak_count", len(assigned_peaks)),
                ("unassigned_peak_count", len(unassigned_peaks)),
                ("key_band_hits", key_band_hits if key_band_hits else None),
                ("key_band_missing", key_band_missing if key_band_missing else None),
                ("key_band_hit_count", len(key_band_hits)),
                ("key_band_missing_count", len(key_band_missing)),
            ]
        )
        if assignment_evidence:
            assignment_evidence = dict(assignment_evidence)
            feature_evidence["assignment_evidence"] = assignment_evidence
            confidence_signals.append(
                {
                    "name": "assignment_confidence",
                    "value": _clean_float(output.get("assignment_confidence", output.get("polymer_score"))),
                    "source": "IR",
                }
            )

        reference_evidence = _non_empty_mapping(
            [
                ("polymer_name", polymer_name or None),
                ("band_count", len(reference_band_records)),
                ("bands", reference_band_records if reference_band_records else None),
                (
                    "source",
                    str(
                        reference_bands_payload.get("source", "IRConfig.polymer_peaks_db")
                        if isinstance(reference_bands_payload, dict)
                        else "IRConfig.polymer_peaks_db"
                    ).strip()
                    or None,
                ),
                ("hit_count", len(key_band_hits)),
                ("missing_count", len(key_band_missing)),
            ]
        )
        if reference_evidence:
            reference_evidence = dict(reference_evidence)
            feature_evidence["reference_evidence"] = reference_evidence

        phase_evidence = _non_empty_mapping(
            [
                ("Xc_pct", _clean_float(output.get("Xc_pct"))),
                ("Xc_method", str(output.get("Xc_method", "") or "").strip() or None),
                ("Xc_calibration_status", x_calibration_status),
            ]
        )
        if phase_evidence:
            phase_evidence = dict(phase_evidence)
            feature_evidence["phase_evidence"] = phase_evidence

        paper_conclusion_candidate = bool(
            len(peak_positions) >= 6
            and assigned_peak_count >= 4
            and len(key_band_hits) >= 3
            and len(key_band_missing) == 0
        )
        structure_evidence = _non_empty_mapping(
            [
                ("classification_basis", "peak_assignment" if key_band_hits else "peak_detection"),
                ("detected_peak_count", len(peak_positions) if peak_positions else None),
                ("assigned_peak_count", assigned_peak_count),
                ("matched_peak_count", matched_peak_count),
                ("reference_band_count", len(reference_band_records)),
                ("reference_band_hit_count", len(key_band_hits)),
                ("reference_band_missing_count", len(key_band_missing)),
                ("key_reference_bands_hit", key_band_hits if key_band_hits else None),
                ("key_reference_bands_missing", key_band_missing if key_band_missing else None),
                ("characteristic_band_support_ok", bool(len(key_band_hits) >= 3 and len(key_band_missing) == 0)),
                ("Xc_pct", _clean_float(output.get("Xc_pct"))),
                ("Xc_method", str(output.get("Xc_method", "") or "").strip() or None),
                ("Xc_calibration_status", x_calibration_status),
                ("paper_conclusion_candidate", paper_conclusion_candidate),
                ("paper_conclusion_ready", paper_conclusion_candidate),
            ]
        )
        if structure_evidence:
            structure_evidence = dict(structure_evidence)
            feature_evidence["structure_evidence"] = structure_evidence
            feature_evidence["classification_evidence"] = structure_evidence

        if wn_min is not None or wn_max is not None or wn_span is not None:
            signal_evidence = _non_empty_mapping(
                [
                    ("wavenumber_min_cm1", wn_min),
                    ("wavenumber_max_cm1", wn_max),
                    ("wavenumber_span_cm1", wn_span),
                ]
            )

        if peak_evidence:
            peak_evidence = dict(peak_evidence)
        if baseline_evidence:
            background_evidence = dict(baseline_evidence)
        if phase_evidence:
            phase_evidence = dict(phase_evidence)
        if structure_evidence:
            structure_evidence = dict(structure_evidence)
        if assignment_evidence:
            assignment_evidence = dict(assignment_evidence)

    if technique_key == "NMR":
        for key in ("n_peaks", "Xc_pct", "Xc_method", "dominant_peak_ppm", "mean_fwhm_ppm", "median_snr", "quality_metrics"):
            if key in output:
                feature_evidence[key] = output.get(key)
        peak_rows = _nmr_peak_rows(output)
        peak_count = _clean_float(output.get("n_peaks"))
        assigned_count = sum(1 for row in peak_rows if row.get("assignment"))
        phase_assigned_count = sum(1 for row in peak_rows if row.get("phase"))
        crystalline_count = sum(1 for row in peak_rows if str(row.get("phase", "")).lower() in {"c", "crystalline"})
        amorphous_count = sum(1 for row in peak_rows if str(row.get("phase", "")).lower() in {"a", "amorphous"})
        assignment_denominator = peak_count if peak_count and peak_count > 0 else len(peak_rows)
        assigned_fraction = assigned_count / assignment_denominator if assignment_denominator else None
        xc_method = str(output.get("Xc_method") or "").strip()
        explicit_xc_assignment_status = str(output.get("Xc_assignment_status") or "").strip()
        assignment_confidence = _clean_float(output.get("assignment_confidence"))
        library_match_fraction = _clean_float(output.get("library_match_fraction"))
        solvent_overlap_penalty = _clean_float(output.get("solvent_overlap_penalty"))
        phase_pair_support = bool(output.get("phase_pair_support")) if output.get("phase_pair_support") is not None else False
        matched_library_count = _safe_int(output.get("matched_library_count"), 0)
        xc_assignment_status = ""
        if explicit_xc_assignment_status:
            xc_assignment_status = explicit_xc_assignment_status
        elif (
            phase_pair_support
            and assignment_confidence is not None
            and assignment_confidence >= 0.7
            and (solvent_overlap_penalty is None or solvent_overlap_penalty <= 0.25)
        ):
            xc_assignment_status = "supported"
        elif output.get("Xc_pct") is not None or xc_method:
            if crystalline_count > 0 and amorphous_count > 0:
                xc_assignment_status = "supported"
            elif (
                assigned_count > 0
                or phase_assigned_count > 0
                or output.get("n_matches") is not None
                or xc_method == "requires_crystalline_amorphous_assignment"
            ):
                xc_assignment_status = "assignment_limited"
            else:
                xc_assignment_status = "missing_assignment"
        signal_evidence = _non_empty_mapping(
            [
                ("nucleus", str(output.get("nucleus") or "").strip() or None),
                ("sample_state", str(output.get("sample_state") or "").strip() or None),
                ("median_snr", _clean_float(output.get("median_snr"))),
                ("mean_fwhm_ppm", _clean_float(output.get("mean_fwhm_ppm"))),
                ("noise_mad", _clean_float(output.get("quality_noise_mad"))),
                ("fit_quality", _clean_float(output.get("quality_fit_quality"))),
            ]
        )
        peak_evidence = _non_empty_mapping(
            [
                ("peak_count", int(peak_count) if peak_count is not None and float(peak_count).is_integer() else peak_count),
                ("dominant_peak_ppm", _clean_float(output.get("dominant_peak_ppm"))),
                ("peak_area_total", _clean_float(output.get("peak_area_total"))),
                ("peaks", peak_rows),
            ]
        )
        assignment_evidence = _non_empty_mapping(
            [
                ("assigned_peak_count", assigned_count),
                ("phase_assignment_count", phase_assigned_count),
                ("assigned_peak_fraction", assigned_fraction),
                ("n_matches", _clean_float(output.get("n_matches"))),
                ("library_match_fraction", library_match_fraction),
                ("assignment_confidence", assignment_confidence),
                ("phase_pair_support", phase_pair_support if output.get("phase_pair_support") is not None else None),
                ("solvent_overlap_penalty", solvent_overlap_penalty),
                ("matched_library_count", matched_library_count if matched_library_count > 0 else None),
                ("assignment_library_source", str(output.get("assignment_library_source", "") or "").strip() or None),
            ]
        )
        phase_evidence = _non_empty_mapping(
            [
                ("crystalline_peak_count", crystalline_count),
                ("amorphous_peak_count", amorphous_count),
                ("phase_assignment_count", phase_assigned_count),
            ]
        )
        structure_evidence = _non_empty_mapping(
            [
                ("Xc_pct", _clean_float(output.get("Xc_pct"))),
                ("Xc_method", xc_method or None),
                ("Xc_assignment_status", xc_assignment_status or None),
                ("assignment_confidence", assignment_confidence),
                ("library_match_fraction", library_match_fraction),
                ("phase_pair_support", phase_pair_support if output.get("phase_pair_support") is not None else None),
                ("solvent_overlap_penalty", solvent_overlap_penalty),
                ("paper_conclusion_ready", xc_assignment_status == "supported"),
            ]
        )
        feature_evidence["signal_evidence"] = signal_evidence
        feature_evidence["peak_evidence"] = peak_evidence
        feature_evidence["assignment_evidence"] = assignment_evidence
        feature_evidence["phase_evidence"] = phase_evidence
        feature_evidence["structure_evidence"] = structure_evidence
        if output.get("median_snr") is not None:
            confidence_signals.append({"name": "median_snr", "value": _clean_float(output.get("median_snr")), "source": "NMR"})
        if assignment_confidence is not None:
            confidence_signals.append({"name": "assignment_confidence", "value": assignment_confidence, "source": "NMR"})

    constraints = evaluate_physical_constraints(technique_key, output, residual, validation)
    constraint_summary = summarize_constraints(constraints)
    for item in constraints:
        if item.get("triggered") and item.get("kind") in {"hard_fail", "soft_warn"}:
            risk_flags.append(str(item.get("name", "")).strip())

    if technique_key == "NMR":
        symptoms = _nmr_symptoms_from_constraints(constraints)
        for symptom in symptoms:
            actionable_symptoms.extend(_nmr_symptom_bridge_lines(symptom))

    if technique_key == "DSC":
        triggered_names = constraint_summary.get("triggered_names", {}) if isinstance(constraint_summary, dict) else {}
        soft_warn_names = {
            str(name).strip()
            for name in (triggered_names.get("soft_warn", []) if isinstance(triggered_names, dict) else [])
            if str(name).strip()
        }
        hard_fail_names = {
            str(name).strip()
            for name in (triggered_names.get("hard_fail", []) if isinstance(triggered_names, dict) else [])
            if str(name).strip()
        }
        if "baseline_sensitive_result" in soft_warn_names:
            actionable_symptoms.append("baseline_sensitive_result -> stabilize baseline_corr and smooth_window before trusting Tg/Tm")
        if "Tg_without_DCp_step" in soft_warn_names or "Tg_outside_supported_window" in soft_warn_names:
            actionable_symptoms.append("Tg support is weak -> re-center the Tg window before promoting Tg as stable")
        if "melting_without_supported_event" in soft_warn_names:
            actionable_symptoms.append("melting_without_supported_event -> check Tm onset/end and peak_components before accepting Tm")
        if "cold_crystallization_conflicts_with_melting" in soft_warn_names:
            actionable_symptoms.append("cold_crystallization_conflicts_with_melting -> separate Tcc from the melting window before re-using the result")
        if "event_polarity_conflict" in soft_warn_names:
            actionable_symptoms.append("event_polarity_conflict -> verify exo_up and signed enthalpy before writing conclusions")
        if "multi_scan_inconsistent" in soft_warn_names:
            actionable_symptoms.append("multi_scan_inconsistent -> stabilize the scan-to-scan evidence before accepting the file-level result")
        if "dsc_baseline_sensitive_xc" in soft_warn_names:
            actionable_symptoms.append("dsc_baseline_sensitive_xc -> keep Xc low-confidence until baseline and integration sensitivity settle")
        structure_evidence = _non_empty_mapping(
            [
                ("scan_mode", scan_mode or None),
                ("exo_up", exo_up if exo_up is not None else None),
                ("Tg_C", _clean_float(output.get("Tg_C"))),
                ("Tm_peak_C", _clean_float(output.get("Tm_peak_C"))),
                ("Tcc_peak_C", _clean_float(output.get("Tcc_peak_C"))),
                ("DHm_Jg", _clean_float(output.get("DHm_Jg"))),
                ("DHm_Jg_mean", dhm_mean),
                ("DHm_Jg_std", dhm_std),
                ("DHcc_Jg", _clean_float(output.get("DHcc_Jg"))),
                ("DHcc_Jg_mean", dhcc_mean),
                ("DHcc_Jg_std", dhcc_std),
                ("Xc_pct", _clean_float(output.get("Xc_pct"))),
                ("Xc_pct_mean", xc_mean),
                ("Xc_pct_std", xc_std),
                ("Xc_pct_ci95", xc_ci95),
                ("Xc_reliability_status", xc_reliability_status),
                ("baseline_sensitivity_pct", baseline_sensitivity),
                ("integration_boundary_sensitivity_pct", boundary_sensitivity),
                ("baseline_variant_count", baseline_variant_count if baseline_variant_count > 0 else None),
                ("integration_variant_count", integration_variant_count if integration_variant_count > 0 else None),
                ("DHm0_source", dhm0_source),
                ("supported_event_count", len(supported_components)),
                ("supported_melting_event_count", len(supported_melting_components)),
                ("supported_crystallization_event_count", len(supported_crystallization_components)),
                ("supported_event_fraction", supported_event_fraction),
                ("event_support_score", event_support_score),
                ("baseline_stability_score", baseline_stability_score),
                ("thermodynamic_consistency_score", thermodynamic_consistency_score),
                ("scan_r_squared_median", scan_r_squared_median),
                ("scan_r_squared_spread", scan_r_squared_spread),
                ("structure_support_score", structure_support_score),
                ("physical_support_pass", bool(
                    len(supported_components) >= 1
                    and len(supported_melting_components) >= 1
                    and event_support_score >= 0.75
                    and baseline_stability_score >= 0.55
                    and thermodynamic_consistency_score >= 0.55
                    and constraint_summary.get("status") != "hard_fail"
                )),
                ("constraint_status", constraint_summary.get("status")),
                ("triggered_constraint_count", constraint_summary.get("triggered_total")),
                ("paper_conclusion_candidate", bool(
                    structure_support_score >= 0.82
                    and event_support_score >= 0.85
                    and baseline_stability_score >= 0.65
                    and thermodynamic_consistency_score >= 0.65
                    and len(supported_components) >= 2
                    and len(supported_melting_components) >= 1
                    and (scan_r_squared_median is None or scan_r_squared_median >= 0.85)
                    and (scan_r_squared_spread is None or scan_r_squared_spread <= 0.08)
                    and constraint_summary.get("status") != "hard_fail"
                )),
                ("paper_conclusion_ready", bool(
                    structure_support_score >= 0.88
                    and event_support_score >= 0.88
                    and baseline_stability_score >= 0.75
                    and thermodynamic_consistency_score >= 0.75
                    and len(supported_components) >= 2
                    and len(supported_melting_components) >= 1
                    and (scan_r_squared_median is None or scan_r_squared_median >= 0.90)
                    and (scan_r_squared_spread is None or scan_r_squared_spread <= 0.05)
                    and constraint_summary.get("status") == "ok"
                    and not hard_fail_names
                )),
            ]
        )
        if structure_evidence:
            feature_evidence["structure_evidence"] = structure_evidence

    if technique_key == "IR" and not is_ir_temperature_2d:
        triggered_total = int(constraint_summary.get("triggered_total", 0) or 0)
        triggered_names = constraint_summary.get("triggered_names", {}) if isinstance(constraint_summary, dict) else {}
        triggered_soft_warn = set()
        if isinstance(triggered_names, dict):
            triggered_soft_warn = {
                str(item).strip()
                for item in triggered_names.get("soft_warn", [])
                if str(item).strip()
            }
        peak_count_value = _clean_float(peak_evidence.get("peak_count"))
        assigned_peak_count_value = _clean_float(peak_evidence.get("assigned_peak_count"))
        key_band_hit_count_value = int(reference_evidence.get("hit_count") or assignment_evidence.get("key_band_hit_count") or 0)
        key_band_missing_count_value = int(reference_evidence.get("missing_count") or assignment_evidence.get("key_band_missing_count") or 0)
        reference_band_count_value = int(reference_evidence.get("band_count") or 0)
        if reference_band_count_value <= 0:
            reference_band_count_value = key_band_hit_count_value + key_band_missing_count_value
        assignment_confidence_score = _clamp_unit(_clean_float(assignment_evidence.get("assignment_confidence", assignment_evidence.get("polymer_score"))))
        key_band_support_score = _clamp_unit(
            (key_band_hit_count_value / reference_band_count_value) if reference_band_count_value > 0 else 0.0
        )
        peak_coverage_score = _clamp_unit(
            (assigned_peak_count_value / peak_count_value) if peak_count_value and peak_count_value > 0 else 0.0
        )
        peak_width_spread = _clean_float(peak_evidence.get("peak_width_spread"))
        if peak_width_spread is None and peak_evidence.get("peak_widths") and len(peak_evidence.get("peak_widths", [])) >= 2:
            peak_width_spread = _relative_spread(peak_evidence.get("peak_widths", []))
        baseline_method = str(baseline_evidence.get("baseline_method", "") or "").strip().lower()
        normalization_method = str(baseline_evidence.get("normalization_method", "") or "").strip().lower()
        smooth_window = _clean_float(baseline_evidence.get("smooth_window"))
        peak_distance = _clean_float(baseline_evidence.get("peak_distance"))
        peak_fit_window = _clean_float(baseline_evidence.get("peak_fit_window_cm1"))
        baseline_stability_score = 0.42
        if baseline_method and baseline_method not in {"none", "unknown"}:
            baseline_stability_score += 0.18
        if normalization_method and normalization_method not in {"none", "unknown"}:
            baseline_stability_score += 0.16
        if smooth_window is not None:
            baseline_stability_score += 0.04
        if peak_distance is not None:
            baseline_stability_score += 0.04
        if peak_fit_window is not None:
            baseline_stability_score += 0.04
        if peak_width_spread is not None:
            baseline_stability_score += 0.12 * max(0.0, 1.0 - min(peak_width_spread, 0.6) / 0.6)
        if "baseline_sensitive_assignment" in triggered_soft_warn:
            baseline_stability_score -= 0.12
        if "baseline_drift_low_wn" in triggered_soft_warn or "baseline_drift_high_wn" in triggered_soft_warn:
            baseline_stability_score -= 0.15
        if "normalization_bias" in triggered_soft_warn:
            baseline_stability_score -= 0.10
        if "over_smoothed_weak_bands" in triggered_soft_warn:
            baseline_stability_score -= 0.06
        baseline_stability_score -= 0.03 * min(triggered_total, 3)
        baseline_stability_score = _clamp_unit(baseline_stability_score)
        ir_support_score = _clamp_unit(
            0.38 * assignment_confidence_score
            + 0.30 * key_band_support_score
            + 0.18 * peak_coverage_score
            + 0.14 * baseline_stability_score
        )

        ir_support_evidence = _non_empty_mapping(
            [
                ("assignment_confidence_score", assignment_confidence_score),
                ("key_band_support_score", key_band_support_score),
                ("peak_coverage_score", peak_coverage_score),
                ("baseline_stability_score", baseline_stability_score),
                ("triggered_constraint_count", triggered_total),
                ("unassigned_key_band_count", key_band_missing_count_value),
                ("ir_support_score", ir_support_score),
            ]
        )
        if ir_support_evidence:
            feature_evidence["ir_support_evidence"] = ir_support_evidence

        if peak_evidence:
            peak_evidence = dict(peak_evidence)
            peak_evidence["peak_coverage_score"] = peak_coverage_score
            feature_evidence["peak_evidence"] = peak_evidence
        if assignment_evidence:
            assignment_evidence = dict(assignment_evidence)
            assignment_evidence["assignment_confidence_score"] = assignment_confidence_score
            assignment_evidence["key_band_support_score"] = key_band_support_score
            assignment_evidence["peak_coverage_score"] = peak_coverage_score
            assignment_evidence["unassigned_key_band_count"] = key_band_missing_count_value
            feature_evidence["assignment_evidence"] = assignment_evidence
        if structure_evidence:
            structure_evidence = dict(structure_evidence)
            structure_evidence["assignment_confidence_score"] = assignment_confidence_score
            structure_evidence["key_band_support_score"] = key_band_support_score
            structure_evidence["peak_coverage_score"] = peak_coverage_score
            structure_evidence["baseline_stability_score"] = baseline_stability_score
            structure_evidence["triggered_constraint_count"] = triggered_total
            structure_evidence["unassigned_key_band_count"] = key_band_missing_count_value
            structure_evidence["ir_support_score"] = ir_support_score
            paper_candidate = bool(structure_evidence.get("paper_conclusion_candidate", structure_evidence.get("paper_conclusion_ready")))
            paper_blocking_warnings = {
                "assignment_confidence",
                "key_band_support_insufficient",
                "assignment_without_characteristic_bands",
                "baseline_sensitive_assignment",
                "baseline_drift_low_wn",
                "baseline_drift_high_wn",
                "key_band_mismatch",
                "crowded_band_underfit",
                "over_smoothed_weak_bands",
                "normalization_bias",
                "noise_dominant",
                "weak_peak_only_support",
                "overcrowded_band_separation_unstable",
                "polymer_score_without_assignment_support",
                "crystallinity_index_without_band_support",
                "ir_xc_uncalibrated",
            }
            structure_evidence["paper_conclusion_ready"] = bool(
                paper_candidate
                and assignment_confidence_score is not None
                and assignment_confidence_score >= 0.80
                and key_band_support_score >= 0.85
                and peak_coverage_score >= 0.60
                and baseline_stability_score >= 0.60
                and ir_support_score >= 0.78
                and key_band_missing_count_value == 0
                and not (triggered_soft_warn & paper_blocking_warnings)
            )
            feature_evidence["structure_evidence"] = structure_evidence
            feature_evidence["classification_evidence"] = structure_evidence
        if assignment_confidence_score is not None:
            confidence_signals.append({"name": "assignment_confidence_score", "value": assignment_confidence_score, "source": "IR"})
        confidence_signals.append({"name": "key_band_support_score", "value": key_band_support_score, "source": "IR"})
        confidence_signals.append({"name": "peak_coverage_score", "value": peak_coverage_score, "source": "IR"})
        confidence_signals.append({"name": "baseline_stability_score", "value": baseline_stability_score, "source": "IR"})
        if structure_evidence and structure_evidence.get("paper_conclusion_ready") is not None:
            confidence_signals.append(
                {
                    "name": "paper_conclusion_ready",
                    "value": 1.0 if bool(structure_evidence.get("paper_conclusion_ready")) else 0.0,
                    "source": "IR",
                }
            )

    if technique_key == "IR" and is_ir_temperature_2d:
        symptoms = _ir_temperature_2d_symptoms_from_constraints(constraints, output, residual, validation)
        for symptom in symptoms:
            actionable_symptoms.extend(_ir_temperature_2d_symptom_bridge_lines(symptom, output))
    elif technique_key == "IR":
        symptoms = _ir_symptoms_from_constraints(constraints, output, residual, validation)
        for symptom in symptoms:
            actionable_symptoms.extend(_ir_symptom_bridge_lines(symptom, output))

    if technique_key == "SAXS":
        symptoms = detect_saxs_symptoms(
            output,
            residual,
            validation,
            constraints=constraints,
            constraint_summary=constraint_summary,
            signal_evidence=signal_evidence,
            peak_evidence=peak_evidence,
            transform_evidence=transform_evidence,
            structure_evidence=structure_evidence,
            batch_evidence=batch_evidence,
            condition_evidence=condition_evidence,
        )
        stability_evidence = _build_saxs_stability_evidence(output, symptoms=symptoms)
        if stability_evidence:
            feature_evidence.setdefault("stability_evidence", stability_evidence)
            for key in (
                "stability_score",
                "parameter_stability_score",
                "method_agreement_score",
                "batch_continuity_score",
            ):
                if stability_evidence.get(key) is not None:
                    confidence_signals.append(
                        {
                            "name": key,
                            "value": _clean_float(stability_evidence.get(key)),
                            "source": "SAXS_stability",
                        }
                    )

    if technique_key == "WAXS":
        config_snapshot = validation.get("config_snapshot", {}) if isinstance(validation.get("config_snapshot", {}), dict) else {}
        waxs_metrics = _waxs_peak_metrics(output)
        peak_count = waxs_metrics.get("peak_count")
        peak_positions = waxs_metrics.get("peak_positions", [])
        peak_widths = waxs_metrics.get("peak_widths", [])
        peak_areas = waxs_metrics.get("peak_areas", [])
        peak_evidence = _non_empty_mapping(
            [
                ("peak_count", peak_count if peak_count is not None else None),
                ("peak_positions", peak_positions if peak_positions else None),
                ("peak_widths", peak_widths if peak_widths else None),
                ("peak_areas", peak_areas if peak_areas else None),
                ("peak_gap_spread", _clean_float(waxs_metrics.get("peak_gap_spread"))),
                ("peak_width_spread", _clean_float(waxs_metrics.get("peak_width_spread"))),
                ("peak_area_ratio", _clean_float(waxs_metrics.get("peak_area_ratio"))),
                ("scherrer_support_peaks", peak_count if peak_count is not None else None),
            ]
        )
        if peak_evidence:
            feature_evidence["peak_evidence"] = peak_evidence
            if peak_count is not None:
                confidence_signals.append({"name": "peak_count", "value": peak_count, "source": "WAXS"})

        background_evidence = _non_empty_mapping(
            [
                ("background_method", str(output.get("background_method", config_snapshot.get("background_method", "")) or "").strip() or None),
                ("amorphous_subtraction", str(output.get("amorphous_subtraction", config_snapshot.get("amorphous_subtraction", "")) or "").strip() or None),
                ("amorphous_n_peaks", _clean_float(output.get("amorphous_n_peaks", config_snapshot.get("amorphous_n_peaks")))),
                ("two_theta_offset", _clean_float(output.get("two_theta_offset", config_snapshot.get("two_theta_offset")))),
            ]
        )
        if background_evidence:
            feature_evidence["background_evidence"] = background_evidence

        phase_evidence = _non_empty_mapping(
            [
                ("Xc_pct", _clean_float(output.get("Xc_pct", output.get("Xc")))),
                ("crystallinity_method", str(output.get("crystallinity_method", output.get("Xc_method", config_snapshot.get("crystallinity_method", ""))) or "").strip() or None),
                ("crystal_system", str(output.get("crystal_system", "") or "").strip() or None),
                ("unit_cell_params_present", bool(output.get("unit_cell_params", config_snapshot.get("unit_cell_params", {}))) or None),
                ("D_Scherrer_nm", _clean_float(output.get("D_Scherrer_nm"))),
                ("D_uncertainty_nm", _clean_float(output.get("D_uncertainty_nm"))),
                ("D_WH_nm", _clean_float(output.get("D_WH_nm"))),
                ("D_WH_uncertainty_nm", _clean_float(output.get("D_WH_uncertainty_nm"))),
                ("epsilon_WH_pct", _clean_float(output.get("epsilon_WH_pct"))),
                ("epsilon_WH_uncertainty_pct", _clean_float(output.get("epsilon_WH_uncertainty_pct"))),
                ("WH_fit_r_squared", _clean_float(output.get("WH_fit_r_squared"))),
                ("size_reliability_status", str(output.get("size_reliability_status", "") or "").strip() or None),
                ("instrument_broadening_model", str(output.get("instrument_broadening_model", "") or "").strip() or None),
            ]
        )
        if phase_evidence:
            feature_evidence["phase_evidence"] = phase_evidence

        structure_evidence = _waxs_structure_metrics(
            output,
            peak_metrics=waxs_metrics,
            config_snapshot=config_snapshot,
        )
        if structure_evidence:
            feature_evidence["structure_evidence"] = structure_evidence
            structure_support = _clean_float(structure_evidence.get("structure_support_score"))
            if structure_support is not None:
                confidence_signals.append({"name": "structure_support_score", "value": structure_support, "source": "WAXS"})

        temperature_values = output.get("temperature_values", [])
        if not isinstance(temperature_values, list):
            temperature_values = []
        temperature_axis_evidence = _non_empty_mapping(
            [
                ("condition_label", str(output.get("condition_label", "") or "").strip() or None),
                ("condition_unit", str(output.get("condition_unit", "") or "").strip() or None),
                ("condition_source", str(output.get("condition_source", "") or "").strip() or None),
                ("condition_source_key", str(output.get("condition_source_key", "") or "").strip() or None),
                ("condition_source_text", str(output.get("condition_source_text", "") or "").strip() or None),
                ("condition_confidence", _clean_float(output.get("condition_confidence"))),
                ("condition_missing_frames", _clean_float(output.get("condition_missing_frames"))),
                ("condition_continuity_score", _clean_float(output.get("condition_continuity_score"))),
                ("temperature_values", temperature_values if temperature_values else None),
                ("temperature_min_C", _clean_float(output.get("temperature_min_C"))),
                ("temperature_max_C", _clean_float(output.get("temperature_max_C"))),
                ("temperature_missing_count", _clean_float(output.get("temperature_missing_count"))),
                ("temperature_duplicate_count", _clean_float(output.get("temperature_duplicate_count"))),
                ("temperature_monotonic", output.get("temperature_monotonic")),
                ("temperature_step_median_C", _clean_float(output.get("temperature_step_median_C"))),
                ("temperature_step_spread", _clean_float(output.get("temperature_step_spread"))),
                ("sequence_order_source", str(output.get("sequence_order_source", "") or "").strip() or None),
                ("sequence_direction", str(output.get("sequence_direction", "") or "").strip() or None),
                ("temperature_axis_confidence", _clean_float(output.get("temperature_axis_confidence"))),
            ]
        )
        if temperature_axis_evidence:
            feature_evidence["sequence_evidence"] = temperature_axis_evidence
            condition_evidence = temperature_axis_evidence
            feature_evidence["condition_evidence"] = condition_evidence
            confidence_signals.append(
                {
                    "name": "temperature_axis_confidence",
                    "value": _clean_float(output.get("temperature_axis_confidence")),
                    "source": "WAXS_temperature",
                }
            )

        frame_evidence_records = output.get("frame_evidence")
        if isinstance(frame_evidence_records, list) and frame_evidence_records:
            feature_evidence["frame_evidence"] = frame_evidence_records

        frame_summary_evidence = _non_empty_mapping(
            [
                ("frame_count", _clean_float(output.get("frame_count"))),
                ("frame_pass_count", _clean_float(output.get("frame_pass_count"))),
                ("frame_low_conf_count", _clean_float(output.get("frame_low_conf_count"))),
                ("valid_frame_count", _clean_float(output.get("valid_frame_count"))),
                ("failed_frame_count", _clean_float(output.get("failed_frame_count"))),
                ("frame_quality_distribution", output.get("frame_quality_distribution") if isinstance(output.get("frame_quality_distribution"), dict) else None),
                ("frame_constraint_summary", output.get("frame_constraint_summary") if isinstance(output.get("frame_constraint_summary"), dict) else None),
                ("low_conf_frame_indices", output.get("low_conf_frame_indices") if isinstance(output.get("low_conf_frame_indices"), list) else None),
                ("low_conf_temperature_values", output.get("low_conf_temperature_values") if isinstance(output.get("low_conf_temperature_values"), list) else None),
                ("dominant_frame_failure_type", str(output.get("dominant_frame_failure_type", "") or "").strip() or None),
                ("median_r_squared", _clean_float(output.get("median_r_squared"))),
                ("median_peak_count", _clean_float(output.get("median_peak_count"))),
                ("median_structure_support_score", _clean_float(output.get("median_structure_support_score"))),
                ("physical_support_pass_ratio", _clean_float(output.get("physical_support_pass_ratio"))),
            ]
        )
        if frame_summary_evidence:
            feature_evidence["frame_summary_evidence"] = frame_summary_evidence
            confidence_signals.append(
                {
                    "name": "frame_pass_ratio",
                    "value": _clean_float(frame_summary_evidence.get("physical_support_pass_ratio")),
                    "source": "WAXS_temperature",
                }
            )

        peak_family_evidence = _non_empty_mapping(
            [
                ("peak_family_count", _clean_float(output.get("peak_family_count"))),
                ("peak_family_assignment_method", str(output.get("peak_family_assignment_method", "") or "").strip() or None),
                ("peak_family_continuity_score", _clean_float(output.get("peak_family_continuity_score"))),
                ("peak_family_missing_frame_count", _clean_float(output.get("peak_family_missing_frame_count"))),
                ("peak_family_identity_swap_count", _clean_float(output.get("peak_family_identity_swap_count"))),
                ("peak_position_drift_per_family", output.get("peak_position_drift_per_family") if isinstance(output.get("peak_position_drift_per_family"), dict) else None),
                ("peak_width_drift_per_family", output.get("peak_width_drift_per_family") if isinstance(output.get("peak_width_drift_per_family"), dict) else None),
                ("peak_area_drift_per_family", output.get("peak_area_drift_per_family") if isinstance(output.get("peak_area_drift_per_family"), dict) else None),
                ("new_peak_birth_temperatures", output.get("new_peak_birth_temperatures") if isinstance(output.get("new_peak_birth_temperatures"), list) else None),
                ("peak_disappearance_temperatures", output.get("peak_disappearance_temperatures") if isinstance(output.get("peak_disappearance_temperatures"), list) else None),
                ("peak_family_fragmented_count", _clean_float(output.get("peak_family_fragmented_count"))),
                ("peak_family_missing_ratio", _clean_float(output.get("peak_family_missing_ratio"))),
                ("peak_family_tracks", output.get("peak_family_tracks") if isinstance(output.get("peak_family_tracks"), list) else None),
            ]
        )
        if peak_family_evidence:
            feature_evidence["peak_family_evidence"] = peak_family_evidence
            confidence_signals.append(
                {
                    "name": "peak_family_continuity_score",
                    "value": _clean_float(output.get("peak_family_continuity_score")),
                    "source": "WAXS_temperature",
                }
            )

        scherrer_trend_evidence = _non_empty_mapping(
            [
                ("D_values_nm", output.get("D_values_nm") if isinstance(output.get("D_values_nm"), list) else None),
                ("D_range_nm", output.get("D_range_nm") if isinstance(output.get("D_range_nm"), (list, tuple)) else None),
                ("D_slope_distribution", output.get("D_slope_distribution") if isinstance(output.get("D_slope_distribution"), dict) else None),
                ("D_trend_monotonicity", str(output.get("D_trend_monotonicity", "") or "").strip() or None),
                ("D_support_peak_count", _clean_float(output.get("D_support_peak_count"))),
                ("D_support_family_count", _clean_float(output.get("D_support_family_count"))),
                ("FWHM_values_by_family", output.get("FWHM_values_by_family") if isinstance(output.get("FWHM_values_by_family"), dict) else None),
                ("instrument_broadening_present", output.get("instrument_broadening_present")),
                ("D_trend_support_score", _clean_float(output.get("D_trend_support_score"))),
                ("D_confidence_by_frame", output.get("D_confidence_by_frame") if isinstance(output.get("D_confidence_by_frame"), list) else None),
                ("D_jump_single_frame_count", _clean_float(output.get("D_jump_single_frame_count"))),
                ("D_jump_single_frame_indices", output.get("D_jump_single_frame_indices") if isinstance(output.get("D_jump_single_frame_indices"), list) else None),
            ]
        )
        if scherrer_trend_evidence:
            feature_evidence["scherrer_trend_evidence"] = scherrer_trend_evidence
            confidence_signals.append(
                {
                    "name": "D_trend_support_score",
                    "value": _clean_float(output.get("D_trend_support_score")),
                    "source": "WAXS_temperature",
                }
            )

        crystallinity_trend_evidence = _non_empty_mapping(
            [
                ("Xc_values", output.get("Xc_values") if isinstance(output.get("Xc_values"), list) else None),
                ("Xc_range_pct", output.get("Xc_range_pct") if isinstance(output.get("Xc_range_pct"), (list, tuple)) else None),
                ("Xc_slope_distribution", output.get("Xc_slope_distribution") if isinstance(output.get("Xc_slope_distribution"), dict) else None),
                ("Xc_trend_monotonicity", str(output.get("Xc_trend_monotonicity", "") or "").strip() or None),
                ("Xc_background_sensitivity", _clean_float(output.get("Xc_background_sensitivity"))),
                ("Xc_peak_support_ratio", _clean_float(output.get("Xc_peak_support_ratio"))),
                ("Xc_transition_candidates", output.get("Xc_transition_candidates") if isinstance(output.get("Xc_transition_candidates"), list) else None),
                ("Xc_trend_support_score", _clean_float(output.get("Xc_trend_support_score"))),
                ("crystallinity_jump_single_frame_count", _clean_float(output.get("crystallinity_jump_single_frame_count"))),
                ("crystallinity_jump_single_frame_indices", output.get("crystallinity_jump_single_frame_indices") if isinstance(output.get("crystallinity_jump_single_frame_indices"), list) else None),
            ]
        )
        if crystallinity_trend_evidence:
            feature_evidence["trend_evidence"] = crystallinity_trend_evidence
            feature_evidence["crystallinity_trend_evidence"] = crystallinity_trend_evidence
            confidence_signals.append(
                {
                    "name": "Xc_trend_support_score",
                    "value": _clean_float(output.get("Xc_trend_support_score")),
                    "source": "WAXS_temperature",
                }
            )

        transition_evidence = _non_empty_mapping(
            [
                ("transition_candidate_count", _clean_float(output.get("transition_candidate_count"))),
                ("transition_support_score", _clean_float(output.get("transition_support_score"))),
                ("n_transitions", _clean_float(output.get("n_transitions"))),
                ("transition_candidates", output.get("Xc_transition_candidates") if isinstance(output.get("Xc_transition_candidates"), list) else None),
            ]
        )
        if transition_evidence:
            feature_evidence["transition_evidence"] = transition_evidence
            confidence_signals.append(
                {
                    "name": "transition_support_score",
                    "value": _clean_float(output.get("transition_support_score")),
                    "source": "WAXS_temperature",
                }
            )

        symptoms = _waxs_symptoms_from_constraints(constraints, output, validation, residual)
        for symptom in symptoms:
            actionable_symptoms.extend(symptom_bridge_lines(symptom))

    if residual_summary:
        actionable_symptoms.append(residual_summary)
    if validation_summary and validation_summary not in actionable_symptoms:
        actionable_symptoms.append(validation_summary)
    if not (technique_key == "IR" and is_ir_temperature_2d):
        actionable_symptoms.extend(symptom_action_hints(technique_key, residual_type, output))
    if technique_key == "SAXS":
        for symptom in symptoms:
            actionable_symptoms.extend(symptom_bridge_lines(symptom))
        triggered_names = constraint_summary.get("triggered_names", {}) if isinstance(constraint_summary, dict) else {}
        soft_warn_names = triggered_names.get("soft_warn", []) if isinstance(triggered_names, dict) else []
        if "fit_regions_unstable" in soft_warn_names and not any(
            "fit_regions_unstable" in str(item) for item in actionable_symptoms
        ):
            actionable_symptoms.append("fit_regions_unstable -> do not trust pretty figures; stabilize preprocessing before another AI round")
    elif technique_key == "WAXS":
        triggered_names = constraint_summary.get("triggered_names", {}) if isinstance(constraint_summary, dict) else {}
        soft_warn_names = triggered_names.get("soft_warn", []) if isinstance(triggered_names, dict) else []
        if "scherrer_instrument_broadening_unresolved" in soft_warn_names and not any(
            "scherrer_instrument_broadening_unresolved" in str(item) for item in actionable_symptoms
        ):
            actionable_symptoms.append("scherrer_instrument_broadening_unresolved -> keep D provisional until instrument broadening is modeled or documented")
        if "scherrer_jump_single_frame" in soft_warn_names and not any(
            "scherrer_jump_single_frame" in str(item) for item in actionable_symptoms
        ):
            actionable_symptoms.append("scherrer_jump_single_frame -> review the unstable frame before trusting the temperature trend")
        if "scherrer_dominated_by_peak_width_noise" in soft_warn_names and not any(
            "scherrer_dominated_by_peak_width_noise" in str(item) for item in actionable_symptoms
        ):
            actionable_symptoms.append("scherrer_dominated_by_peak_width_noise -> stabilize peak widths and family tracking before promoting D")

    actionable_symptoms = list(dict.fromkeys(item for item in actionable_symptoms if str(item).strip()))

    summary_bits = []
    if quality_flag:
        summary_bits.append(f"quality={quality_flag}")
    if residual_type and residual_type != "unknown":
        summary_bits.append(f"residual={residual_type}")
    if risk_flags:
        summary_bits.append(f"risks={len(list(dict.fromkeys(risk_flags)))}")
    if constraints:
        summary_bits.append(f"constraints={len(constraints)}")
    if constraint_summary.get("status") not in {"", "ok"}:
        summary_bits.append(f"constraint_status={constraint_summary.get('status')}")
    if constraint_summary.get("triggered_total"):
        summary_bits.append(f"triggered_constraints={constraint_summary.get('triggered_total')}")

    if technique_key == "NMR":
        if signal_evidence.get("median_snr") is not None:
            summary_bits.append(f"nmr_snr={signal_evidence.get('median_snr')}")
        if peak_evidence.get("peak_count") is not None:
            summary_bits.append(f"nmr_peaks={peak_evidence.get('peak_count')}")
        if structure_evidence.get("Xc_assignment_status"):
            summary_bits.append(f"nmr_xc={structure_evidence.get('Xc_assignment_status')}")

    if technique_key == "SAXS":
        if batch_evidence:
            summary_bits.append(f"batch_frames={batch_evidence.get('batch_frames')}")
        if condition_evidence.get("condition_source"):
            summary_bits.append(f"condition_source={condition_evidence.get('condition_source')}")
        if condition_evidence.get("condition_label") == "strain":
            strain_conf = condition_evidence.get("strain_axis_confidence")
            if strain_conf is not None:
                summary_bits.append(f"strain_axis={strain_conf}")
            if structure_evidence.get("Q_star_rel_mean") is not None:
                summary_bits.append(f"Q_star_rel={structure_evidence.get('Q_star_rel_mean')}")
            elif structure_evidence.get("Q_star_rel") is not None:
                summary_bits.append(f"Q_star_rel={structure_evidence.get('Q_star_rel')}")
            if structure_evidence.get("phi_void_mean") is not None:
                summary_bits.append(f"phi_void={structure_evidence.get('phi_void_mean')}")
            elif structure_evidence.get("phi_void") is not None:
                summary_bits.append(f"phi_void={structure_evidence.get('phi_void')}")
            if structure_evidence.get("f_Herman_mean") is not None:
                summary_bits.append(f"f_Herman={structure_evidence.get('f_Herman_mean')}")
            elif structure_evidence.get("f_Herman") is not None:
                summary_bits.append(f"f_Herman={structure_evidence.get('f_Herman')}")
            if structure_evidence.get("void_detected_frames") is not None:
                summary_bits.append(f"void_frames={structure_evidence.get('void_detected_frames')}")
            if structure_evidence.get("porod_slope_mean") is not None:
                summary_bits.append(f"porod_slope={structure_evidence.get('porod_slope_mean')}")
            if structure_evidence.get("strain_reliability_status"):
                summary_bits.append(f"strain_status={structure_evidence.get('strain_reliability_status')}")
            if structure_evidence.get("dominant_phase"):
                summary_bits.append(f"dominant_phase={structure_evidence.get('dominant_phase')}")
            if structure_evidence.get("paper_figure_candidate") is not None:
                summary_bits.append(f"paper_figure_candidate={bool(structure_evidence.get('paper_figure_candidate'))}")
            if structure_evidence.get("paper_conclusion_candidate") is not None:
                summary_bits.append(f"paper_candidate={bool(structure_evidence.get('paper_conclusion_candidate'))}")
            if structure_evidence.get("paper_conclusion_ready") is not None:
                summary_bits.append(f"paper_ready={bool(structure_evidence.get('paper_conclusion_ready'))}")
        if batch_evidence.get("batch_calibration_summary"):
            batch_calib = batch_evidence.get("batch_calibration_summary", {})
            if isinstance(batch_calib, dict) and batch_calib.get("fallback_ratio") is not None:
                summary_bits.append(f"fallback_ratio={batch_calib.get('fallback_ratio')}")
        if stability_evidence.get("stability_score") is not None:
            summary_bits.append(f"stability={stability_evidence.get('stability_score')}")
        if raw_structure_evidence.get("raw_structure_available"):
            summary_bits.append("raw_structure_available=True")
        if structure_evidence.get("lc_method"):
            summary_bits.append(f"lc_method={structure_evidence.get('lc_method')}")
        if structure_evidence.get("calibrated_fallback_active"):
            summary_bits.append(f"fallback={structure_evidence.get('calibrated_fallback_reason')}")
        if structure_evidence.get("calibration_skipped_reason"):
            summary_bits.append(f"calibration_skip={structure_evidence.get('calibration_skipped_reason')}")
        if structure_evidence.get("lamellar_interpretation_mode"):
            summary_bits.append(f"lamellar_mode={structure_evidence.get('lamellar_interpretation_mode')}")
        if structure_evidence.get("melting_window_status"):
            summary_bits.append(f"melting_window={structure_evidence.get('melting_window_status')}")
        if structure_evidence.get("lc_reliability_status"):
            summary_bits.append(f"lc_status={structure_evidence.get('lc_reliability_status')}")
        batch_structure = batch_evidence.get("batch_structure_summary", {}) if isinstance(batch_evidence.get("batch_structure_summary"), dict) else {}
        if batch_structure.get("diagnostic_only_rows") is not None:
            summary_bits.append(f"diagnostic_lc_rows={batch_structure.get('diagnostic_only_rows')}")
        if batch_structure.get("within_window_rows") is not None:
            summary_bits.append(f"melting_window_rows={batch_structure.get('within_window_rows')}")

    if technique_key == "DSC":
        if structure_evidence.get("structure_support_score") is not None:
            summary_bits.append(f"structure_support={structure_evidence.get('structure_support_score')}")
        if structure_evidence.get("event_support_score") is not None:
            summary_bits.append(f"event_support={structure_evidence.get('event_support_score')}")
        if structure_evidence.get("baseline_stability_score") is not None:
            summary_bits.append(f"baseline_stability={structure_evidence.get('baseline_stability_score')}")
        if structure_evidence.get("thermodynamic_consistency_score") is not None:
            summary_bits.append(f"thermo_consistency={structure_evidence.get('thermodynamic_consistency_score')}")
        if structure_evidence.get("paper_conclusion_candidate") is not None:
            summary_bits.append(f"paper_candidate={bool(structure_evidence.get('paper_conclusion_candidate'))}")
        if structure_evidence.get("paper_conclusion_ready") is not None:
            summary_bits.append(f"paper_ready={bool(structure_evidence.get('paper_conclusion_ready'))}")

    if technique_key == "WAXS" and peak_evidence and peak_evidence.get("peak_count") is not None:
        peak_count_value = _clean_float(peak_evidence.get("peak_count"))
        if peak_count_value is not None:
            confidence_signals.append({"name": "peak_evidence_peak_count", "value": peak_count_value, "source": "WAXS"})
        if output.get("temperature_axis_confidence") is not None:
            summary_bits.append(f"temperature_axis={output.get('temperature_axis_confidence')}")
        elif output.get("condition_confidence") is not None:
            summary_bits.append(f"condition_confidence={output.get('condition_confidence')}")
        if condition_evidence.get("condition_source"):
            summary_bits.append(f"condition_source={condition_evidence.get('condition_source')}")
        if structure_evidence.get("physical_support_pass") is not None:
            summary_bits.append(f"physical_support={bool(structure_evidence.get('physical_support_pass'))}")
        if structure_evidence.get("paper_ready_candidate") is not None:
            summary_bits.append(f"paper_ready={bool(structure_evidence.get('paper_ready_candidate'))}")

    if technique_key == "WAXS":
        if output.get("frame_count") is not None:
            summary_bits.append(f"frames={output.get('frame_count')}")
        if output.get("frame_low_conf_count") is not None:
            summary_bits.append(f"low_conf_frames={output.get('frame_low_conf_count')}")
        if output.get("dominant_frame_failure_type"):
            summary_bits.append(f"dominant_failure={output.get('dominant_frame_failure_type')}")
        if output.get("peak_family_count") is not None:
            summary_bits.append(f"peak_families={output.get('peak_family_count')}")
        if output.get("peak_family_continuity_score") is not None:
            summary_bits.append(f"family_continuity={output.get('peak_family_continuity_score')}")
        if output.get("peak_family_identity_swap_count") is not None:
            summary_bits.append(f"family_swaps={output.get('peak_family_identity_swap_count')}")
        if output.get("D_trend_support_score") is not None:
            summary_bits.append(f"D_trend={output.get('D_trend_support_score')}")
        if output.get("D_trend_monotonicity"):
            summary_bits.append(f"D_trend_mode={output.get('D_trend_monotonicity')}")
        if output.get("Xc_trend_support_score") is not None:
            summary_bits.append(f"xc_trend={output.get('Xc_trend_support_score')}")
        if output.get("transition_support_score") is not None:
            summary_bits.append(f"transition_support={output.get('transition_support_score')}")
        if output.get("Xc_trend_monotonicity"):
            summary_bits.append(f"xc_trend_mode={output.get('Xc_trend_monotonicity')}")

    if is_ir_temperature_2d:
        temp_metrics = _ir_temperature_2d_metrics(output, validation)
        if temp_metrics.get("n_frames") is not None:
            summary_bits.append(f"frames={temp_metrics.get('n_frames')}")
        if temp_metrics.get("T_range_C"):
            summary_bits.append(f"T_range={temp_metrics.get('T_range_C')}")
        if temp_metrics.get("sequence_axis_score") is not None:
            summary_bits.append(f"sequence_axis={temp_metrics.get('sequence_axis_score')}")
        if temp_metrics.get("matrix_quality_score") is not None:
            summary_bits.append(f"matrix_quality={temp_metrics.get('matrix_quality_score')}")
        if temp_metrics.get("cos_signal_score") is not None:
            summary_bits.append(f"cos_signal={temp_metrics.get('cos_signal_score')}")
        if temp_metrics.get("sync_cross_peak_count") is not None:
            summary_bits.append(f"sync_peaks={temp_metrics.get('sync_cross_peak_count')}")
        if temp_metrics.get("async_cross_peak_count") is not None:
            summary_bits.append(f"async_peaks={temp_metrics.get('async_cross_peak_count')}")
        if temp_metrics.get("transition_count") is not None:
            summary_bits.append(f"transitions={temp_metrics.get('transition_count')}")
        if temp_metrics.get("band_index_transition_support_band_count") is not None:
            summary_bits.append(f"band_support={temp_metrics.get('band_index_transition_support_band_count')}")
        if temp_metrics.get("band_index_transition_reproducible") is not None:
            summary_bits.append(f"trend_reproducible={bool(temp_metrics.get('band_index_transition_reproducible'))}")
        if temp_metrics.get("neg_fraction") is not None:
            summary_bits.append(f"neg_fraction={temp_metrics.get('neg_fraction')}")
        if temp_metrics.get("interpretation_ready") is not None:
            summary_bits.append(f"interpretation_ready={bool(temp_metrics.get('interpretation_ready'))}")
        if temp_metrics.get("paper_conclusion_ready") is not None:
            summary_bits.append(f"paper_ready={bool(temp_metrics.get('paper_conclusion_ready'))}")
    elif technique_key == "IR":
        if peak_evidence.get("peak_count") is not None:
            summary_bits.append(f"peak_count={peak_evidence.get('peak_count')}")
        if assignment_evidence.get("assignment_confidence") is not None:
            summary_bits.append(f"assignment_confidence={assignment_evidence.get('assignment_confidence')}")
        if assignment_evidence.get("key_band_support_score") is not None:
            summary_bits.append(f"key_band_support={assignment_evidence.get('key_band_support_score')}")
        if assignment_evidence.get("peak_coverage_score") is not None:
            summary_bits.append(f"peak_coverage={assignment_evidence.get('peak_coverage_score')}")
        if structure_evidence.get("baseline_stability_score") is not None:
            summary_bits.append(f"baseline_stability={structure_evidence.get('baseline_stability_score')}")
        if reference_evidence.get("band_count") is not None:
            summary_bits.append(f"ref_bands={reference_evidence.get('band_count')}")
        if reference_evidence.get("hit_count") is not None:
            summary_bits.append(f"ref_hits={reference_evidence.get('hit_count')}")
        if structure_evidence.get("reference_band_missing_count") is not None:
            summary_bits.append(f"ref_missing={structure_evidence.get('reference_band_missing_count')}")
        if structure_evidence.get("characteristic_band_support_ok") is not None:
            summary_bits.append(f"band_support={bool(structure_evidence.get('characteristic_band_support_ok'))}")
        if structure_evidence.get("paper_conclusion_ready") is not None:
            summary_bits.append(f"paper_ready={bool(structure_evidence.get('paper_conclusion_ready'))}")

    return AnalysisEvidence(
        technique=technique_key,
        summary="; ".join(summary_bits),
        fit_evidence=fit_evidence,
        physical_evidence=physical_evidence,
        residual_evidence=residual_evidence,
        feature_evidence=feature_evidence,
        signal_evidence=signal_evidence,
        peak_evidence=peak_evidence,
        assignment_evidence=assignment_evidence,
        reference_evidence=reference_evidence,
        background_evidence=background_evidence,
        phase_evidence=phase_evidence,
        transform_evidence=transform_evidence,
        structure_evidence=structure_evidence,
        raw_structure_evidence=raw_structure_evidence,
        batch_evidence=batch_evidence,
        condition_evidence=condition_evidence,
        stability_evidence=stability_evidence,
        symptoms=symptoms,
        risk_flags=list(dict.fromkeys(risk_flags)),
        confidence_signals=confidence_signals,
        actionable_symptoms=actionable_symptoms,
        constraints=constraints,
        constraint_summary=constraint_summary,
        cross_validation=validation.get("cross_validation", {}) if isinstance(validation.get("cross_validation", {}), dict) else {},
        source_fields=sorted(
            set(
                list(fit_evidence.keys())
                + list(physical_evidence.keys())
                + list(feature_evidence.keys())
                + list(residual_evidence.keys())
                + list(signal_evidence.keys())
                + list(peak_evidence.keys())
                + list(background_evidence.keys())
                + list(phase_evidence.keys())
                + list(transform_evidence.keys())
                + list(structure_evidence.keys())
                + list(reference_evidence.keys())
                + list(raw_structure_evidence.keys())
                + list(batch_evidence.keys())
                + list(condition_evidence.keys())
                + list(stability_evidence.keys())
                + (["symptoms"] if symptoms else [])
            )
        ),
    )
