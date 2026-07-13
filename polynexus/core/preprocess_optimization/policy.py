from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass, fields, replace
from numbers import Real
from typing import Any

from .contracts import PreprocessIntent


class PolicyValidationError(ValueError):
    """Raised when a preprocessing policy or candidate violates local rules."""


@dataclass(frozen=True)
class ParameterRule:
    name: str
    value_type: type
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] = ()

    def validate(self, value: object) -> None:
        if self.value_type in {int, float} and isinstance(value, bool):
            raise PolicyValidationError(f"{self.name}: bool is not numeric")
        if self.value_type is int and not isinstance(value, int):
            raise PolicyValidationError(f"{self.name}: expected int")
        if self.value_type is float and not isinstance(value, Real):
            raise PolicyValidationError(f"{self.name}: expected float")
        if self.value_type is str and not isinstance(value, str):
            raise PolicyValidationError(f"{self.name}: expected str")
        if self.value_type not in {int, float, str, bool}:
            raise PolicyValidationError(f"{self.name}: unsupported parameter type")
        if self.value_type is bool and not isinstance(value, bool):
            raise PolicyValidationError(f"{self.name}: expected bool")

        if self.choices and value not in self.choices:
            raise PolicyValidationError(f"{self.name}: unsupported choice {value!r}")

        if self.value_type in {int, float}:
            number = float(value)
            if not math.isfinite(number):
                raise PolicyValidationError(f"{self.name}: must be finite")
            if self.minimum is not None and number < self.minimum:
                raise PolicyValidationError(f"{self.name}: below minimum {self.minimum}")
            if self.maximum is not None and number > self.maximum:
                raise PolicyValidationError(f"{self.name}: above maximum {self.maximum}")


@dataclass(frozen=True)
class PreprocessPolicy:
    policy_version: str
    technique: str
    allowed_targets: tuple[str, ...]
    allowed_directions: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    allowed_protected_features: tuple[str, ...]
    parameters: dict[str, ParameterRule]
    required_evidence: tuple[str, ...]
    hard_limits: dict[str, float]
    score_weights: dict[str, float]
    medium_threshold: float
    high_threshold: float
    min_candidate_margin: float
    max_candidates: int
    candidate_timeout_s: float
    automation_state: str = "shadow"
    calibrated: bool = False

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise PolicyValidationError("policy_version is required")
        if self.automation_state not in {"shadow", "confirm_only", "tiered_auto"}:
            raise PolicyValidationError(f"unknown automation state: {self.automation_state}")
        if self.automation_state == "tiered_auto" and not self.calibrated:
            raise PolicyValidationError("tiered_auto requires a calibrated policy")
        if not (0.0 <= self.medium_threshold < self.high_threshold <= 1.0):
            raise PolicyValidationError("confidence threshold order is invalid")
        if self.max_candidates < 2:
            raise PolicyValidationError("max_candidates must include control and a trial")
        if not math.isfinite(self.candidate_timeout_s) or self.candidate_timeout_s <= 0:
            raise PolicyValidationError("candidate_timeout_s must be positive")
        if any(weight < 0 or not math.isfinite(weight) for weight in self.score_weights.values()):
            raise PolicyValidationError("score weights must be finite and non-negative")
        if not any(weight > 0 for weight in self.score_weights.values()):
            raise PolicyValidationError("at least one score weight must be positive")

    def validate_intent(self, intent: PreprocessIntent) -> None:
        if intent.technique.upper() != self.technique:
            raise PolicyValidationError("intent technique does not match policy")
        if intent.target not in self.allowed_targets:
            raise PolicyValidationError(f"target is not allowed: {intent.target}")
        if intent.direction not in self.allowed_directions:
            raise PolicyValidationError(f"direction is not allowed: {intent.direction}")
        if intent.desired_effect not in self.allowed_effects:
            raise PolicyValidationError(f"effect is not allowed: {intent.desired_effect}")
        unknown = set(intent.protected_features) - set(self.allowed_protected_features)
        if unknown:
            raise PolicyValidationError(f"unknown protected feature: {sorted(unknown)}")

    def validate_delta(self, delta: dict[str, object]) -> None:
        if not isinstance(delta, dict):
            raise PolicyValidationError("candidate delta must be a dictionary")
        for name, value in delta.items():
            rule = self.parameters.get(name)
            if rule is None:
                raise PolicyValidationError(f"unknown parameter: {name}")
            rule.validate(value)

    def validate_candidate(
        self,
        base_config: dict[str, Any],
        delta: dict[str, object],
    ) -> None:
        self.validate_delta(delta)
        effective = {**base_config, **delta}
        self._validate_window_dependency(effective, "smooth_window", "smooth_order")
        self._validate_window_dependency(effective, "savgol_window", "savgol_order")

    @staticmethod
    def _validate_window_dependency(
        effective: dict[str, Any],
        window_name: str,
        order_name: str,
    ) -> None:
        if window_name not in effective:
            return
        window = effective.get(window_name)
        if isinstance(window, bool) or not isinstance(window, int):
            raise PolicyValidationError(f"{window_name}: expected int")
        if window % 2 == 0:
            raise PolicyValidationError(f"{window_name}: must be odd")
        order = effective.get(order_name)
        if order is not None and window <= int(order):
            raise PolicyValidationError(f"{window_name}: must be greater than {order_name}")

    def with_automation_state(self, state: str) -> "PreprocessPolicy":
        return replace(self, automation_state=state)

    def to_dict(self) -> dict[str, Any]:
        return {item.name: deepcopy(getattr(self, item.name)) for item in fields(self)}
