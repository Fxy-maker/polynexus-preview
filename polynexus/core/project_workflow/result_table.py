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
    minimum: float | None
    maximum: float | None
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
            "minimum": self.minimum,
            "maximum": self.maximum,
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

    def condition_trend(self, metric_key: str) -> tuple[dict[str, Any], ...]:
        """Return deterministic condition-ordered values for one metric."""
        records = [item for item in self.statistics(metric_key) if item.count > 0]
        records.sort(key=lambda item: _condition_sort_key(item.condition_value))
        return tuple({
            "condition_key": item.condition_key,
            "condition_value": item.condition_value,
            "metric_key": item.metric_key,
            "count": item.count,
            "mean": item.mean,
            "minimum": item.minimum,
            "maximum": item.maximum,
            "std": item.std,
            "cv": item.cv,
            "source_row_ids": list(item.source_row_ids),
        } for item in records)

    def repeatability(self, metric_key: str) -> dict[str, Any]:
        """Summarize replicate availability without imposing a quality cutoff."""
        conditions = []
        records = sorted(self.statistics(metric_key), key=lambda item: _condition_sort_key(item.condition_value))
        for item in records:
            conditions.append({
                "condition_value": item.condition_value,
                "count": item.count,
                "cv": item.cv,
                "status": "available" if item.count >= 2 else "insufficient_replicates",
                "source_row_ids": list(item.source_row_ids),
            })
        return {
            "condition_key": self.rows[0].condition_key,
            "metric_key": metric_key,
            "conditions": conditions,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "technique": self.technique,
            "rows": [row.to_dict() for row in self.rows],
            "statistics": [item.to_dict() for item in self.statistics()],
            "trends": {
                metric_key: list(self.condition_trend(metric_key))
                for metric_key in sorted({key for row in self.rows for key in row.metrics})
            },
            "repeatability": {
                metric_key: self.repeatability(metric_key)
                for metric_key in sorted({key for row in self.rows for key in row.metrics})
            },
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
                minimum=float(item["minimum"]) if item.get("minimum") is not None else None,
                maximum=float(item["maximum"]) if item.get("maximum") is not None else None,
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

    def statistics_csv_rows(self) -> tuple[dict[str, Any], ...]:
        """Return condition-level statistics as flat export rows."""
        return tuple({
            "group_id": self.group_id,
            "technique": self.technique,
            "row_type": "statistic",
            "condition_key": item.condition_key,
            "condition_value": item.condition_value,
            "metric_key": item.metric_key,
            "count": item.count,
            "mean": item.mean,
            "std": item.std,
            "cv": item.cv,
            "minimum": item.minimum,
            "maximum": item.maximum,
            "source_row_ids": ";".join(item.source_row_ids),
        } for item in self.statistics())


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
                minimum=min(values),
                maximum=max(values),
                source_row_ids=tuple(row_id for row_id, _ in numeric),
            ))
    return tuple(records)


def _condition_sort_key(value: Any) -> tuple[int, Any]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, float(value))
    return (1, str(value))


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


def build_result_tables_from_runs(runs: Iterable[Any]) -> tuple[dict[str, Any], ...]:
    """Project scalar ComputeRun manifest leaves into persisted group tables.

    ``runs`` is intentionally duck-typed to avoid coupling this DTO module to
    the project-workflow envelope classes. The caller supplies the workflow
    step as the only condition key; scientific axes must be selected upstream.
    """
    tables: list[dict[str, Any]] = []
    for run in runs:
        analysis_run = getattr(run, "analysis_run", None)
        if analysis_run is None:
            continue
        for step in getattr(analysis_run, "steps", ()):
            compute_run = getattr(step, "compute_run", None)
            if not isinstance(compute_run, Mapping):
                continue
            result = compute_run.get("result")
            if not isinstance(result, Mapping):
                continue
            if not _projection_is_computed(compute_run, expected_status="completed"):
                continue
            manifest = result.get("metric_manifest")
            if not isinstance(manifest, (list, tuple)):
                continue
            metrics: dict[str, Any] = {}
            warnings = [str(value) for value in getattr(step, "reason_codes", ()) if value]
            warnings.extend(str(value) for value in result.get("warnings", ()) if value)
            for item in manifest:
                if not isinstance(item, Mapping) or item.get("status") != "computed":
                    continue
                if not _projection_is_computed(item, expected_status="computed"):
                    continue
                if item.get("kind") != "scalar" or "value" not in item:
                    continue
                metrics[str(item.get("path", "metric"))] = item.get("value")
                warnings.extend(str(value) for value in item.get("warnings", ()) if value)
            if not metrics:
                continue
            artifact = compute_run.get("artifact")
            source = artifact.get("path") if isinstance(artifact, Mapping) else None
            source = str(source or getattr(run, "run_id", "unknown"))
            step_id = str(getattr(step, "step_id", "step"))
            technique = str(getattr(step, "technique", "unknown"))
            row = ResultTableRow(
                row_id=str(getattr(run, "run_id", "run")),
                technique=technique,
                source=source,
                condition_key="step_id",
                condition_value=step_id,
                metrics=metrics,
                warnings=tuple(dict.fromkeys(warnings)),
            )
            tables.append(build_group_result_table(f"{technique}:{step_id}", (row,)).to_dict())
    return tuple(tables)


def _projection_is_computed(
    value: Mapping[str, Any],
    *,
    expected_status: str,
) -> bool:
    """Return whether one shared projection is eligible for table values.

    A run envelope and a manifest row have different lifecycle vocabularies,
    so both are checked explicitly.  State is optional only for the smallest
    historical projections; whenever it is present it must be a complete,
    canonical four-axis state and its aliases must agree.
    """

    if not isinstance(value, Mapping):
        return False
    status = value.get("status")
    if not isinstance(status, str) or status.strip().casefold() != expected_status:
        return False

    state_values = [value[key] for key in ("computation_state", "state") if key in value]
    if not state_values:
        return True

    from ..ai_platform.contracts import ComputationState

    normalized = []
    for candidate in state_values:
        if isinstance(candidate, ComputationState):
            state = candidate
        elif isinstance(candidate, Mapping):
            try:
                state = ComputationState.from_dict(candidate)
            except (KeyError, TypeError, ValueError):
                return False
        else:
            return False
        if state.computability != "computed":
            return False
        normalized.append(state)
    first = normalized[0]
    return all(state.to_dict() == first.to_dict() for state in normalized[1:])


__all__ = [
    "GroupResultTable",
    "ResultStatistic",
    "ResultTableRow",
    "build_group_result_table",
    "build_result_tables_from_runs",
]
