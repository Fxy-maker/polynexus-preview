"""Renderer-neutral data and graph document models for Reactive Figure V2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


class MutableValueError(TypeError):
    """Raised when a data column contains a nested mutable value."""


def normalize_scalar(value: Any) -> Any:
    """Return a JSON-safe scalar and reject nested arrays/containers."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (bytes, bytearray, memoryview, list, tuple, dict, set)):
        raise MutableValueError(
            f"data columns require scalar values, got {type(value).__name__}"
        )
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return normalize_scalar(item())
        except (TypeError, ValueError, AttributeError) as exc:
            raise MutableValueError(
                f"cannot normalize scalar value of type {type(value).__name__}"
            ) from exc
    raise MutableValueError(f"unsupported scalar value: {type(value).__name__}")


def freeze_json(value: Any) -> Any:
    """Freeze JSON-like style/metadata values while retaining JSON semantics."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return tuple(
            (str(key), freeze_json(item))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(freeze_json(item) for item in value)
    raise MutableValueError(f"unsupported nested value: {type(value).__name__}")


def thaw_json(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(isinstance(item, tuple) and len(item) == 2 for item in value):
            return {str(key): thaw_json(item) for key, item in value}
        return [thaw_json(item) for item in value]
    return value


def _pairs(value: Any) -> tuple[tuple[str, Any], ...]:
    frozen = freeze_json(value if value is not None else {})
    if not isinstance(frozen, tuple):
        raise MutableValueError("expected a JSON object")
    return tuple((str(key), item) for key, item in frozen)


def _stable_id(prefix: str, payload: Any) -> str:
    encoded = json.dumps(thaw_json(freeze_json(payload)), sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


@dataclass(frozen=True)
class ColumnSpec:
    column_id: str
    name: str
    unit: str = ""
    dtype: str = "float64"

    def to_payload(self) -> dict[str, str]:
        return {
            "column_id": self.column_id,
            "name": self.name,
            "unit": self.unit,
            "dtype": self.dtype,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ColumnSpec":
        return cls(
            column_id=str(payload.get("column_id") or ""),
            name=str(payload.get("name") or payload.get("column_id") or ""),
            unit=str(payload.get("unit") or ""),
            dtype=str(payload.get("dtype") or "float64"),
        )


@dataclass(frozen=True)
class Provenance:
    source_dataset_id: str
    source_revision_id: str
    operation: str
    parent_revision_id: str = ""
    metadata: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _pairs(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "source_dataset_id": self.source_dataset_id,
            "source_revision_id": self.source_revision_id,
            "operation": self.operation,
            "parent_revision_id": self.parent_revision_id,
            "metadata": thaw_json(self.metadata),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Provenance":
        return cls(
            source_dataset_id=str(payload.get("source_dataset_id") or ""),
            source_revision_id=str(payload.get("source_revision_id") or ""),
            operation=str(payload.get("operation") or ""),
            parent_revision_id=str(payload.get("parent_revision_id") or ""),
            metadata=tuple(dict(payload.get("metadata") or {}).items()),
        )


def _normalize_columns(
    columns: tuple[ColumnSpec, ...],
    values: Mapping[str, tuple[Any, ...]],
) -> tuple[tuple[ColumnSpec, ...], tuple[tuple[str, tuple[Any, ...]], ...]]:
    normalized_columns = tuple(columns)
    ids = [column.column_id for column in normalized_columns]
    if not ids or len(set(ids)) != len(ids) or any(not item for item in ids):
        raise ValueError("column IDs must be non-empty and unique")
    lengths = set()
    normalized_values: list[tuple[str, tuple[Any, ...]]] = []
    for column in normalized_columns:
        raw_values = values.get(column.column_id)
        if raw_values is None:
            raise ValueError(f"missing values for column: {column.column_id}")
        normalized = tuple(normalize_scalar(value) for value in raw_values)
        lengths.add(len(normalized))
        normalized_values.append((column.column_id, normalized))
    if len(lengths) > 1:
        raise ValueError("all worksheet columns must have equal length")
    return normalized_columns, tuple(normalized_values)


@dataclass(frozen=True)
class DataRevision:
    revision_id: str
    source_dataset_id: str
    parent_revision_id: str
    columns: tuple[ColumnSpec, ...]
    values: tuple[tuple[str, tuple[Any, ...]], ...]
    provenance: Provenance
    read_only: bool = False
    changed_columns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        value_map = dict(self.values)
        columns, normalized = _normalize_columns(tuple(self.columns), value_map)
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "values", normalized)
        object.__setattr__(
            self,
            "changed_columns",
            tuple(sorted(str(item) for item in self.changed_columns)),
        )

    def values_for(self, column_id: str) -> tuple[Any, ...]:
        try:
            return dict(self.values)[str(column_id)]
        except KeyError as exc:
            raise KeyError(f"unknown column: {column_id}") from exc

    def column_by_id(self, column_id: str) -> ColumnSpec:
        for column in self.columns:
            if column.column_id == str(column_id):
                return column
        raise KeyError(f"unknown column: {column_id}")

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "revision_id": self.revision_id,
            "source_dataset_id": self.source_dataset_id,
            "parent_revision_id": self.parent_revision_id,
            "columns": [column.to_payload() for column in self.columns],
            "values": {column_id: list(values) for column_id, values in self.values},
            "provenance": self.provenance.to_payload(),
            "read_only": self.read_only,
            "changed_columns": list(self.changed_columns),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DataRevision":
        columns = tuple(ColumnSpec.from_payload(item) for item in payload.get("columns", ()))
        return cls(
            revision_id=str(payload.get("revision_id") or ""),
            source_dataset_id=str(payload.get("source_dataset_id") or ""),
            parent_revision_id=str(payload.get("parent_revision_id") or ""),
            columns=columns,
            values=tuple(
                (str(key), tuple(value))
                for key, value in dict(payload.get("values") or {}).items()
            ),
            provenance=Provenance.from_payload(dict(payload.get("provenance") or {})),
            read_only=bool(payload.get("read_only", False)),
            changed_columns=tuple(str(item) for item in payload.get("changed_columns", ())),
        )


@dataclass(frozen=True)
class SourceDataset:
    dataset_id: str
    revision_id: str
    columns: tuple[ColumnSpec, ...]
    values: tuple[tuple[str, tuple[Any, ...]], ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        columns, normalized = _normalize_columns(tuple(self.columns), dict(self.values))
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "values", normalized)

    @classmethod
    def from_columns(
        cls,
        *,
        dataset_id: str,
        revision_id: str,
        columns: Mapping[str, Any],
        units: Mapping[str, str] | None = None,
        names: Mapping[str, str] | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> "SourceDataset":
        units = units or {}
        names = names or {}
        specs = tuple(
            ColumnSpec(
                column_id=str(column_id),
                name=str(names.get(column_id, column_id)),
                unit=str(units.get(column_id, "")),
            )
            for column_id in columns
        )
        prov = Provenance(
            source_dataset_id=dataset_id,
            source_revision_id=revision_id,
            operation="source_import",
            metadata=tuple((str(key), value) for key, value in (provenance or {}).items()),
        )
        _, normalized = _normalize_columns(specs, {str(key): tuple(value) for key, value in columns.items()})
        return cls(dataset_id, revision_id, specs, normalized, prov)

    def values_for(self, column_id: str) -> tuple[Any, ...]:
        return dict(self.values)[str(column_id)]

    def column_by_id(self, column_id: str) -> ColumnSpec:
        for column in self.columns:
            if column.column_id == str(column_id):
                return column
        raise KeyError(f"unknown column: {column_id}")

    def to_revision(self) -> DataRevision:
        return DataRevision(
            revision_id=self.revision_id,
            source_dataset_id=self.dataset_id,
            parent_revision_id="",
            columns=self.columns,
            values=self.values,
            provenance=self.provenance,
            read_only=True,
        )

    def to_payload(self) -> dict[str, Any]:
        payload = self.to_revision().to_payload()
        payload["dataset_id"] = self.dataset_id
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "SourceDataset":
        revision = DataRevision.from_payload(payload)
        return cls(
            dataset_id=str(payload.get("dataset_id") or revision.source_dataset_id),
            revision_id=revision.revision_id,
            columns=revision.columns,
            values=revision.values,
            provenance=revision.provenance,
        )


@dataclass(frozen=True)
class Worksheet:
    source: SourceDataset
    current: DataRevision

    @classmethod
    def from_source(cls, source: SourceDataset) -> "Worksheet":
        return cls(source=source, current=source.to_revision())

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "source": self.source.to_payload(),
            "current": self.current.to_payload(),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Worksheet":
        source = SourceDataset.from_payload(dict(payload.get("source") or {}))
        current = DataRevision.from_payload(dict(payload.get("current") or {}))
        return cls.from_source(source).checkout(current)

    def checkout(self, revision: DataRevision) -> "Worksheet":
        if revision.source_dataset_id != self.source.dataset_id:
            raise ValueError("revision belongs to a different source dataset")
        return Worksheet(source=self.source, current=revision)

    def edit_cells(self, changes: Mapping[str, Mapping[int, Any]]) -> DataRevision:
        if not changes:
            raise ValueError("at least one cell change is required")
        value_map = {column_id: list(values) for column_id, values in self.current.values}
        changed_columns: list[str] = []
        for column_id, cell_changes in changes.items():
            column_id = str(column_id)
            if column_id not in value_map:
                raise KeyError(f"unknown column: {column_id}")
            if not isinstance(cell_changes, Mapping) or not cell_changes:
                raise ValueError(f"cell changes for {column_id} must be non-empty")
            target = value_map[column_id]
            for row_index, value in cell_changes.items():
                row_index = int(row_index)
                if row_index < 0 or row_index >= len(target):
                    raise IndexError(f"row index out of range: {row_index}")
                target[row_index] = normalize_scalar(value)
            changed_columns.append(column_id)
        changed_columns = sorted(set(changed_columns))
        revision_id = _stable_id(
            "data",
            {
                "parent": self.current.revision_id,
                "changes": {
                    column_id: value_map[column_id] for column_id in changed_columns
                },
            },
        )
        provenance = Provenance(
            source_dataset_id=self.source.dataset_id,
            source_revision_id=self.source.revision_id,
            operation="edit_cells",
            parent_revision_id=self.current.revision_id,
            metadata=(
                ("changed_columns", tuple(changed_columns)),
            ),
        )
        return DataRevision(
            revision_id=revision_id,
            source_dataset_id=self.source.dataset_id,
            parent_revision_id=self.current.revision_id,
            columns=self.current.columns,
            values=tuple((column_id, tuple(values)) for column_id, values in value_map.items()),
            provenance=provenance,
            read_only=False,
            changed_columns=tuple(changed_columns),
        )


@dataclass(frozen=True)
class AxisModel:
    label: str
    unit: str = ""
    scale: str = "linear"
    reversed: bool = False
    minimum: float | None = None
    maximum: float | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "unit": self.unit,
            "scale": self.scale,
            "reversed": self.reversed,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AxisModel":
        return cls(
            label=str(payload.get("label") or ""),
            unit=str(payload.get("unit") or ""),
            scale=str(payload.get("scale") or "linear"),
            reversed=bool(payload.get("reversed", False)),
            minimum=(
                float(payload["minimum"])
                if payload.get("minimum") is not None
                else None
            ),
            maximum=(
                float(payload["maximum"])
                if payload.get("maximum") is not None
                else None
            ),
        )


@dataclass(frozen=True)
class PanelModel:
    panel_id: str
    row: int
    column: int
    x_axis: AxisModel
    y_axis: AxisModel
    title: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "grid_position": {"row": self.row, "column": self.column},
            "x_axis": self.x_axis.to_payload(),
            "y_axis": self.y_axis.to_payload(),
            "title": self.title,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "PanelModel":
        position = dict(payload.get("grid_position") or {})
        return cls(
            panel_id=str(payload.get("panel_id") or ""),
            row=int(position.get("row", 0) or 0),
            column=int(position.get("column", 0) or 0),
            x_axis=AxisModel.from_payload(dict(payload.get("x_axis") or {})),
            y_axis=AxisModel.from_payload(dict(payload.get("y_axis") or {})),
            title=str(payload.get("title") or ""),
        )


@dataclass(frozen=True)
class GraphObject:
    object_id: str
    object_type: str
    panel_id: str
    binding_id: str = ""
    style: Any = ()
    properties: Any = ()
    visible: bool = True
    z_index: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "style", _pairs(self.style))
        object.__setattr__(self, "properties", _pairs(self.properties))

    @property
    def style_map(self) -> dict[str, Any]:
        return thaw_json(self.style)

    @property
    def property_map(self) -> dict[str, Any]:
        return thaw_json(self.properties)

    def with_style(self, updates: Mapping[str, Any]) -> "GraphObject":
        next_style = self.style_map
        next_style.update(dict(updates))
        return GraphObject(
            object_id=self.object_id,
            object_type=self.object_type,
            panel_id=self.panel_id,
            binding_id=self.binding_id,
            style=next_style,
            properties=self.property_map,
            visible=self.visible,
            z_index=self.z_index,
        )

    def with_properties(self, updates: Mapping[str, Any]) -> "GraphObject":
        next_properties = self.property_map
        next_properties.update(dict(updates))
        return GraphObject(
            object_id=self.object_id,
            object_type=self.object_type,
            panel_id=self.panel_id,
            binding_id=self.binding_id,
            style=self.style_map,
            properties=next_properties,
            visible=self.visible,
            z_index=self.z_index,
        )

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "id": self.object_id,
            "type": self.object_type,
            "panel_id": self.panel_id,
            "binding_id": self.binding_id,
            "style": self.style_map,
            "properties": self.property_map,
            "visible": self.visible,
            "z_index": self.z_index,
        }
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "GraphObject":
        return cls(
            object_id=str(payload.get("id") or payload.get("object_id") or ""),
            object_type=str(payload.get("type") or payload.get("object_type") or ""),
            panel_id=str(payload.get("panel_id") or "main"),
            binding_id=str(payload.get("binding_id") or payload.get("data_ref") or ""),
            style=dict(payload.get("style") or {}),
            properties=dict(payload.get("properties") or {}),
            visible=bool(payload.get("visible", True)),
            z_index=int(payload.get("z_index", 0) or 0),
        )


@dataclass(frozen=True)
class GraphDocument:
    graph_id: str
    revision_id: str
    canvas_width_px: int
    canvas_height_px: int
    panels: tuple[PanelModel, ...]
    objects: tuple[GraphObject, ...]
    bindings: tuple[Any, ...] = ()
    metadata: Any = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        panels = tuple(self.panels)
        objects = tuple(self.objects)
        bindings = tuple(self.bindings)
        panel_ids = [panel.panel_id for panel in panels]
        object_ids = [item.object_id for item in objects]
        binding_ids = [item.binding_id for item in bindings]
        if not panel_ids or len(set(panel_ids)) != len(panel_ids):
            raise ValueError("graph panels must have unique IDs")
        if len(set(object_ids)) != len(object_ids) or any(not item for item in object_ids):
            raise ValueError("graph objects must have unique non-empty IDs")
        if len(set(binding_ids)) != len(binding_ids):
            raise ValueError("graph bindings must have unique IDs")
        if any(item.panel_id not in panel_ids for item in objects):
            raise ValueError("graph object references an unknown panel")
        object.__setattr__(self, "panels", panels)
        object.__setattr__(self, "objects", objects)
        object.__setattr__(self, "bindings", bindings)
        object.__setattr__(self, "metadata", _pairs(self.metadata))

    def object_by_id(self, object_id: str) -> GraphObject:
        for item in self.objects:
            if item.object_id == str(object_id):
                return item
        raise KeyError(f"unknown graph object: {object_id}")

    def object_ids_for_columns(self, column_ids: set[str]) -> tuple[str, ...]:
        return tuple(
            item.object_id
            for item in self.objects
            if any(
                getattr(reference, "column_id", "") in column_ids
                for binding in self.bindings
                if getattr(binding, "binding_id", "") == item.binding_id
                for reference in getattr(binding, "columns", ())
            )
        )

    def replace_object(self, replacement: GraphObject) -> "GraphDocument":
        objects = tuple(
            replacement if item.object_id == replacement.object_id else item
            for item in self.objects
        )
        if objects == self.objects:
            raise KeyError(f"unknown graph object: {replacement.object_id}")
        return GraphDocument(
            graph_id=self.graph_id,
            revision_id=_stable_id("graph", {"parent": self.revision_id, "object": replacement.to_payload()}),
            canvas_width_px=self.canvas_width_px,
            canvas_height_px=self.canvas_height_px,
            panels=self.panels,
            objects=objects,
            bindings=self.bindings,
            metadata=self.metadata,
            schema_version=self.schema_version,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "graph_id": self.graph_id,
            "revision_id": self.revision_id,
            "canvas": {
                "width_px": self.canvas_width_px,
                "height_px": self.canvas_height_px,
            },
            "panels": [panel.to_payload() for panel in self.panels],
            "objects": [item.to_payload() for item in self.objects],
            "bindings": [binding.to_payload() for binding in self.bindings],
            "metadata": thaw_json(self.metadata),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "GraphDocument":
        from .bindings import DataBinding

        canvas = dict(payload.get("canvas") or {})
        return cls(
            graph_id=str(payload.get("graph_id") or ""),
            revision_id=str(payload.get("revision_id") or ""),
            canvas_width_px=int(canvas.get("width_px", 0) or 0),
            canvas_height_px=int(canvas.get("height_px", 0) or 0),
            panels=tuple(PanelModel.from_payload(item) for item in payload.get("panels", ())),
            objects=tuple(GraphObject.from_payload(item) for item in payload.get("objects", ())),
            bindings=tuple(DataBinding.from_payload(item) for item in payload.get("bindings", ())),
            metadata=dict(payload.get("metadata") or {}),
            schema_version=int(payload.get("schema_version", 1) or 1),
        )
