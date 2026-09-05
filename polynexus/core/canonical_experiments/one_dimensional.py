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
_NMR_X_ALIASES = frozenset({"ppm", "chemicalshift", "chemicalshiftppm", "shiftppm"})
_Q_ALIASES = frozenset({"q", "qnm1", "qangstrom1"})
_TWO_THETA_ALIASES = frozenset({"2theta", "twotheta", "theta2"})
_TGA_TEMPERATURE_ALIASES = frozenset({"temperature", "temperaturec", "temp", "tempc", "sampletemperature"})
_TGA_TIME_ALIASES = frozenset({"time", "times", "timesec", "timemin", "elapsedtime", "elapsedtimes"})
_TGA_MASS_ALIASES = frozenset({
    "mass", "massmg", "massg", "massug", "masspercent", "masspct",
    "massweightpercent", "massweightpct", "masswtpercent", "masswtpct",
    "weight", "weightmg", "weightg", "weightpercent", "weightpct",
    "wtpercent", "wtpct", "residue", "residuemass", "remainingmass",
    "residuepercent", "remainingweight", "samplemass",
})
_DMA_FREQUENCY_ALIASES = frozenset({"frequency", "frequencyhz", "freq", "freqhz", "angularfrequency", "omega"})
_DMA_TEMPERATURE_ALIASES = frozenset({"temperature", "temperaturec", "temp", "tempc", "sampletemperature"})
_DMA_TIME_ALIASES = frozenset({"time", "times", "timesec", "timemin", "elapsedtime", "elapsedtimes"})
_DMA_SIGNAL_ALIASES = frozenset({
    "storagemodulus", "lossmodulus", "complexmodulus", "youngsmodulus", "modulus",
    "eprime", "edoubleprime", "gprime", "gdoubleprime", "tandelta", "tangentdelta",
    "damping", "stress", "strain", "displacement", "force",
})
_RHEOLOGY_SHEAR_RATE_ALIASES = frozenset({
    "shearrate", "shearrates1", "shearrate1s", "gammadot", "rateofshear",
})
_RHEOLOGY_FREQUENCY_ALIASES = frozenset({"frequency", "frequencyhz", "freq", "freqhz"})
_RHEOLOGY_ANGULAR_FREQUENCY_ALIASES = frozenset({"angularfrequency", "omega"})
_RHEOLOGY_TEMPERATURE_ALIASES = _DMA_TEMPERATURE_ALIASES
_RHEOLOGY_TIME_ALIASES = _DMA_TIME_ALIASES
_RHEOLOGY_STRAIN_ALIASES = frozenset({
    "strain", "shearstrain", "strainamplitude", "shearstrainamplitude",
    "gamma", "gamma0",
})
_RHEOLOGY_SIGNAL_ALIASES = frozenset({
    "shearstress", "stress", "viscosity", "dynamicviscosity", "apparentviscosity",
    "complexviscosity", "etastar", "storagemodulus", "lossmodulus", "gprime",
    "gdoubleprime", "tandelta", "tangentdelta", "normalstress", "normalforce",
    "torque",
})
_SEC_TIME_ALIASES = frozenset(
    {"time", "retentiontime", "elutiontime", "retention", "elution"}
)
_SEC_VOLUME_ALIASES = frozenset(
    {"volume", "retentionvolume", "elutionvolume"}
)
_MECHANICS_TIME_ALIASES = _TGA_TIME_ALIASES
_MECHANICS_DISPLACEMENT_ALIASES = frozenset(
    {"displacement", "extension", "elongation", "crossheaddisplacement", "stroke"}
)
_MECHANICS_STRAIN_ALIASES = frozenset(
    {"strain", "engineeringstrain", "elongationpercent", "strainpercent"}
)
_MECHANICS_DEFLECTION_ALIASES = frozenset(
    {"deflection", "displacementdeflection", "flexuraldeflection"}
)
_MECHANICS_CYCLE_ALIASES = frozenset(
    {"cycle", "cycles", "cyclenumber", "fatiguecycle", "fatiguecycles"}
)
_MECHANICS_SIGNAL_ALIASES = frozenset(
    {
        "stress",
        "tensilestress",
        "compressivestress",
        "compressionstress",
        "flexuralstress",
        "bendingstress",
        "shearstress",
        "force",
        "load",
        "tensileforce",
        "compressionforce",
        "displacement",
        "extension",
        "elongation",
        "strain",
        "deflection",
        "energy",
        "work",
        "impactenergy",
        "modulus",
        "youngsmodulus",
        "elasticmodulus",
        "tensilemodulus",
        "flexuralmodulus",
        "compressivemodulus",
        "vendormodulus",
    }
)


@dataclass(frozen=True)
class _Table:
    frame: pd.DataFrame
    sheet_name: str | None
    sheet_index: int | None
    table_index: int
    header_row: int = 0
    data_rows: tuple[tuple[int, int], ...] = ()
    raw_headers: tuple[str, ...] = ()


