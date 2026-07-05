"""Multi-technique timeline alignment for Phase C."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

import pandas as pd


@dataclass
class TimelinePoint:
    condition_value: Any
    value: Any
    batch_id: str = ""
    batch_label: str = ""
    sample_id: str = ""
    sample_name: str = ""
    technique: str = ""


@dataclass
class TimelineSeries:
    """One aligned measurement series on the shared condition axis."""

    batch_id: str
    technique: str
    param_key: str
    series_key: str = ""
    batch_label: str = ""
    sample_id: str = ""
    sample_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    points: list[TimelinePoint] = field(default_factory=list)


class MultiTechniqueTimeline:
    """Shared condition-axis view across techniques."""

    def __init__(self, condition_key: str):
        self.key = condition_key
        self._series: dict[str, TimelineSeries] = {}

    @staticmethod
    def _ensure_list(values: Any) -> list[Any]:
        if values is None:
            return []
        if isinstance(values, list):
            return values
        if isinstance(values, tuple):
            return list(values)
        if isinstance(values, (str, bytes)):
            return [values]
        try:
            return list(values)
        except TypeError:
            return [values]

    def add_series(self, batch, param_key, condition_values, param_values):
        """Add a data series from a batch analysis."""
        batch_id = ""
        batch_label = ""
        sample_id = ""
        sample_name = ""
        technique = ""
        metadata = {}

        if isinstance(batch, dict):
            batch_id = str(batch.get("batch_id") or batch.get("id") or "").strip()
            batch_label = str(batch.get("batch_label") or batch.get("label") or "").strip()
            sample_id = str(batch.get("sample_id") or "").strip()
            sample_name = str(batch.get("sample_name") or "").strip()
            technique = str(batch.get("technique") or "").strip().lower()
            metadata = dict(batch)
        else:
            batch_id = str(batch or "").strip()

        key = str(param_key)
        series_key = f"{technique}:{key}" if technique else key
        series = self._series.get(series_key)
        if series is None:
            series = TimelineSeries(
                batch_id=batch_id,
                technique=technique,
                param_key=key,
                series_key=series_key,
                batch_label=batch_label,
                sample_id=sample_id,
                sample_name=sample_name,
                metadata=metadata,
            )
            self._series[series_key] = series

        condition_list = self._ensure_list(condition_values)
        value_list = self._ensure_list(param_values)
        for cond, val in zip(condition_list, value_list):
            series.points.append(
                TimelinePoint(
                    cond,
                    val,
                    batch_id=batch_id,
                    batch_label=batch_label,
                    sample_id=sample_id,
                    sample_name=sample_name,
                    technique=technique,
                )
            )

        if batch_id and not series.batch_id:
            series.batch_id = batch_id
        if batch_label and not series.batch_label:
            series.batch_label = batch_label
        if sample_id and not series.sample_id:
            series.sample_id = sample_id
        if sample_name and not series.sample_name:
            series.sample_name = sample_name
        if technique and not series.technique:
            series.technique = technique
        if metadata:
            series.metadata.update(metadata)

    def get_shared_axis(self, mode="auto"):
        """Compute the shared condition axis."""
        all_conditions: list[float] = []
        for series in self._series.values():
            for point in series.points:
                try:
                    numeric = float(point.condition_value)
                except Exception:
                    continue
                if math.isfinite(numeric):
                    all_conditions.append(numeric)

        if not all_conditions:
            return []

        unique = sorted(set(all_conditions))
        if mode == "dense" and len(unique) > 1:
            diffs = [b - a for a, b in zip(unique, unique[1:]) if (b - a) > 0]
            if not diffs:
                return unique
            step = min(diffs)
            if step > 0:
                start = unique[0]
                stop = unique[-1]
                count = int(round((stop - start) / step)) + 1
                return [start + i * step for i in range(count)]

        return unique

    def to_dataframe(self):
        """Export aligned data."""
        shared_axis = self.get_shared_axis()
        axis_index = {
            round(float(value), 12): idx
            for idx, value in enumerate(shared_axis)
            if isinstance(value, (int, float)) and math.isfinite(float(value))
        }

        rows = []
        for series in self._series.values():
            for point in series.points:
                shared_condition_value = None
                shared_condition_index = None
                try:
                    numeric_condition = float(point.condition_value)
                    if math.isfinite(numeric_condition):
                        key = round(numeric_condition, 12)
                        shared_condition_index = axis_index.get(key)
                        if shared_condition_index is not None:
                            shared_condition_value = shared_axis[shared_condition_index]
                except Exception:
                    pass
                rows.append(
                    {
                        "condition_key": self.key,
                        "condition_value": point.condition_value,
                        "shared_condition_value": shared_condition_value,
                        "shared_condition_index": shared_condition_index,
                        "series_key": series.series_key,
                        "param_key": series.param_key,
                        "value": point.value,
                        "batch_id": point.batch_id or series.batch_id,
                        "batch_label": point.batch_label or series.batch_label,
                        "sample_id": point.sample_id or series.sample_id,
                        "sample_name": point.sample_name or series.sample_name,
                        "technique": point.technique or series.technique,
                    }
                )
        return pd.DataFrame(rows)
