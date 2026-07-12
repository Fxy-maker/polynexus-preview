"""Publication eligibility decisions from emitted SAXS evidence only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ..figures.contracts import FigureEligibilityDecision
from .figure_common import SAXSFrameView


def _emitted_values(frame: SAXSFrameView, key: str) -> tuple[Any, ...]:
    values: list[Any] = []
    if key in frame.parameters:
        values.append(frame.parameters[key])
    final_parameters = getattr(frame.analysis, "final_parameters", {})
    if isinstance(final_parameters, Mapping) and key in final_parameters:
        values.append(final_parameters[key])
    if hasattr(frame.analysis, key):
        values.append(getattr(frame.analysis, key))
    return tuple(values)


def _explicit_bool(values: Sequence[Any]) -> bool | None:
    emitted = [bool(value) for value in values if isinstance(value, (bool, np.bool_))]
    if False in emitted:
        return False
    if True in emitted:
        return True
    return None


def classify_frame_eligibility(frame: SAXSFrameView) -> FigureEligibilityDecision:
    """Classify a frame without deriving, repairing, or recomputing evidence."""

    quality_tokens = tuple(
        token.strip()
        for value in _emitted_values(frame, "quality_flag")
        for token in str(value or "").upper().split(";")
        if token.strip()
    )
    if any(token.startswith("ERROR") for token in quality_tokens):
        return FigureEligibilityDecision("diagnostic", ("analysis_error",))

    paper_candidate = _explicit_bool(_emitted_values(frame, "paper_figure_candidate"))
    if paper_candidate is False:
        return FigureEligibilityDecision(
            "diagnostic", ("analysis_rejected_paper_figure",)
        )
    if paper_candidate is True:
        return FigureEligibilityDecision("main", ("analysis_approved_paper_figure",))

    reliability = tuple(
        str(value or "").strip().lower()
        for value in _emitted_values(frame, "lc_reliability_status")
    )
    if "usable" in reliability:
        return FigureEligibilityDecision("main", ("usable_lamellar_result",))
    if "OK" in quality_tokens:
        return FigureEligibilityDecision("main", ("quality_ok",))
    return FigureEligibilityDecision("si", ("limited_or_unclassified_quality",))


__all__ = ["FigureEligibilityDecision", "classify_frame_eligibility"]
