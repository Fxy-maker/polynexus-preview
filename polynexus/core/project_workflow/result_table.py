"""Technique-neutral per-file and condition-scoped result tables."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import math
from numbers import Real
from typing import Any


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


@dataclass(frozen=True)
class ResultTableRow:
    """One source-file result row selected by the caller."""

    row_id: str
    technique: str
    source: str
    condition_key: str
    condition_value: Any
    metrics: Mapping[str, Any]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("row_id", "technique", "source", "condition_key"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"result table {name} must not be empty")
        if not isinstance(self.metrics, Mapping):
            raise TypeError("result table metrics must be a mapping")
        object.__setattr__(self, "metrics", dict(self.metrics))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "technique": self.technique,
            "source": self.source,
            "condition_key": self.condition_key,
            "condition_value": self.condition_value,
            "metrics": dict(self.metrics),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ResultStatistic:
    condition_key: str
    condition_value: Any
    metric_key: str
    count: int
    mean: float
    std: float
    cv: float | None
    source_row_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_key": self.condition_key,
            "condition_value": self.condition_value,
            "metric_key": self.metric_key,
            "count": self.count,
            "mean": self.mean,
            "std": self.std,
            "cv": self.cv,
            "source_row_ids": list(self.source_row_ids),
        }


@dataclass(frozen=True)
class GroupResultTable:
    group_id: str
    technique: str
    rows: tuple[ResultTableRow, ...]
    statistics_records: tuple[ResultStatistic, ...] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))
        if self.statistics_records is None:
            object.__setattr__(self, "statistics_records", _compute_statistics(self.rows))
        else:
            object.__setattr__(self, "statistics_records", tuple(self.statistics_records))

    def statistics(self, metric_key: str | None = None) -> tuple[ResultStatistic, ...]:
        records = tuple(self.statistics_records or ())
        if metric_key is None:
            return records
        return tuple(item for item in records if item.metric_key == metric_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "technique": self.technique,
            "rows": [row.to_dict() for row in self.rows],
            "statistics": [item.to_dict() for item in self.statistics()],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GroupResultTable":
        """Restore a persisted table without recomputing provider values."""
        if not isinstance(payload, Mapping):
            raise TypeError("result table payload must be a mapping")
        raw_rows = payload.get("rows")
        if not isinstance(raw_rows, (list, tuple)):
            raise ValueError("result table rows must be a sequence")
        rows: list[ResultTableRow] = []
        for item in raw_rows:
            if not isinstance(item, Mapping):
                raise TypeError("result table rows must be mappings")
            rows.append(ResultTableRow(
                row_id=str(item["row_id"]),
                technique=str(item["technique"]),
                source=str(item["source"]),
                condition_key=str(item["condition_key"]),
                condition_value=item.get("condition_value"),
                metrics=item.get("metrics", {}),
                warnings=tuple(item.get("warnings", ())),
            ))
        has_statistics = "statistics" in payload
        raw_statistics = payload.get("statistics", ())
        if not isinstance(raw_statistics, (list, tuple)):
            raise TypeError("result table statistics must be a sequence")
        statistics = tuple(
            ResultStatistic(
                condition_key=str(item["condition_key"]),
                condition_value=item.get("condition_value"),
                metric_key=str(item["metric_key"]),
                count=int(item["count"]),
                mean=float(item["mean"]),
                std=float(item["std"]),
                cv=float(item["cv"]) if item.get("cv") is not None else None,
                source_row_ids=tuple(str(value) for value in item.get("source_row_ids", ())),
            )
            for item in raw_statistics
            if isinstance(item, Mapping)
        )
        if len(statistics) != len(raw_statistics):
            raise TypeError("result table statistics must be mappings")
        return build_group_result_table(
            str(payload.get("group_id", "")),
            rows,
            statistics_records=statistics if has_statistics else None,
        )

    def csv_rows(self) -> tuple[dict[str, Any], ...]:
        """Return flat, deterministic rows suitable for CSV export."""
        rows: list[dict[str, Any]] = []
        for row in self.rows:
            base = {
                "group_id": self.group_id,
                "technique": self.technique,
                "row_id": row.row_id,
                "source": row.source,
                "condition_key": row.condition_key,
                "condition_value": row.condition_value,
                "warnings": ";".join(row.warnings),
            }
            for key, value in sorted(row.metrics.items(), key=lambda item: str(item[0])):
                rows.append({**base, "metric_key": str(key), "value": value})
        return tuple(rows)


def _condition_values(rows: tuple[ResultTableRow, ...]) -> tuple[Any, ...]:
    values: list[Any] = []
    for row in rows:
        if row.condition_value not in values:
            values.append(row.condition_value)
    return tuple(values)


def _compute_statistics(rows: tuple[ResultTableRow, ...]) -> tuple[ResultStatistic, ...]:
    records: list[ResultStatistic] = []
    for condition_value in _condition_values(rows):
        selected = [row for row in rows if row.condition_value == condition_value]
        keys = {key for row in selected for key in row.metrics}
        for key in sorted(str(item) for item in keys):
            numeric = [(row.row_id, _number(row.metrics.get(key))) for row in selected]
            numeric = [(row_id, value) for row_id, value in numeric if value is not None]
            if not numeric:
                continue
            values = [value for _, value in numeric]
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            std = math.sqrt(variance)
            records.append(ResultStatistic(
                condition_key=rows[0].condition_key,
                condition_value=condition_value,
                metric_key=key,
                count=len(values),
                mean=mean,
                std=std,
                cv=(std / abs(mean)) if mean else None,
                source_row_ids=tuple(row_id for row_id, _ in numeric),
            ))
    return tuple(records)


def build_group_result_table(
    group_id: str,
    rows: Iterable[ResultTableRow],
    *,
    statistics_records: Iterable[ResultStatistic] | None = None,
) -> GroupResultTable:
    """Build a table while refusing mixed techniques or missing condition axes."""

    group = str(group_id).strip()
    if not group:
        raise ValueError("group_id must not be empty")
    selected = tuple(rows)
    if not selected:
        raise ValueError("result table requires at least one row")
    if not all(isinstance(row, ResultTableRow) for row in selected):
        raise TypeError("result table rows must be ResultTableRow values")
    if len({row.row_id for row in selected}) != len(selected):
        raise ValueError("result table row_id values must be unique")
    techniques = {row.technique.casefold() for row in selected}
    if len(techniques) != 1:
        raise ValueError("result table rows must use one technique")
    condition_keys = {row.condition_key for row in selected}
    if len(condition_keys) != 1:
        raise ValueError("result table rows must use one condition key")
    if statistics_records is not None:
        statistics = tuple(statistics_records)
        if any(not isinstance(item, ResultStatistic) for item in statistics):
            raise TypeError("result table statistics must be ResultStatistic values")
    else:
        statistics = None
    return GroupResultTable(group, selected[0].technique, selected, statistics)


__all__ = ["GroupResultTable", "ResultStatistic", "ResultTableRow", "build_group_result_table"]
