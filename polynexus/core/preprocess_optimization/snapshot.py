from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .candidates import stable_config_hash


@dataclass(frozen=True)
class AnalysisSnapshot:
    config: dict[str, Any]
    output_parameters: dict[str, Any]
    residual_pattern: dict[str, Any]
    analysis_evidence: dict[str, Any]
    config_hash: str

    @classmethod
    def from_parts(
        cls,
        *,
        config: dict[str, Any],
        output_parameters: dict[str, Any],
        residual_pattern: dict[str, Any],
        analysis_evidence: dict[str, Any],
    ) -> "AnalysisSnapshot":
        config_copy = deepcopy(config)
        return cls(
            config=config_copy,
            output_parameters=deepcopy(output_parameters),
            residual_pattern=deepcopy(residual_pattern),
            analysis_evidence=deepcopy(analysis_evidence),
            config_hash=stable_config_hash(config_copy),
        )
