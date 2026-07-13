from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol, Sequence

from .contracts import PreprocessCandidate, PreprocessIntent
from .policy import PolicyValidationError, PreprocessPolicy


class CandidateAdapter(Protocol):
    name: str
    version: str

    def baseline_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]: ...

    def smoothing_deltas(
        self,
        intent: PreprocessIntent,
        base_config: dict[str, Any],
    ) -> list[dict[str, Any]]: ...


def _canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, set):
        items = [_canonical_value(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    if isinstance(value, Path):
        return str(value)
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except (TypeError, ValueError):
            pass
    return value


def _stable_json(value: Any) -> str:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def stable_config_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json(config).encode("utf-8")).hexdigest()


def generate_preprocess_candidates(
    intent: PreprocessIntent,
    base_config: dict[str, Any],
    policy: PreprocessPolicy,
    adapter: CandidateAdapter,
    *,
    experience_deltas: Sequence[dict[str, Any]] = (),
) -> list[PreprocessCandidate]:
    policy.validate_intent(intent)
    base_snapshot = deepcopy(base_config)
    base_hash = stable_config_hash(base_snapshot)
    intent_id = hashlib.sha256(_stable_json(intent.to_dict()).encode("utf-8")).hexdigest()[:24]

    staged: list[tuple[str, dict[str, Any]]] = [("control", {})]
    staged.extend(("experience", deepcopy(delta)) for delta in experience_deltas)
    if intent.target in {"baseline", "both"}:
        staged.extend(
            ("baseline", deepcopy(delta))
            for delta in adapter.baseline_deltas(intent, deepcopy(base_snapshot))
        )
    if intent.target in {"smoothing", "both"}:
        staged.extend(
            ("smoothing", deepcopy(delta))
            for delta in adapter.smoothing_deltas(intent, deepcopy(base_snapshot))
        )

    candidates: list[PreprocessCandidate] = []
    seen: set[str] = set()
    for stage, delta in staged:
        if not isinstance(delta, dict):
            continue
        try:
            policy.validate_candidate(base_snapshot, delta)
        except PolicyValidationError:
            continue

        signature = _stable_json(delta)
        if signature in seen:
            continue
        seen.add(signature)
        identity = ":".join(
            (
                base_hash,
                intent_id,
                str(adapter.name),
                str(adapter.version),
                stage,
                signature,
            )
        )
        candidates.append(
            PreprocessCandidate(
                schema_version=intent.schema_version,
                candidate_id=hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
                parent_intent_id=intent_id,
                technique=intent.technique,
                generator_name=str(adapter.name),
                generator_version=str(adapter.version),
                base_config_hash=base_hash,
                config_delta=deepcopy(delta),
                expected_effect=intent.desired_effect,
                protected_features=intent.protected_features,
                generation_reason=stage,
            )
        )
        if len(candidates) >= policy.max_candidates:
            break
    return candidates
