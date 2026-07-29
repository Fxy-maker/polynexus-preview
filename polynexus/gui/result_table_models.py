"""Immutable presentation contracts for structured GUI result tables."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, TypeAlias

import numpy as np

from .scientific_review_presentation import ScientificReviewDisplay


TableScalar: TypeAlias = str | bytes | bool | int | float | complex | None
_TABLE_SCALAR_TYPES = (str, bytes, bool, int, float, complex)


def normalize_table_scalar(value: Any) -> TableScalar:
    """Return an immutable built-in scalar suitable for a table cell."""
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or isinstance(value, _TABLE_SCALAR_TYPES):
        return value
    raise TypeError("table raw values must be immutable Python scalars")


@dataclass(frozen=True)
class TableColumn:
    key: str
    label: str
    unit: str = ""
    digits: int | None = None
    alignment: str = "left"

    @property
    def header(self) -> str:
        return f"{self.label} / {self.unit}" if self.unit else self.label


@dataclass(frozen=True)
class TableCell:
    raw: TableScalar = None
    display: str = "—"
    status: str = "neutral"
    tooltip: str = ""
    provenance: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", normalize_table_scalar(self.raw))


@dataclass(frozen=True)
class ResultTableSection:
    columns: tuple[TableColumn, ...] = ()
    rows: tuple[tuple[TableCell, ...], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "columns", tuple(self.columns))
        object.__setattr__(self, "rows", tuple(tuple(row) for row in self.rows))

    @classmethod
    def empty(cls) -> "ResultTableSection":
        return cls()


@dataclass(frozen=True)
class HeroMetric:
    key: str
    label: str
    raw: TableScalar
    display: str
    unit: str = ""
    status: str = "neutral"
    provenance: str = ""
    tooltip: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", normalize_table_scalar(self.raw))


@dataclass(frozen=True)
class ResultsTablePresentation:
    kind: str
    primary: ResultTableSection
    detail: ResultTableSection
    diagnostics: ResultTableSection
    hero_metrics: tuple[HeroMetric, ...] = ()
    risk_text: str = ""
    next_text: str = ""
    summary_count: int = 0
    sortable: bool = False
    copy_enabled: bool = False
    export_enabled: bool = False
    scientific_review: ScientificReviewDisplay = field(default_factory=ScientificReviewDisplay)

    def __post_init__(self) -> None:
        object.__setattr__(self, "hero_metrics", tuple(self.hero_metrics))


def format_table_value(
    value: Any,
    *,
    digits: int | None = None,
    missing_text: str = "—",
    unavailable_text: str = "不可用",
    true_text: str = "是",
    false_text: str = "否",
) -> str:
    """Format a raw table value without discarding the raw value itself."""
    if isinstance(value, np.generic):
        value = normalize_table_scalar(value)
    if value is None or (isinstance(value, str) and value == ""):
        return missing_text
    if isinstance(value, bool):
        return true_text if value else false_text
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return unavailable_text
        if digits is not None:
            if isinstance(digits, bool) or not isinstance(digits, int):
                raise TypeError("digits must be a non-boolean integer or None")
            if digits < 0:
                raise ValueError("digits must be non-negative")
            return f"{value:.{digits}f}"
    return str(value)
