"""Dataset assembly helpers for the Joint Analysis Hub.

The hub is intentionally built around existing analysis runs rather than raw
input files.  These helpers convert SampleDB rows into a small, stable model
that the GUI can preview, filter, validate, and export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable, Sequence

from .validation import run_all_cross_validations
from .conclusion import classify_joint_conclusion
from ..scientific_review import review_decision_snapshot, review_record_from_payload


TECHNIQUES = ("dsc", "saxs", "waxs", "ir", "nmr")

XC_KEYS = ("Xc_pct", "Xc", "phi_c", "crystallinity", "crystallinity_pct")

KEY_PARAMETER_LABELS: dict[str, list[tuple[str, tuple[str, ...], str]]] = {
    "dsc": [
        ("Xc", XC_KEYS, "%"),
        ("Tm", ("Tm_peak_C", "Tm_C"), "C"),
    ],
    "saxs": [
        ("L", ("L_nm", "long_period_nm", "L_best"), "nm"),
        ("lc", ("lc_nm", "crystalline_thickness_nm"), "nm"),
        ("Xc", XC_KEYS, "%"),
    ],
    "waxs": [
        ("Xc", XC_KEYS, "%"),
        ("D", ("D_Scherrer_nm", "D_nm", "crystallite_size_nm"), "nm"),
    ],
    "ir": [
        ("Xc", XC_KEYS, "%"),
        ("CI", ("crystallinity_index", "CI"), ""),
    ],
    "nmr": [
        ("Xc", XC_KEYS, "%"),
    ],
}


def _normalise_technique(value: Any) -> str:
    text = str(value or "").strip().lower()
    for tech in TECHNIQUES:
        if text.startswith(tech):
            return tech
    return text


def _coerce_float(value: Any) -> float:
    if value is None or isinstance(value, bool):
        return math.nan
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else math.nan
    if isinstance(value, str):
        text = value.strip().replace("%", "")
        if not text:
            return math.nan
        try:
            return float(text)
        except ValueError:
            return math.nan
    return math.nan


def _iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    """Yield dictionaries from nested parameter payloads, shallow-first."""
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            if isinstance(nested, dict):
                yield nested


def _condition_label(condition_values: Any) -> str:
    if isinstance(condition_values, dict):
        if not condition_values:
            return ""
        parts = []
        for key, value in condition_values.items():
            if isinstance(value, (list, tuple)):
                if len(value) == 1:
                    parts.append(f"{key}={value[0]}")
                elif len(value) > 1:
                    parts.append(f"{key}={value[0]}..{value[-1]}")
            else:
                parts.append(f"{key}={value}")
        return ", ".join(parts[:3])
    if condition_values:
        return str(condition_values)
    return ""


@dataclass
class JointRunRecord:
    """One latest analysis run for a technique within a batch."""

    run_id: str
    technique: str
    submodule: str = ""
    created_at: str = ""
    output_dir: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    results_summary: dict[str, Any] = field(default_factory=dict)
    analysis_evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def values(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        if isinstance(self.parameters, dict):
            merged.update(self.parameters)
        if isinstance(self.results_summary, dict):
            merged.update(self.results_summary)
        return merged

    def get_first_number(self, keys: Iterable[str]) -> float:
        key_set = tuple(keys)
        for payload in _iter_dicts(self.values):
            for key in key_set:
                if key in payload:
                    value = _coerce_float(payload.get(key))
                    if not math.isnan(value):
                        return value
        return math.nan

    def format_key_parameters(self) -> str:
        specs = KEY_PARAMETER_LABELS.get(self.technique, [])
        parts = []
        for label, keys, unit in specs:
            value = self.get_first_number(keys)
            if math.isnan(value):
                continue
            if label == "Xc" and unit == "%" and 0.0 <= value <= 1.5:
                value *= 100.0
            fmt = f"{value:.1f}" if abs(value) >= 10 else f"{value:.2f}"
            parts.append(f"{label} {fmt}{unit}")
        return "; ".join(parts) if parts else "ready"


@dataclass
class JointBatchRow:
    """One batch row in the hub matrix."""

    sample_id: str
    sample_name: str
    family: str
    batch_id: str
    batch_label: str
    condition_type: str = ""
    condition_label: str = ""
    condition_values: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    runs: dict[str, JointRunRecord] = field(default_factory=dict)
    scientific_review: dict[str, Any] = field(default_factory=dict)

    @property
    def technique_count(self) -> int:
        return len(self.runs)

    @property
    def technique_label(self) -> str:
        return ", ".join(t.upper() for t in TECHNIQUES if t in self.runs)

    def run(self, technique: str) -> JointRunRecord | None:
        return self.runs.get(technique)

    def technique_cell(self, technique: str) -> str:
        run = self.run(technique)
        return run.format_key_parameters() if run else "-"


def collect_joint_dataset(
    sample_db,
    sample_ids: list[str] | None = None,
    batch_ids: list[str] | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[JointBatchRow]:
    """Collect latest analysis runs into batch rows for the hub."""
    batch_filter = set(batch_ids or [])
    samples = []

    if sample_ids:
        for sample_id in sample_ids:
            sample = sample_db.get_sample(sample_id)
            if sample:
                samples.append(sample)
    elif batch_filter:
        seen_samples = set()
        for batch_id in batch_filter:
            batch = sample_db.get_batch(batch_id)
            if not batch:
                continue
            sample_id = batch.get("sample_id")
            if sample_id and sample_id not in seen_samples:
                sample = sample_db.get_sample(sample_id)
                if sample:
                    samples.append(sample)
                    seen_samples.add(sample_id)
    else:
        samples = sample_db.list_samples(search=search or None, limit=limit)

    rows: list[JointBatchRow] = []
    for sample in samples:
        sample_id = sample.get("id", "")
        for batch in sample_db.get_batches(sample_id):
            batch_id = batch.get("id", "")
            if batch_filter and batch_id not in batch_filter:
                continue

            latest_by_technique: dict[str, JointRunRecord] = {}
            for run in sample_db.get_analysis_runs(batch_id):
                technique = _normalise_technique(run.get("technique"))
                if technique not in TECHNIQUES or technique in latest_by_technique:
                    continue
                latest_by_technique[technique] = JointRunRecord(
                    run_id=run.get("id", ""),
                    technique=technique,
                    submodule=run.get("submodule", "") or "",
                    created_at=run.get("created_at", "") or "",
                    output_dir=run.get("output_dir", "") or "",
                    parameters=run.get("parameters", {}) or {},
                    results_summary=run.get("results_summary", {}) or {},
                    analysis_evidence=run.get("analysis_evidence", {}) or {},
                )

            if latest_by_technique:
                rows.append(
                    JointBatchRow(
                        sample_id=sample_id,
                        sample_name=sample.get("polymer_name", "") or sample_id,
                        family=sample.get("family", "") or "",
                        batch_id=batch_id,
                        batch_label=batch.get("label", "") or batch_id,
                        condition_type=batch.get("condition_type", "") or "",
                        condition_label=_condition_label(batch.get("condition_values")),
                        condition_values=dict(batch.get("condition_values") or {}),
                        created_at=batch.get("created_at", "") or "",
                        runs=latest_by_technique,
                        scientific_review=dict(batch.get("scientific_review") or {}),
                    )
                )
    return rows


def _normalise_xc(value: float) -> float:
    if math.isnan(value):
        return math.nan
    if abs(value) <= 1.5:
        return value
    return value / 100.0


def _saxs_xc(row: JointBatchRow) -> float:
    saxs = row.run("saxs")
    if not saxs:
        return math.nan
    xc = saxs.get_first_number(XC_KEYS)
    if not math.isnan(xc):
        return _normalise_xc(xc)
    lc = saxs.get_first_number(("lc_nm", "crystalline_thickness_nm"))
    long_period = saxs.get_first_number(("L_nm", "long_period_nm", "L_best"))
    if not math.isnan(lc) and not math.isnan(long_period) and long_period > 0:
        return lc / long_period
    return math.nan


def _xc_pct_for(row: JointBatchRow, technique: str) -> float:
    if technique == "saxs":
        value = _saxs_xc(row)
    else:
        run = row.run(technique)
        value = run.get_first_number(XC_KEYS) if run else math.nan
        value = _normalise_xc(value)
    return value * 100.0 if not math.isnan(value) else math.nan


def _run_analysis_evidence(run: JointRunRecord | None) -> dict[str, Any]:
    if run is None:
        return {}
    evidence = run.analysis_evidence if isinstance(run.analysis_evidence, dict) else {}
    if evidence:
        return evidence
    embedded = run.values.get("analysis_evidence")
    return embedded if isinstance(embedded, dict) else {}


def _run_evidence_context(run: JointRunRecord | None) -> dict[str, Any]:
    evidence = _run_analysis_evidence(run)
    if not evidence:
        return {"status": "unknown", "weight": 0.5, "reasons": ["evidence_missing"]}

    summary = evidence.get("constraint_summary", {}) if isinstance(evidence.get("constraint_summary"), dict) else {}
    structure = evidence.get("structure_evidence", {}) if isinstance(evidence.get("structure_evidence"), dict) else {}
    status = str(summary.get("status") or "ok").strip().lower()
    weight = 1.0
    reasons: list[str] = []
    if status == "hard_fail":
        weight = 0.0
        reasons.append("hard_fail")
    elif status == "soft_warn":
        weight = 0.45
        reasons.append("soft_warn")

    if str(structure.get("Xc_assignment_status") or "").strip() == "assignment_limited":
        weight = min(weight, 0.25)
        reasons.append("assignment-limited")
    if str(structure.get("lc_reliability_status") or "").strip() == "diagnostic_only":
        weight = min(weight, 0.25)
        reasons.append("diagnostic-only-lc")
    if str(structure.get("Xc_reliability_status") or "").strip() == "diagnostic_only":
        weight = min(weight, 0.25)
        reasons.append("diagnostic-only-xc")
    elif str(structure.get("Xc_reliability_status") or "").strip() == "low_confidence":
        weight = min(weight, 0.45)
        reasons.append("low-confidence-xc")

    return {"status": status or "ok", "weight": weight, "reasons": reasons}


def build_joint_run_provenance(
    row: JointBatchRow,
    techniques: Iterable[str] = TECHNIQUES,
) -> dict[str, Any]:
    """Serialize the exact Joint source runs and their evidence weights."""

    sources: dict[str, dict[str, Any]] = {}
    for raw_technique in techniques:
        technique = _normalise_technique(raw_technique)
        if technique in sources:
            continue
        run = row.run(technique)
        if run is None:
            sources[technique] = {
                "available": False,
                "run_id": "",
                "technique": technique,
                "submodule": "",
                "created_at": "",
                "evidence_status": "missing",
                "evidence_weight": 0.0,
                "evidence_reasons": ["run_missing"],
            }
            continue
        evidence = _run_evidence_context(run)
        sources[technique] = {
            "available": True,
            "run_id": str(run.run_id or ""),
            "technique": str(run.technique or technique),
            "submodule": str(run.submodule or ""),
            "created_at": str(run.created_at or ""),
            "evidence_status": str(evidence["status"]),
            "evidence_weight": float(evidence["weight"]),
            "evidence_reasons": [str(item) for item in evidence["reasons"]],
        }
    return {
        "sample_id": str(row.sample_id or ""),
        "sample": str(row.sample_name or ""),
        "batch_id": str(row.batch_id or ""),
        "batch": str(row.batch_label or ""),
        "sources": sources,
    }


def build_joint_scientific_review_snapshot(
    rows: Sequence[JointBatchRow],
) -> dict[str, Any]:
    """Gate Joint promotion on accepted review records for every selected row."""

    if not rows:
        return review_decision_snapshot(
            None,
            expected_scope="joint",
            source_ref="",
        )
    decisions = [
        review_decision_snapshot(
            review_record_from_payload(row.scientific_review or None),
            expected_scope="joint",
            source_ref=str(row.batch_id or ""),
        )
        for row in rows
    ]
    denied = next((item for item in decisions if not item["allowed"]), None)
    if denied is not None:
        return denied
    return {
        "allowed": True,
        "reason": "review_accepted",
        "record_id": "+".join(str(item["record_id"]) for item in decisions),
        "scope": "joint",
        "source_ref": ",".join(str(item["source_ref"]) for item in decisions),
    }


def _validation_source_techniques(check_name: object) -> tuple[str, ...]:
    key = str(check_name or "").strip().lower()
    if "phi_c" in key:
        return ("dsc", "waxs", "saxs")
    if "tm_gt" in key or "/tm_" in key:
        return ("dsc", "saxs")
    if "l_consistency" in key:
        return ("saxs",)
    return TECHNIQUES


def detect_joint_opportunities(row: JointBatchRow) -> list[str]:
    """Return user-facing analysis opportunities for one row."""
    opportunities = []
    xc_count = sum(
        not math.isnan(_xc_pct_for(row, tech))
        for tech in ("dsc", "waxs", "saxs", "ir", "nmr")
    )
    if xc_count >= 2:
        opportunities.append("crystallinity consistency")

    dsc = row.run("dsc")
    saxs = row.run("saxs")
    waxs = row.run("waxs")
    ir = row.run("ir")

    tm = dsc.get_first_number(("Tm_peak_C", "Tm_C")) if dsc else math.nan
    long_period = saxs.get_first_number(("L_nm", "long_period_nm", "L_best")) if saxs else math.nan
    lc = saxs.get_first_number(("lc_nm", "crystalline_thickness_nm")) if saxs else math.nan
    d_size = waxs.get_first_number(("D_Scherrer_nm", "D_nm", "crystallite_size_nm")) if waxs else math.nan
    ir_ci = ir.get_first_number(("crystallinity_index", "CI")) if ir else math.nan

    if not math.isnan(tm) and (not math.isnan(long_period) or not math.isnan(lc)):
        opportunities.append("structure-thermodynamics")
    if not math.isnan(long_period) and not math.isnan(d_size):
        opportunities.append("SAXS-WAXS multiscale")
    if not math.isnan(ir_ci) and not math.isnan(_xc_pct_for(row, "dsc")):
        opportunities.append("IR/DSC calibration")

    return opportunities


def validate_joint_row(row: JointBatchRow) -> list[dict[str, Any]]:
    """Run cross-technique validation checks for one hub row."""
    dsc = row.run("dsc")
    waxs = row.run("waxs")
    saxs = row.run("saxs")

    tm = dsc.get_first_number(("Tm_peak_C", "Tm_C")) if dsc else math.nan
    long_period = saxs.get_first_number(("L_nm", "long_period_nm", "L_best")) if saxs else math.nan
    lc = saxs.get_first_number(("lc_nm", "crystalline_thickness_nm")) if saxs else math.nan
    l_bragg = saxs.get_first_number(("L_bragg_nm", "L_bragg", "L_nm")) if saxs else math.nan
    l_corr = saxs.get_first_number(("L_corr_nm", "L_corr", "L_corr_best_nm")) if saxs else math.nan
    phi_c_weights = {
        tech: _run_evidence_context(row.run(tech))["weight"]
        for tech in ("dsc", "waxs", "saxs")
    }
    tm_evidence_weight = min(phi_c_weights.get("dsc", 1.0), phi_c_weights.get("saxs", 1.0))

    results = run_all_cross_validations(
        sample_id=f"{row.sample_name}/{row.batch_label}",
        phi_c_dsc=_normalise_xc(dsc.get_first_number(XC_KEYS)) if dsc else math.nan,
        phi_c_waxs=_normalise_xc(waxs.get_first_number(XC_KEYS)) if waxs else math.nan,
        phi_c_saxs=_saxs_xc(row),
        phi_c_weights=phi_c_weights,
        tm_dsc=tm,
        L_saxs=long_period,
        lc_saxs=lc,
        L_bragg=l_bragg,
        L_corr=l_corr,
        polymer_family=row.sample_name,
    )
    for item in results.get("tm", []):
        item.details["evidence_weight"] = float(tm_evidence_weight)
        if not item.passed and tm_evidence_weight < 0.5:
            item.severity = "WARN"
    output = []
    for item in results.get("all", []):
        output.append(
            {
                "sample": row.sample_name,
                "batch": row.batch_label,
                "check": item.check_name,
                "severity": item.severity,
                "passed": item.passed,
                "message": item.message,
                "details": item.details,
                "provenance": {
                    "check": str(item.check_name),
                    **build_joint_run_provenance(
                        row,
                        _validation_source_techniques(item.check_name),
                    ),
                },
            }
        )
    return output


def _joint_issue_family(check_name: str) -> str:
    key = str(check_name or "").strip().lower()
    if "phi_c" in key:
        return "phi_c inconsistency"
    if "tm_gt" in key or "/tm_" in key or key.endswith("tm_gt"):
        return "Tm bidirectional gap"
    if "l_consistency" in key or key.endswith("l_consistency"):
        return "L consistency unstable"
    return "cross-tech issue"


def _compact_joint_issue(item: dict[str, Any]) -> str:
    severity = str(item.get("severity") or "").strip().upper() or "WARN"
    sample = str(item.get("sample") or "").strip()
    batch = str(item.get("batch") or "").strip()
    check = str(item.get("check") or "").strip()
    message = str(item.get("message") or "").strip()

    parts = [severity]
    if sample:
        parts.append(sample)
    if batch:
        parts.append(batch)
    if check:
        parts.append(check.rsplit("/", 1)[-1])
    if message:
        parts.append(message)
    return " | ".join(parts)


def _technique_confidence(run: JointRunRecord | None) -> dict[str, Any]:
    evidence = _run_analysis_evidence(run)
    summary = evidence.get("constraint_summary", {}) if isinstance(evidence.get("constraint_summary"), dict) else {}
    structure = evidence.get("structure_evidence", {}) if isinstance(evidence.get("structure_evidence"), dict) else {}
    status = str(summary.get("status") or "unknown").strip() or "unknown"
    risk_flags = evidence.get("risk_flags", []) if isinstance(evidence.get("risk_flags"), list) else []
    paper_ready = bool(structure.get("paper_conclusion_ready", status == "ok"))
    xc_assignment_status = str(structure.get("Xc_assignment_status") or "").strip()
    if run and run.technique == "nmr" and xc_assignment_status and xc_assignment_status != "supported":
        paper_ready = False
    return {
        "status": status,
        "risk_flags": risk_flags,
        "paper_conclusion_ready": paper_ready,
        "Xc_assignment_status": xc_assignment_status,
    }


def _joint_technique_issue_rows(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in summary_rows:
        technique_confidence = row.get("technique_confidence", {})
        if not isinstance(technique_confidence, dict):
            continue
        nmr_confidence = technique_confidence.get("nmr", {})
        if not isinstance(nmr_confidence, dict):
            continue
        assignment_status = str(nmr_confidence.get("Xc_assignment_status") or "").strip()
        if assignment_status and assignment_status != "supported":
            issues.append(
                {
                    "family": "NMR assignment limited",
                    "severity": "WARN",
                    "sample": row.get("sample"),
                    "batch": row.get("batch"),
                    "check": "nmr_assignment_limited",
                    "message": "NMR Xc is assignment-limited; review crystalline/amorphous peak support before using it as a joint conclusion source.",
                }
            )
    return issues


def _joint_weak_xc_sources(summary_rows: list[dict[str, Any]]) -> tuple[dict[str, str], list[str]]:
    weak_xc_sources: dict[str, str] = {}
    recommended_review_targets: list[str] = []
    for row in summary_rows:
        technique_confidence = row.get("technique_confidence", {})
        if not isinstance(technique_confidence, dict):
            continue
        nmr_confidence = technique_confidence.get("nmr", {})
        if not isinstance(nmr_confidence, dict):
            continue
        assignment_status = str(nmr_confidence.get("Xc_assignment_status") or "").strip()
        if assignment_status and assignment_status != "supported":
            weak_xc_sources["nmr"] = assignment_status
            if "nmr" not in recommended_review_targets:
                recommended_review_targets.append("nmr")
    return weak_xc_sources, recommended_review_targets


def _build_joint_ai_context(
    summary_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    issue_rows = [
        item for item in validation_rows
        if str(item.get("severity") or "").strip().upper() in {"WARN", "ERROR"}
    ]
    technique_issue_rows = _joint_technique_issue_rows(summary_rows)
    weak_xc_sources, recommended_review_targets = _joint_weak_xc_sources(summary_rows)
    sample_names: list[str] = []
    batch_labels: list[str] = []
    for row in summary_rows:
        sample = str(row.get("sample") or "").strip()
        batch = str(row.get("batch") or "").strip()
        if sample and sample not in sample_names:
            sample_names.append(sample)
        if batch and batch not in batch_labels:
            batch_labels.append(batch)

    scope = "selected rows"
    if len(sample_names) == 1:
        scope = sample_names[0]
    elif sample_names:
        scope = " / ".join(sample_names[:2])

    ai_boundary = {
        "mode": "off",
        "provider_status": "not_configured",
        "fallback": "rule_based_report",
        "failure_policy": "preserve_source_evidence_and_diagnostic_status",
    }

    if not issue_rows and not technique_issue_rows:
        return {
            "summary": f"Cross-tech checks passed for {scope}.",
            "scope": scope,
            "sample_count": len(sample_names) or len(summary_rows),
            "batch_count": len(batch_labels),
            "issue_count": 0,
            "warning_count": 0,
            "error_count": 0,
            "issue_families": [],
            "highlights": [],
            "weak_xc_sources": weak_xc_sources,
            "recommended_review_targets": recommended_review_targets,
            "samples": sample_names[:3],
            "batches": batch_labels[:3],
            "row_count": len(summary_rows),
            "ai_boundary": ai_boundary,
        }

    family_stats: dict[str, dict[str, Any]] = {}
    warning_count = 0
    error_count = 0
    for item in issue_rows:
        severity = str(item.get("severity") or "").strip().upper()
        family = _joint_issue_family(item.get("check", ""))
        stats = family_stats.setdefault(
            family,
            {
                "count": 0,
                "warning_count": 0,
                "error_count": 0,
                "first": item,
            },
        )
        stats["count"] += 1
        if severity == "ERROR":
            stats["error_count"] += 1
            error_count += 1
        else:
            stats["warning_count"] += 1
            warning_count += 1
    for item in technique_issue_rows:
        severity = str(item.get("severity") or "").strip().upper()
        family = str(item.get("family") or "").strip() or "technique confidence issue"
        stats = family_stats.setdefault(
            family,
            {
                "count": 0,
                "warning_count": 0,
                "error_count": 0,
                "first": item,
            },
        )
        stats["count"] += 1
        if severity == "ERROR":
            stats["error_count"] += 1
            error_count += 1
        else:
            stats["warning_count"] += 1
            warning_count += 1

    ordered_families = sorted(
        family_stats.items(),
        key=lambda pair: (
            0 if pair[1]["error_count"] else 1,
            -int(pair[1]["count"]),
            pair[0],
        ),
    )
    issue_families = [family for family, _ in ordered_families[:3]]
    highlights = [
        _compact_joint_issue(family_stats[family]["first"])
        for family in issue_families
        if family in family_stats
    ]

    summary = f"Cross-tech consistency for {scope}: {error_count} errors, {warning_count} warnings"
    if issue_families:
        summary += "; focus on " + ", ".join(issue_families)

    return {
        "summary": summary,
        "scope": scope,
        "sample_count": len(sample_names) or len(summary_rows),
        "batch_count": len(batch_labels),
        "issue_count": len(issue_rows) + len(technique_issue_rows),
        "warning_count": warning_count,
        "error_count": error_count,
        "issue_families": issue_families,
        "highlights": highlights,
        "weak_xc_sources": weak_xc_sources,
        "recommended_review_targets": recommended_review_targets,
        "samples": sample_names[:3],
        "batches": batch_labels[:3],
        "row_count": len(summary_rows),
        "ai_boundary": ai_boundary,
    }


def build_joint_hub_report(rows: list[JointBatchRow]) -> dict[str, Any]:
    """Build summary and validation tables for selected hub rows."""
    summary_rows = []
    validation_rows = []

    for row in rows:
        validations = validate_joint_row(row)
        validation_rows.extend(validations)
        alert_count = sum(v["severity"] in {"WARN", "ERROR"} for v in validations)
        technique_confidence = {
            technique: _technique_confidence(row.run(technique))
            for technique in TECHNIQUES
            if row.run(technique)
        }
        paper_ready_by_technique = {
            technique: bool(confidence.get("paper_conclusion_ready"))
            for technique, confidence in technique_confidence.items()
        }
        summary_rows.append(
            {
                "sample": row.sample_name,
                "batch": row.batch_label,
                "condition": row.condition_label or row.condition_type,
                "condition_values": row.condition_values,
                "techniques": row.technique_label,
                "dsc_Xc_pct": _xc_pct_for(row, "dsc"),
                "waxs_Xc_pct": _xc_pct_for(row, "waxs"),
                "saxs_Xc_pct": _xc_pct_for(row, "saxs"),
                "ir_Xc_pct": _xc_pct_for(row, "ir"),
                "nmr_Xc_pct": _xc_pct_for(row, "nmr"),
                "Tm_C": row.run("dsc").get_first_number(("Tm_peak_C", "Tm_C")) if row.run("dsc") else math.nan,
                "L_nm": row.run("saxs").get_first_number(("L_nm", "long_period_nm", "L_best")) if row.run("saxs") else math.nan,
                "lc_nm": row.run("saxs").get_first_number(("lc_nm", "crystalline_thickness_nm")) if row.run("saxs") else math.nan,
                "D_Scherrer_nm": row.run("waxs").get_first_number(("D_Scherrer_nm", "D_nm", "crystallite_size_nm")) if row.run("waxs") else math.nan,
                "opportunities": "; ".join(detect_joint_opportunities(row)),
                "alerts": alert_count,
                "technique_confidence": technique_confidence,
                "paper_conclusion_ready_by_technique": paper_ready_by_technique,
            }
        )

    issue_count = sum(v["severity"] == "ERROR" for v in validation_rows)
    warn_count = sum(v["severity"] == "WARN" for v in validation_rows)
    scientific_review = build_joint_scientific_review_snapshot(rows)
    technique_issue_rows = _joint_technique_issue_rows(summary_rows)
    joint_conclusion = classify_joint_conclusion(
        review_records=[row.scientific_review for row in rows],
        review_snapshot=scientific_review,
        validation_rows=validation_rows,
        technique_issue_rows=technique_issue_rows,
    )
    ai_context = _build_joint_ai_context(summary_rows, validation_rows)
    ai_context["joint_conclusion"] = joint_conclusion
    return {
        "name": "joint_analysis_hub",
        "rows": summary_rows,
        "validations": validation_rows,
        "scientific_review": scientific_review,
        "joint_conclusion": joint_conclusion,
        "ai_context": ai_context,
        "summary": (
            f"{len(summary_rows)} batch rows, "
            f"{len(validation_rows)} validation checks, "
            f"{issue_count} errors, {warn_count} warnings."
        ),
    }
