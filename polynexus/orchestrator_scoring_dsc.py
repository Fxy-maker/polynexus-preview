from __future__ import annotations

from typing import Any


def _dsc_support_snapshot(
    self: Any,
    output: dict[str, Any],
    analysis_evidence: dict[str, Any],
) -> dict[str, Any]:
    if self.technique != "dsc":
        return {
            "event_support_score": 1.0,
            "baseline_stability_score": 1.0,
            "thermodynamic_consistency_score": 1.0,
            "crystallinity_support_score": 1.0,
            "dsc_support_score": 1.0,
            "scan_r_squared_median": 1.0,
            "scan_r_squared_spread": 0.0,
            "supported_event_fraction": 1.0,
            "supported_component_count": 0.0,
            "triggered_constraint_count": 0.0,
            "validation_passed_count": 0.0,
            "validation_total_count": 0.0,
        }

    output = dict(output or {})
    analysis_evidence = dict(analysis_evidence or {})
    feature_evidence = analysis_evidence.get("feature_evidence", {})
    if not isinstance(feature_evidence, dict):
        feature_evidence = {}
    event_evidence = feature_evidence.get("event_support_evidence", {})
    if not isinstance(event_evidence, dict):
        event_evidence = {}
    baseline_evidence = feature_evidence.get("baseline_evidence", {})
    if not isinstance(baseline_evidence, dict):
        baseline_evidence = {}
    crystallinity_evidence = feature_evidence.get("crystallinity_evidence", {})
    if not isinstance(crystallinity_evidence, dict):
        crystallinity_evidence = {}

    cross_validation = analysis_evidence.get("cross_validation", {})
    validation_passed_count = 0.0
    validation_total_count = 0.0
    if isinstance(cross_validation, dict):

        def _visit(node: Any) -> None:
            nonlocal validation_passed_count, validation_total_count
            if isinstance(node, dict):
                if "passed" in node:
                    validation_total_count += 1.0
                    if bool(node.get("passed")):
                        validation_passed_count += 1.0
                else:
                    for value in node.values():
                        _visit(value)
            elif isinstance(node, list):
                for value in node:
                    _visit(value)

        _visit(cross_validation)

    event_support_score = self._safe_float(
        event_evidence.get(
            "event_support_score",
            output.get("event_support_score", 0.0),
        )
    )
    baseline_stability_score = self._safe_float(
        event_evidence.get(
            "baseline_stability_score",
            baseline_evidence.get(
                "baseline_stability_score",
                output.get("baseline_stability_score", 0.0),
            ),
        )
    )
    thermodynamic_consistency_score = self._safe_float(
        event_evidence.get(
            "thermodynamic_consistency_score",
            output.get("thermodynamic_consistency_score", 0.0),
        )
    )
    supported_event_fraction = self._safe_float(
        event_evidence.get("supported_event_fraction", 0.0)
    )
    supported_component_count = self._safe_float(
        event_evidence.get("supported_component_count", 0.0)
    )
    scan_r_squared_median = self._safe_float(
        event_evidence.get(
            "scan_r_squared_median",
            output.get("scan_r_squared_median", output.get("scan_r_squared", 0.0)),
        )
    )
    scan_r_squared_spread = self._safe_float(
        event_evidence.get("scan_r_squared_spread", output.get("scan_r_squared_spread", 0.0))
    )
    quality_score = self._safe_float(output.get("quality_score", 0.0))
    crystallinity_support_score = self._safe_float(
        crystallinity_evidence.get(
            "crystallinity_support_score",
            output.get("crystallinity_support_score", 0.0),
        )
    )
    if crystallinity_support_score <= 0.0:
        crystallinity_support_score = max(
            0.0,
            min(
                1.0,
                0.45 * (1.0 if self._safe_float(output.get("Xc_pct")) > 0 else 0.0)
                + 0.35
                * (
                    1.0
                    if self._safe_float(output.get("DHm_Jg")) not in {None, 0.0}
                    else 0.0
                )
                + 0.20 * event_support_score,
            ),
        )
    constraint_summary = analysis_evidence.get("constraint_summary", {})
    if not isinstance(constraint_summary, dict):
        constraint_summary = {}
    triggered_constraint_count = self._safe_float(
        constraint_summary.get("triggered_total", 0.0)
    )

    dsc_support_score = max(
        0.0,
        min(
            1.0,
            0.30 * event_support_score
            + 0.22 * baseline_stability_score
            + 0.18 * thermodynamic_consistency_score
            + 0.18 * crystallinity_support_score
            + 0.12 * max(0.0, min(1.0, quality_score)),
        ),
    )
    if validation_total_count > 0:
        dsc_support_score = min(
            dsc_support_score,
            0.85 + 0.15 * (validation_passed_count / validation_total_count),
        )

    return {
        "event_support_score": event_support_score,
        "baseline_stability_score": baseline_stability_score,
        "thermodynamic_consistency_score": thermodynamic_consistency_score,
        "crystallinity_support_score": crystallinity_support_score,
        "dsc_support_score": dsc_support_score,
        "scan_r_squared_median": scan_r_squared_median,
        "scan_r_squared_spread": scan_r_squared_spread,
        "supported_event_fraction": supported_event_fraction,
        "supported_component_count": supported_component_count,
        "triggered_constraint_count": triggered_constraint_count,
        "validation_passed_count": validation_passed_count,
        "validation_total_count": validation_total_count,
    }
