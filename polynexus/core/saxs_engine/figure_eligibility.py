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

    paper_candidate = _explicit_bool(
        _emitted_values(frame, "paper_figure_candidate")
    )
    if paper_candidate is False:
        return FigureEligibilityDecision(
            "diagnostic",
            ("analysis_rejected_paper_figure",),
        )
    if paper_candidate is True:
        return FigureEligibilityDecision("main", ("analysis_approved_paper_figure",))

    if require_explicit_publication_candidate:
        return FigureEligibilityDecision(
            "si",
            ("publication_authorization_missing",),
        )

    reliability_values = tuple(
        str(value or "").strip().lower()
        for value in _emitted_values(frame, "lc_reliability_status")
    )
    if "usable" in reliability_values:
        return FigureEligibilityDecision("main", ("usable_lamellar_result",))

    if "OK" in quality_tokens:
        return FigureEligibilityDecision("main", ("quality_ok",))
    return FigureEligibilityDecision("si", ("limited_or_unclassified_quality",))


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
    """Read the emitted Q_star_valid gate; never infer validity from a value."""

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
