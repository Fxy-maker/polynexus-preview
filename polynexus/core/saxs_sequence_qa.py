"""Auditable QA summaries for SAXS sequence loading."""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

import numpy as np


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _safe_float_array(values: Sequence[Any]) -> np.ndarray:
    items = list(values)
    result = np.full(len(items), np.nan, dtype=float)
    for index, value in enumerate(items):
        try:
            result[index] = float(value)
        except (TypeError, ValueError, OverflowError):
            pass
    return result


def _safe_float_or_none(value: Any) -> float | None:
    try:
        number = float(value) if value is not None else np.nan
    except (TypeError, ValueError, OverflowError):
        number = np.nan
    return number if np.isfinite(number) else None


def _condition_axis_summary(
    conditions: Sequence[Any],
    condition_keys: Sequence[Any],
    sources: Sequence[Any],
    source_keys: Sequence[Any],
    source_texts: Sequence[Any],
    confidences: Sequence[Any],
) -> dict[str, Any]:
    condition_items = list(conditions)
    key_items = list(condition_keys)
    source_items = list(sources)
    source_key_items = list(source_keys)
    source_text_items = list(source_texts)
    confidence_items = list(confidences)
    values = _safe_float_array(condition_items)
    keys = [_text(value) for value in key_items]
    source_values = [_text(value) for value in source_items]
    entry_count = max(len(condition_items), len(key_items), len(source_items))
    unresolved: list[int] = []
    missing_count = 0
    for index in range(entry_count):
        value = values[index] if index < len(values) else np.nan
        key = keys[index] if index < len(keys) else ""
        source = source_values[index] if index < len(source_values) else ""
        if (
            not np.isfinite(value)
            or key.strip().startswith("unresolved::")
            or source.strip().lower() == "unresolved"
        ):
            unresolved.append(index)
        if (
            index >= len(condition_items)
            or index >= len(key_items)
            or index >= len(source_items)
            or not key.strip()
            or not source.strip()
        ):
            missing_count += 1
    nonempty_keys = [key for key in keys if key.strip()]
    duplicate_count = len(nonempty_keys) - len(set(nonempty_keys))
    finite = values[np.isfinite(values)]
    if unresolved:
        monotonicity = "unresolved"
    elif len(finite) < 2:
        monotonicity = "unknown"
    else:
        differences = np.diff(finite)
        if np.allclose(differences, 0.0):
            monotonicity = "constant"
        elif np.all(differences > 0):
            monotonicity = "strictly_increasing"
        elif np.all(differences < 0):
            monotonicity = "strictly_decreasing"
        elif np.all(differences >= 0):
            monotonicity = "non_decreasing"
        elif np.all(differences <= 0):
            monotonicity = "non_increasing"
        else:
            monotonicity = "non_monotonic"
    entries = []
    for index in range(entry_count):
        value = values[index] if index < len(values) else np.nan
        entries.append(
            {
                "index": index,
                "value": float(value) if np.isfinite(value) else None,
                "key": keys[index] if index < len(keys) else "",
                "source": source_values[index] if index < len(source_values) else "",
                "source_key": _text(source_key_items[index]) if index < len(source_key_items) else "",
                "source_text": _text(source_text_items[index]) if index < len(source_text_items) else "",
                "confidence": _safe_float_or_none(
                    confidence_items[index] if index < len(confidence_items) else None
                ),
            }
        )
    nonempty_sources = {entry["source"] for entry in entries if entry["source"]}
    return {
        "entries": entries,
        "source_count": len(nonempty_sources),
        "mixed_source": len(nonempty_sources) > 1,
        "unresolved_count": len(unresolved),
        "duplicate_count": max(0, duplicate_count),
        "missing_count": missing_count,
        "monotonicity": monotonicity,
    }


def build_sequence_qa_summary(
    *,
    discovered_files: Sequence[Any],
    loaded_files: Sequence[Any],
    skipped_files: Sequence[dict[str, Any]],
    conditions: Sequence[Any],
    condition_keys: Sequence[Any],
    condition_sources: Sequence[Any],
    condition_source_keys: Sequence[Any],
    condition_source_texts: Sequence[Any],
    condition_confidences: Sequence[Any],
    geometry_sources: Sequence[Any],
    geometry_confidences: Sequence[Any],
) -> dict[str, Any]:
    skipped_by_reason = Counter(
        _text(item.get("reason", "unknown") or "unknown") for item in skipped_files
    )
    geometry_values = [_text(value) for value in geometry_sources]
    defaulted = sum(value in {"config_default", "defaulted", "unknown"} for value in geometry_values)
    header = sum(value == "header" for value in geometry_values)
    unrecognized = sum(
        value not in {"config_default", "defaulted", "unknown", "header"}
        for value in geometry_values
    )
    if (defaulted and header) or (unrecognized and (defaulted or header)):
        geometry_status = "mixed"
    elif defaulted:
        geometry_status = "defaulted"
    elif header:
        geometry_status = "header"
    else:
        geometry_status = "unknown"
    return {
        "discovered_frame_count": len(discovered_files),
        "loaded_frame_count": len(loaded_files),
        "skipped_frame_count": len(skipped_files),
        "skipped_by_reason": dict(sorted(skipped_by_reason.items())),
        "condition_axis": _condition_axis_summary(
            conditions,
            condition_keys,
            condition_sources,
            condition_source_keys,
            condition_source_texts,
            condition_confidences,
        ),
        "geometry": {
            "status": geometry_status,
            "header_frame_count": header,
            "defaulted_frame_count": defaulted,
            "unrecognized_frame_count": unrecognized,
            "confidence": [_safe_float_or_none(value) for value in geometry_confidences],
        },
    }


__all__ = ["build_sequence_qa_summary"]
