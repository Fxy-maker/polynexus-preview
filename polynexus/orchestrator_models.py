from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoundRecord:
    round_num: int
    config_snapshot: dict[str, Any]
    output_parameters: dict[str, Any]
    residuals_pattern: dict[str, Any]
    analysis_evidence: dict[str, Any]
    polymer_knowledge: dict[str, Any]
    r_squared: float
    eval_score: float
    llm_advice: dict[str, Any] | None
    round_idx: int = 0
    r_squared_before: float = 0.0
    r_squared_after: float = 0.0
    changes: dict[str, Any] | None = None
    accepted: bool = True
    prompt: str = ""
    symptoms: list[dict[str, Any]] = field(default_factory=list)
    symptom_names: list[str] = field(default_factory=list)
    symptom_summary: str = ""
    target_symptom: str = ""
    rollback_detail: str = ""
    decision_summary: str = ""
    preprocess_intent: dict[str, Any] = field(default_factory=dict)
    preprocess_candidates: list[dict[str, Any]] = field(default_factory=list)
    preprocess_evidence: list[dict[str, Any]] = field(default_factory=list)
    preprocess_decision: dict[str, Any] = field(default_factory=dict)
