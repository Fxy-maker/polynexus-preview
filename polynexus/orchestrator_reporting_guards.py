from __future__ import annotations

import math
from typing import Any


def _quality_guard(self: Any, candidate: Any) -> tuple[bool, str]:
    if self.technique == "dsc":
        quality = self._safe_float(candidate.output_parameters.get("quality_score", 1.0))
        if quality < 0.5:
            return False, f"quality_score below PHYS guard threshold: {quality:.3f}"
    elif self.technique == "saxs":
        quality = self._safe_float(candidate.output_parameters.get("quality_score", 1.0))
        if quality < 0.05:
            return False, f"quality_score below PHYS guard threshold: {quality:.3f}"
    elif self.technique == "ir":
        quality = self._safe_float(candidate.output_parameters.get("quality_score", 1.0))
        if quality < 0.05:
            return False, f"quality_score below IR assignment guard threshold: {quality:.3f}"
    elif self.technique == "nmr":
        quality = self._safe_float(candidate.output_parameters.get("quality_score", 1.0))
        if quality < -10.0:
            return False, f"quality_score below NMR fit guard threshold: {quality:.3f}"
    return True, ""


def _objective_gain_threshold(self: Any) -> float:
    threshold = 0.01
    joint_ai_context = self._joint_ai_context()
    if not joint_ai_context:
        return threshold

    issue_count = self._safe_float(joint_ai_context.get("issue_count"))
    warning_count = self._safe_float(joint_ai_context.get("warning_count"))
    error_count = self._safe_float(joint_ai_context.get("error_count"))
    issue_families = joint_ai_context.get("issue_families")

    if math.isfinite(issue_count) and issue_count > 0:
        threshold += 0.004 * min(issue_count, 5.0)
    if math.isfinite(warning_count) and warning_count > 0:
        threshold += 0.001 * min(warning_count, 4.0)
    if math.isfinite(error_count) and error_count > 0:
        threshold += 0.008 * min(error_count, 3.0)
    if isinstance(issue_families, list):
        families = {str(item).strip().lower() for item in issue_families if str(item).strip()}
        if "phi_c inconsistency" in families:
            threshold += 0.002
        if "tm bidirectional gap" in families:
            threshold += 0.002
        if "l consistency unstable" in families:
            threshold += 0.0015
    return min(threshold, 0.05)


def _r_squared_drop_tolerance(self: Any) -> float:
    return 0.001


def _component_drop_tolerance(self: Any) -> float:
    return 0.06
