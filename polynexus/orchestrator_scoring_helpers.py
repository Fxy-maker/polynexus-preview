from __future__ import annotations

import math
from typing import Any


def _first_text(
    self: Any,
    primary: dict[str, Any],
    fallback: dict[str, Any],
    keys: tuple[str, ...],
) -> str:
    for key in keys:
        value = primary.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        value = fallback.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _mean_or_none(self: Any, values: Any) -> float | None:
    items = []
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            items.append(number)
    if not items:
        return None
    return sum(items) / len(items)
