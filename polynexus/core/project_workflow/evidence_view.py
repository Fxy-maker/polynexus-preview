"""Technique-neutral read model for an immutable evidence package."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .figure_index import FigureIndexEntry, load_figure_index


@dataclass(frozen=True)
class EvidenceTechniqueView:
    key: str
    run_ids: tuple[str, ...]
    statuses: tuple[str, ...]
    evidence_count: int


@dataclass(frozen=True)
class EvidenceMetricView:
    metric_id: str
    technique: str
    metric_key: str
    value: float | int
    unit: str
    method: str
    source_locator: str
    evidence_id: str
    run_id: str
    raw_source_hashes: tuple[str, ...]
    status: str
    writing_eligibility: str
    reason_codes: tuple[str, ...]
    figures: tuple[str, ...]
    tables: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceItemView:
    evidence_id: str
    technique: str
    status: str
    source_runs: tuple[str, ...]
    raw_sources: tuple[str, ...]
    figures: tuple[str, ...]
    tables: tuple[str, ...]
    results_metric_ids: tuple[str, ...]
    discussion_metric_ids: tuple[str, ...]
    supported_interpretations: tuple[str, ...]
    prohibited_conclusions: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class HumanReviewView:
    evidence_id: str
    action: str
    reason: str


@dataclass(frozen=True)
class EvidencePackageView:
    package_id: str
    version: int
    status: str
    run_ids: tuple[str, ...]
    questions: tuple[str, ...]
    techniques: tuple[EvidenceTechniqueView, ...]
    evidence: tuple[EvidenceItemView, ...]
    metrics: tuple[EvidenceMetricView, ...]
    figures: tuple[str, ...]
    tables: tuple[str, ...]
    limitations: tuple[str, ...]
    human_review: tuple[HumanReviewView, ...]
    figure_views: tuple[FigureIndexEntry, ...] = ()
    package_root: str = ""


def load_evidence_package_view(package_path: str | Path) -> EvidencePackageView:
    root = Path(package_path).expanduser().resolve()
    manifest = _read(root, "manifest.json")
    techniques_payload = _read(root, "techniques.json").get("techniques", {})
    writing = _read(root, "writing-evidence.json").get("techniques", {})
    metric_file = str(manifest.get("citation_metrics", "citation-metrics.json"))
    metrics_payload = _read(root, metric_file)
    ars_file = str(manifest.get("ars_writing_input", "ars-writing-input.json"))
    ars = _read(root, ars_file)
    limitations = _read(root, "limitations.json").get("limitations", manifest.get("limitations", ()))
    if not isinstance(techniques_payload, Mapping) or not isinstance(writing, Mapping):
        raise ValueError("evidence package techniques are invalid")
    records = metrics_payload.get("records", ())
    if not isinstance(records, list):
        raise ValueError("evidence package metrics are invalid")
    metric_views: list[EvidenceMetricView] = []
    metric_by_id: dict[str, EvidenceMetricView] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("metric record is invalid")
        try:
            view = EvidenceMetricView(
                metric_id=str(record["metric_id"]), technique=str(record["technique"]),
                metric_key=str(record["metric_key"]), value=record["value"], unit=str(record["unit"]),
                method=str(record["method"]), source_locator=str(record["source_locator"]),
                evidence_id=str(record["evidence_id"]), run_id=str(record["run_id"]),
                raw_source_hashes=tuple(str(value) for value in record.get("raw_source_hashes", ())),
                status=str(record["status"]), writing_eligibility=str(record["writing_eligibility"]),
                reason_codes=tuple(str(value) for value in record.get("reason_codes", ())),
                figures=tuple(str(value) for value in record.get("figures", ())),
                tables=tuple(str(value) for value in record.get("tables", ())),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("metric record is invalid") from exc
        if not view.metric_id or view.metric_id in metric_by_id:
            raise ValueError("metric IDs are invalid")
        metric_by_id[view.metric_id] = view
        metric_views.append(view)
    evidence_views: list[EvidenceItemView] = []
    for technique, group in writing.items():
        if not isinstance(group, Mapping):
            raise ValueError("writing evidence is invalid")
        for item in group.get("evidence", ()):
            if not isinstance(item, Mapping):
                raise ValueError("writing evidence item is invalid")
            all_ids = tuple(str(value) for value in item.get("citation_metric_ids", ()))
            ars_item = _ars_evidence_item(ars, str(technique).lower(), str(item.get("evidence_id", "")))
            result_ids = tuple(str(value) for value in ars_item.get("results_metric_ids", ()))
            discussion_ids = tuple(str(value) for value in ars_item.get("discussion_metric_ids", ()))
            linked = all_ids or (*result_ids, *discussion_ids)
            for metric_id in linked:
                metric = metric_by_id.get(metric_id)
                if metric is None or metric.evidence_id != str(item.get("evidence_id", "")):
                    raise ValueError("metric evidence reference is invalid")
            if set(linked) != set((*result_ids, *discussion_ids)):
                raise ValueError("ARS metric evidence reference is invalid")
            for metric_id in result_ids:
                if metric_by_id[metric_id].writing_eligibility != "results_candidate":
                    raise ValueError("diagnostic metric promoted to Results")
            for metric_id in discussion_ids:
                if metric_by_id[metric_id].writing_eligibility == "results_candidate":
                    raise ValueError("Results metric projected as diagnostic")
            evidence_views.append(EvidenceItemView(
                evidence_id=str(item.get("evidence_id", "")), technique=str(technique).lower(),
                status=str(item.get("status", "unknown")),
                source_runs=tuple(str(value) for value in item.get("source_runs", ())),
                raw_sources=tuple(str(value) for value in item.get("raw_sources", ())),
                figures=tuple(str(value) for value in item.get("figures", ())),
                tables=tuple(str(value) for value in item.get("tables", ())),
                results_metric_ids=result_ids, discussion_metric_ids=discussion_ids,
                supported_interpretations=tuple(str(value) for value in item.get("supported_interpretations", ())),
                prohibited_conclusions=tuple(str(value) for value in item.get("prohibited_conclusions", item.get("disallowed_conclusions", ()))),
                limitations=tuple(str(value) for value in item.get("limitations", ())),
            ))
    human_review_values = ars.get("human_review", ())
    if not isinstance(human_review_values, list):
        raise ValueError("ARS human review list is invalid")
    human_review = tuple(HumanReviewView(str(item.get("evidence_id", "")), str(item.get("action", "")), str(item.get("reason", ""))) for item in human_review_values if isinstance(item, Mapping))
    technique_views = tuple(
        EvidenceTechniqueView(
            key=str(key), run_ids=tuple(str(value) for value in value.get("run_ids", ())),
            statuses=tuple(str(value) for value in value.get("statuses", ())),
            evidence_count=int(value.get("evidence_count", len([item for item in evidence_views if item.technique == str(key).lower()]))),
        )
        for key, value in techniques_payload.items() if isinstance(value, Mapping)
    )
    return EvidencePackageView(
        package_id=str(manifest.get("package_id", "")), version=int(manifest.get("version", 0)),
        status=str(manifest.get("status", "unknown")), run_ids=tuple(str(value) for value in manifest.get("run_ids", ())),
        questions=tuple(str(value) for value in manifest.get("questions", ())), techniques=technique_views,
        evidence=tuple(evidence_views), metrics=tuple(metric_views),
        figures=tuple(f"figures/{path.name}" for path in (root / "figures").iterdir() if path.is_file()) if (root / "figures").is_dir() else (),
        tables=tuple(f"tables/{path.name}" for path in (root / "tables").iterdir() if path.is_file()) if (root / "tables").is_dir() else (),
        limitations=tuple(str(value) for value in limitations), human_review=human_review,
        figure_views=load_figure_index(root),
        package_root=str(root),
    )


def _read(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise ValueError(f"evidence package file is missing: {relative}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"evidence package file is invalid: {relative}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"evidence package file is invalid: {relative}")
    return value


def _ars_evidence_item(ars: Mapping[str, Any], technique: str, evidence_id: str) -> Mapping[str, Any]:
    sections = ars.get("techniques", {})
    section = sections.get(technique, {}) if isinstance(sections, Mapping) else {}
    items = section.get("evidence", ()) if isinstance(section, Mapping) else ()
    for item in items:
        if isinstance(item, Mapping) and str(item.get("evidence_id", "")) == evidence_id:
            return item
    raise ValueError("ARS evidence reference is invalid")


__all__ = ["EvidenceItemView", "EvidenceMetricView", "EvidencePackageView", "EvidencePackageView", "EvidenceTechniqueView", "HumanReviewView", "load_evidence_package_view"]
