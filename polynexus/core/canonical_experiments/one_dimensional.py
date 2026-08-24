"""Deterministic conversion of generic material-neutral one-dimensional tables."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import pandas as pd

from .models import (
    CanonicalExperiment,
    ConversionOutcome,
    ConversionRecord,
    MappingProposal,
    MappingSelection,
    Measurement,
)


_CONVERTER_ID = "generic.one-dimensional.v1"
_SUPPORTED_EXTENSIONS = frozenset({".csv", ".tsv", ".txt", ".dat", ".asc", ".xy", ".chi", ".xls", ".xlsx", ".xlsm"})
_WORKBOOK_EXTENSIONS = frozenset({".xls", ".xlsx", ".xlsm"})
_INTENSITY_ALIASES = frozenset({"absorbance", "transmittance", "intensity", "i", "counts", "count", "cps"})
_IR_X_ALIASES = frozenset({"wavenumber", "wavenumbercm1", "cm1"})
_Q_ALIASES = frozenset({"q", "qnm1", "qangstrom1"})
_TWO_THETA_ALIASES = frozenset({"2theta", "twotheta", "theta2"})


@dataclass(frozen=True)
class _Table:
    frame: pd.DataFrame
    sheet_name: str | None
    sheet_index: int | None
    table_index: int
    header_row: int = 0
    data_rows: tuple[tuple[int, int], ...] = ()
    raw_headers: tuple[str, ...] = ()


def convert_one_dimensional_table(
    path: str | Path,
    *,
    technique: str,
    source_artifact_id: str,
    mapping_proposal: MappingProposal | None = None,
) -> ConversionOutcome:
    """Convert supported generic two-column tables without scientific transformation."""
    source_path = Path(path)
    extension = source_path.suffix.casefold()
    if extension not in _SUPPORTED_EXTENSIONS:
        return _outcome("blocked", source_artifact_id, "conversion_unsupported_format")

    try:
        tables = _load_tables(source_path, extension)
    except Exception:
        return _outcome("blocked", source_artifact_id, "conversion_source_unreadable")

    observed_columns = tuple(
        f"{table.sheet_name if table.sheet_name is not None else 'flat'}:{header}"
        for table in tables
        for header in table.raw_headers
    )
    normalized_technique = technique.strip().upper()
    if any(_raw_headers_ambiguous(table, normalized_technique) for table in tables):
        return _outcome(
            "needs_input", source_artifact_id, "conversion_mapping_ambiguous", observed_columns=observed_columns
        )
    observed_by_table = {
        (table.sheet_index, table.table_index): _observed_selection(table, normalized_technique)
        for table in tables
    }
    if mapping_proposal is not None and not _valid_proposal(
        mapping_proposal,
        tables=tables,
        observed_by_table=observed_by_table,
        technique=normalized_technique,
        source_artifact_id=source_artifact_id,
    ):
        return _outcome(
            "needs_input", source_artifact_id, "conversion_mapping_proposal_invalid", observed_columns=observed_columns
        )

    selected: list[MappingSelection] = []
    proposal_by_table = (
        {(selection.sheet_index, selection.table_index): selection for selection in mapping_proposal.selections}
        if mapping_proposal is not None
        else {}
    )
    proposal_used = False
    for table in tables:
        observed = observed_by_table[(table.sheet_index, table.table_index)]
        if observed is not None:
            selected.append(observed)
            continue
        proposal_selection = proposal_by_table.get((table.sheet_index, table.table_index))
        if proposal_selection is None:
            return _outcome(
                "needs_input", source_artifact_id, "conversion_mapping_ambiguous", observed_columns=observed_columns
            )
        selected.append(proposal_selection)
        proposal_used = True

    measurements: list[Measurement] = []
    for table, selection in zip(tables, selected, strict=True):
        x_values = pd.to_numeric(table.frame[selection.x_column], errors="coerce")
        intensity_values = pd.to_numeric(table.frame[selection.intensity_column], errors="coerce")
        pairs = [
            (float(x_value), float(intensity_value))
            for x_value, intensity_value in zip(x_values, intensity_values, strict=True)
            if _finite_pair(x_value, intensity_value)
        ]
        if len(pairs) < 2:
            return _outcome(
                "needs_input", source_artifact_id, "conversion_no_numeric_table", observed_columns=observed_columns
            )
        locator = _source_locator(source_path, table, selection, point_count=len(pairs))
        warnings = _unit_warnings(selection)
        measurements.append(
            Measurement(
                measurement_id=selection.measurement_id,
                family="spectrum_1d" if normalized_technique == "IR" else "scattering_1d",
                role="raw_curve",
                channels={"x": tuple(pair[0] for pair in pairs), "intensity": tuple(pair[1] for pair in pairs)},
                units={"x": selection.x_unit, "intensity": selection.intensity_unit},
                source_locator=locator,
                acquisition_metadata=(
                    {} if normalized_technique == "IR"
                    else {"background_state": "unknown", "normalization_state": "unknown"}
                ),
                mapping=selection,
                warnings=warnings,
            )
        )

    warnings = tuple(warning for measurement in measurements for warning in measurement.warnings)
    record = ConversionRecord.create(
        conversion_id=_CONVERTER_ID,
        source_artifact_id=source_artifact_id,
        observed_columns=observed_columns,
        extracted_segments=tuple(
            {"measurement_id": measurement.measurement_id, "source_locator": measurement.source_locator}
            for measurement in measurements
        ),
        warnings=warnings,
    )
    template = CanonicalExperiment.create(
        template_id="spectrum_1d.v1" if normalized_technique == "IR" else "scattering_1d.v1",
        source_artifact_id=source_artifact_id,
        payload={"technique": normalized_technique},
        conversion_record=record,
        measurements=measurements,
        mapping_proposal=mapping_proposal if proposal_used else None,
    )
    return ConversionOutcome(status="ready", record=record, template=template)


def _load_tables(path: Path, extension: str) -> tuple[_Table, ...]:
    if extension not in _WORKBOOK_EXTENSIONS:
        raw_headers, header_row, data_rows, whitespace_comment_rows = _flat_source_records(path)
        frame = _string_headers(
            pd.read_csv(path, sep=None, engine="python", comment="#", skiprows=whitespace_comment_rows), raw_headers
        )
        if len(frame) != len(data_rows):
            raise ValueError("Flat source records cannot be mapped to pandas rows")
        return (_Table(frame, None, None, 0, header_row, data_rows, raw_headers),)
    with pd.ExcelFile(path) as workbook:
        return tuple(
            _workbook_table(workbook, sheet_name=str(sheet_name), sheet_index=index)
            for index, sheet_name in enumerate(workbook.sheet_names)
        )


def _workbook_table(workbook: pd.ExcelFile, *, sheet_name: str, sheet_index: int) -> _Table:
    raw_header_row = pd.read_excel(workbook, sheet_name=sheet_name, header=None, nrows=1)
    raw_headers = tuple(_display_header(value) for value in raw_header_row.iloc[0].tolist()) if not raw_header_row.empty else ()
    frame = _string_headers(pd.read_excel(workbook, sheet_name=sheet_name), raw_headers)
    return _Table(frame, sheet_name, sheet_index, 0, raw_headers=raw_headers)


def _string_headers(frame: pd.DataFrame, raw_headers: tuple[str, ...] | None = None) -> pd.DataFrame:
    headers = raw_headers if raw_headers is not None else tuple(str(header) for header in frame.columns)
    if len(headers) != len(frame.columns):
        raise ValueError("Raw header count does not match pandas columns")
    frame.columns = list(headers)
    return frame


class _PhysicalLineIterator:
    def __init__(self, lines: list[tuple[int, str]]) -> None:
        self._lines = lines
        self._position = 0
        self.last_line = -1

    @property
    def next_line(self) -> int:
        return self._lines[self._position][0] if self._position < len(self._lines) else -1

    def __iter__(self) -> "_PhysicalLineIterator":
        return self

    def __next__(self) -> str:
        if self._position >= len(self._lines):
            raise StopIteration
        line_index, line = self._lines[self._position]
        self._position += 1
        self.last_line = line_index
        return line


def _flat_source_records(path: Path) -> tuple[tuple[str, ...], int, tuple[tuple[int, int], ...], tuple[int, ...]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        physical_lines = list(enumerate(handle))
    whitespace_comment_rows = tuple(
        index for index, line in physical_lines if line[:1].isspace() and line.lstrip().startswith("#")
    )
    records = _PhysicalLineIterator(
        [(index, line) for index, line in physical_lines if not line.lstrip().startswith("#")]
    )
    sample = "".join(line for _, line in records._lines[:20])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;| ") if sample else csv.excel
        reader = csv.reader(records, dialect)
    except csv.Error:
        reader = csv.reader(records, delimiter=_fallback_delimiter(sample))
    parsed: list[tuple[list[str], int, int]] = []
    while True:
        start = records.next_line
        try:
            row = next(reader)
        except StopIteration:
            break
        if row:
            parsed.append((row, start, records.last_line))
    if not parsed:
        raise ValueError("Flat source has no table records")
    header, header_start, _ = parsed[0]
    data_rows = tuple((start, end) for _, start, end in parsed[1:])
    return tuple(_display_header(value) for value in header), header_start, data_rows, whitespace_comment_rows


def _display_header(value: Any) -> str:
    return "" if pd.isna(value) else str(value)


def _fallback_delimiter(sample: str) -> str:
    first_line = sample.splitlines()[0] if sample else ""
    for delimiter in (",", "\t", ";", "|"):
        if delimiter in first_line:
            return delimiter
    return " "


def _raw_headers_ambiguous(table: _Table, technique: str) -> bool:
    if any(not header.strip() for header in table.raw_headers):
        return True
    relevant = [
        _normalize_header(header)
        for header in table.raw_headers
        if _x_kind(header, technique) is not None or _is_intensity_header(header)
    ]
    return len(relevant) != len(set(relevant))


def _valid_proposal(
    proposal: MappingProposal,
    *,
    tables: tuple[_Table, ...],
    observed_by_table: dict[tuple[int | None, int], MappingSelection | None],
    technique: str,
    source_artifact_id: str,
) -> bool:
    if proposal.source_artifact_id != source_artifact_id or proposal.technique.strip().upper() != technique:
        return False
    if len(proposal.selections) != len(tables):
        return False
    table_by_key = {(table.sheet_index, table.table_index): table for table in tables}
    if len({(selection.sheet_index, selection.table_index) for selection in proposal.selections}) != len(tables):
        return False
    if all(observed_by_table[(table.sheet_index, table.table_index)] is not None for table in tables):
        return False
    for selection in proposal.selections:
        table = table_by_key.get((selection.sheet_index, selection.table_index))
        if table is None or selection.source != proposal.source:
            return False
        if selection.measurement_id != _measurement_id(table):
            return False
        if selection.sheet_name != table.sheet_name or selection.header_row != table.header_row:
            return False
        if selection.x_column not in table.frame.columns or selection.intensity_column not in table.frame.columns:
            return False
        if selection.x_column == selection.intensity_column or not _kind_allowed(selection.x_kind, technique):
            return False
        if selection.x_unit != _x_unit(selection.x_column, selection.x_kind):
            return False
        if selection.intensity_unit != _intensity_unit(selection.intensity_column):
            return False
        observed = observed_by_table[(table.sheet_index, table.table_index)]
        if observed is not None and not _matches_observed_mapping(selection, observed):
            return False
        start, end = _table_row_range(table)
        if selection.data_row_start != start or selection.data_row_end != end:
            return False
    return True


def _matches_observed_mapping(proposed: MappingSelection, observed: MappingSelection) -> bool:
    return (
        proposed.measurement_id == observed.measurement_id
        and proposed.sheet_name == observed.sheet_name
        and proposed.sheet_index == observed.sheet_index
        and proposed.table_index == observed.table_index
        and proposed.header_row == observed.header_row
        and proposed.data_row_start == observed.data_row_start
        and proposed.data_row_end == observed.data_row_end
        and proposed.x_column == observed.x_column
        and proposed.intensity_column == observed.intensity_column
        and proposed.x_kind == observed.x_kind
        and proposed.x_unit == observed.x_unit
        and proposed.intensity_unit == observed.intensity_unit
    )


def _observed_selection(table: _Table, technique: str) -> MappingSelection | None:
    x_candidates = [
        (str(header), _x_kind(str(header), technique))
        for header in table.frame.columns
        if _x_kind(str(header), technique) is not None
    ]
    intensity_candidates = [
        str(header) for header in table.frame.columns if _is_intensity_header(str(header))
    ]
    if len(x_candidates) != 1 or len(intensity_candidates) != 1:
        return None
    x_column, x_kind = x_candidates[0]
    intensity_column = intensity_candidates[0]
    if x_column == intensity_column:
        return None
    start, end = _table_row_range(table)
    return MappingSelection(
        measurement_id=_measurement_id(table),
        sheet_name=table.sheet_name,
        sheet_index=table.sheet_index,
        table_index=table.table_index,
        header_row=table.header_row,
        data_row_start=start,
        data_row_end=end,
        x_column=x_column,
        intensity_column=intensity_column,
        x_kind=x_kind,
        x_unit=_x_unit(x_column, x_kind),
        intensity_unit=_intensity_unit(intensity_column),
        source="observed",
    )


def _measurement_id(table: _Table) -> str:
    return f"sheet-{table.sheet_index if table.sheet_index is not None else 0}-table-{table.table_index}"


def _table_row_range(table: _Table) -> tuple[int, int]:
    if table.frame.empty:
        return 0, 0
    if table.data_rows:
        return table.data_rows[0][0], table.data_rows[-1][1]
    return int(table.frame.index[0]) + 1, int(table.frame.index[-1]) + 1


def _source_locator(
    path: Path, table: _Table, selection: MappingSelection, *, point_count: int
) -> dict[str, Any]:
    return {
        "source_path": str(path.resolve()),
        "sheet_name": table.sheet_name,
        "sheet_index": table.sheet_index,
        "table_index": table.table_index,
        "header_row": table.header_row,
        "data_row_start": selection.data_row_start,
        "data_row_end": selection.data_row_end,
        "point_start": 0,
        "point_end": point_count - 1,
    }


def _finite_pair(x_value: Any, intensity_value: Any) -> bool:
    return bool(pd.notna(x_value) and pd.notna(intensity_value) and math.isfinite(float(x_value)) and math.isfinite(float(intensity_value)))


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold().replace("θ", "theta"))


def _x_kind(header: str, technique: str) -> str | None:
    normalized = _normalize_header(header)
    if technique == "IR":
        without_wavenumber_unit = _normalize_header(
            re.sub(r"(?:cm\s*(?:\^?\s*-\s*1|⁻¹)|1\s*/\s*cm)", "", header.casefold())
        )
        return "wavenumber" if {normalized, without_wavenumber_unit}.intersection(_IR_X_ALIASES) else None
    if technique in {"SAXS", "WAXS"}:
        without_q_unit = _normalize_header(
            re.sub(r"(?:nm|angstrom|å|a)\s*(?:\^?\s*-\s*1|⁻¹)", "", header.casefold())
        )
        without_angle_unit = _normalize_header(
            re.sub(r"(?:degrees?|deg|°)", "", header.casefold())
        )
        if {normalized, without_q_unit}.intersection(_Q_ALIASES):
            return "q"
        if {normalized, without_angle_unit}.intersection(_TWO_THETA_ALIASES):
            return "two_theta"
    return None


def _is_intensity_header(header: str) -> bool:
    return _intensity_alias(header) in _INTENSITY_ALIASES


def _intensity_alias(header: str) -> str:
    normalized = _normalize_header(header)
    if normalized in _INTENSITY_ALIASES:
        return normalized
    without_unit_suffix = re.sub(
        r"\s*[\(\[]?\s*(?:counts|cps|a\s*\.\s*u\s*\.)\s*[\)\]]?\s*$", "", header.casefold()
    )
    return _normalize_header(without_unit_suffix)


def _kind_allowed(x_kind: str, technique: str) -> bool:
    return (technique == "IR" and x_kind == "wavenumber") or (
        technique in {"SAXS", "WAXS"} and x_kind in {"q", "two_theta"}
    )


def _x_unit(header: str, x_kind: str) -> str:
    text = header.casefold()
    if x_kind == "wavenumber" and re.search(r"(?:cm\s*(?:\^?\s*-\s*1|⁻¹)|1\s*/\s*cm)", text):
        return "cm^-1"
    if x_kind == "q" and re.search(r"nm\s*(?:\^?\s*-\s*1|⁻¹)", text):
        return "nm^-1"
    if x_kind == "q" and re.search(r"(?:a|å|angstrom)\s*(?:\^?\s*-\s*1|⁻¹)", text):
        return "angstrom^-1"
    if x_kind == "two_theta" and re.search(r"(?:degrees?|deg|°)", text):
        return "deg"
    return "unknown"


def _intensity_unit(header: str) -> str:
    text = header.casefold()
    if re.search(r"a\s*\.\s*u\s*\.", text):
        return "a.u."
    for unit in ("absorbance", "transmittance", "counts", "cps"):
        if re.search(rf"\b{re.escape(unit)}\b", text):
            return unit
    return "unknown"


def _unit_warnings(selection: MappingSelection) -> tuple[str, ...]:
    warnings: list[str] = []
    if selection.x_unit == "unknown":
        warnings.append("coordinate_unit_unknown")
    if selection.intensity_unit == "unknown":
        warnings.append("intensity_unit_unknown")
    return tuple(warnings)


def _outcome(
    status: str,
    source_artifact_id: str,
    reason: str,
    *,
    observed_columns: tuple[str, ...] = (),
) -> ConversionOutcome:
    record = ConversionRecord.create(
        conversion_id=_CONVERTER_ID,
        source_artifact_id=source_artifact_id,
        observed_columns=observed_columns,
        reason_codes=(reason,),
    )
    return ConversionOutcome(status=status, record=record, reason_codes=(reason,))