@dataclass(frozen=True)
class _FlatSource:
    raw_headers: tuple[str, ...]
    header_row: int
    data_rows: tuple[tuple[int, int], ...]
    whitespace_comment_rows: tuple[int, ...]
    records: tuple[tuple[str, ...], ...] = ()
    metadata_preamble: bool = False


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
    observed_selections_by_table = {
        (table.sheet_index, table.table_index): (
            _observed_dma_selections(table)
            if normalized_technique == "DMA"
            else _observed_rheology_selections(table)
            if normalized_technique == "RHEOLOGY"
            else _observed_sec_selections(table)
            if normalized_technique == "SEC"
            else _observed_mechanics_selections(table)
            if normalized_technique == "MECHANICS"
            else _as_selection_tuple(_observed_selection(table, normalized_technique))
        )
        for table in tables
    }
    if mapping_proposal is not None and any(
        selections is not None and len(selections) > 1
        for selections in observed_selections_by_table.values()
    ):
        return _outcome(
            "needs_input",
            source_artifact_id,
            "conversion_mapping_proposal_invalid",
            observed_columns=observed_columns,
        )
    proposal_observed_by_table = {
        key: selections[0] if selections is not None and len(selections) == 1 else None
        for key, selections in observed_selections_by_table.items()
    }
    if mapping_proposal is not None and not _valid_proposal(
        mapping_proposal,
        tables=tables,
        observed_by_table=proposal_observed_by_table,
        technique=normalized_technique,
        source_artifact_id=source_artifact_id,
    ):
        return _outcome(
            "needs_input", source_artifact_id, "conversion_mapping_proposal_invalid", observed_columns=observed_columns
        )

    selected: list[tuple[_Table, MappingSelection]] = []
    proposal_by_table = (
        {(selection.sheet_index, selection.table_index): selection for selection in mapping_proposal.selections}
        if mapping_proposal is not None
        else {}
    )
    proposal_used = False
    for table in tables:
        observed = observed_selections_by_table[(table.sheet_index, table.table_index)]
        if observed:
            selected.extend((table, selection) for selection in observed)
            continue
        proposal_selection = proposal_by_table.get((table.sheet_index, table.table_index))
        if proposal_selection is None:
            return _outcome(
                "needs_input", source_artifact_id, "conversion_mapping_ambiguous", observed_columns=observed_columns
            )
        selected.append((table, proposal_selection))
        proposal_used = True

    measurements: list[Measurement] = []
    for table, selection in selected:
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
                family=(
                    "spectrum_1d" if normalized_technique in {"IR", "NMR"}
                    else "thermal_1d" if normalized_technique == "TGA"
                    else "viscoelastic_1d" if normalized_technique == "DMA"
                    else "rheological_1d" if normalized_technique == "RHEOLOGY"
                    else "chromatography_1d" if normalized_technique == "SEC"
                    else "mechanical_1d" if normalized_technique == "MECHANICS"
                    else "scattering_1d"
                ),
                role="raw_curve",
                channels={"x": tuple(pair[0] for pair in pairs), "intensity": tuple(pair[1] for pair in pairs)},
                units={"x": selection.x_unit, "intensity": selection.intensity_unit},
                source_locator=locator,
                acquisition_metadata=(
                    {"axis_kind": selection.x_kind, "signal_kind": "mass_or_weight"}
                    if normalized_technique == "TGA"
                    else _dma_acquisition_metadata(selection)
                    if normalized_technique == "DMA"
                    else _rheology_acquisition_metadata(selection)
                    if normalized_technique == "RHEOLOGY"
                    else _sec_acquisition_metadata(selection)
                    if normalized_technique == "SEC"
                    else _mechanics_acquisition_metadata(selection)
                    if normalized_technique == "MECHANICS"
                    else {} if normalized_technique == "IR"
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
        template_id=(
            "nmr.spectrum.v1" if normalized_technique == "NMR"
            else "spectrum_1d.v1" if normalized_technique == "IR"
            else "thermal_curve_1d.v1" if normalized_technique == "TGA"
            else "dma_curve_1d.v1" if normalized_technique == "DMA"
            else "rheology_curve_1d.v1" if normalized_technique == "RHEOLOGY"
            else "sec_chromatogram_1d.v1" if normalized_technique == "SEC"
            else "mechanics_curve_1d.v1" if normalized_technique == "MECHANICS"
            else "scattering_1d.v1"
        ),
        source_artifact_id=source_artifact_id,
        payload={
            "technique": normalized_technique,
            "measurement_family": (
                "thermal_1d" if normalized_technique == "TGA"
                else "viscoelastic_1d" if normalized_technique == "DMA"
                else "rheological_1d" if normalized_technique == "RHEOLOGY"
                else "chromatography_1d" if normalized_technique == "SEC"
                else "mechanical_1d" if normalized_technique == "MECHANICS"
                else "spectrum_1d" if normalized_technique in {"IR", "NMR"}
                else "scattering_1d"
            ),
        },
        conversion_record=record,
        measurements=measurements,
        mapping_proposal=mapping_proposal if proposal_used else None,
    )
    return ConversionOutcome(status="ready", record=record, template=template)


def _load_tables(path: Path, extension: str) -> tuple[_Table, ...]:
    if extension not in _WORKBOOK_EXTENSIONS:
        flat = _flat_source_records(path)
        if flat.metadata_preamble:
            frame = pd.DataFrame(flat.records, columns=flat.raw_headers)
        else:
            frame = _string_headers(
                pd.read_csv(
                    path,
                    sep=None,
                    engine="python",
                    comment="#",
                    skiprows=flat.whitespace_comment_rows,
                ),
                flat.raw_headers,
            )
        if len(frame) != len(flat.data_rows):
            raise ValueError("Flat source records cannot be mapped to pandas rows")
        return (_Table(frame, None, None, 0, flat.header_row, flat.data_rows, flat.raw_headers),)
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


def _flat_source_records(path: Path) -> _FlatSource:
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
    metadata = _metadata_preamble(parsed)
    if metadata is not None:
        raw_headers, header_row, data_start = metadata
        selected = parsed[data_start:]
        return _FlatSource(
            raw_headers=raw_headers,
            header_row=header_row,
            data_rows=tuple((start, end) for _, start, end in selected),
            whitespace_comment_rows=whitespace_comment_rows,
            records=tuple(tuple(_display_header(value) for value in row[: len(raw_headers)]) for row, _, _ in selected),
            metadata_preamble=True,
        )
    header, header_start, _ = parsed[0]
    data_rows = tuple((start, end) for _, start, end in parsed[1:])
    return _FlatSource(
        raw_headers=tuple(_display_header(value) for value in header),
        header_row=header_start,
        data_rows=data_rows,
        whitespace_comment_rows=whitespace_comment_rows,
    )


def _metadata_preamble(
    parsed: list[tuple[list[str], int, int]],
) -> tuple[tuple[str, str], int, int] | None:
    """Recognize vendor FTIR XLabel/YLabel rows before the numeric curve."""
    x_row: tuple[list[str], int, int] | None = None
    y_row: tuple[list[str], int, int] | None = None
    for row in parsed[: min(len(parsed), 12)]:
        if len(row[0]) < 2:
            continue
        key = _normalize_header(row[0][0])
        if key == "xlabel" and not _display_header(row[0][1]).strip() == "":
            x_row = row
        elif key == "ylabel" and not _display_header(row[0][1]).strip() == "":
            y_row = row
    if x_row is None or y_row is None:
        return None
    x_header = _display_header(x_row[0][1]).strip()
    intensity_header = _display_header(y_row[0][1]).strip()
    if not x_header or not intensity_header:
        return None
    metadata_end = max(parsed.index(x_row), parsed.index(y_row)) + 1
    data_start = next(
        (
            index
            for index, (row, _, _) in enumerate(parsed[metadata_end:], start=metadata_end)
            if len(row) >= 2 and _numeric_text(row[0]) and _numeric_text(row[1])
        ),
        None,
    )
    if data_start is None:
        return None
    return (x_header, intensity_header), min(x_row[1], y_row[1]), data_start


def _numeric_text(value: Any) -> bool:
    try:
        numeric = float(str(value).strip())
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric)


def _display_header(value: Any) -> str:
    return "" if pd.isna(value) else str(value)


