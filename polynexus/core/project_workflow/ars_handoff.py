"""Validated ARS Results/Discussion handoff built from package artifacts."""

from __future__ import annotations

from typing import Any, Mapping

from .analysis_plan_evaluation import project_analysis_plan_evaluation


def analysis_plan_evaluation_for_ars(plan: Any, evaluation: Any) -> dict[str, Any]:
    """Expose the same bounded plan view to ARS without adding prose."""
    return project_analysis_plan_evaluation(plan, evaluation)


def build_ars_writing_input(
    *,
    package_manifest: Mapping[str, Any],
    writing_evidence: Mapping[str, Any],
    citation_metrics: Mapping[str, Any],
    limitations: Mapping[str, Any],
) -> dict[str, Any]:
    """Build an evidence map; this function deliberately emits no prose."""
    records = citation_metrics.get("records", ())
    if not isinstance(records, list):
        raise ValueError("citation metric records are invalid")
    metric_by_id = {str(item.get("metric_id")): item for item in records if isinstance(item, Mapping)}
    sections: dict[str, dict[str, Any]] = {}
    review_items: list[dict[str, str]] = []
    for technique, group in writing_evidence.get("techniques", {}).items():
        if not isinstance(group, Mapping):
            continue
        evidence_values: list[dict[str, Any]] = []
        for item in group.get("evidence", ()):
            if not isinstance(item, Mapping):
                continue
            ids = [str(value) for value in item.get("citation_metric_ids", ())]
            linked = []
            for metric_id in ids:
                metric = metric_by_id.get(metric_id)
                if metric is None or str(metric.get("evidence_id")) != str(item.get("evidence_id")):
                    raise ValueError("writing evidence metric link is invalid")
                linked.append(metric)
            result_ids = [str(metric["metric_id"]) for metric in linked if metric.get("writing_eligibility") == "results_candidate"]
            diagnostic_ids = [str(metric["metric_id"]) for metric in linked if metric.get("writing_eligibility") != "results_candidate"]
            prohibited = list(dict.fromkeys(str(value) for value in item.get("disallowed_conclusions", ()) if value))
            limitations_local = list(dict.fromkeys(str(value) for value in item.get("limitations", ()) if value))
            if item.get("status") == "review_required" or prohibited:
                review_items.append({
                    "evidence_id": str(item.get("evidence_id", "")),
                    "action": "human_scientific_review",
                    "reason": "; ".join(prohibited) or "review_required",
                })
            evidence_values.append({
                "evidence_id": item.get("evidence_id"),
                "status": item.get("status", "unknown"),
                "source_runs": list(item.get("source_runs", ())),
                "raw_sources": list(item.get("raw_sources", ())),
                "figures": list(item.get("figures", ())),
                "tables": list(item.get("tables", ())),
                "results_metric_ids": result_ids,
                "discussion_metric_ids": diagnostic_ids,
                "supported_interpretations": list(item.get("supported_interpretations", ())),
                "prohibited_conclusions": prohibited,
                "limitations": limitations_local,
            })
        sections[str(technique).lower()] = {
            "run_ids": list(group.get("run_ids", ())),
            "statuses": list(group.get("statuses", ())),
            "evidence": evidence_values,
        }
    payload = {
        "version": 1,
        "package": {
            "package_id": package_manifest.get("package_id"),
            "version": package_manifest.get("version"),
            "status": package_manifest.get("status"),
            "run_ids": list(package_manifest.get("run_ids", ())),
            "questions": list(package_manifest.get("questions", ())),
        },
        "techniques": sections,
        "citation_metrics": "citation-metrics.json",
        "allowed_results": [
            metric_id for metric_id, metric in metric_by_id.items()
            if metric.get("writing_eligibility") == "results_candidate"
        ],
        "discussion_only": [
            metric_id for metric_id, metric in metric_by_id.items()
            if metric.get("writing_eligibility") != "results_candidate"
        ],
        "limitations": list(limitations.get("limitations", ())),
        "human_review": list({(item["evidence_id"], item["action"], item["reason"]): item for item in review_items}.values()),
        "prohibited_cross_technique_claims": ["sample_identity", "batch_identity", "causal_mechanism"],
    }
    validate_ars_writing_input(payload, citation_metrics=citation_metrics)
    return payload


def validate_ars_writing_input(payload: Mapping[str, Any], *, citation_metrics: Mapping[str, Any]) -> None:
    if payload.get("version") != 1 or not isinstance(payload.get("techniques"), Mapping):
        raise ValueError("ARS writing input is invalid")
    known = {
        str(item.get("metric_id")): item
        for item in citation_metrics.get("records", ())
        if isinstance(item, Mapping) and item.get("metric_id")
    }
    allowed = set(str(value) for value in payload.get("allowed_results", ()))
    discussion = set(str(value) for value in payload.get("discussion_only", ()))
    if not allowed.issubset(known) or not discussion.issubset(known) or allowed & discussion:
        raise ValueError("ARS metric eligibility projection is invalid")
    for section in payload["techniques"].values():
        for item in section.get("evidence", ()):
            for metric_id in item.get("results_metric_ids", ()):
                if metric_id not in allowed:
                    raise ValueError("diagnostic metric promoted to Results")
            for metric_id in item.get("discussion_metric_ids", ()):
                if metric_id not in discussion:
                    raise ValueError("Results metric projected as diagnostic")


__all__ = ["build_ars_writing_input", "validate_ars_writing_input", "analysis_plan_evaluation_for_ars"]
