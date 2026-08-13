"""Immutable, JSON-safe contracts for Codex-managed project workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "1"


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Project contracts do not allow non-finite numbers")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_json_safe(item) for item in sorted(value, key=str)]
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict())
    raise TypeError(f"Project contracts do not support {type(value).__name__}")


def _freeze(value: Any) -> Any:
    normalized = _json_safe(value)
    if isinstance(normalized, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in normalized.items()})
    if isinstance(normalized, list):
        return tuple(_freeze(item) for item in normalized)
    return normalized


def _public(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_public(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _hash_payload(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProjectFact:
    key: str
    value: Any = None
    status: str = "unknown"
    source: str = "unknown"
    discrepancies: tuple[str, ...] = ()
    sources: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", str(self.key))
        object.__setattr__(self, "value", _freeze(self.value))
        object.__setattr__(self, "status", str(self.status))
        object.__setattr__(self, "source", str(self.source))
        object.__setattr__(self, "discrepancies", tuple(str(item) for item in self.discrepancies))
        object.__setattr__(self, "sources", _freeze(dict(self.sources)))

    @classmethod
    def from_sources(
        cls,
        *,
        key: str,
        raw_value: Any = None,
        record_value: Any = None,
        directory_value: Any = None,
        filename_value: Any = None,
        inference_value: Any = None,
    ) -> "ProjectFact":
        candidates = (
            ("raw", raw_value),
            ("record", record_value),
            ("directory", directory_value),
            ("filename", filename_value),
            ("inference", inference_value),
        )
        chosen_source, chosen_value = next(
            ((name, value) for name, value in candidates if value is not None), ("unknown", None)
        )
        status = {"raw": "verified_from_raw", "record": "verified_from_record"}.get(
            chosen_source,
            "inferred" if chosen_source in {"directory", "filename", "inference"} else "unknown",
        )
        discrepancies: list[str] = []
        if chosen_value is not None:
            for name, value in candidates:
                if name == chosen_source or value is None:
                    continue
                if value != chosen_value:
                    discrepancies.append(f"{name}_value_disagrees")
        return cls(
            key=key,
            value=chosen_value,
            status=status,
            source=chosen_source,
            discrepancies=tuple(discrepancies),
            sources={name: value for name, value in candidates if value is not None},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": _public(self.value),
            "status": self.status,
            "source": self.source,
            "discrepancies": list(self.discrepancies),
            "sources": _public(self.sources),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProjectFact":
        return cls(
            key=str(value["key"]),
            value=value.get("value"),
            status=str(value.get("status", "unknown")),
            source=str(value.get("source", "unknown")),
            discrepancies=tuple(value.get("discrepancies", ())),
            sources=value.get("sources", {}),
        )


@dataclass(frozen=True)
class ProjectArtifact:
    artifact_id: str
    relative_path: str
    technique: str
    sha256: str | None
    facts: Mapping[str, ProjectFact] = field(default_factory=dict)
    format: str = ""
    inspection_status: str = "ready"
    reason_codes: tuple[str, ...] = ()
    discrepancies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "relative_path", str(self.relative_path))
        object.__setattr__(self, "technique", str(self.technique).lower())
        object.__setattr__(self, "sha256", str(self.sha256) if self.sha256 else None)
        object.__setattr__(self, "format", str(self.format))
        object.__setattr__(self, "inspection_status", str(self.inspection_status))
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))
        if self.inspection_status not in {"ready", "review_required", "blocked"}:
            raise ValueError(f"Unsupported inspection status: {self.inspection_status}")
        object.__setattr__(
            self,
            "facts",
            MappingProxyType(
                {
                    str(k): (
                        v
                        if isinstance(v, ProjectFact)
                        else ProjectFact.from_sources(key=str(k), raw_value=v)
                    )
                    for k, v in dict(self.facts).items()
                }
            ),
        )
        object.__setattr__(self, "discrepancies", tuple(str(item) for item in self.discrepancies))

    @property
    def path(self) -> str:
        return self.relative_path

    @property
    def observed_facts(self) -> Mapping[str, ProjectFact]:
        return self.facts

    @classmethod
    def create(
        cls,
        *,
        project_root: str | Path,
        path: str | Path,
        technique: str,
        sha256: str | None,
        observed_facts: Mapping[str, Any] | None = None,
        facts: Mapping[str, ProjectFact] | None = None,
        format: str = "",
        inspection_status: str = "ready",
        reason_codes: Sequence[str] = (),
    ) -> "ProjectArtifact":
        # Use lexical absolute paths here. A project may expose an external
        # read-only laboratory directory through a `raw/` junction/symlink;
        # the indexer has already enforced the lexical project boundary.
        root = Path(project_root).expanduser().absolute()
        source = Path(path).expanduser().absolute()
        try:
            relative = source.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError("artifact path must be inside project root") from exc
        fact_values = (
            facts
            if facts is not None
            else {
                str(k): ProjectFact.from_sources(key=str(k), raw_value=v)
                for k, v in (observed_facts or {}).items()
            }
        )
        identity = cls._identity_payload(
            relative_path=relative,
            technique=technique,
            sha256=sha256,
            facts=fact_values,
        )
        return cls(
            artifact_id=_hash_payload(identity),
            relative_path=relative,
            technique=technique,
            sha256=sha256,
            facts=fact_values,
            format=format,
            inspection_status=inspection_status,
            reason_codes=tuple(reason_codes),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "relative_path": self.relative_path,
            "path": self.relative_path,
            "technique": self.technique,
            "sha256": self.sha256,
            "format": self.format,
            "inspection_status": self.inspection_status,
            "reason_codes": list(self.reason_codes),
            "facts": {k: v.to_dict() for k, v in self.facts.items()},
            "observed_facts": {k: v.to_dict() for k, v in self.facts.items()},
            "discrepancies": list(self.discrepancies),
        }

    @staticmethod
    def _identity_payload(
        *,
        relative_path: str,
        technique: str,
        sha256: str | None,
        facts: Mapping[str, ProjectFact],
    ) -> dict[str, Any]:
        """Raw identity excludes inspection outcomes, which are graph state."""
        return {
            "relative_path": str(relative_path),
            "technique": str(technique).lower(),
            "sha256": str(sha256) if sha256 else None,
            "facts": {key: fact.to_dict() for key, fact in facts.items()},
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProjectArtifact":
        if not value.get("artifact_id"):
            raise ValueError("artifact hash is missing")
        raw_facts = value.get("facts", value.get("observed_facts", {}))
        facts = {
            str(k): ProjectFact.from_dict(v)
            if isinstance(v, Mapping) and "key" in v
            else ProjectFact.from_sources(key=str(k), raw_value=v)
            for k, v in raw_facts.items()
        }
        artifact = cls(
            artifact_id=str(value["artifact_id"]),
            relative_path=str(value.get("relative_path", value.get("path", ""))),
            technique=str(value.get("technique", "unknown")),
            sha256=str(value["sha256"]) if value.get("sha256") else None,
            facts=facts,
            format=str(value.get("format", "")),
            inspection_status=str(value.get("inspection_status", "ready")),
            reason_codes=tuple(value.get("reason_codes", ())),
            discrepancies=tuple(value.get("discrepancies", ())),
        )
        identity = cls._identity_payload(
            relative_path=artifact.relative_path,
            technique=artifact.technique,
            sha256=artifact.sha256,
            facts=artifact.facts,
        )
        if artifact.artifact_id != _hash_payload(identity):
            raise ValueError("artifact hash does not match its content")
        return artifact


@dataclass(frozen=True)
class Formulation:
    formulation_id: str
    label: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "formulation_id": self.formulation_id,
            "label": self.label,
            "metadata": _public(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Formulation":
        return cls(str(value["formulation_id"]), str(value["label"]), value.get("metadata", {}))


@dataclass(frozen=True)
class PreparationBatch:
    batch_id: str
    formulation_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "formulation_id": self.formulation_id,
            "metadata": _public(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PreparationBatch":
        return cls(str(value["batch_id"]), str(value["formulation_id"]), value.get("metadata", {}))


@dataclass(frozen=True)
class Condition:
    condition_id: str
    batch_id: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", _freeze(self.parameters))

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "batch_id": self.batch_id,
            "parameters": _public(self.parameters),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Condition":
        return cls(str(value["condition_id"]), str(value["batch_id"]), value.get("parameters", {}))


@dataclass(frozen=True)
class Measurement:
    measurement_id: str
    condition_id: str
    technique: str
    artifact_ids: tuple[str, ...] | str = ()
    segment: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.artifact_ids, str):
            object.__setattr__(self, "artifact_ids", (self.artifact_ids,))
        else:
            object.__setattr__(self, "artifact_ids", tuple(str(x) for x in self.artifact_ids))
        object.__setattr__(self, "segment", _freeze(self.segment))

    @property
    def artifact_id(self) -> str:
        """Compatibility accessor for the primary raw artifact."""
        return self.artifact_ids[0] if self.artifact_ids else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "condition_id": self.condition_id,
            "technique": self.technique,
            "artifact_ids": list(self.artifact_ids),
            "artifact_id": self.artifact_id,
            "segment": _public(self.segment),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Measurement":
        artifact_ids = value.get("artifact_ids")
        if artifact_ids is None:
            artifact_ids = (value["artifact_id"],) if value.get("artifact_id") else ()
        return cls(
            measurement_id=str(value["measurement_id"]),
            condition_id=str(value["condition_id"]),
            technique=str(value["technique"]),
            artifact_ids=artifact_ids,
            segment=value.get("segment", {}),
        )


@dataclass(frozen=True)
class ResearchGraph:
    study_id: str
    formulations: tuple[Formulation, ...] = ()
    batches: tuple[PreparationBatch, ...] = ()
    conditions: tuple[Condition, ...] = ()
    measurements: tuple[Measurement, ...] = ()
    artifacts: tuple[ProjectArtifact, ...] = ()
    graph_hash: str = ""

    @classmethod
    def create(
        cls,
        *,
        study_id: str,
        formulations: Sequence[Formulation] = (),
        batches: Sequence[PreparationBatch] = (),
        conditions: Sequence[Condition] = (),
        measurements: Sequence[Measurement] = (),
        artifacts: Sequence[ProjectArtifact] = (),
    ) -> "ResearchGraph":
        payload = {
            "study_id": study_id,
            "formulations": [x.to_dict() for x in formulations],
            "batches": [x.to_dict() for x in batches],
            "conditions": [x.to_dict() for x in conditions],
            "measurements": [x.to_dict() for x in measurements],
            "artifacts": [x.to_dict() for x in artifacts],
        }
        return cls(
            study_id=str(study_id),
            formulations=tuple(formulations),
            batches=tuple(batches),
            conditions=tuple(conditions),
            measurements=tuple(measurements),
            artifacts=tuple(artifacts),
            graph_hash=_hash_payload(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "study_id": self.study_id,
            "formulations": [x.to_dict() for x in self.formulations],
            "batches": [x.to_dict() for x in self.batches],
            "conditions": [x.to_dict() for x in self.conditions],
            "measurements": [x.to_dict() for x in self.measurements],
            "artifacts": [x.to_dict() for x in self.artifacts],
            "graph_hash": self.graph_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResearchGraph":
        graph = cls.create(
            study_id=str(value["study_id"]),
            formulations=tuple(Formulation.from_dict(x) for x in value.get("formulations", ())),
            batches=tuple(PreparationBatch.from_dict(x) for x in value.get("batches", ())),
            conditions=tuple(Condition.from_dict(x) for x in value.get("conditions", ())),
            measurements=tuple(Measurement.from_dict(x) for x in value.get("measurements", ())),
            artifacts=tuple(ProjectArtifact.from_dict(x) for x in value.get("artifacts", ())),
        )
        if not value.get("graph_hash"):
            raise ValueError("graph hash is missing")
        if value["graph_hash"] != graph.graph_hash:
            legacy_artifacts = value.get("artifacts", ())
            if not any(
                "inspection_status" not in artifact or "reason_codes" not in artifact
                for artifact in legacy_artifacts
                if isinstance(artifact, Mapping)
            ):
                raise ValueError("Research graph hash does not match its content")
            legacy_payload = {
                "study_id": str(value["study_id"]),
                "formulations": list(value.get("formulations", ())),
                "batches": list(value.get("batches", ())),
                "conditions": list(value.get("conditions", ())),
                "measurements": list(value.get("measurements", ())),
                "artifacts": list(legacy_artifacts),
            }
            if value["graph_hash"] != _hash_payload(legacy_payload):
                raise ValueError("Research graph hash does not match its content")
        return graph


@dataclass(frozen=True)
class AnalysisRequest:
    request_id: str
    question: str
    purpose: str = "exploration"
    requested_outputs: tuple[str, ...] = ()
    data_scope: tuple[str, ...] = ()
    context_sources: tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(default_factory=dict)
    request_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested_outputs", tuple(str(x) for x in self.requested_outputs))
        object.__setattr__(self, "data_scope", tuple(str(x) for x in self.data_scope))
        object.__setattr__(self, "context_sources", tuple(str(x) for x in self.context_sources))
        object.__setattr__(self, "parameters", _freeze(self.parameters))

    @classmethod
    def create(
        cls,
        *,
        question: str,
        purpose: str = "exploration",
        requested_outputs: Sequence[str] = (),
        data_scope: Sequence[str] = (),
        context_sources: Sequence[str] = (),
        parameters: Mapping[str, Any] | None = None,
        request_id: str | None = None,
    ) -> "AnalysisRequest":
        payload = {
            "question": str(question),
            "purpose": str(purpose),
            "requested_outputs": list(requested_outputs),
            "data_scope": list(data_scope),
            "context_sources": list(context_sources),
            "parameters": parameters or {},
        }
        digest = _hash_payload(payload)
        return cls(
            request_id=request_id or f"request-{digest[:16]}", request_hash=digest, **payload
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "question": self.question,
            "purpose": self.purpose,
            "requested_outputs": list(self.requested_outputs),
            "data_scope": list(self.data_scope),
            "context_sources": list(self.context_sources),
            "parameters": _public(self.parameters),
            "request_hash": self.request_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AnalysisRequest":
        request = cls.create(
            question=str(value["question"]),
            purpose=str(value.get("purpose", "exploration")),
            requested_outputs=value.get("requested_outputs", ()),
            data_scope=value.get("data_scope", ()),
            context_sources=value.get("context_sources", ()),
            parameters=value.get("parameters", {}),
            request_id=str(value.get("request_id", "")) or None,
        )
        if not value.get("request_hash"):
            raise ValueError("request hash is missing")
        if value["request_hash"] != request.request_hash:
            raise ValueError("Analysis request hash does not match its content")
        return request


@dataclass(frozen=True)
class AnalysisPlan:
    """Frozen, replayable description of one deterministic analysis request."""

    source_files: tuple[Mapping[str, Any], ...] = ()
    scope: Mapping[str, Any] = field(default_factory=dict)
    analysis_intent: str | None = None
    requested_metrics: tuple[str, ...] = ()
    requested_figures: tuple[str, ...] = ()
    canonical_template: Mapping[str, Any] = field(default_factory=dict)
    algorithm: Mapping[str, Any] = field(default_factory=dict)
    default_config: Mapping[str, Any] = field(default_factory=dict)
    candidate_configs: tuple[Mapping[str, Any], ...] = ()
    protected_metrics: tuple[str, ...] = ()
    scientific_constraints: tuple[str, ...] = ()
    review_thresholds: Mapping[str, Any] = field(default_factory=dict)
    ai_context: Mapping[str, Any] = field(default_factory=dict)
    random_seed: int | None = None
    selected_candidate_id: str | None = None
    approval: Mapping[str, Any] = field(default_factory=dict)
    parent_run_id: str | None = None
    replan_of: str | None = None
    replay: Mapping[str, Any] = field(default_factory=dict)
    plan_version: str = CONTRACT_VERSION
    plan_id: str = ""
    plan_hash: str = ""

    def __post_init__(self) -> None:
        normalized_sources = tuple(_freeze(dict(item)) for item in self.source_files)
        object.__setattr__(self, "source_files", normalized_sources)
        object.__setattr__(self, "scope", _freeze(self.scope))
        object.__setattr__(self, "analysis_intent", None if self.analysis_intent is None else str(self.analysis_intent))
        for name in ("requested_metrics", "requested_figures", "protected_metrics", "scientific_constraints"):
            object.__setattr__(self, name, tuple(str(item) for item in getattr(self, name)))
        for name in ("canonical_template", "algorithm", "default_config", "review_thresholds", "ai_context", "approval", "replay"):
            object.__setattr__(self, name, _freeze(getattr(self, name)))
        if self.ai_context:
            required_ai = {"provider", "model_version", "input_hash", "output_hash", "decision_hash"}
            if not required_ai.issubset(set(self.ai_context)):
                raise ValueError("Analysis plan AI provenance is incomplete")
        object.__setattr__(self, "candidate_configs", tuple(_freeze(dict(item)) for item in self.candidate_configs))
        object.__setattr__(self, "plan_version", str(self.plan_version))
        object.__setattr__(self, "plan_id", str(self.plan_id))
        if self.random_seed is not None:
            object.__setattr__(self, "random_seed", int(self.random_seed))
        for name in ("selected_candidate_id", "parent_run_id", "replan_of"):
            value = getattr(self, name)
            object.__setattr__(self, name, None if value is None else str(value))

    @classmethod
    def create(cls, *, source_files: Sequence[Mapping[str, Any]], canonical_template: Mapping[str, Any], algorithm: Mapping[str, Any], **values: Any) -> "AnalysisPlan":
        sources = tuple(dict(item) for item in source_files)
        for source in sources:
            if not source.get("path") or not source.get("sha256"):
                raise ValueError("Analysis plan source hash is required")
        if not canonical_template.get("template_id") or not canonical_template.get("conversion_version"):
            raise ValueError("Analysis plan canonical template version is required")
        if not algorithm.get("algorithm_id"):
            raise ValueError("Analysis plan algorithm id is required")
        if not algorithm.get("algorithm_version"):
            raise ValueError("Analysis plan algorithm version is required")
        ai_context = values.get("ai_context", {})
        if ai_context:
            required_ai = {"provider", "model_version", "input_hash", "output_hash", "decision_hash"}
            if not required_ai.issubset(set(ai_context)):
                raise ValueError("Analysis plan AI provenance is incomplete")
        payload = {
            "source_files": [_public(item) for item in sources],
            "scope": _public(values.get("scope", {})),
            "analysis_intent": values.get("analysis_intent"),
            "requested_metrics": list(values.get("requested_metrics", ())),
            "requested_figures": list(values.get("requested_figures", ())),
            "canonical_template": _public(canonical_template),
            "algorithm": _public(algorithm),
            "default_config": _public(values.get("default_config", {})),
            "candidate_configs": [_public(item) for item in values.get("candidate_configs", ())],
            "protected_metrics": list(values.get("protected_metrics", ())),
            "scientific_constraints": list(values.get("scientific_constraints", ())),
            "review_thresholds": _public(values.get("review_thresholds", {})),
            "ai_context": _public(values.get("ai_context", {})),
            "random_seed": values.get("random_seed"),
            "selected_candidate_id": values.get("selected_candidate_id"),
            "approval": _public(values.get("approval", {})),
            "parent_run_id": values.get("parent_run_id"),
            "replan_of": values.get("replan_of"),
            "replay": _public(values.get("replay", {})),
            "plan_version": str(values.get("plan_version", CONTRACT_VERSION)),
        }
        digest = _hash_payload(payload)
        return cls(
            source_files=sources,
            canonical_template=canonical_template,
            algorithm=algorithm,
            plan_id=str(values.get("plan_id") or f"plan-{digest[:16]}"),
            plan_hash=digest,
            **{key: value for key, value in values.items() if key not in {"plan_id", "plan_hash"}},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_files": [_public(item) for item in self.source_files], "scope": _public(self.scope),
            "analysis_intent": self.analysis_intent, "requested_metrics": list(self.requested_metrics),
            "requested_figures": list(self.requested_figures), "canonical_template": _public(self.canonical_template),
            "algorithm": _public(self.algorithm), "default_config": _public(self.default_config),
            "candidate_configs": [_public(item) for item in self.candidate_configs],
            "protected_metrics": list(self.protected_metrics), "scientific_constraints": list(self.scientific_constraints),
            "review_thresholds": _public(self.review_thresholds), "ai_context": _public(self.ai_context),
            "random_seed": self.random_seed, "selected_candidate_id": self.selected_candidate_id,
            "approval": _public(self.approval), "parent_run_id": self.parent_run_id, "replan_of": self.replan_of,
            "replay": _public(self.replay), "plan_version": self.plan_version, "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AnalysisPlan":
        payload = dict(value)
        supplied_hash = str(payload.pop("plan_hash", ""))
        supplied_id = str(payload.pop("plan_id", ""))
        if not supplied_hash:
            raise ValueError("Analysis plan hash is missing")
        plan = cls.create(plan_id=supplied_id or None, **payload)
        if supplied_hash != plan.plan_hash:
            raise ValueError("Analysis plan hash does not match its content")
        return plan


@dataclass(frozen=True)
class ProjectPlan:
    request_hash: str
    steps: tuple[Mapping[str, Any], ...] = ()
    status: str = "proposed"
    reason_codes: tuple[str, ...] = ()
    required_context: tuple[str, ...] = ()
    plan_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(_freeze(x) for x in self.steps))
        object.__setattr__(self, "reason_codes", tuple(str(x) for x in self.reason_codes))
        object.__setattr__(self, "required_context", tuple(str(x) for x in self.required_context))

    @classmethod
    def create(
        cls,
        *,
        request_hash: str,
        steps: Sequence[Mapping[str, Any]] = (),
        status: str = "proposed",
        reason_codes: Sequence[str] = (),
        required_context: Sequence[str] = (),
    ) -> "ProjectPlan":
        payload = {
            "request_hash": request_hash,
            "steps": [_public(x) for x in steps],
            "status": status,
            "reason_codes": list(reason_codes),
            "required_context": list(required_context),
        }
        return cls(
            request_hash=str(request_hash),
            steps=tuple(steps),
            status=str(status),
            reason_codes=tuple(reason_codes),
            required_context=tuple(required_context),
            plan_hash=_hash_payload(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_hash": self.request_hash,
            "steps": [_public(x) for x in self.steps],
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "required_context": list(self.required_context),
            "plan_hash": self.plan_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProjectPlan":
        plan = cls.create(
            request_hash=str(value["request_hash"]),
            steps=value.get("steps", ()),
            status=str(value.get("status", "proposed")),
            reason_codes=value.get("reason_codes", ()),
            required_context=value.get("required_context", ()),
        )
        if not value.get("plan_hash"):
            raise ValueError("plan hash is missing")
        if value["plan_hash"] != plan.plan_hash:
            raise ValueError("Project plan hash does not match its content")
        return plan


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    kind: str
    technique: str
    claim_scope: str
    observed_results: Mapping[str, Any] = field(default_factory=dict)
    supported_interpretations: tuple[str, ...] = ()
    disallowed_conclusions: tuple[str, ...] = ()
    source_runs: tuple[str, ...] = ()
    raw_sources: tuple[str, ...] = ()
    figures: tuple[str, ...] = ()
    tables: tuple[str, ...] = ()
    status: str = "review_required"
    limitations: tuple[str, ...] = ()
    item_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_results", _freeze(self.observed_results))
        object.__setattr__(
            self, "supported_interpretations", tuple(str(x) for x in self.supported_interpretations)
        )
        object.__setattr__(
            self, "disallowed_conclusions", tuple(str(x) for x in self.disallowed_conclusions)
        )
        object.__setattr__(self, "source_runs", tuple(str(x) for x in self.source_runs))
        object.__setattr__(self, "raw_sources", tuple(str(x) for x in self.raw_sources))
        object.__setattr__(self, "figures", tuple(str(x) for x in self.figures))
        object.__setattr__(self, "tables", tuple(str(x) for x in self.tables))
        object.__setattr__(self, "limitations", tuple(str(x) for x in self.limitations))

    @classmethod
    def create(cls, **values: Any) -> "EvidenceItem":
        payload = dict(values)
        payload.pop("item_hash", None)
        provisional = cls(item_hash="", **payload)
        identity = provisional.to_dict()
        identity.pop("item_hash", None)
        return cls(item_hash=_hash_payload(identity), **payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "kind": self.kind,
            "technique": self.technique,
            "claim_scope": self.claim_scope,
            "observed_results": _public(self.observed_results),
            "supported_interpretations": list(self.supported_interpretations),
            "disallowed_conclusions": list(self.disallowed_conclusions),
            "source_runs": list(self.source_runs),
            "raw_sources": list(self.raw_sources),
            "figures": list(self.figures),
            "tables": list(self.tables),
            "status": self.status,
            "limitations": list(self.limitations),
            "item_hash": self.item_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceItem":
        item = cls.create(
            **{
                k: value.get(
                    k,
                    []
                    if k
                    in {
                        "supported_interpretations",
                        "disallowed_conclusions",
                        "source_runs",
                        "raw_sources",
                        "figures",
                        "tables",
                        "limitations",
                    }
                    else {},
                )
                for k in (
                    "evidence_id",
                    "kind",
                    "technique",
                    "claim_scope",
                    "observed_results",
                    "supported_interpretations",
                    "disallowed_conclusions",
                    "source_runs",
                    "raw_sources",
                    "figures",
                    "tables",
                    "status",
                    "limitations",
                )
            }
        )
        if not value.get("item_hash"):
            raise ValueError("evidence hash is missing")
        if value["item_hash"] != item.item_hash:
            raise ValueError("Evidence item hash does not match its content")
        return item


__all__ = [
    "AnalysisPlan",
    "AnalysisRequest",
    "Condition",
    "EvidenceItem",
    "Formulation",
    "Measurement",
    "PreparationBatch",
    "ProjectArtifact",
    "ProjectFact",
    "ProjectPlan",
    "ResearchGraph",
    "canonical_json",
]