def _fallback_delimiter(sample: str) -> str:
    first_line = sample.splitlines()[0] if sample else ""
    for delimiter in (",", "\t", ";", "|"):
        if delimiter in first_line:
            return delimiter
    return " "


def _raw_headers_ambiguous(table: _Table, technique: str) -> bool:
    headers = list(table.raw_headers)
    while headers and not headers[-1].strip():
        headers.pop()
    if any(not header.strip() for header in headers):
        return True
    if technique in {"DMA", "RHEOLOGY", "SEC", "MECHANICS"}:
        relevant: list[tuple[str, ...]] = []
        for header in headers:
            x_kind = _x_kind(header, technique)
            descriptor = (
                _dma_signal_descriptor(header)
                if technique == "DMA"
                else _rheology_signal_descriptor(header)
                if technique == "RHEOLOGY"
                else _sec_signal_descriptor(header)
                if technique == "SEC"
                else _mechanics_signal_descriptor(header)
            )
            if x_kind is not None:
                relevant.append(("axis", x_kind))
            elif descriptor is not None:
                relevant.append(("signal", *descriptor))
        if technique == "MECHANICS":
            signal_kinds = {
                item[1] for item in relevant if item[0] == "signal"
            }
            if "stress" in signal_kinds and any(
                kind.endswith("_stress") for kind in signal_kinds
            ):
                return True
        return len(relevant) != len(set(relevant))
    relevant = [
        (_normalize_header(header),)
        for header in headers
        if _x_kind(header, technique) is not None or _is_intensity_header(header, technique)
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
        if selection.intensity_unit != _intensity_unit(selection.intensity_column, technique):
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
        str(header) for header in table.frame.columns if _is_intensity_header(str(header), technique)
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
        intensity_unit=_intensity_unit(intensity_column, technique),
        source="observed",
    )


def _as_selection_tuple(
    selection: MappingSelection | None,
) -> tuple[MappingSelection, ...] | None:
    return None if selection is None else (selection,)


def _observed_dma_selections(table: _Table) -> tuple[MappingSelection, ...] | None:
    x_candidates = [
        (str(header), _x_kind(str(header), "DMA"))
        for header in table.frame.columns
        if _x_kind(str(header), "DMA") is not None
    ]
    signal_candidates = [
        (str(header), _dma_signal_descriptor(str(header)))
        for header in table.frame.columns
        if _dma_signal_descriptor(str(header)) is not None
    ]
    if len(x_candidates) != 1 or not signal_candidates:
        return None
    descriptors = [descriptor for _, descriptor in signal_candidates]
    if len(descriptors) != len(set(descriptors)):
        return None
    x_column, x_kind = x_candidates[0]
    if x_column in {header for header, _ in signal_candidates}:
        return None
    start, end = _table_row_range(table)
    multi_signal = len(signal_candidates) > 1
    selections: list[MappingSelection] = []
    for intensity_column, descriptor in signal_candidates:
        if descriptor is None:
            continue
        signal_kind, modulus_basis = descriptor
        measurement_id = _measurement_id(table)
        if multi_signal:
            measurement_id += (
                f"-signal-{signal_kind.replace('_', '-')}-{modulus_basis}"
            )
        selections.append(
            MappingSelection(
                measurement_id=measurement_id,
                sheet_name=table.sheet_name,
                sheet_index=table.sheet_index,
                table_index=table.table_index,
                header_row=table.header_row,
                data_row_start=start,
                data_row_end=end,
                x_column=x_column,
                intensity_column=intensity_column,
                x_kind=str(x_kind),
                x_unit=_x_unit(x_column, str(x_kind)),
                intensity_unit=_intensity_unit(intensity_column, "DMA"),
                source="observed",
            )
        )
    return tuple(selections)


def _observed_rheology_selections(table: _Table) -> tuple[MappingSelection, ...] | None:
    x_candidates = [
        (str(header), _x_kind(str(header), "RHEOLOGY"))
        for header in table.frame.columns
        if _x_kind(str(header), "RHEOLOGY") is not None
    ]
    signal_candidates = [
        (str(header), _rheology_signal_descriptor(str(header)))
        for header in table.frame.columns
        if _rheology_signal_descriptor(str(header)) is not None
    ]
    if len(x_candidates) != 1 or not signal_candidates:
        return None
    descriptors = [descriptor for _, descriptor in signal_candidates]
    if len(descriptors) != len(set(descriptors)):
        return None
    x_column, x_kind = x_candidates[0]
    if x_column in {header for header, _ in signal_candidates}:
        return None
    start, end = _table_row_range(table)
    multi_signal = len(signal_candidates) > 1
    selections: list[MappingSelection] = []
    for intensity_column, descriptor in signal_candidates:
        if descriptor is None:
            continue
        signal_kind, signal_basis = descriptor
        measurement_id = _measurement_id(table)
        if multi_signal:
            measurement_id += (
                f"-signal-{signal_kind.replace('_', '-')}-{signal_basis}"
            )
        selections.append(
            MappingSelection(
                measurement_id=measurement_id,
                sheet_name=table.sheet_name,
                sheet_index=table.sheet_index,
                table_index=table.table_index,
                header_row=table.header_row,
                data_row_start=start,
                data_row_end=end,
                x_column=x_column,
                intensity_column=intensity_column,
                x_kind=str(x_kind),
                x_unit=_x_unit(x_column, str(x_kind)),
                intensity_unit=_intensity_unit(intensity_column, "RHEOLOGY"),
                source="observed",
            )
        )
    return tuple(selections)


def _observed_sec_selections(table: _Table) -> tuple[MappingSelection, ...] | None:
    x_candidates = [
        (str(header), _x_kind(str(header), "SEC"))
        for header in table.frame.columns
        if _x_kind(str(header), "SEC") is not None
    ]
    signal_candidates = [
        (str(header), _sec_signal_descriptor(str(header)))
        for header in table.frame.columns
        if _sec_signal_descriptor(str(header)) is not None
    ]
    if len(x_candidates) != 1 or not signal_candidates:
        return None
    descriptors = [descriptor for _, descriptor in signal_candidates]
    if len(descriptors) != len(set(descriptors)):
        return None
    x_column, x_kind = x_candidates[0]
    if x_column in {header for header, _ in signal_candidates}:
        return None
    start, end = _table_row_range(table)
    multi_signal = len(signal_candidates) > 1
    selections: list[MappingSelection] = []
    for intensity_column, descriptor in signal_candidates:
        if descriptor is None:
            continue
        signal_kind, detector_kind = descriptor
        measurement_id = _measurement_id(table)
        if multi_signal:
            measurement_id += (
                f"-signal-{signal_kind.replace('_', '-')}-{detector_kind}"
            )
        selections.append(
            MappingSelection(
                measurement_id=measurement_id,
                sheet_name=table.sheet_name,
                sheet_index=table.sheet_index,
                table_index=table.table_index,
                header_row=table.header_row,
                data_row_start=start,
                data_row_end=end,
                x_column=x_column,
                intensity_column=intensity_column,
                x_kind=str(x_kind),
                x_unit=_x_unit(x_column, str(x_kind)),
                intensity_unit=_intensity_unit(intensity_column, "SEC"),
                source="observed",
            )
        )
    return tuple(selections)


