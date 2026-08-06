"""Publication eligibility decisions based on emitted SAXS evidence only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .figure_common import SAXSFrameView


@dataclass(frozen=True)
class FigureEligibilityDecision:
    """The highest publication role supported by an existing frame result."""

    highest_role: str
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(self.reasons))


def _analysis_parameters(frame: SAXSFrameView) -> Mapping[str, Any]:
    parameters = getattr(frame.analysis, "final_parameters", {})
    return parameters if isinstance(parameters, Mapping) else {}


def _emitted_values(frame: SAXSFrameView, key: str) -> tuple[Any, ...]:
    values: list[Any] = []
    if key in frame.parameters:
        values.append(frame.parameters[key])
    analysis_parameters = _analysis_parameters(frame)
    if key in analysis_parameters:
        values.append(analysis_parameters[key])
    if hasattr(frame.analysis, key):
        values.append(getattr(frame.analysis, key))
    return tuple(values)


def _explicit_bool(values: Sequence[Any]) -> bool | None:
    emitted: list[bool] = []
    for value in values:
        if isinstance(value, (bool, np.bool_)):
            emitted.append(bool(value))
    if False in emitted:
        return False
    if True in emitted:
        return True
    return None


def _geometry_gate(frame: SAXSFrameView) -> tuple[bool, str]:
    """Require complete detector geometry when detector evidence is emitted."""
    for source in _emitted_values(frame, "geometry_source"):
        source_key = str(source or "").strip().lower()
        if source_key in {"header_partial", "config_default", "missing"}:
            return False, "geometry_incomplete"
    for confidence in _emitted_values(frame, "geometry_confidence"):
        try:
            if np.isfinite(float(confidence)) and float(confidence) < 0.95:
                return False, "geometry_incomplete"
        except (TypeError, ValueError, OverflowError):
            continue
    reports = _emitted_values(frame, "detector_quality_report")
    saw_report = False
    for report in reports:
        if not isinstance(report, Mapping):
            continue
        saw_report = True
        geometry = report.get("geometry_provenance")
        if not isinstance(geometry, Mapping):
            return False, "geometry_provenance_missing"
        validity = str(geometry.get("validity") or "").strip().lower()
        field_sources = geometry.get("field_sources")
        complete = validity in {"validated", "metadata_complete", "configured_shape_match"}
        complete = complete and isinstance(field_sources, Mapping) and all(
            str(field_sources.get(name) or "").strip()
            for name in ("wavelength_m", "pixel_size_m", "sdd_m", "beam_center_x", "beam_center_y")
        )
        if not complete:
            return False, "geometry_incomplete"
    return True, "geometry_not_applicable" if not saw_report else "geometry_complete"


def classify_frame_eligibility(
    frame: SAXSFrameView,
    *,
    require_explicit_publication_candidate: bool = False,
) -> FigureEligibilityDecision:
    """Classify one frame without deriving or repairing analysis evidence."""

    quality_tokens = tuple(
        token.strip()
        for value in _emitted_values(frame, "quality_flag")
        for token in str(value or "").upper().split(";")
        if token.strip()
    )
    if any(token.startswith("ERROR") for token in quality_tokens):
        return FigureEligibilityDecision("diagnostic", ("analysis_error",))

    geometry_ok, geometry_reason = _geometry_gate(frame)
    if not geometry_ok:
        return FigureEligibilityDecision("si", (geometry_reason,))

    acceptance_audits = _emitted_values(frame, "scientific_acceptance_audit")
    for audit in acceptance_audits:
        if isinstance(audit, Mapping):
            calibration = audit.get("absolute_calibration")
            reasons = audit.get("reason_codes") or ()
            if (
                isinstance(calibration, Mapping)
                and calibration.get("available") is False
                and "absolute_contrast_required" in reasons
            ):
                return FigureEligibilityDecision("si", ("absolute_contrast_required",))

    physical_gate = (
        q_star_valid_for_invariant_panels(frame)
        or "usable" in {
            value.strip().lower()
            for value in _emitted_values(frame, "lc_reliability_status")
        }
    )

    paper_candidate = _explicit_bool(
        _emitted_values(frame, "paper_figure_candidate")
    )
    if paper_candidate is False:
        return FigureEligibilityDecision(
            "diagnostic",
            ("analysis_rejected_paper_figure",),
        )
    if paper_candidate is True:
        if physical_gate:
            return FigureEligibilityDecision("main", ("analysis_approved_paper_figure",))
        return FigureEligibilityDecision("si", ("physical_eligibility_missing",))

    if require_explicit_publication_candidate:
        return FigureEligibilityDecision(
            "si",
            ("publication_authorization_missing",),
        )

    reliability_values = tuple(
        str(value or "").strip().lower()
        for value in _emitted_values(frame, "lc_reliability_status")
    )
    if "usable" in reliability_values and physical_gate:
        return FigureEligibilityDecision("main", ("usable_lamellar_result",))

    if "OK" in quality_tokens and physical_gate:
        return FigureEligibilityDecision("main", ("quality_ok",))
    reason = "limited_or_unclassified_quality" if "OK" not in quality_tokens else "physical_eligibility_missing"
    return FigureEligibilityDecision("si", (reason,))


def _is_finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def trend_panel_eligible(
    values: Sequence[Any],
    *,
    minimum_points: int = 3,
) -> bool:
    """Return whether a trend has enough existing finite values to draw a line."""

    required_points = max(3, minimum_points)
    return sum(_is_finite(value) for value in values) >= required_points


def q_star_valid_for_invariant_panels(frame: SAXSFrameView) -> bool:
    """Read the emitted invariant validity gate without inferring from values."""

    canonical = _emitted_values(frame, "invariant_Q_valid")
    if canonical:
        return _explicit_bool(canonical) is True
    return _explicit_bool(_emitted_values(frame, "Q_star_valid")) is True


def invariant_panel_eligible(
    frames: Sequence[SAXSFrameView],
    values: Sequence[Any],
    *,
    minimum_points: int = 3,
) -> bool:
    """Gate invariant trends using both finite values and emitted validity flags."""

    valid_values = tuple(
        value
        for frame, value in zip(frames, values)
        if q_star_valid_for_invariant_panels(frame)
    )
    return trend_panel_eligible(valid_values, minimum_points=minimum_points)


def crystallinity_panel_eligible(
    frames: Sequence[SAXSFrameView],
    values: Sequence[Any],
    *,
    minimum_points: int = 3,
) -> bool:
    """Apply the same emitted Q_star_valid gate to invariant-derived Xc trends."""

    return invariant_panel_eligible(
        frames,
        values,
        minimum_points=minimum_points,
    )


__all__ = [
    "FigureEligibilityDecision",
    "classify_frame_eligibility",
    "crystallinity_panel_eligible",
    "invariant_panel_eligible",
    "q_star_valid_for_invariant_panels",
    "trend_panel_eligible",
]
