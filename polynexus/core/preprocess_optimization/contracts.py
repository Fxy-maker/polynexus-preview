from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "1.0"


def _contract_dict(value: object, tuple_fields: tuple[str, ...]) -> dict[str, Any]:
    payload = asdict(value)
    for name in tuple_fields:
        payload[name] = list(payload.get(name, ()))
    return deepcopy(payload)


@dataclass(frozen=True)
class PreprocessIntent:
    schema_version: str
    analysis_id: str
    technique: str
    target: str
    direction: str
    desired_effect: str
    protected_features: tuple[str, ...] = ()
    target_symptoms: tuple[str, ...] = ()
    rationale_code: str = ""
    human_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self, ("protected_features", "target_symptoms"))


@dataclass(frozen=True)
class PreprocessCandidate:
    schema_version: str
    candidate_id: str
    parent_intent_id: str
    technique: str
    generator_name: str
    generator_version: str
    base_config_hash: str
    config_delta: dict[str, Any]
    expected_effect: str
    protected_features: tuple[str, ...] = ()
    generation_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self, ("protected_features",))


@dataclass(frozen=True)
class PreprocessEvidence:
    schema_version: str
    candidate_id: str
    run_status: str
    evidence_coverage: float
    noise_reduction: float | None = None
    baseline_flatness: float | None = None
    residual_autocorrelation: float | None = None
    negative_fraction: float | None = None
    peak_shift: float | None = None
    fwhm_change: float | None = None
    integrated_area_change: float | None = None
    weak_peak_retention: float | None = None
    physical_parameter_drift: float | None = None
    technique_specific: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self, ("warnings",))


@dataclass(frozen=True)
class DecisionRecord:
    schema_version: str
    analysis_id: str
    original_config_hash: str
    selected_candidate_id: str | None
    decision: str
    confidence_band: str
    score_components: dict[str, float]
    hard_guard_results: dict[str, bool]
    evidence_refs: tuple[str, ...]
    policy_version: str
    core_version: str
    model_id: str = ""
    prompt_version: str = ""
    reason_codes: tuple[str, ...] = ()
    user_decision: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _contract_dict(self, ("evidence_refs", "reason_codes"))