def _observed_mechanics_selections(
    table: _Table,
) -> tuple[MappingSelection, ...] | None:
    x_candidates = [
        (str(header), _x_kind(str(header), "MECHANICS"))
        for header in table.frame.columns
        if _x_kind(str(header), "MECHANICS") is not None
    ]
    if len(x_candidates) != 1:
        return None
    x_column, x_kind = x_candidates[0]
    signal_candidates = [
        (str(header), _mechanics_signal_descriptor(str(header)))
        for header in table.frame.columns
        if str(header) != x_column
        and _mechanics_signal_descriptor(str(header)) is not None
    ]
    if not signal_candidates:
        return None
    descriptors = [descriptor for _, descriptor in signal_candidates]
    if len(descriptors) != len(set(descriptors)):
        return None
    signal_kinds = {descriptor[0] for descriptor in descriptors if descriptor is not None}
    if "stress" in signal_kinds and any(kind.endswith("_stress") for kind in signal_kinds):
        return None
    start, end = _table_row_range(table)
    multi_signal = len(signal_candidates) > 1
    selections: list[MappingSelection] = []
    for intensity_column, descriptor in signal_candidates:
        if descriptor is None:
            continue
        signal_kind, test_mode = descriptor
        measurement_id = _measurement_id(table)
        if multi_signal:
            measurement_id += (
                f"-signal-{signal_kind.replace('_', '-')}-{test_mode}"
            )
        selections.append(
            MappingSelection(
                measurement_id=measurement_id,
                sheet_name=table.sheet_name,
                sheet_index=table.sheet_index,
                table_index=table.table_index,
                header_row=table.header_row,
                data_row_start=start,
                data_row_end=end,
                x_column=x_column,
                intensity_column=intensity_column,
                x_kind=str(x_kind),
                x_unit=_x_unit(x_column, str(x_kind)),
                intensity_unit=_intensity_unit(intensity_column, "MECHANICS"),
                source="observed",
            )
        )
    return tuple(selections)


def _dma_acquisition_metadata(selection: MappingSelection) -> dict[str, str]:
    descriptor = _dma_signal_descriptor(selection.intensity_column)
    signal_kind, modulus_basis = descriptor or ("viscoelastic_signal", "unspecified")
    return {
        "axis_kind": selection.x_kind,
        "signal_kind": signal_kind,
        "modulus_basis": modulus_basis,
        "source_table_id": (
            f"sheet-{selection.sheet_index if selection.sheet_index is not None else 0}"
            f"-table-{selection.table_index}"
        ),
    }


def _rheology_acquisition_metadata(selection: MappingSelection) -> dict[str, str]:
    descriptor = _rheology_signal_descriptor(selection.intensity_column)
    signal_kind, modulus_basis = descriptor or ("rheology_signal", "unspecified")
    return {
        "axis_kind": selection.x_kind,
        "signal_kind": signal_kind,
        "modulus_basis": modulus_basis,
        "source_table_id": (
            f"sheet-{selection.sheet_index if selection.sheet_index is not None else 0}"
            f"-table-{selection.table_index}"
        ),
    }


def _sec_acquisition_metadata(selection: MappingSelection) -> dict[str, str]:
    descriptor = _sec_signal_descriptor(selection.intensity_column)
    signal_kind, detector_kind = descriptor or ("chromatogram_signal", "unknown")
    return {
        "axis_kind": selection.x_kind,
        "signal_kind": signal_kind,
        "detector_kind": detector_kind,
        "source_table_id": (
            f"sheet-{selection.sheet_index if selection.sheet_index is not None else 0}"
            f"-table-{selection.table_index}"
        ),
    }


