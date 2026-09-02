"""Deterministic, provenance-preserving numeric projection for ARS writing."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import math
from typing import Any, Iterable, Mapping

from polynexus.core.compute.projection import (
    parse_compute_run_projection,
    read_compute_run_projection,
)

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
    descriptor_id: str | None = None
    computation_state: Mapping[str, Any] | None = None
    provenance: Mapping[str, Any] | None = None
    uncertainty: Mapping[str, Any] | None = None

    def public_dict(self) -> dict[str, Any]:
        payload = {
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
        # Keep historical metric identities stable: optional shared-platform
        # fields participate in the identity only when a producer supplied
        # them explicitly.
        if self.descriptor_id is not None:
            payload["descriptor_id"] = self.descriptor_id
        if self.computation_state is not None:
            payload["computation_state"] = dict(self.computation_state)
        if self.provenance is not None:
            payload["provenance"] = dict(self.provenance)
        if self.uncertainty is not None:
            payload["uncertainty"] = dict(self.uncertainty)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return {"metric_id": self.metric_id, **self.public_dict()}


def extract_writing_metrics(item: EvidenceItem | Mapping[str, Any]) -> tuple[CitationMetric, ...]:
    """Extract documented provider metrics from one public evidence item."""
    payload = item.to_dict() if isinstance(item, EvidenceItem) else dict(item)
    technique = str(payload.get("technique", "")).lower()
    summary = _summary(payload)
    shared_projection = read_compute_run_projection(summary)
    if shared_projection.present and (
        not shared_projection.valid or not shared_projection.computed
    ):
        # An explicit shared envelope is authoritative.  Never fall back to
        # legacy parameters when that envelope is malformed or blocked.
        return ()
    generic = (
        _capability_metrics(payload)
        + _metric_manifest_metrics(payload)
        + _method_sensitivity_metrics(payload)
    )
    if shared_projection.present:
        # Once a shared envelope is supplied, its manifest/capability outputs
        # are the sole source of writing metrics.  Technique-specific legacy
        # summaries are not a fallback, even when they happen to contain a
        # numerically plausible value.
        records = generic
    elif technique == "dsc":
        records = generic + _dsc(payload)
    elif technique in {"ir", "ftir"}:
        records = generic + _ir(payload)
    elif technique == "saxs":
        records = generic + _saxs(payload)
    elif technique == "waxs":
        records = generic + _waxs(payload)
    else:
        records = generic
    # ``ComputationState.promotion`` is a run-level scientific review gate,
    # not a statement that every computed scalar is merely diagnostic.  A
    # valid computed manifest is therefore projected as provisional Results
    # candidates; evidence/package review status and the review ledger still
    # prevent publication-ready claims.  Explicit provider diagnostics and
    # method-sensitivity observations retain their own diagnostic eligibility.
    return tuple(_with_id(record) for record in records)


def _metric_manifest_metrics(payload: Mapping[str, Any]) -> tuple[CitationMetric, ...]:
    """Project the complete ComputeRun metric manifest without promotion."""
    summary = _summary(payload)
    projection = read_compute_run_projection(summary)
    if not projection.present or not projection.valid or not projection.computed:
        return ()
    compute_run = projection.payload or {}
    result = projection.result or {}
    manifest = result.get("metric_manifest", ()) if isinstance(result, Mapping) else ()
    if not isinstance(manifest, (list, tuple)):
        return ()
    records: list[CitationMetric] = []
    for item in manifest:
        if not isinstance(item, Mapping) or item.get("kind") != "scalar":
            continue
        if not _manifest_metric_is_computed(item, compute_run):
            continue
        value = _finite(item.get("value"))
        path = str(item.get("path", "")).strip()
        if value is None or not path:
            continue
        reasons = tuple(str(reason) for reason in item.get("warnings", ()) if reason)
        records.append(_base(
            payload,
            key=path,
            value=value,
            unit=str(item.get("unit") or "unknown"),
            method=str(item.get("method") or "unknown"),
            locator=f"{item.get('source') or 'unknown'}::{path}",
            eligibility="results_candidate",
            reasons=reasons or ("compute_metric_manifest",),
            descriptor_id=item.get("descriptor_id"),
            computation_state=item.get("computation_state"),
            provenance=item.get("provenance"),
            uncertainty=item.get("uncertainty"),
        ))
    return tuple(records)


def _method_sensitivity_metrics(payload: Mapping[str, Any]) -> tuple[CitationMetric, ...]:
    """Expose explicit primary/candidate method values to ARS as diagnostics."""
    summary = _summary(payload)
    projection = read_compute_run_projection(summary)
    if not projection.present or not projection.valid or not projection.computed:
        return ()
    result = projection.result or {}
    entries = result.get("method_sensitivities", ()) if isinstance(result, Mapping) else ()
    if not isinstance(entries, (list, tuple)):
        return ()
    records: list[CitationMetric] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        metric_path = str(entry.get("metric_path", "")).strip()
        primary = entry.get("primary")
        if not metric_path or not isinstance(primary, Mapping):
            continue
        methods = [(str(primary.get("method", "primary")), primary.get("value"))]
        candidates = entry.get("candidates", ())
        if isinstance(candidates, (list, tuple)):
            methods.extend(
                (str(item.get("method", "candidate")), item.get("value"))
                for item in candidates if isinstance(item, Mapping)
            )
        difference = _finite(entry.get("difference_range"))
        for method, value in methods:
            numeric = _finite(value)
            if numeric is None:
                continue
            records.append(_base(
                payload,
                key=f"method_sensitivity.{metric_path}.{method}",
                value=numeric,
                unit="unknown",
                method=method,
                locator=f"compute_run.result.method_sensitivities[{metric_path}]::{method}",
                eligibility="diagnostic_only",
                reasons=("method_sensitivity_observation",) + (("method_difference_range_present",) if difference is not None else ()),
            ))
    return tuple(records)


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
          eligibility: str = "results_candidate", reasons: Iterable[str] = (),
          descriptor_id: Any = None, computation_state: Any = None,
          provenance: Any = None, uncertainty: Any = None) -> CitationMetric:
    source_runs = tuple(str(value) for value in payload.get("source_runs", ()))
    normalized_descriptor = str(descriptor_id).strip() if descriptor_id is not None else None
    if normalized_descriptor == "":
        normalized_descriptor = None
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
        descriptor_id=normalized_descriptor,
        computation_state=dict(computation_state) if isinstance(computation_state, Mapping) else None,
        provenance=dict(provenance) if isinstance(provenance, Mapping) else None,
        uncertainty=dict(uncertainty) if isinstance(uncertainty, Mapping) else None,
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


def _manifest_metric_is_computed(
    metric: Mapping[str, Any], compute_run: Mapping[str, Any]
) -> bool:
    """Fail closed when a manifest row or its run is not computable."""

    projection = parse_compute_run_projection(compute_run)
    if not projection.valid or not projection.computed:
        return False
    status_value = metric.get("status")
    if not isinstance(status_value, str) or status_value.strip().lower() != "computed":
        return False
    for candidate in (metric.get("computation_state"), metric.get("state")):
        if candidate is None:
            continue
        try:
            from polynexus.core.ai_platform.contracts import ComputationState

            if type(candidate) is ComputationState:
                state = candidate
            elif isinstance(candidate, ComputationState):
                # A Mapping-capable state subclass can otherwise enter the
                # deserializer and override its axis lookups.  Only the exact
                # canonical DTO may cross this consumer boundary.
                return False
            elif isinstance(candidate, Mapping):
                state = ComputationState.from_dict(candidate)
            else:
                return False
        except (KeyError, TypeError, ValueError):
            return False
        if state.computability != "computed":
            return False
        if projection.state is None or state.to_dict() != projection.state.to_dict():
            return False
    return True


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


def _capability_metrics(payload: Mapping[str, Any]) -> tuple[CitationMetric, ...]:
    """Project completed canonical capabilities without promoting them."""
    summary = _summary(payload)
    item_sets = (
        (summary.get("capability_items", ()), "canonical"),
        (summary.get("provider_capability_items", ()), "canonical.provider"),
    )
    records: list[CitationMetric] = []
    for items, method_prefix in item_sets:
        if not isinstance(items, (list, tuple)):
            continue
        for item in items:
            if not isinstance(item, Mapping) or item.get("status") != "completed":
                continue
            result = item.get("result")
            if not isinstance(result, Mapping):
                continue
            capability_id = str(item.get("capability_id", "")).strip()
            item_id = str(item.get("item_id", "")).strip()
            measurement_id = str(item.get("measurement_id", "")).strip()
            if not capability_id or not item_id or not measurement_id:
                continue
            # Provider projections have one value and its original metric path;
            # generic canonical items retain their nested numeric leaves.
            if method_prefix == "canonical.provider":
                value = _finite(result.get("value"))
                if value is None:
                    continue
                path = str(result.get("metric_path", "value"))
                records.append(_base(
                    payload,
                    key=f"{capability_id}.{path}",
                    value=value,
                    unit="unknown",
                    method=f"{method_prefix}.{capability_id}",
                    locator=f"capability_item_id={item_id};measurement_id={measurement_id};result.value;metric_path={path}",
                    eligibility="diagnostic_only",
                    reasons=("provider_capability_observation",),
                ))
                continue
            units = result.get("units", {})
            if not isinstance(units, Mapping):
                units = {}
            for path, value in _numeric_leaves(result):
                field = path[-1]
                if field in {"units", "x", "intensity"}:
                    continue
                if field == "point_count":
                    unit = "count"
                elif field.startswith("x_") or field == "x":
                    unit = str(units.get("x", "unknown"))
                elif field.startswith("intensity_") or field == "intensity":
                    unit = str(units.get("intensity", "unknown"))
                else:
                    unit = "unknown"
                locator = (
                    f"capability_item_id={item_id};measurement_id={measurement_id};"
                    f"result.{'.'.join(path)}"
                )
                records.append(_base(
                    payload,
                    key=f"{capability_id}.{'.'.join(path)}",
                    value=value,
                    unit=unit,
                    method=f"{method_prefix}.{capability_id}",
                    locator=locator,
                    eligibility="diagnostic_only",
                    reasons=("canonical_capability_observation",),
                ))
    return tuple(records)


def _numeric_leaves(value: Mapping[str, Any], prefix: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], float | int]]:
    for key, child in value.items():
        path = (*prefix, str(key))
        numeric = _finite(child)
        if numeric is not None:
            yield path, numeric
        elif isinstance(child, Mapping):
            yield from _numeric_leaves(child, path)


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
        if isinstance(r_squared, (int, float)) and r_squared < 0.95 and "low_avrami_r_squared" not in reasons:
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
