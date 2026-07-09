from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnalysisEvidence:
    technique: str
    summary: str = ""
    fit_evidence: dict[str, Any] = field(default_factory=dict)
    physical_evidence: dict[str, Any] = field(default_factory=dict)
    residual_evidence: dict[str, Any] = field(default_factory=dict)
    feature_evidence: dict[str, Any] = field(default_factory=dict)
    signal_evidence: dict[str, Any] = field(default_factory=dict)
    peak_evidence: dict[str, Any] = field(default_factory=dict)
    assignment_evidence: dict[str, Any] = field(default_factory=dict)
    reference_evidence: dict[str, Any] = field(default_factory=dict)
    background_evidence: dict[str, Any] = field(default_factory=dict)
    phase_evidence: dict[str, Any] = field(default_factory=dict)
    transform_evidence: dict[str, Any] = field(default_factory=dict)
    structure_evidence: dict[str, Any] = field(default_factory=dict)
    raw_structure_evidence: dict[str, Any] = field(default_factory=dict)
    batch_evidence: dict[str, Any] = field(default_factory=dict)
    condition_evidence: dict[str, Any] = field(default_factory=dict)
    stability_evidence: dict[str, Any] = field(default_factory=dict)
    symptoms: list[dict[str, Any]] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    confidence_signals: list[dict[str, Any]] = field(default_factory=list)
    actionable_symptoms: list[str] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    constraint_summary: dict[str, Any] = field(default_factory=dict)
    cross_validation: dict[str, Any] = field(default_factory=dict)
    source_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