def _mechanics_acquisition_metadata(selection: MappingSelection) -> dict[str, str]:
    descriptor = _mechanics_signal_descriptor(selection.intensity_column)
    signal_kind, test_mode = descriptor or ("mechanics_signal", "unspecified")
    return {
        "axis_kind": selection.x_kind,
        "signal_kind": signal_kind,
        "test_mode": test_mode,
        "source_table_id": (
            f"sheet-{selection.sheet_index if selection.sheet_index is not None else 0}"
            f"-table-{selection.table_index}"
        ),
    }


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
    if technique == "NMR":
        without_ppm_unit = _normalize_header(
            re.sub(r"(?:ppm|chemical\s*shift)", "", header.casefold())
        )
        return "chemical_shift" if {normalized, without_ppm_unit}.intersection(_NMR_X_ALIASES) else None
    if technique == "SEC":
        without_unit = _normalize_header(
            re.sub(
                r"(?:milliseconds?|ms|minutes?|min|seconds?|secs?|sec|s|"
                r"microliters?|milliliters?|liters?|[µμu]l|ml|l)\b",
                "",
                header.casefold(),
            )
        )
        if normalized in _SEC_VOLUME_ALIASES or without_unit in _SEC_VOLUME_ALIASES:
            return "elution_volume"
        if normalized in _SEC_TIME_ALIASES or without_unit in _SEC_TIME_ALIASES:
            return "retention_time"
    if technique == "MECHANICS":
        without_time_unit = _normalize_header(
            re.sub(
                r"(?:milliseconds?|ms|minutes?|min|seconds?|secs?|sec|s)\b",
                "",
                header.casefold(),
            )
        )
        without_length_unit = _normalize_header(
            re.sub(
                r"(?:micrometers?|[µμu]m|millimeters?|mm|centimeters?|cm|meters?|m)\b",
                "",
                header.casefold(),
            )
        )
        without_strain_unit = _normalize_header(
            re.sub(r"(?:%|percent)", "", header.casefold())
        )
        if normalized in _MECHANICS_TIME_ALIASES or without_time_unit in _MECHANICS_TIME_ALIASES:
            return "time"
        if normalized in _MECHANICS_DEFLECTION_ALIASES or without_length_unit in _MECHANICS_DEFLECTION_ALIASES:
            return "deflection"
        if normalized in _MECHANICS_DISPLACEMENT_ALIASES or without_length_unit in _MECHANICS_DISPLACEMENT_ALIASES:
            return "displacement"
        if normalized in _MECHANICS_STRAIN_ALIASES or without_strain_unit in _MECHANICS_STRAIN_ALIASES:
            return "strain"
        if normalized in _MECHANICS_CYCLE_ALIASES:
            return "cycle"
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
    if technique == "DMA":
        without_frequency_unit = _normalize_header(
            re.sub(r"(?:hz|khz|mhz|rad\s*/\s*s|rad\s*s\^-?1)", "", header.casefold())
        )
        without_temperature_unit = _normalize_header(
            re.sub(r"(?:°\s*[cfk]|degrees?\s*[cfk]|deg\s*[cfk]|\b[cfk]\b)", "", header.casefold())
        )
        without_time_unit = _normalize_header(
            re.sub(r"(?:milliseconds?|ms|minutes?|min|seconds?|secs?|sec|s)\b", "", header.casefold())
        )
        if normalized in _DMA_FREQUENCY_ALIASES or without_frequency_unit in _DMA_FREQUENCY_ALIASES:
            return "frequency"
        if normalized in _DMA_TEMPERATURE_ALIASES or without_temperature_unit in _DMA_TEMPERATURE_ALIASES:
            return "temperature"
        if normalized in _DMA_TIME_ALIASES or without_time_unit in _DMA_TIME_ALIASES:
            return "time"
    if technique == "RHEOLOGY":
        rheology_header = (
            header.casefold()
            .replace("γ", "gamma")
            .replace("\u0307", "dot")
            .replace("˙", "dot")
            .replace("ω", "omega")
        )
        normalized = _normalize_header(rheology_header)
        without_rate_unit = _normalize_header(
            re.sub(
                r"(?:1\s*/\s*s|/\s*s|s\s*(?:\^?\s*-\s*1|⁻¹))",
                "",
                rheology_header,
            )
        )
        without_frequency_unit = _normalize_header(
            re.sub(r"(?:hz|khz)", "", rheology_header)
        )
        without_angular_unit = _normalize_header(
            re.sub(r"(?:rad\s*/\s*s|rad\s*s\^-?1)", "", rheology_header)
        )
        has_angular_frequency_unit = bool(
            re.search(r"(?:rad\s*/\s*s|rad\s*s\^-?1)", rheology_header)
        )
        without_temperature_unit = _normalize_header(
            re.sub(
                r"(?:°\s*[cfk]|degrees?\s*[cfk]|deg\s*[cfk]|\b[cfk]\b)",
                "",
                rheology_header,
            )
        )
        without_time_unit = _normalize_header(
            re.sub(
                r"(?:milliseconds?|ms|minutes?|min|seconds?|secs?|sec|s)\b",
                "",
                rheology_header,
            )
        )
        without_strain_unit = _normalize_header(
            re.sub(r"(?:%|percent)", "", rheology_header)
        )
        if normalized in _RHEOLOGY_SHEAR_RATE_ALIASES or without_rate_unit in _RHEOLOGY_SHEAR_RATE_ALIASES:
            return "shear_rate"
        if (
            normalized in _RHEOLOGY_ANGULAR_FREQUENCY_ALIASES
            or without_angular_unit in _RHEOLOGY_ANGULAR_FREQUENCY_ALIASES
            or (
                has_angular_frequency_unit
                and without_angular_unit in _RHEOLOGY_FREQUENCY_ALIASES
            )
        ):
            return "angular_frequency"
        if normalized in _RHEOLOGY_FREQUENCY_ALIASES or without_frequency_unit in _RHEOLOGY_FREQUENCY_ALIASES:
            return "frequency"
        if normalized in _RHEOLOGY_TEMPERATURE_ALIASES or without_temperature_unit in _RHEOLOGY_TEMPERATURE_ALIASES:
            return "temperature"
        if normalized in _RHEOLOGY_TIME_ALIASES or without_time_unit in _RHEOLOGY_TIME_ALIASES:
            return "time"
        if normalized in _RHEOLOGY_STRAIN_ALIASES or without_strain_unit in _RHEOLOGY_STRAIN_ALIASES:
            return "strain"
    if technique == "TGA":
        without_temperature_unit = _normalize_header(
            re.sub(r"(?:°\s*[cfk]|degrees?\s*[cfk]|deg\s*[cfk]|\b[cfk]\b)", "", header.casefold())
        )
        without_time_unit = _normalize_header(
            re.sub(r"(?:milliseconds?|ms|minutes?|min|seconds?|secs?|sec|s)\b", "", header.casefold())
        )
        if normalized in _TGA_TEMPERATURE_ALIASES or without_temperature_unit in _TGA_TEMPERATURE_ALIASES:
            return "temperature"
        if normalized in _TGA_TIME_ALIASES or without_time_unit in _TGA_TIME_ALIASES:
            return "time"
    return None


def _is_intensity_header(header: str, technique: str | None = None) -> bool:
    if str(technique or "").upper() == "DMA":
        return _dma_signal_descriptor(header) is not None
    if str(technique or "").upper() == "TGA":
        return _tga_mass_alias(header) in _TGA_MASS_ALIASES
    if str(technique or "").upper() == "RHEOLOGY":
        return _rheology_signal_descriptor(header) is not None
    if str(technique or "").upper() == "SEC":
        return _sec_signal_descriptor(header) is not None
    if str(technique or "").upper() == "MECHANICS":
        return _mechanics_signal_descriptor(header) is not None
    return _intensity_alias(header) in _INTENSITY_ALIASES


def _intensity_alias(header: str) -> str:
    normalized = _normalize_header(header)
    if normalized in _INTENSITY_ALIASES:
        return normalized
    without_unit_suffix = re.sub(
        r"\s*[\(\[]?\s*(?:counts|cps|a\s*\.\s*u\s*\.)\s*[\)\]]?\s*$", "", header.casefold()
    )
    return _normalize_header(without_unit_suffix)


def _tga_mass_alias(header: str) -> str:
    """Normalize common mass/weight labels without interpreting chemistry."""
    text = header.casefold().replace("%", " percent ")
    text = re.sub(r"\bwt\.?\b", "weight", text)
    normalized = _normalize_header(text)
    return normalized.replace("weightweight", "weight")


