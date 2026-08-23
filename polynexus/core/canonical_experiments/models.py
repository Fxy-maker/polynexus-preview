"""Immutable, JSON-safe experiment templates used by deterministic providers."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "1"
MAPPING_SOURCES = frozenset({"observed", "user", "AI proposal", "default"})
CAPABILITY_ITEM_STATUSES = frozenset({"completed", "needs_input", "failed", "not_applicable"})


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Canonical templates do not allow non-finite floats")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    raise TypeError(f"Canonical templates do not support {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _freeze(value: Any) -> Any:
    """Freeze a canonical JSON value after checking it is persistable."""
    _canonical_json(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _public(value: Any) -> Any:
    return _json_safe(value)


def _hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MappingSelection:
    """A source-bound, validated mapping from a table to a measurement."""

    measurement_id: str
    sheet_name: str | None
    sheet_index: int | None
    table_index: int
    header_row: int
    data_row_start: int
    data_row_end: int
    x_column: str
    intensity_column: str
    x_kind: str
    x_unit: str
    intensity_unit: str
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "measurement_id", str(self.measurement_id))
        object.__setattr__(self, "sheet_name", None if self.sheet_name is None else str(self.sheet_name))
        object.__setattr__(self, "sheet_index", None if self.sheet_index is None else int(self.sheet_index))
        for name in ("table_index", "header_row", "data_row_start", "data_row_end"):
            object.__setattr__(self, name, int(getattr(self, name)))
        for name in ("x_column", "intensity_column", "x_kind", "x_unit", "intensity_unit", "source"):
            object.__setattr__(self, name, str(getattr(self, name)))
        if self.source not in MAPPING_SOURCES:
            raise ValueError(f"Unsupported mapping source: {self.source}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "sheet_name": self.sheet_name,
            "sheet_index": self.sheet_index,
            "table_index": self.table_index,
            "header_row": self.header_row,
            "data_row_start": self.data_row_start,
            "data_row_end": self.data_row_end,
            "x_column": self.x_column,
            "intensity_column": self.intensity_column,
            "x_kind": self.x_kind,
            "x_unit": self.x_unit,
            "intensity_unit": self.intensity_unit,
            "source": self.source,
        }


@dataclass(frozen=True)
class MappingProposal:
    """A deterministic user or AI mapping proposal for one source artifact."""

    proposal_id: str
    source_artifact_id: str
    technique: str
    selections: tuple[MappingSelection, ...]
    source: str
    warnings: tuple[str, ...] = ()
    alternatives: tuple[MappingSelection, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "proposal_id", str(self.proposal_id))
        object.__setattr__(self, "source_artifact_id", str(self.source_artifact_id))
        object.__setattr__(self, "technique", str(self.technique))
        object.__setattr__(self, "source", str(self.source))
        object.__setattr__(self, "selections", tuple(self.selections))
        object.__setattr__(self, "warnings", tuple(str(warning) for warning in self.warnings))
        object.__setattr__(self, "alternatives", tuple(self.alternatives))
        if self.source not in {"user", "AI proposal"}:
            raise ValueError(f"Unsupported mapping proposal source: {self.source}")
        if not all(isinstance(selection, MappingSelection) for selection in self.selections):
            raise TypeError("Mapping proposal selections must be MappingSelection values")
        if not all(isinstance(selection, MappingSelection) for selection in self.alternatives):
            raise TypeError("Mapping proposal alternatives must be MappingSelection values")
        if any(selection.source != self.source for selection in self.selections):
            raise ValueError("Mapping proposal selections must use the proposal source")
        if any(selection.source not in {self.source, "observed"} for selection in self.alternatives):
            raise ValueError("Mapping proposal alternatives must be observed or use the proposal source")

    @classmethod
    def create(
        cls,
        *,
        source_artifact_id: str,
        technique: str,
        source: str,
        selections: Sequence[MappingSelection],
        warnings: Sequence[str] = (),
        alternatives: Sequence[MappingSelection] = (),
    ) -> "MappingProposal":
        payload = cls._identity_payload(
            source_artifact_id=source_artifact_id,
            technique=technique,
            source=source,
            selections=selections,
            warnings=warnings,
            alternatives=alternatives,
        )
        return cls(
            proposal_id=_hash(payload),
            source_artifact_id=str(source_artifact_id),
            technique=str(technique),
            selections=tuple(selections),
            source=str(source),
            warnings=tuple(warnings),
            alternatives=tuple(alternatives),
        )

    @staticmethod
    def _identity_payload(**values: Any) -> dict[str, Any]:
        return {
            "source_artifact_id": str(values["source_artifact_id"]),
            "technique": str(values["technique"]),
            "selections": [selection.to_dict() for selection in values["selections"]],
            "source": str(values["source"]),
            "warnings": [str(warning) for warning in values["warnings"]],
            "alternatives": [selection.to_dict() for selection in values["alternatives"]],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            **self._identity_payload(
                source_artifact_id=self.source_artifact_id,
                technique=self.technique,
                selections=self.selections,
                source=self.source,
                warnings=self.warnings,
                alternatives=self.alternatives,
            ),
        }


@dataclass(frozen=True)
class Measurement:
    """An immutable, source-located one-dimensional measurement."""

    measurement_id: str
    family: str
    role: str
    channels: Mapping[str, tuple[float, ...]]
    units: Mapping[str, str]
    source_locator: Mapping[str, Any]
    acquisition_metadata: Mapping[str, Any] = field(default_factory=dict)
    mapping: MappingSelection | None = None
    warnings: tuple[str, ...] = ()

    _CHANNEL_KEYS = frozenset({"x", "intensity"})
    _SOURCE_LOCATOR_KEYS = frozenset({
        "source_path", "sheet_name", "sheet_index", "table_index", "header_row",
        "data_row_start", "data_row_end", "point_start", "point_end",
    })

    def __post_init__(self) -> None:
        object.__setattr__(self, "measurement_id", str(self.measurement_id))
        object.__setattr__(self, "family", str(self.family))
        object.__setattr__(self, "role", str(self.role))
        if not isinstance(self.channels, Mapping) or set(self.channels) != self._CHANNEL_KEYS:
            raise ValueError("Measurement channels must be exactly x and intensity")
        if not isinstance(self.units, Mapping) or set(self.units) != self._CHANNEL_KEYS:
            raise ValueError("Measurement units must use the channel keys exactly")
        if not all(isinstance(unit, str) for unit in self.units.values()):
            raise ValueError("Measurement units must be strings")
        normalized_channels: dict[str, tuple[float, ...]] = {}
        for key in ("x", "intensity"):
            values = tuple(self.channels[key])
            if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in values):
                raise ValueError("Measurement channels must contain numeric values")
            normalized = tuple(float(item) for item in values)
            if not all(math.isfinite(item) for item in normalized):
                raise ValueError("Measurement channels do not allow non-finite numeric values")
            normalized_channels[key] = normalized
        if len(normalized_channels["x"]) < 2 or len(normalized_channels["x"]) != len(normalized_channels["intensity"]):
            raise ValueError("Measurement channels must have equal lengths of at least two")
        object.__setattr__(self, "channels", _freeze(normalized_channels))
        object.__setattr__(self, "units", _freeze({key: self.units[key] for key in ("x", "intensity")}))
        if not isinstance(self.source_locator, Mapping):
            raise ValueError("Measurement source locator must be a mapping")
        missing_locator_keys = self._SOURCE_LOCATOR_KEYS.difference(self.source_locator)
        if missing_locator_keys:
            raise ValueError(f"Measurement source locator is missing: {', '.join(sorted(missing_locator_keys))}")
        object.__setattr__(self, "source_locator", _freeze(self.source_locator))
        if not isinstance(self.acquisition_metadata, Mapping):
            raise ValueError("Measurement acquisition metadata must be a mapping")
        object.__setattr__(self, "acquisition_metadata", _freeze(self.acquisition_metadata))
        if self.mapping is not None and not isinstance(self.mapping, MappingSelection):
            raise TypeError("Measurement mapping must be a MappingSelection")
        object.__setattr__(self, "warnings", tuple(str(warning) for warning in self.warnings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "family": self.family,
            "role": self.role,
            "channels": _public(self.channels),
            "units": _public(self.units),
            "source_locator": _public(self.source_locator),
            "acquisition_metadata": _public(self.acquisition_metadata),
            "mapping": None if self.mapping is None else self.mapping.to_dict(),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class CapabilityItemResult:
    """A finite, technique-neutral outcome for one requested capability."""

    item_id: str
    measurement_id: str
    capability_id: str
    status: str
    result: Mapping[str, Any] = field(default_factory=dict)
    figures: Mapping[str, str] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("item_id", "measurement_id", "capability_id", "status"):
            object.__setattr__(self, name, str(getattr(self, name)))
        if self.status not in CAPABILITY_ITEM_STATUSES:
            raise ValueError(f"Unsupported capability item status: {self.status}")
        if not isinstance(self.result, Mapping) or not isinstance(self.figures, Mapping):
            raise ValueError("Capability item result and figures must be mappings")
        if self.status != "completed" and (self.result or self.figures):
            raise ValueError("Only completed capability items may contain results or figures")
        if not all(isinstance(value, str) for value in self.figures.values()):
            raise ValueError("Capability item figure values must be strings")
        object.__setattr__(self, "result", _freeze(self.result))
        object.__setattr__(self, "figures", _freeze(self.figures))
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "measurement_id": self.measurement_id,
            "capability_id": self.capability_id,
            "status": self.status,
            "result": _public(self.result),
            "figures": _public(self.figures),
            "reason_codes": list(self.reason_codes),
        }


def _mapping_selection_from_dict(value: Mapping[str, Any]) -> MappingSelection:
    return MappingSelection(
        measurement_id=str(value["measurement_id"]),
        sheet_name=value.get("sheet_name"),
        sheet_index=value.get("sheet_index"),
        table_index=int(value["table_index"]),
        header_row=int(value["header_row"]),
        data_row_start=int(value["data_row_start"]),
        data_row_end=int(value["data_row_end"]),
        x_column=str(value["x_column"]),
        intensity_column=str(value["intensity_column"]),
        x_kind=str(value["x_kind"]),
        x_unit=str(value["x_unit"]),
        intensity_unit=str(value["intensity_unit"]),
        source=str(value["source"]),
    )


def _mapping_proposal_from_dict(value: Mapping[str, Any]) -> MappingProposal:
    selections_value = value.get("selections", ())
    alternatives_value = value.get("alternatives", ())
    if not isinstance(selections_value, Sequence) or isinstance(selections_value, (str, bytes)):
        raise ValueError("Mapping proposal selections must be a sequence")
    if not isinstance(alternatives_value, Sequence) or isinstance(alternatives_value, (str, bytes)):
        raise ValueError("Mapping proposal alternatives must be a sequence")
    if not all(isinstance(item, Mapping) for item in tuple(selections_value) + tuple(alternatives_value)):
        raise ValueError("Mapping proposal selections must be mappings")
    proposal = MappingProposal.create(
        source_artifact_id=str(value["source_artifact_id"]),
        technique=str(value["technique"]),
        source=str(value["source"]),
        selections=tuple(_mapping_selection_from_dict(item) for item in selections_value),
        warnings=tuple(value.get("warnings", ())),
        alternatives=tuple(_mapping_selection_from_dict(item) for item in alternatives_value),
    )
    if str(value.get("proposal_id", "")) != proposal.proposal_id:
        raise ValueError("Mapping proposal ID does not match its content")
    return proposal


def _measurement_from_dict(value: Mapping[str, Any]) -> Measurement:
    mapping_value = value.get("mapping")
    if mapping_value is not None and not isinstance(mapping_value, Mapping):
        raise ValueError("Measurement mapping must be a mapping")
    return Measurement(
        measurement_id=str(value["measurement_id"]),
        family=str(value["family"]),
        role=str(value["role"]),
        channels=value["channels"],
        units=value["units"],
        source_locator=value["source_locator"],
        acquisition_metadata=value.get("acquisition_metadata", {}),
        mapping=None if mapping_value is None else _mapping_selection_from_dict(mapping_value),
        warnings=tuple(value.get("warnings", ())),
    )


@dataclass(frozen=True)
class ConversionRecord:
    """Auditable observations and decisions made while converting raw data."""

    conversion_id: str
    source_artifact_id: str
    contract_version: str = CONTRACT_VERSION
    observed_columns: tuple[str, ...] = ()
    extracted_segments: tuple[Mapping[str, Any], ...] = ()
    excluded_segments: tuple[Mapping[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    conversion_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_columns", tuple(str(column) for column in self.observed_columns))
        object.__setattr__(self, "extracted_segments", tuple(_freeze(item) for item in self.extracted_segments))
        object.__setattr__(self, "excluded_segments", tuple(_freeze(item) for item in self.excluded_segments))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        object.__setattr__(self, "reason_codes", tuple(str(item) for item in self.reason_codes))

    @classmethod
    def create(
        cls,
        *,
        conversion_id: str,
        source_artifact_id: str,
        observed_columns: Sequence[str] = (),
        extracted_segments: Sequence[Mapping[str, Any]] = (),
        excluded_segments: Sequence[Mapping[str, Any]] = (),
        warnings: Sequence[str] = (),
        reason_codes: Sequence[str] = (),
        contract_version: str = CONTRACT_VERSION,
    ) -> "ConversionRecord":
        payload = cls._payload(
            conversion_id=conversion_id,
            source_artifact_id=source_artifact_id,
            contract_version=contract_version,
            observed_columns=observed_columns,
            extracted_segments=extracted_segments,
            excluded_segments=excluded_segments,
            warnings=warnings,
            reason_codes=reason_codes,
        )
        return cls(
            conversion_id=str(conversion_id),
            source_artifact_id=str(source_artifact_id),
            contract_version=str(contract_version),
            observed_columns=tuple(observed_columns),
            extracted_segments=tuple(extracted_segments),
            excluded_segments=tuple(excluded_segments),
            warnings=tuple(warnings),
            reason_codes=tuple(reason_codes),
            conversion_hash=_hash(payload),
        )

    @staticmethod
    def _payload(**values: Any) -> dict[str, Any]:
        return {
            "conversion_id": str(values["conversion_id"]),
            "source_artifact_id": str(values["source_artifact_id"]),
            "contract_version": str(values["contract_version"]),
            "observed_columns": list(values["observed_columns"]),
            "extracted_segments": _public(tuple(values["extracted_segments"])),
            "excluded_segments": _public(tuple(values["excluded_segments"])),
            "warnings": list(values["warnings"]),
            "reason_codes": list(values["reason_codes"]),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(
                conversion_id=self.conversion_id,
                source_artifact_id=self.source_artifact_id,
                contract_version=self.contract_version,
                observed_columns=self.observed_columns,
                extracted_segments=self.extracted_segments,
                excluded_segments=self.excluded_segments,
                warnings=self.warnings,
                reason_codes=self.reason_codes,
            ),
            "conversion_hash": self.conversion_hash,
        }


@dataclass(frozen=True)
class CanonicalExperiment:
    """A validated template that can be passed to a deterministic provider."""

    template_id: str
    source_artifact_id: str
    payload: Mapping[str, Any]
    conversion_record: ConversionRecord
    measurements: tuple[Measurement, ...] = ()
    mapping_proposal: MappingProposal | None = None
    contract_version: str = CONTRACT_VERSION
    content_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _freeze(self.payload))
        object.__setattr__(self, "measurements", tuple(self.measurements))
        if not all(isinstance(measurement, Measurement) for measurement in self.measurements):
            raise TypeError("Canonical experiment measurements must be Measurement values")
        if self.mapping_proposal is not None and not isinstance(self.mapping_proposal, MappingProposal):
            raise TypeError("Canonical experiment mapping proposal must be a MappingProposal")

    @classmethod
    def create(
        cls,
        *,
        template_id: str,
        source_artifact_id: str,
        payload: Mapping[str, Any],
        conversion_record: ConversionRecord,
        measurements: Sequence[Measurement] = (),
        mapping_proposal: MappingProposal | None = None,
        contract_version: str = CONTRACT_VERSION,
    ) -> "CanonicalExperiment":
        identity_payload = cls._payload(
            template_id=template_id,
            source_artifact_id=source_artifact_id,
            payload=payload,
            conversion_record=conversion_record,
            measurements=measurements,
            mapping_proposal=mapping_proposal,
            contract_version=contract_version,
        )
        return cls(
            template_id=str(template_id),
            source_artifact_id=str(source_artifact_id),
            payload=payload,
            conversion_record=conversion_record,
            measurements=tuple(measurements),
            mapping_proposal=mapping_proposal,
            contract_version=str(contract_version),
            content_hash=_hash(identity_payload),
        )

    @staticmethod
    def _payload(**values: Any) -> dict[str, Any]:
        return {
            "template_id": str(values["template_id"]),
            "source_artifact_id": str(values["source_artifact_id"]),
            "payload": _public(values["payload"]),
            "conversion_record": values["conversion_record"].to_dict(),
            "measurements": [measurement.to_dict() for measurement in values["measurements"]],
            "mapping_proposal": None
            if values["mapping_proposal"] is None
            else values["mapping_proposal"].to_dict(),
            "contract_version": str(values["contract_version"]),
        }

    @staticmethod
    def _legacy_payload(**values: Any) -> dict[str, Any]:
        return {
            "template_id": str(values["template_id"]),
            "source_artifact_id": str(values["source_artifact_id"]),
            "payload": _public(values["payload"]),
            "conversion_record": values["conversion_record"].to_dict(),
            "contract_version": str(values["contract_version"]),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(
                template_id=self.template_id,
                source_artifact_id=self.source_artifact_id,
                payload=self.payload,
                conversion_record=self.conversion_record,
                measurements=self.measurements,
                mapping_proposal=self.mapping_proposal,
                contract_version=self.contract_version,
            ),
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CanonicalExperiment":
        record_value = value.get("conversion_record")
        if not isinstance(record_value, Mapping):
            raise ValueError("Canonical template conversion record is missing")
        record = ConversionRecord.create(
            conversion_id=str(record_value["conversion_id"]),
            source_artifact_id=str(record_value["source_artifact_id"]),
            contract_version=str(record_value.get("contract_version", CONTRACT_VERSION)),
            observed_columns=record_value.get("observed_columns", ()),
            extracted_segments=record_value.get("extracted_segments", ()),
            excluded_segments=record_value.get("excluded_segments", ()),
            warnings=record_value.get("warnings", ()),
            reason_codes=record_value.get("reason_codes", ()),
        )
        if str(record_value.get("conversion_hash", "")) != record.conversion_hash:
            raise ValueError("Canonical conversion record hash does not match its content")
        has_measurements = "measurements" in value
        has_mapping_proposal = "mapping_proposal" in value
        if has_measurements != has_mapping_proposal:
            raise ValueError("Canonical template contract fields must be serialized together")
        measurements_value = value.get("measurements", ())
        if not isinstance(measurements_value, Sequence) or isinstance(measurements_value, (str, bytes)):
            raise ValueError("Canonical template measurements must be a sequence")
        if not all(isinstance(item, Mapping) for item in measurements_value):
            raise ValueError("Canonical template measurements must be mappings")
        measurements = tuple(_measurement_from_dict(item) for item in measurements_value)
        mapping_proposal_value = value.get("mapping_proposal")
        if mapping_proposal_value is not None and not isinstance(mapping_proposal_value, Mapping):
            raise ValueError("Canonical template mapping proposal must be a mapping")
        mapping_proposal = None if mapping_proposal_value is None else _mapping_proposal_from_dict(mapping_proposal_value)
        template = cls.create(
            template_id=str(value["template_id"]),
            source_artifact_id=str(value["source_artifact_id"]),
            payload=value.get("payload", {}),
            conversion_record=record,
            measurements=measurements,
            mapping_proposal=mapping_proposal,
            contract_version=str(value.get("contract_version", CONTRACT_VERSION)),
        )
        expected_hash = template.content_hash
        if not has_measurements:
            expected_hash = _hash(
                cls._legacy_payload(
                    template_id=template.template_id,
                    source_artifact_id=template.source_artifact_id,
                    payload=template.payload,
                    conversion_record=template.conversion_record,
                    contract_version=template.contract_version,
                )
            )
        if str(value.get("content_hash", "")) != expected_hash:
            raise ValueError("Canonical template content hash does not match its content")
        return template


@dataclass(frozen=True)
class ConversionOutcome:
    """Explicit conversion status; blocked conversions cannot supply a template."""

    status: str
    record: ConversionRecord
    template: CanonicalExperiment | None = None
    reason_codes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.status not in {"ready", "review_required", "blocked", "needs_input"}:
            raise ValueError(f"Unsupported conversion status: {self.status}")
        if self.status in {"blocked", "needs_input"} and self.template is not None:
            raise ValueError(f"{self.status} conversion cannot contain a canonical template")
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))
