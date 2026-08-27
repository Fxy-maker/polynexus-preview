"""Deterministic, provenance-preserving numeric projection for ARS writing."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import math
from typing import Any, Iterable, Mapping

from .models import EvidenceItem, canonical_json


@dataclass(frozen=True)
class CitationMetric:
    """One numeric observation that ARS may cite only within its boundary."""

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
    reason_codes: tuple[str, ...] = ()
    figures: tuple[str, ...] = ()
    tables: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, Any]:
        return {
            "technique": self.technique,
            "metric_key": self.metric_key,
            "value": self.value,
            "unit": self.unit,
            "method": self.method,
            "source_locator": self.source_locator,
            "evidence_id": self.evidence_id,
            "run_id": self.run_id,
            "raw_source_hashes": list(self.raw_source_hashes),
            "status": self.status,
            "writing_eligibility": self.writing_eligibility,
            "reason_codes": list(self.reason_codes),
            "figures": list(self.figures),
            "tables": list(self.tables),
        }

    def to_dict(self) -> dict[str, Any]:
        return {"metric_id": self.metric_id, **self.public_dict()}


def extract_writing_metrics(item: EvidenceItem | Mapping[str, Any]) -> tuple[CitationMetric, ...]:
    """Extract documented provider metrics from one public evidence item."""
    payload = item.to_dict() if isinstance(item, EvidenceItem) else dict(item)
    technique = str(payload.get("technique", "")).lower()
    if technique == "dsc":
        records = _dsc(payload)
    elif technique in {"ir", "ftir"}:
        records = _ir(payload)
    elif technique == "saxs":
        records = _saxs(payload)
    elif technique == "waxs":
        records = _waxs(payload)
    else:
        records = ()
    return tuple(_with_id(record) for record in records)


def extract_package_metrics(items: Iterable[EvidenceItem | Mapping[str, Any]]) -> tuple[CitationMetric, ...]:
    records = [record for item in items for record in extract_writing_metrics(item)]
    return tuple(sorted(records, key=lambda record: (record.technique, record.source_locator, record.metric_key)))


def with_package_assets(
    metrics: Iterable[CitationMetric], asset_paths: Mapping[str, str]
) -> tuple[CitationMetric, ...]:
    """Replace source asset paths and regenerate IDs from the public package record."""
    return tuple(
        _with_id(replace(
            metric,
            figures=tuple(asset_paths[path] for path in metric.figures if path in asset_paths),
            tables=tuple(asset_paths[path] for path in metric.tables if path in asset_paths),
        ))
        for metric in metrics
    )


def _base(payload: Mapping[str, Any], *, key: str, value: float | int, unit: str, method: str, locator: str,
          eligibility: str = "results_candidate", reasons: Iterable[str] = ()) -> CitationMetric:
    source_runs = tuple(str(value) for value in payload.get("source_runs", ()))
    return CitationMetric(
        metric_id="",
        technique=str(payload.get("technique", "")).lower(),
        metric_key=key,
        value=value,
        unit=unit,
        method=method,
        source_locator=locator,
        evidence_id=str(payload.get("evidence_id", "")),
        run_id=source_runs[0] if source_runs else "",
        raw_source_hashes=tuple(str(value) for value in payload.get("raw_sources", ())),
        status=str(payload.get("status", "unknown")),
        writing_eligibility=eligibility,
        reason_codes=tuple(dict.fromkeys(str(value) for value in reasons if value)),
        figures=tuple(str(value) for value in payload.get("figures", ())),
        tables=tuple(str(value) for value in payload.get("tables", ())),
    )


def _with_id(record: CitationMetric) -> CitationMetric:
    digest = hashlib.sha256(canonical_json(record.public_dict()).encode("utf-8")).hexdigest()
    return replace(record, metric_id=f"metric-{digest[:24]}")


def _finite(value: Any) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("observed_results", {})
    if not isinstance(value, Mapping):
        return {}
    result = value.get("result_summary", value)
    return result if isinstance(result, Mapping) else {}


def _analysis(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("observed_results", {})
    if not isinstance(value, Mapping):
        return {}
    result = value.get("analysis_evidence", {})
    return result if isinstance(result, Mapping) else {}


def _dsc(payload: Mapping[str, Any]) -> tuple[CitationMetric, ...]:
    parameters = _summary(payload).get("parameters", {})
    if not isinstance(parameters, Mapping):
        return ()
    fields = {
        "T_iso_C": "°C", "DHc_iso_Jg": "J/g", "Avrami_n": "dimensionless",
        "Avrami_k": "model_parameter", "Avrami_R2": "dimensionless", "t_half_min": "min",
    }
    records: list[CitationMetric] = []
    emitted_signatures: set[tuple[Any, ...]] = set()
    metric_fields = tuple(fields)

    def normalized_quality_flags(value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            values = value.replace(";", ",").split(",")
        elif isinstance(value, (list, tuple, set, frozenset)):
            values = [str(item) for item in value]
        elif isinstance(value, Mapping):
            values = [str(key) for key, flag in value.items() if str(flag).upper() not in {"", "OK", "PASS"}]
        else:
            values = []
        return tuple(dict.fromkeys(item.strip() for item in values if item and item.strip()))

    def signature(values: Mapping[str, Any]) -> tuple[Any, ...]:
        return tuple(_finite(values.get(key)) for key in metric_fields)

    ordered_parameters = sorted(
        parameters.items(),
        key=lambda item: (str(item[0]) == "best_avrami", str(item[0])),
    )
    for name, values in ordered_parameters:
        if not (str(name).startswith("segment_") or str(name) == "best_avrami") or not isinstance(values, Mapping):
            continue
        current_signature = signature(values)
        if str(name) == "best_avrami" and current_signature in emitted_signatures:
            continue
        emitted_signatures.add(current_signature)
        method = "dsc.isothermal_avrami_fit"
        reasons = list(normalized_quality_flags(values.get("quality_flags")))
        r_squared = _finite(values.get("Avrami_R2"))
        if isinstance(r_squared, (int, float)) and r_squared < 0.9 and "low_avrami_r_squared" not in reasons:
            reasons.append("low_avrami_r_squared")
        eligibility = "diagnostic_only" if reasons else "results_candidate"
        for key, unit in fields.items():
            value = _finite(values.get(key))
            if value is None:
                continue
            records.append(_base(payload, key=key, value=value, unit=unit, method=method,
                                 locator=f"parameters.{name}.{key}",
                                 eligibility=eligibility, reasons=reasons))
    return tuple(records)


def _ir(payload: Mapping[str, Any]) -> tuple[CitationMetric, ...]:
    summary = _summary(payload)
    parameters = summary.get("parameters", {})
    records: list[CitationMetric] = []
    if isinstance(parameters, Mapping):
        for sample, values in parameters.items():
            if not isinstance(values, Mapping):
                continue
            band = values.get("Xc_band")
            method = values.get("Xc_method") or values.get("Xc_calibration_status")
            if values.get("Xc_calibration_status") == "uncalibrated_index" or (
                isinstance(band, str) and isinstance(method, str) and "uncalibrated" in method
            ):
                value = _finite(values.get("Xc_pct"))
                if value is not None and isinstance(band, str) and isinstance(method, str):
                    records.append(_base(payload, key=band, value=value, unit="index", method=method,
                                         locator=f"result_summary.parameters.{sample}.Xc_pct",
                                         eligibility="diagnostic_only",
                                         reasons=("absolute_crystallinity_not_supported",)))
    evidence = _analysis(payload).get("assignment_evidence", {})
    peaks = evidence.get("assigned_peaks", ()) if isinstance(evidence, Mapping) else ()
    if isinstance(peaks, list):
        count = _finite(evidence.get("assigned_peak_count")) if isinstance(evidence, Mapping) else None
        if count is not None:
            records.append(_base(payload, key="assigned_peak_count", value=count, unit="count",
                                 method="ir.assigned_peak_fit", locator="analysis_evidence.assignment_evidence.assigned_peak_count",
                                 eligibility="diagnostic_only", reasons=("human_review_required",)))
        for index, peak in enumerate(peaks, 1):
            if not isinstance(peak, Mapping):
                continue
            for field, unit in (("wavenumber", "cm^-1"), ("fwhm_cm1", "cm^-1")):
                value = _finite(peak.get(field))
                if value is None:
                    continue
                records.append(_base(payload, key=f"peak_{index}_{field}", value=value, unit=unit,
                                     method="ir.assigned_peak_fit", locator=f"analysis_evidence.assignment_evidence.assigned_peaks[{index - 1}].{field}",
                                     eligibility="diagnostic_only", reasons=("human_review_required",)))
    return tuple(records)


def _saxs(payload: Mapping[str, Any]) -> tuple[CitationMetric, ...]:
    parameters = _summary(payload).get("parameters", {})
    metrics = parameters.get("metric_evidence", {}) if isinstance(parameters, Mapping) else {}
    if not isinstance(metrics, Mapping):
        return ()
    records: list[CitationMetric] = []
    for name, report in metrics.items():
        if not isinstance(report, Mapping):
            continue
        value = _finite(report.get("value"))
        unit = report.get("unit")
        method = report.get("source_ref")
        if value is None or not isinstance(unit, str) or not unit or not isinstance(method, str) or not method:
            continue
        applicable = report.get("applicable") is True
        reasons = report.get("reason_codes", ())
        if not isinstance(reasons, (list, tuple)):
            reasons = ()
        records.append(_base(payload, key=str(name), value=value, unit=unit, method=method,
                             locator=f"result_summary.parameters.metric_evidence.{name}.value",
                             eligibility="results_candidate" if applicable else "diagnostic_only",
                             reasons=reasons))
    return tuple(records)


def _waxs(payload: Mapping[str, Any]) -> tuple[CitationMetric, ...]:
    evidence = _analysis(payload)
    feature = evidence.get("feature_evidence", {})
    phase = feature.get("phase_evidence", {}) if isinstance(feature, Mapping) else {}
    if not isinstance(phase, Mapping):
        return ()
    constraints = evidence.get("constraint_summary", {})
    if not isinstance(constraints, Mapping) and isinstance(feature, Mapping):
        constraints = feature.get("constraint_summary", {})
    triggered: list[str] = []
    if isinstance(constraints, Mapping):
        names = constraints.get("triggered_names", {})
        if isinstance(names, Mapping):
            for values in names.values():
                if isinstance(values, (list, tuple)):
                    triggered.extend(str(value) for value in values)
    records: list[CitationMetric] = []
    for key, unit, method, locator in (
        ("Xc_pct", "%", str(phase.get("crystallinity_method", "")), "analysis_evidence.feature_evidence.phase_evidence.Xc_pct"),
        ("D_Scherrer_nm", "nm", "scherrer", "analysis_evidence.feature_evidence.phase_evidence.D_Scherrer_nm"),
    ):
        value = _finite(phase.get(key))
        if value is None or not method:
            continue
        reasons = tuple(triggered)
        supported = phase.get("physical_support_pass") is True
        if key == "D_Scherrer_nm" and phase.get("size_reliability_status") not in {"reliable", "high_confidence"}:
            supported = False
        records.append(_base(payload, key=key, value=value, unit=unit, method=method, locator=locator,
                             eligibility="results_candidate" if supported else "diagnostic_only",
                             reasons=reasons if not supported else ()))
    return tuple(records)


__all__ = ["CitationMetric", "extract_package_metrics", "extract_writing_metrics", "with_package_assets"]