def _dma_signal_alias(header: str) -> str:
    """Normalize common DMA signal labels without assigning a model."""
    text = re.sub(r"\([^)]*\)|\[[^]]*\]", "", header.casefold())
    text = text.replace("δ", "delta")
    text = text.replace("″", "doubleprime").replace("′", "prime")
    text = text.replace("''", "doubleprime").replace('"', "doubleprime")
    text = text.replace("'", "prime")
    text = re.sub(r"\b(storage|loss)\s+modulus\b", lambda match: match.group(1) + "modulus", text)
    text = re.sub(r"\btan\s*delta\b", "tandelta", text)
    normalized = _normalize_header(text)
    for alias in sorted(_DMA_SIGNAL_ALIASES, key=len, reverse=True):
        if normalized == alias or normalized.startswith(alias):
            return alias
    return normalized


def _dma_signal_descriptor(header: str) -> tuple[str, str] | None:
    alias = _dma_signal_alias(header)
    descriptors = {
        "eprime": ("storage_modulus", "tensile"),
        "edoubleprime": ("loss_modulus", "tensile"),
        "gprime": ("storage_modulus", "shear"),
        "gdoubleprime": ("loss_modulus", "shear"),
        "storagemodulus": ("storage_modulus", "unspecified"),
        "lossmodulus": ("loss_modulus", "unspecified"),
        "complexmodulus": ("complex_modulus", "unspecified"),
        "youngsmodulus": ("youngs_modulus", "tensile"),
        "modulus": ("modulus", "unspecified"),
        "tandelta": ("tan_delta", "unspecified"),
        "tangentdelta": ("tan_delta", "unspecified"),
        "damping": ("damping", "unspecified"),
        "stress": ("stress", "unspecified"),
        "strain": ("strain", "unspecified"),
        "displacement": ("displacement", "unspecified"),
        "force": ("force", "unspecified"),
    }
    return descriptors.get(alias)


def _rheology_signal_alias(header: str) -> str:
    """Normalize common rheometer response labels without fitting semantics."""
    text = re.sub(r"\([^)]*\)|\[[^]]*\]", "", header.casefold())
    text = text.replace("δ", "delta").replace("τ", "shearstress")
    text = text.replace("η*", "complexviscosity").replace("eta*", "complexviscosity")
    text = text.replace("η", "viscosity")
    text = text.replace("″", "doubleprime").replace("′", "prime")
    text = text.replace("''", "doubleprime").replace('"', "doubleprime")
    text = text.replace("'", "prime")
    text = re.sub(r"\b(storage|loss)\s+modulus\b", lambda match: match.group(1) + "modulus", text)
    text = re.sub(r"\b(complex|dynamic|apparent)\s+viscosity\b", lambda match: match.group(1) + "viscosity", text)
    text = re.sub(r"\b(shear|normal)\s+(stress|force)\b", lambda match: match.group(1) + match.group(2), text)
    text = re.sub(r"\btan\s*delta\b", "tandelta", text)
    normalized = _normalize_header(text)
    for alias in sorted(_RHEOLOGY_SIGNAL_ALIASES, key=len, reverse=True):
        if normalized == alias or normalized.startswith(alias):
            return alias
    return normalized


def _rheology_signal_descriptor(header: str) -> tuple[str, str] | None:
    alias = _rheology_signal_alias(header)
    descriptors = {
        "shearstress": ("shear_stress", "unspecified"),
        "stress": ("shear_stress", "unspecified"),
        "viscosity": ("viscosity", "unspecified"),
        "dynamicviscosity": ("viscosity", "unspecified"),
        "apparentviscosity": ("viscosity", "unspecified"),
        "complexviscosity": ("complex_viscosity", "unspecified"),
        "etastar": ("complex_viscosity", "unspecified"),
        "storagemodulus": ("storage_modulus", "shear"),
        "lossmodulus": ("loss_modulus", "shear"),
        "gprime": ("storage_modulus", "shear"),
        "gdoubleprime": ("loss_modulus", "shear"),
        "tandelta": ("tan_delta", "unspecified"),
        "tangentdelta": ("tan_delta", "unspecified"),
        "normalstress": ("normal_stress", "unspecified"),
        "normalforce": ("normal_force", "unspecified"),
        "torque": ("torque", "unspecified"),
    }
    return descriptors.get(alias)


def _sec_signal_descriptor(header: str) -> tuple[str, str] | None:
    """Return only explicit SEC detector or vendor-distribution semantics."""
    text = header.casefold().replace("δ", "delta").replace("Δ", "delta")
    without_units = re.sub(r"\([^)]*\)|\[[^]]*\]", "", text)
    normalized = _normalize_header(without_units)

    distribution_kind: str | None = None
    if any(token in normalized for token in ("dwdlogm", "dwdm", "differentialweight")):
        distribution_kind = "differential_weight_distribution"
    elif any(token in normalized for token in ("dndlogm", "dndm", "differentialnumber")):
        distribution_kind = "differential_number_distribution"
    elif "differential" in normalized and "distribution" in normalized:
        distribution_kind = "differential_distribution"
    elif any(token in normalized for token in ("cumulativeweight", "cumweight")):
        distribution_kind = "cumulative_weight_distribution"
    elif any(token in normalized for token in ("cumulativenumber", "cumnumber")):
        distribution_kind = "cumulative_number_distribution"
    elif "cumulative" in normalized and "distribution" in normalized:
        distribution_kind = "cumulative_distribution"
    if distribution_kind is not None:
        return distribution_kind, "vendor_derived"

    if normalized in {"logm", "logmolarmass", "logmolecularweight", "logmw"}:
        return "log_molar_mass", "vendor_derived"
    if normalized in {
        "m",
        "mw",
        "molarmass",
        "molecularweight",
        "molecularmass",
    }:
        return "molar_mass", "vendor_derived"
    if normalized in {"ri", "dri", "ridetector", "refractiveindex", "refractiveindexresponse"}:
        return "refractive_index_response", "ri"
    if normalized in {"uv", "uvdetector", "uvresponse", "absorbance"}:
        return "uv_response", "uv"
    for detector in ("mals", "rals", "lals"):
        if normalized == detector or normalized.startswith(detector):
            return "light_scattering_response", detector
    if normalized in {"lightscattering", "lightscatteringresponse", "ls"}:
        return "light_scattering_response", "light_scattering"
    if normalized in {
        "viscometer",
        "viscometerresponse",
        "viscositydetector",
        "differentialpressure",
        "deltap",
        "dp",
    }:
        return "viscometer_response", "viscometer"
    if normalized in {"concentration", "concentrationresponse"}:
        return "concentration_response", "concentration"
    return None


