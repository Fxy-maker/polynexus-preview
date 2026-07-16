"""Data bindings from graph objects to immutable worksheet revisions."""

from __future__ import annotations

from dataclasses import dataclass
from math import log10
from operator import eq, ge, gt, le, lt, ne
from typing import Any, Mapping

from .models import DataRevision


class BindingError(ValueError):
    """Base class for structured data-binding failures."""


class MissingColumnError(BindingError):
    pass


class UnitMismatchError(BindingError):
    pass


@dataclass(frozen=True)
class ColumnReference:
    role: str
    column_id: str
    expected_unit: str = ""

    def to_payload(self) -> dict[str, str]:
        return {
            "role": self.role,
            "column_id": self.column_id,
            "expected_unit": self.expected_unit,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ColumnReference":
        return cls(
            role=str(payload.get("role") or ""),
            column_id=str(payload.get("column_id") or ""),
            expected_unit=str(payload.get("expected_unit") or ""),
        )


@dataclass(frozen=True)
class RowFilter:
    column_id: str
    operator: str
    value: Any

    def to_payload(self) -> dict[str, Any]:
        return {
            "column_id": self.column_id,
            "operator": self.operator,
            "value": self.value,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RowFilter":
        return cls(
            column_id=str(payload.get("column_id") or ""),
            operator=str(payload.get("operator") or "=="),
            value=payload.get("value"),
        )


@dataclass(frozen=True)
class ColumnTransform:
    role: str
    operation: str
    operand: float = 0.0

    def to_payload(self) -> dict[str, Any]:
        return {"role": self.role, "operation": self.operation, "operand": self.operand}

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ColumnTransform":
        return cls(
            role=str(payload.get("role") or ""),
            operation=str(payload.get("operation") or "identity"),
            operand=float(payload.get("operand", 0.0) or 0.0),
        )


@dataclass(frozen=True)
class BindingDiagnostic:
    reason_code: str
    message: str
    error: Exception


@dataclass(frozen=True)
class BindingProvenance:
    source_dataset_id: str
    revision_id: str
    binding_id: str


@dataclass(frozen=True)
class BindingResolution:
    columns: dict[str, tuple[Any, ...]]
    provenance: BindingProvenance
    diagnostics: tuple[BindingDiagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True)
class DataBinding:
    binding_id: str
    object_id: str
    kind: str
    columns: tuple[ColumnReference, ...]
    filters: tuple[RowFilter, ...] = ()
    transforms: tuple[ColumnTransform, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "object_id": self.object_id,
            "kind": self.kind,
            "columns": [item.to_payload() for item in self.columns],
            "filters": [item.to_payload() for item in self.filters],
            "transforms": [item.to_payload() for item in self.transforms],
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DataBinding":
        return cls(
            binding_id=str(payload.get("binding_id") or ""),
            object_id=str(payload.get("object_id") or ""),
            kind=str(payload.get("kind") or "line"),
            columns=tuple(ColumnReference.from_payload(item) for item in payload.get("columns", ())),
            filters=tuple(RowFilter.from_payload(item) for item in payload.get("filters", ())),
            transforms=tuple(ColumnTransform.from_payload(item) for item in payload.get("transforms", ())),
        )

    def resolve(self, revision: DataRevision) -> BindingResolution:
        provenance = BindingProvenance(
            source_dataset_id=revision.source_dataset_id,
            revision_id=revision.revision_id,
            binding_id=self.binding_id,
        )
        try:
            row_indices = self._matching_rows(revision)
            result: dict[str, tuple[Any, ...]] = {}
            for reference in self.columns:
                spec = revision.column_by_id(reference.column_id)
                if reference.expected_unit and spec.unit != reference.expected_unit:
                    raise UnitMismatchError(
                        f"{reference.column_id}: expected {reference.expected_unit}, got {spec.unit}"
                    )
                values = tuple(revision.values_for(reference.column_id)[index] for index in row_indices)
                transform = next(
                    (item for item in self.transforms if item.role == reference.role),
                    None,
                )
                if transform is not None:
                    values = tuple(self._transform(value, transform) for value in values)
                result[reference.role] = values
            return BindingResolution(result, provenance)
        except MissingColumnError as exc:
            return BindingResolution(
                {}, provenance, (BindingDiagnostic("missing_column", str(exc), exc),)
            )
        except UnitMismatchError as exc:
            return BindingResolution(
                {}, provenance, (BindingDiagnostic("unit_mismatch", str(exc), exc),)
            )
        except BindingError as exc:
            return BindingResolution(
                {}, provenance, (BindingDiagnostic("binding_error", str(exc), exc),)
            )

    def _matching_rows(self, revision: DataRevision) -> tuple[int, ...]:
        if not revision.columns:
            return ()
        row_count = len(revision.values_for(revision.columns[0].column_id))
        indices = list(range(row_count))
        operators = {"==": eq, "!=": ne, ">": gt, ">=": ge, "<": lt, "<=": le}
        for item in self.filters:
            try:
                values = revision.values_for(item.column_id)
            except KeyError as exc:
                raise MissingColumnError(item.column_id) from exc
            comparator = operators.get(item.operator)
            if comparator is None:
                raise BindingError(f"unsupported row filter operator: {item.operator}")
            indices = [index for index in indices if comparator(values[index], item.value)]
        return tuple(indices)

    @staticmethod
    def _transform(value: Any, transform: ColumnTransform) -> Any:
        try:
            if transform.operation == "identity":
                return value
            if transform.operation == "scale":
                return float(value) * transform.operand
            if transform.operation == "offset":
                return float(value) + transform.operand
            if transform.operation == "log10":
                return log10(float(value))
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            raise BindingError(
                f"transform {transform.operation} failed for value {value!r}"
            ) from exc
        raise BindingError(f"unsupported column transform: {transform.operation}")
