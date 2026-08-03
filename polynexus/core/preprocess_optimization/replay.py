"""JSON-safe audit records for preprocessing candidate replays."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import json
import math
from collections.abc import Mapping
from numbers import Real
from pathlib import Path
from typing import Any

from .candidates import stable_config_hash
from .contracts import PreprocessCandidate, PreprocessEvidence, SCHEMA_VERSION


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _json_safe(asdict(value))
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _json_safe(to_dict())
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _payload(value: Any) -> dict[str, Any]:
    normalized = _json_safe(value)
    if not isinstance(normalized, dict):
        raise TypeError("replay evidence and decision must serialize to objects")
    return normalized


@dataclass(frozen=True)
class PreprocessReplayAudit:
    """One candidate trial's immutable, candidate-only audit projection."""

    schema_version: str
    candidate_id: str
    technique: str
    mode: str
    generation_reason: str
    source_context: dict[str, Any]
    original_config_hash: str
    effective_config_hash: str | None
    run_status: str
    trial_engine_created: bool
    error: str
    evidence: dict[str, Any]
    decision: dict[str, Any]
    original_preserved: bool = True
    apply_allowed: bool = False
    apply_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)


def build_preprocess_replay_audit(
    *,
    candidate: PreprocessCandidate,
    source_config: Mapping[str, Any],
    effective_config: Mapping[str, Any] | None,
    mode: str,
    source_context: Mapping[str, Any] | None,
    evidence: PreprocessEvidence,
    decision: Any,
    trial_engine_created: bool,
    error: str,
    apply_performed: bool = False,
) -> PreprocessReplayAudit:
    """Build a replay row without retaining raw data or applying a candidate."""

    decision_payload = _payload(decision)
    effective_hash = (
        stable_config_hash(dict(effective_config)) if effective_config is not None else None
    )
    return PreprocessReplayAudit(
        schema_version=SCHEMA_VERSION,
        candidate_id=str(candidate.candidate_id),
        technique=str(candidate.technique).upper(),
        mode=str(mode or "static").strip().lower() or "static",
        generation_reason=str(candidate.generation_reason or ""),
        source_context=_payload(source_context or {}),
        original_config_hash=stable_config_hash(dict(source_config)),
        effective_config_hash=effective_hash,
        run_status=str(evidence.run_status or "failed"),
        trial_engine_created=bool(trial_engine_created),
        error=str(error or ""),
        evidence=_payload(evidence),
        decision=decision_payload,
        original_preserved=True,
        apply_allowed=bool(decision_payload.get("apply_allowed", False)),
        apply_performed=bool(apply_performed),
    )


__all__ = ["PreprocessReplayAudit", "build_preprocess_replay_audit"]