def _mechanics_signal_descriptor(header: str) -> tuple[str, str] | None:
    """Return explicit mechanics response semantics without fitting a model."""
    text = re.sub(r"\([^)]*\)|\[[^]]*\]", "", header.casefold())
    text = text.replace("young's", "youngs")
    text = re.sub(r"\bcompression\b", "compressive", text)
    text = re.sub(r"\bbending\b", "flexural", text)
    normalized = _normalize_header(text)
    alias = next(
        (
            candidate
            for candidate in sorted(_MECHANICS_SIGNAL_ALIASES, key=len, reverse=True)
            if normalized == candidate or normalized.startswith(candidate)
        ),
        None,
    )
    if alias is None:
        return None

    test_mode = "unspecified"
    for marker, mode in (
        ("tensile", "tensile"),
        ("compressive", "compression"),
        ("flexural", "flexural"),
        ("impact", "impact"),
        ("fatigue", "fatigue"),
        ("cyclic", "fatigue"),
        ("creep", "creep"),
        ("shear", "shear"),
    ):
        if marker in normalized:
            test_mode = mode
            break

    if alias in {"tensilestress", "compressivestress", "flexuralstress", "shearstress"}:
        return {
            "tensilestress": ("tensile_stress", "tensile"),
            "compressivestress": ("compressive_stress", "compression"),
            "flexuralstress": ("flexural_stress", "flexural"),
            "shearstress": ("shear_stress", "shear"),
        }[alias]
    if alias in {"youngsmodulus", "tensilemodulus"}:
        return "tensile_modulus", "tensile"
    if alias == "flexuralmodulus":
        return "flexural_modulus", "flexural"
    if alias == "compressivemodulus":
        return "compressive_modulus", "compression"
    if alias in {"modulus", "elasticmodulus", "vendormodulus"}:
        return "vendor_modulus", "vendor_derived"
    if alias in {"force", "tensileforce", "compressionforce"}:
        return "force", test_mode
    if alias == "load":
        return "load", test_mode
    if alias in {"displacement", "extension", "elongation"}:
        return alias, test_mode
    if alias == "strain":
        return "strain", test_mode
    if alias == "deflection":
        return "deflection", test_mode
    if alias in {"energy", "impactenergy"}:
        return "energy", "impact" if alias == "impactenergy" else test_mode
    if alias == "work":
        return "work", test_mode
    return "stress", test_mode


def _kind_allowed(x_kind: str, technique: str) -> bool:
    return (technique == "IR" and x_kind == "wavenumber") or (
        technique == "NMR" and x_kind == "chemical_shift"
    ) or (
        technique in {"SAXS", "WAXS"} and x_kind in {"q", "two_theta"}
    ) or (
        technique == "TGA" and x_kind in {"temperature", "time"}
    ) or (
        technique == "DMA" and x_kind in {"frequency", "temperature", "time"}
    ) or (
        technique == "RHEOLOGY"
        and x_kind in {"shear_rate", "frequency", "angular_frequency", "temperature", "time", "strain"}
    ) or (
        technique == "SEC" and x_kind in {"retention_time", "elution_volume"}
    ) or (
        technique == "MECHANICS"
        and x_kind in {"time", "displacement", "strain", "deflection", "cycle"}
    )


def _x_unit(header: str, x_kind: str) -> str:
    text = header.casefold()
    if x_kind == "chemical_shift" and re.search(r"ppm|chemical\s*shift", text):
        return "ppm"
    if x_kind == "wavenumber" and re.search(r"(?:cm\s*(?:\^?\s*-\s*1|⁻¹)|1\s*/\s*cm)", text):
        return "cm^-1"
    if x_kind == "q" and re.search(r"nm\s*(?:\^?\s*-\s*1|⁻¹)", text):
        return "nm^-1"
    if x_kind == "q" and re.search(r"(?:a|å|angstrom)\s*(?:\^?\s*-\s*1|⁻¹)", text):
        return "angstrom^-1"
    if x_kind == "two_theta" and re.search(r"(?:degrees?|deg|°)", text):
        return "deg"
    if x_kind == "temperature":
        if re.search(r"(?:°\s*c|degrees?\s*c|deg\s*c|\bc\b)", text):
            return "°C"
        if re.search(r"(?:°\s*k|degrees?\s*k|deg\s*k|\bk\b)", text):
            return "K"
        if re.search(r"(?:°\s*f|degrees?\s*f|deg\s*f|\bf\b)", text):
            return "°F"
    if x_kind == "time":
        if re.search(r"(?:milliseconds?|\bms\b)", text):
            return "ms"
        if re.search(r"(?:minutes?|\bmin\b)", text):
            return "min"
        if re.search(r"(?:seconds?|\bsecs?\b|\bs\b)", text):
            return "s"
    if x_kind == "retention_time":
        if re.search(r"(?:milliseconds?|\bms\b)", text):
            return "ms"
        if re.search(r"(?:minutes?|\bmin\b)", text):
            return "min"
        if re.search(r"(?:seconds?|\bsecs?\b|\bs\b)", text):
            return "s"
    if x_kind == "elution_volume":
        if re.search(r"(?:microliters?|[µμu]l)\b", text):
            return "uL"
        if re.search(r"(?:milliliters?|\bml\b)", text):
            return "mL"
        if re.search(r"(?:liters?|\bl\b)", text):
            return "L"
    if x_kind == "frequency":
        if re.search(r"(?:rad\s*/\s*s|rad\s*s\^-?1)", text):
            return "rad/s"
        if re.search(r"(?:\bkhz\b)", text):
            return "kHz"
        if re.search(r"(?:\bmhz\b)", text):
            return "MHz"
        if re.search(r"(?:\bhz\b)", text):
            return "Hz"
    if x_kind == "angular_frequency" and re.search(r"(?:rad\s*/\s*s|rad\s*s\^-?1)", text):
        return "rad/s"
    if x_kind == "shear_rate" and re.search(
        r"(?:1\s*/\s*s|/\s*s|s\s*(?:\^?\s*-\s*1|⁻¹))",
        text,
    ):
        return "s^-1"
    if x_kind == "strain" and ("%" in text or "percent" in text):
        return "%"
    if x_kind in {"displacement", "deflection"}:
        if re.search(r"(?:micrometers?|[µμu]m)\b", text):
            return "um"
        if re.search(r"(?:millimeters?|\bmm\b)", text):
            return "mm"
        if re.search(r"(?:centimeters?|\bcm\b)", text):
            return "cm"
        if re.search(r"(?:meters?|\bm\b)", text):
            return "m"
    if x_kind == "cycle":
        return "cycle"
    return "unknown"


