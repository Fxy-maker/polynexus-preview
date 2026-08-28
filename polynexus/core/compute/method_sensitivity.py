"""Technique-neutral method sensitivity result contract."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from numbers import Real
from typing import Any, Mapping


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


@dataclass(frozen=True)
class MethodSensitivity:
    """Primary method plus explicitly computed alternatives for one metric."""

    metric_path: str
    primary_method: str
    primary_value: float | None
    candidates: Mapping[str, float | None] = field(default_factory=dict)
    parameters: Mapping[str, Any] = field(default_factory=dict)
    source: str | None = None
    warnings: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        metric_path: str,
        primary_method: str,
        primary_value: Any,
        candidates: Mapping[str, Any] | None = None,
        parameters: Mapping[str, Any] | None = None,
        source: str | None = None,
        warnings: tuple[str, ...] = (),
    ) -> "MethodSensitivity":
        if not str(metric_path).strip() or not str(primary_method).strip():
            raise ValueError("method sensitivity metric and primary method are required")
        if candidates is None:
            candidates = {}
        if not isinstance(candidates, Mapping):
            raise TypeError("method sensitivity candidates must be a mapping")
        normalized = {str(name): _finite(value) for name, value in candidates.items()}
        return cls(
            metric_path=str(metric_path),
            primary_method=str(primary_method),
            primary_value=_finite(primary_value),
            candidates=normalized,
            parameters=dict(parameters or {}),
            source=str(source) if source else None,
            warnings=tuple(str(item) for item in warnings),
        )

    @property
    def difference_range(self) -> float | None:
        values = [value for value in (self.primary_value, *self.candidates.values()) if value is not None]
        return max(values) - min(values) if len(values) >= 2 else None

    @property
    def status(self) -> str:
        return "computed" if self.primary_value is not None else "unavailable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_path": self.metric_path,
            "primary": {"method": self.primary_method, "value": self.primary_value},
            "candidates": [
                {"method": method, "value": self.candidates[method]}
                for method in sorted(self.candidates)
            ],
            "difference_range": self.difference_range,
            "parameters": dict(self.parameters),
            "source": self.source,
            "warnings": list(self.warnings),
            "status": self.status,
        }


__all__ = ["MethodSensitivity"]
