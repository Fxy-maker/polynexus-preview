"""Shared, JSON-safe contracts for evidence-grounded paper workflows.

The contracts deliberately contain references and decisions only.  Scientific
values remain owned by the immutable evidence package and ComputeRun objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping


CONTRACT_VERSION = 1


def _json(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(v) for v in value]
    return value


def stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    """Return a deterministic identifier for a logical paper object."""
    if not isinstance(prefix, str) or not prefix.strip():
        raise ValueError("id prefix is invalid")
    encoded = json.dumps(_json(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
    return f"{prefix.strip().lower()}-{digest}"


def _text(value: Any, label: str, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is invalid")
    return value.strip()


def _strings(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{label} is invalid")
    result = tuple(str(v).strip() for v in value)
    if any(not v for v in result):
        raise ValueError(f"{label} is invalid")
    return tuple(dict.fromkeys(result))


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is invalid")
    return {str(k): _json(v) for k, v in value.items()}


@dataclass(frozen=True)
class InputRequest:
    request_id: str
    reason: str
    message: str
    fields: tuple[str, ...] = ()
    material: bool = True
    version: int = CONTRACT_VERSION

    @property
    def schema_version(self) -> int:
        return self.version

    @property
    def object_id(self) -> str:
        return self.request_id

    @classmethod
    def create(cls, *, reason: str, message: str, fields: tuple[str, ...] = (), material: bool = True) -> "InputRequest":
        reason = _text(reason, "reason") or ""
        message = _text(message, "message") or ""
        fields = _strings(fields, "fields")
        if not isinstance(material, bool):
            raise ValueError("material is invalid")
        rid = stable_id("input", {"reason": reason, "message": message, "fields": fields, "material": material})
        return cls(rid, reason, message, fields, material)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "request_id": self.request_id, "reason": self.reason, "message": self.message, "fields": list(self.fields), "material": self.material}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "InputRequest":
        if not isinstance(payload, Mapping) or int(payload.get("version", -1)) != CONTRACT_VERSION:
            raise ValueError("input request version is invalid")
        return cls(str(payload.get("request_id", "")), _text(payload.get("reason"), "reason") or "", _text(payload.get("message"), "message") or "", _strings(payload.get("fields", ()), "fields"), bool(payload.get("material", True)))


@dataclass(frozen=True)
class PaperBrief:
    research_question: str
    title_hint: str | None = None
    comparison_scope: Mapping[str, Any] = field(default_factory=dict)
    figure_budget: Mapping[str, int] = field(default_factory=dict)
    notes: str | None = None
    needs_input: tuple[InputRequest, ...] = ()
    status: str = "draft"
    brief_id: str = ""
    version: int = CONTRACT_VERSION

    @property
    def schema_version(self) -> int:
        return self.version

    @property
    def object_id(self) -> str:
        return self.brief_id

    @classmethod
    def create(cls, *, research_question: str, title_hint: str | None = None, comparison_scope: Mapping[str, Any] | None = None, figure_budget: Mapping[str, int] | None = None, notes: str | None = None, needs_input: tuple[InputRequest, ...] = ()) -> "PaperBrief":
        question = _text(research_question, "research question") or ""
        scope = _mapping(comparison_scope, "comparison scope")
        budget = {str(k): int(v) for k, v in (figure_budget or {"main_max": 6, "supporting_max": 12}).items()}
        if any(v < 0 for v in budget.values()):
            raise ValueError("figure budget is invalid")
        requests = tuple(needs_input)
        if any(not isinstance(v, InputRequest) for v in requests):
            raise ValueError("needs_input is invalid")
        status = "needs_input" if any(v.material for v in requests) else "draft"
        bid = stable_id("brief", {"research_question": question, "title_hint": title_hint, "comparison_scope": scope, "figure_budget": budget, "notes": notes})
        return cls(question, title_hint, scope, budget, notes, requests, status, bid)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "brief_id": self.brief_id, "research_question": self.research_question, "title_hint": self.title_hint, "comparison_scope": _json(self.comparison_scope), "figure_budget": dict(self.figure_budget), "notes": self.notes, "needs_input": [v.to_dict() for v in self.needs_input], "status": self.status}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PaperBrief":
        if not isinstance(payload, Mapping) or int(payload.get("version", -1)) != CONTRACT_VERSION:
            raise ValueError("paper brief version is invalid")
        requests = tuple(InputRequest.from_dict(v) for v in payload.get("needs_input", ()))
        obj = cls.create(research_question=payload.get("research_question"), title_hint=payload.get("title_hint"), comparison_scope=payload.get("comparison_scope"), figure_budget=payload.get("figure_budget"), notes=payload.get("notes"), needs_input=requests)
        return cls(obj.research_question, obj.title_hint, obj.comparison_scope, obj.figure_budget, obj.notes, requests, str(payload.get("status", obj.status)), str(payload.get("brief_id", obj.brief_id)))


@dataclass(frozen=True)
class ClaimRecord:
    text: str
    evidence_ids: tuple[str, ...] = ()
    metric_ids: tuple[str, ...] = ()
    figure_ids: tuple[str, ...] = ()
    role: str = "results"
    claim_id: str = ""
    version: int = CONTRACT_VERSION

    @property
    def schema_version(self) -> int: return self.version
    @property
    def object_id(self) -> str: return self.claim_id

    @classmethod
    def create(cls, *, text: str, evidence_ids: tuple[str, ...] = (), metric_ids: tuple[str, ...] = (), figure_ids: tuple[str, ...] = (), role: str = "results") -> "ClaimRecord":
        text = _text(text, "claim text") or ""
        role = _text(role, "claim role") or ""
        if role not in {"results", "discussion", "hypothesis"}:
            raise ValueError("claim role is invalid")
        e, m, f = _strings(evidence_ids, "evidence_ids"), _strings(metric_ids, "metric_ids"), _strings(figure_ids, "figure_ids")
        cid = stable_id("claim", {"text": text, "evidence_ids": e, "metric_ids": m, "figure_ids": f, "role": role})
        return cls(text, e, m, f, role, cid)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "claim_id": self.claim_id, "text": self.text, "evidence_ids": list(self.evidence_ids), "metric_ids": list(self.metric_ids), "figure_ids": list(self.figure_ids), "role": self.role}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ClaimRecord":
        if int(payload.get("version", -1)) != CONTRACT_VERSION:
            raise ValueError("claim version is invalid")
        obj = cls.create(text=payload.get("text"), evidence_ids=_strings(payload.get("evidence_ids", ()), "evidence_ids"), metric_ids=_strings(payload.get("metric_ids", ()), "metric_ids"), figure_ids=_strings(payload.get("figure_ids", ()), "figure_ids"), role=payload.get("role", "results"))
        return cls(obj.text, obj.evidence_ids, obj.metric_ids, obj.figure_ids, obj.role, str(payload.get("claim_id", obj.claim_id)))


@dataclass(frozen=True)
class FigurePlan:
    title: str
    layout: str = "single"
    source_ids: tuple[str, ...] = ()
    metric_ids: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ("svg", "json")
    figure_id: str = ""
    status: str = "candidate"
    x_label: str = ""
    y_label: str = ""
    unit: str = ""
    data: tuple[tuple[float, float], ...] = ()
    version: int = CONTRACT_VERSION

    @property
    def schema_version(self) -> int: return self.version
    @property
    def object_id(self) -> str: return self.figure_id

    @classmethod
    def create(cls, *, title: str, source_ids: tuple[str, ...] = (), metric_ids: tuple[str, ...] = (), layout: str = "single", outputs: tuple[str, ...] = ("svg", "json"), status: str = "candidate", x_label: str = "", y_label: str = "", unit: str = "", data: tuple[tuple[float, float], ...] = ()) -> "FigurePlan":
        title = _text(title, "figure title") or ""
        layout = _text(layout, "figure layout") or ""
        source_ids, metric_ids, outputs = _strings(source_ids, "source_ids"), _strings(metric_ids, "metric_ids"), _strings(outputs, "outputs")
        if "svg" not in outputs or "json" not in outputs:
            raise ValueError("figure outputs must include svg and json")
        fid = stable_id("figure", {"title": title, "layout": layout, "source_ids": source_ids, "metric_ids": metric_ids})
        points = tuple((float(x), float(y)) for x, y in data)
        return cls(title, layout, source_ids, metric_ids, outputs, fid, status, x_label, y_label, unit, points)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "figure_id": self.figure_id, "title": self.title, "layout": self.layout, "source_ids": list(self.source_ids), "metric_ids": list(self.metric_ids), "outputs": list(self.outputs), "status": self.status, "x_label": self.x_label, "y_label": self.y_label, "unit": self.unit, "data": [list(p) for p in self.data]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FigurePlan":
        if int(payload.get("version", -1)) != CONTRACT_VERSION:
            raise ValueError("figure plan version is invalid")
        obj = cls.create(title=payload.get("title"), source_ids=_strings(payload.get("source_ids", ()), "source_ids"), metric_ids=_strings(payload.get("metric_ids", ()), "metric_ids"), layout=payload.get("layout", "single"), outputs=_strings(payload.get("outputs", ("svg", "json")), "outputs"), status=payload.get("status", "candidate"), x_label=payload.get("x_label", ""), y_label=payload.get("y_label", ""), unit=payload.get("unit", ""), data=tuple(tuple(v) for v in payload.get("data", ())))
        return cls(obj.title, obj.layout, obj.source_ids, obj.metric_ids, obj.outputs, str(payload.get("figure_id", obj.figure_id)), obj.status, obj.x_label, obj.y_label, obj.unit, obj.data)


@dataclass(frozen=True)
class CitationRequest:
    key: str
    locator: str
    mode: str = "auto"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    citation_id: str = ""
    version: int = CONTRACT_VERSION

    @property
    def schema_version(self) -> int: return self.version
    @property
    def object_id(self) -> str: return self.citation_id

    @classmethod
    def create(cls, *, key: str, locator: str, mode: str = "auto", metadata: Mapping[str, Any] | None = None) -> "CitationRequest":
        key, locator = _text(key, "citation key") or "", _text(locator, "citation locator") or ""
        if mode not in {"auto", "dynamic", "static"}:
            raise ValueError("citation mode is invalid")
        metadata = _mapping(metadata, "citation metadata")
        cid = stable_id("citation", {"key": key, "locator": locator, "mode": mode, "metadata": metadata})
        return cls(key, locator, mode, metadata, cid)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "citation_id": self.citation_id, "key": self.key, "locator": self.locator, "mode": self.mode, "metadata": _json(self.metadata)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CitationRequest":
        if int(payload.get("version", -1)) != CONTRACT_VERSION:
            raise ValueError("citation version is invalid")
        obj = cls.create(key=payload.get("key"), locator=payload.get("locator"), mode=payload.get("mode", "auto"), metadata=payload.get("metadata"))
        return cls(obj.key, obj.locator, obj.mode, obj.metadata, str(payload.get("citation_id", obj.citation_id)))


@dataclass(frozen=True)
class ManuscriptSource:
    package_id: str
    claim_ids: tuple[str, ...] = ()
    figure_plan_ids: tuple[str, ...] = ()
    table_ids: tuple[str, ...] = ()
    citation_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    source_id: str = ""
    status: str = "draft"
    needs_input: tuple[InputRequest, ...] = ()
    projection: Mapping[str, Any] = field(default_factory=dict)
    version: int = CONTRACT_VERSION

    @property
    def schema_version(self) -> int: return self.version
    @property
    def object_id(self) -> str: return self.source_id

    @classmethod
    def create(cls, *, package_id: str, claim_ids: tuple[str, ...] = (), figure_plan_ids: tuple[str, ...] = (), table_ids: tuple[str, ...] = (), citation_ids: tuple[str, ...] = (), limitations: tuple[str, ...] = (), needs_input: tuple[InputRequest, ...] = ()) -> "ManuscriptSource":
        package_id = _text(package_id, "package id") or ""
        values = [_strings(v, n) for v, n in ((claim_ids, "claim_ids"), (figure_plan_ids, "figure_plan_ids"), (table_ids, "table_ids"), (citation_ids, "citation_ids"), (limitations, "limitations"))]
        requests = tuple(needs_input)
        sid = stable_id("manuscript", {"package_id": package_id, "claim_ids": values[0], "figure_plan_ids": values[1], "table_ids": values[2], "citation_ids": values[3], "limitations": values[4]})
        return cls(package_id, *values[:4], values[4], sid, "needs_input" if any(r.material for r in requests) else "draft", requests, {})

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "source_id": self.source_id, "package_id": self.package_id, "claim_ids": list(self.claim_ids), "figure_plan_ids": list(self.figure_plan_ids), "table_ids": list(self.table_ids), "citation_ids": list(self.citation_ids), "limitations": list(self.limitations), "status": self.status, "needs_input": [r.to_dict() for r in self.needs_input], "projection": _json(self.projection)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ManuscriptSource":
        if int(payload.get("version", -1)) != CONTRACT_VERSION:
            raise ValueError("manuscript source version is invalid")
        requests = tuple(InputRequest.from_dict(v) for v in payload.get("needs_input", ()))
        obj = cls.create(package_id=payload.get("package_id"), claim_ids=_strings(payload.get("claim_ids", ()), "claim_ids"), figure_plan_ids=_strings(payload.get("figure_plan_ids", ()), "figure_plan_ids"), table_ids=_strings(payload.get("table_ids", ()), "table_ids"), citation_ids=_strings(payload.get("citation_ids", ()), "citation_ids"), limitations=_strings(payload.get("limitations", ()), "limitations"), needs_input=requests)
        return cls(obj.package_id, obj.claim_ids, obj.figure_plan_ids, obj.table_ids, obj.citation_ids, obj.limitations, str(payload.get("source_id", obj.source_id)), str(payload.get("status", obj.status)), requests, _mapping(payload.get("projection", {}), "projection"))


@dataclass(frozen=True)
class PreflightReport:
    source_id: str
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    checks: Mapping[str, str] = field(default_factory=dict)
    report_id: str = ""
    status: str = "passed"
    version: int = CONTRACT_VERSION

    @property
    def schema_version(self) -> int: return self.version
    @property
    def object_id(self) -> str: return self.report_id

    @classmethod
    def create(cls, *, source_id: str, errors: tuple[str, ...] = (), warnings: tuple[str, ...] = (), checks: Mapping[str, str] | None = None) -> "PreflightReport":
        source_id = _text(source_id, "source id") or ""
        errors, warnings = _strings(errors, "errors"), _strings(warnings, "warnings")
        checks = {str(k): str(v) for k, v in (checks or {}).items()}
        status = "failed" if errors else ("review_required" if warnings else "passed")
        rid = stable_id("preflight", {"source_id": source_id, "errors": errors, "warnings": warnings, "checks": checks})
        return cls(source_id, errors, warnings, checks, rid, status)

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "report_id": self.report_id, "source_id": self.source_id, "errors": list(self.errors), "warnings": list(self.warnings), "checks": dict(self.checks), "status": self.status}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PreflightReport":
        if int(payload.get("version", -1)) != CONTRACT_VERSION:
            raise ValueError("preflight version is invalid")
        obj = cls.create(source_id=payload.get("source_id"), errors=_strings(payload.get("errors", ()), "errors"), warnings=_strings(payload.get("warnings", ()), "warnings"), checks=payload.get("checks"))
        return cls(obj.source_id, obj.errors, obj.warnings, obj.checks, str(payload.get("report_id", obj.report_id)), str(payload.get("status", obj.status)))


__all__ = ["CONTRACT_VERSION", "stable_id", "InputRequest", "PaperBrief", "ClaimRecord", "FigurePlan", "CitationRequest", "ManuscriptSource", "PreflightReport"]