def _intensity_unit(header: str, technique: str | None = None) -> str:
    text = header.casefold()
    if str(technique or "").upper() == "TGA":
        if "%" in text or re.search(r"(?:percent|pct|wt\.?\s*%)", text):
            return "%"
        if re.search(r"(?:\bmg\b|milligrams?)", text):
            return "mg"
        if re.search(r"(?:\b(?:μ|µ|u)g\b|micrograms?)", text):
            return "µg"
        if re.search(r"(?:\bg\b|grams?)", text):
            return "g"
        return "unknown"
    if str(technique or "").upper() == "DMA":
        descriptor = _dma_signal_descriptor(header)
        if descriptor is not None and descriptor[0] == "tan_delta":
            return "%" if "%" in text or "percent" in text else "1"
        if re.search(r"(?:gpa)", text):
            return "GPa"
        if re.search(r"(?:mpa)", text):
            return "MPa"
        if re.search(r"(?:kpa)", text):
            return "kPa"
        if re.search(r"(?:\bpa\b|pascal)", text):
            return "Pa"
        if "%" in text or "percent" in text:
            return "%"
        if re.search(r"(?:\b(?:n|mn)\b|newton)", text):
            return "N"
        if re.search(r"(?:\bmm\b|millimeters?)", text):
            return "mm"
        return "unknown"
    if str(technique or "").upper() == "RHEOLOGY":
        return _rheology_intensity_unit(header)
    if str(technique or "").upper() == "SEC":
        return _sec_intensity_unit(header)
    if str(technique or "").upper() == "MECHANICS":
        return _mechanics_intensity_unit(header)
    if re.search(r"a\s*\.\s*u\s*\.", text):
        return "a.u."
    for unit in ("absorbance", "transmittance", "counts", "cps"):
        if re.search(rf"\b{re.escape(unit)}\b", text):
            return unit
    return "unknown"


def _rheology_intensity_unit(header: str) -> str:
    descriptor = _rheology_signal_descriptor(header)
    signal_kind = descriptor[0] if descriptor is not None else "unknown"
    text = header.casefold()
    if signal_kind == "tan_delta":
        return "%" if "%" in text or "percent" in text else "1"
    if signal_kind in {"viscosity", "complex_viscosity"}:
        if re.search(r"\bcp\b|centipoise", text):
            return "cP"
        for token, unit in (
            (r"\bmPa\s*(?:[·.*-]|\s)\s*s\b", "mPa*s"),
            (r"\bkPa\s*(?:[·.*-]|\s)\s*s\b", "kPa*s"),
            (r"\bMPa\s*(?:[·.*-]|\s)\s*s\b", "MPa*s"),
            (r"\bPa\s*(?:[·.*-]|\s)\s*s\b", "Pa*s"),
        ):
            if re.search(token, header):
                return unit
        return "unknown"
    if signal_kind in {"storage_modulus", "loss_modulus", "shear_stress", "normal_stress"}:
        if re.search(r"(?:gpa)", text):
            return "GPa"
        if re.search(r"(?:mpa)", text):
            return "MPa"
        if re.search(r"(?:kpa)", text):
            return "kPa"
        if re.search(r"(?:\bpa\b|pascal)", text):
            return "Pa"
        return "unknown"
    if signal_kind == "normal_force":
        if re.search(r"\bmn\b", text):
            return "mN"
        if re.search(r"\bn\b|newton", text):
            return "N"
    if signal_kind == "torque":
        if re.search(r"\bmn\s*(?:[·.*-]|\s)\s*m\b", text):
            return "mN*m"
        if re.search(r"\bn\s*(?:[·.*-]|\s)\s*m\b", text):
            return "N*m"
    return "unknown"


def _sec_intensity_unit(header: str) -> str:
    descriptor = _sec_signal_descriptor(header)
    signal_kind = descriptor[0] if descriptor is not None else "unknown"
    text = header.casefold()
    if signal_kind == "log_molar_mass":
        return "log10(g/mol)"
    if signal_kind == "molar_mass":
        if re.search(r"\bkg\s*/\s*mol\b", text):
            return "kg/mol"
        if re.search(r"\b(?:kda|kilodaltons?)\b", text):
            return "kDa"
        if re.search(r"\b(?:da|daltons?)\b", text):
            return "Da"
        if re.search(r"\bg\s*/\s*mol\b", text):
            return "g/mol"
    if signal_kind == "concentration_response":
        for pattern, unit in (
            (r"\bmg\s*/\s*ml\b", "mg/mL"),
            (r"\bg\s*/\s*l\b", "g/L"),
            (r"\bmg\s*/\s*l\b", "mg/L"),
        ):
            if re.search(pattern, text):
                return unit
    if "%" in text or "percent" in text:
        return "%"
    if re.search(r"\bmau\b", text):
        return "mAU"
    if re.search(r"\bau\b", text):
        return "AU"
    if re.search(r"\bmv\b", text):
        return "mV"
    if re.search(r"(?:µ|μ|u)V\b", header):
        return "uV"
    if re.search(r"\bv\b", text):
        return "V"
    if re.search(r"\bkpa\b", text):
        return "kPa"
    if re.search(r"\bpa\b", text):
        return "Pa"
    return "unknown"


def _mechanics_intensity_unit(header: str) -> str:
    descriptor = _mechanics_signal_descriptor(header)
    signal_kind = descriptor[0] if descriptor is not None else "unknown"
    text = header.casefold()
    if signal_kind in {
        "stress",
        "tensile_stress",
        "compressive_stress",
        "flexural_stress",
        "shear_stress",
        "vendor_modulus",
        "tensile_modulus",
        "flexural_modulus",
        "compressive_modulus",
    }:
        for pattern, unit in (
            (r"\bgpa\b", "GPa"),
            (r"\bmpa\b", "MPa"),
            (r"\bkpa\b", "kPa"),
            (r"\bpa\b|pascal", "Pa"),
        ):
            if re.search(pattern, text):
                return unit
    if signal_kind in {"force", "load"}:
        for pattern, unit in (
            (r"\bkn\b", "kN"),
            (r"\bmn\b", "mN"),
            (r"\bn\b|newton", "N"),
        ):
            if re.search(pattern, text):
                return unit
    if signal_kind == "strain" and ("%" in text or "percent" in text):
        return "%"
    if signal_kind in {"displacement", "extension", "elongation", "deflection"}:
        for pattern, unit in (
            (r"(?:micrometers?|[µμu]m)\b", "um"),
            (r"(?:millimeters?|\bmm\b)", "mm"),
            (r"(?:centimeters?|\bcm\b)", "cm"),
            (r"(?:meters?|\bm\b)", "m"),
        ):
            if re.search(pattern, text):
                return unit
    if signal_kind in {"energy", "work"}:
        if re.search(r"\bkj\b", text):
            return "kJ"
        if re.search(r"\bmj\b", text):
            return "mJ"
        if re.search(r"\bj\b|joule", text):
            return "J"
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
