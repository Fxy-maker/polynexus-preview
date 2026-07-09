from __future__ import annotations

from typing import Any


def _clean_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _clamp_unit(value: float | None, default: float = 0.0) -> float:
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def _mean_finite(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None]
    if not finite:
        return None
    return sum(finite) / len(finite)


def _relative_spread(values: list[Any]) -> float | None:
    finite = [float(value) for value in values if _clean_float(value) is not None]
    if len(finite) < 2:
        return None
    scale = max(max(abs(value) for value in finite), 1e-9)
    return (max(finite) - min(finite)) / scale


def _inverse_ratio_score(value: float | None, limit: float) -> float | None:
    if value is None or limit <= 0:
        return None
    return _clamp_unit(1.0 - abs(float(value)) / float(limit), default=0.0)


def _match_constraint_value(output: dict[str, Any], field: str | None) -> Any:
    if not field:
        return None
    current: Any = output
    for part in field.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _non_empty_mapping(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if value in (None, "", [], {}):
            continue
        out[key] = value
    return out


def _extract_nested_mapping(value: Any, *keys: str) -> dict[str, Any]:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _shape_tuple(value: Any) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    out: list[int] = []
    for item in value:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            return ()
    return tuple(out)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
