"""Technique-neutral method sensitivity result contract."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from numbers import Real
from collections.abc import Callable, Mapping
from typing import Any


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


def evaluate_method_sensitivity(
    *,
    metric_path: str,
    primary_method: str,
    methods: Mapping[str, Callable[[], Any]],
    parameters: Mapping[str, Any] | None = None,
    source: str | None = None,
    warnings: tuple[str, ...] = (),
) -> MethodSensitivity:
    """Evaluate an explicitly declared method set without selecting for the caller.

    The primary method is evaluated first. Candidate methods are evaluated in
    lexical order so the resulting JSON is stable. A failed candidate remains
    present as ``None`` and receives an explicit warning rather than being
    silently dropped.
    """
    if not isinstance(methods, Mapping) or not methods:
        raise ValueError("method sensitivity requires at least one method")
    normalized = {str(name).strip(): callback for name, callback in methods.items()}
    if not str(primary_method).strip() or primary_method not in normalized:
        raise ValueError("primary method must be one of the declared methods")
    local_warnings = list(warnings)

    def run(name: str) -> float | None:
        callback = normalized[name]
        if not callable(callback):
            local_warnings.append(f"method_not_callable:{name}")
            return None
        try:
            return _finite(callback())
        except Exception:
            local_warnings.append(f"method_failed:{name}")
            return None

    primary_value = run(primary_method)
    candidates = {name: run(name) for name in sorted(normalized) if name != primary_method}
    return MethodSensitivity.create(
        metric_path=metric_path,
        primary_method=primary_method,
        primary_value=primary_value,
        candidates=candidates,
        parameters=parameters,
        source=source,
        warnings=tuple(dict.fromkeys(local_warnings)),
    )


def sensitivities_from_metrics(
    metrics: Mapping[str, Any],
    *,
    technique: str = "",
    source: str | None = None,
) -> tuple[MethodSensitivity, ...]:
    """Restore only explicit provider-declared method alternatives.

    Providers may publish a ``method_variants`` mapping with the DTO shape
    accepted by :meth:`MethodSensitivity.create`. DSC's existing
    ``baseline_variants`` list is also adapted because it is already a
    deterministic, provenance-bearing result. No candidate is inferred from
    a scalar metric or from a material name.
    """
    if not isinstance(metrics, Mapping):
        return ()
    values: list[MethodSensitivity] = []
    explicit = metrics.get("method_variants", metrics.get("method_sensitivities"))
    if isinstance(explicit, Mapping):
        for metric_path in sorted(explicit, key=str):
            payload = explicit[metric_path]
            if not isinstance(payload, Mapping):
                continue
            values.append(MethodSensitivity.create(
                metric_path=str(metric_path),
                primary_method=payload.get("primary_method", "explicit"),
                primary_value=payload.get("primary", payload.get("primary_value")),
                candidates=payload.get("candidates", {}),
                parameters=payload.get("parameters", {}),
                source=payload.get("source", source),
                warnings=tuple(payload.get("warnings", ())),
            ))

    def collect_baseline_variants(container: Mapping[str, Any], prefix: str = "") -> None:
        variants = container.get("baseline_variants")
        if isinstance(variants, (list, tuple)):
            by_metric: dict[str, dict[str, float | None]] = {}
            methods: list[str] = []
            for variant in variants:
                if not isinstance(variant, Mapping):
                    continue
                method = str(variant.get("method", "")).strip()
                if not method:
                    continue
                methods.append(method)
                for key, value in variant.items():
                    if key == "method" or _finite(value) is None:
                        continue
                    by_metric.setdefault(str(key), {})[method] = _finite(value)
            primary_method = str(container.get("baseline_method", "")).strip()
            if primary_method and primary_method in methods:
                for metric_path in sorted(by_metric):
                    method_values = by_metric[metric_path]
                    primary_value = method_values.get(primary_method)
                    candidates = {name: value for name, value in method_values.items() if name != primary_method}
                    if candidates:
                        values.append(MethodSensitivity.create(
                            metric_path=f"{prefix}.{metric_path}" if prefix else metric_path,
                            primary_method=primary_method,
                            primary_value=primary_value,
                            candidates=candidates,
                            parameters={"technique": str(technique).lower(), "source": "baseline_variants"},
                            source=source,
                        ))
        for key, child in container.items():
            if isinstance(child, Mapping):
                collect_baseline_variants(child, f"{prefix}.{key}" if prefix else str(key))

    collect_baseline_variants(metrics)
    return tuple(values)


__all__ = ["MethodSensitivity", "evaluate_method_sensitivity", "sensitivities_from_metrics"]
