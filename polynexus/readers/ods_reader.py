"""Bounded reader for standard OpenDocument Spreadsheet containers."""

from __future__ import annotations

from dataclasses import dataclass
import posixpath
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET


MAX_SOURCE_BYTES = 256 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 512
MAX_ROWS = 1_000_000
MAX_COLUMNS = 4_096

_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "calcext": "urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0",
}
_TABLE = f"{{{_NS['table']}}}table"
_ROW = f"{{{_NS['table']}}}table-row"
_CELL = f"{{{_NS['table']}}}table-cell"
_COVERED_CELL = f"{{{_NS['table']}}}covered-table-cell"
_ROWS_REPEATED = f"{{{_NS['table']}}}number-rows-repeated"
_COLS_REPEATED = f"{{{_NS['table']}}}number-columns-repeated"
_VALUE = f"{{{_NS['office']}}}value"
_VALUE_TYPE = f"{{{_NS['office']}}}value-type"
_STRING_VALUE = f"{{{_NS['office']}}}string-value"
_DATE_VALUE = f"{{{_NS['office']}}}date-value"


@dataclass(frozen=True)
class ODSRowTable:
    """One ODS sheet represented as raw cell values."""

    sheet_name: str
    rows: tuple[tuple[object, ...], ...]


def read_ods_tables(path: str | Path) -> tuple[ODSRowTable, ...]:
    """Read spreadsheet cells without evaluating formulas, macros, or links."""

    source = Path(path)
    if source.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("ODS source exceeds the bounded reader size")
    try:
        archive = zipfile.ZipFile(source)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("ODS archive is not a valid ZIP container") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS:
            raise ValueError("ODS archive contains too many members")
        names = {item.filename for item in infos}
        if any(_unsafe_member(item.filename) for item in infos):
            raise ValueError("ODS archive contains an unsafe member path")
        if "mimetype" not in names or "content.xml" not in names:
            raise ValueError("ODS archive is missing required members")
        total = sum(item.file_size for item in infos)
        if total > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("ODS archive exceeds the uncompressed size budget")
        mimetype = archive.read("mimetype")
        if mimetype[:128] != b"application/vnd.oasis.opendocument.spreadsheet":
            raise ValueError("source is not an OpenDocument Spreadsheet")
        try:
            root = ET.fromstring(archive.read("content.xml"))
        except (ET.ParseError, KeyError, OSError) as exc:
            raise ValueError("ODS content.xml is malformed") from exc
    tables: list[ODSRowTable] = []
    for table in root.iter(_TABLE):
        name = str(table.attrib.get(f"{{{_NS['table']}}}name", "Sheet"))
        rows: list[tuple[object, ...]] = []
        for row in table.findall(_ROW):
            repeat_rows = _positive_repeat(row.attrib.get(_ROWS_REPEATED, "1"))
            cells: list[object] = []
            for cell in list(row):
                if cell.tag not in {_CELL, _COVERED_CELL}:
                    continue
                repeat_columns = _positive_repeat(cell.attrib.get(_COLS_REPEATED, "1"))
                value = _cell_value(cell)
                if len(cells) + repeat_columns > MAX_COLUMNS:
                    raise ValueError("ODS row exceeds the column limit")
                cells.extend([value] * repeat_columns)
            if len(rows) + repeat_rows > MAX_ROWS:
                raise ValueError("ODS sheet exceeds the row limit")
            rows.extend([tuple(cells)] * repeat_rows)
        if rows:
            tables.append(ODSRowTable(sheet_name=name, rows=tuple(rows)))
    if not tables:
        raise ValueError("ODS spreadsheet contains no table rows")
    return tuple(tables)


def looks_like_ods(path: str | Path, prefix: bytes | None = None) -> bool:
    """Return true only for a valid ODS mimetype member."""

    source = Path(path)
    if prefix is not None and not prefix.startswith(b"PK"):
        return False
    try:
        with zipfile.ZipFile(source) as archive:
            return archive.read("mimetype")[:128] == b"application/vnd.oasis.opendocument.spreadsheet"
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def _unsafe_member(name: str) -> bool:
    normalized = posixpath.normpath(name)
    return (
        name.startswith("/")
        or normalized.startswith("../")
        or normalized == ".."
        or "\\" in name
    )


def _positive_repeat(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("ODS repeat count is invalid") from exc
    if parsed < 1 or parsed > MAX_ROWS:
        raise ValueError("ODS repeat count is out of bounds")
    return parsed


def _cell_value(cell: ET.Element) -> object:
    value_type = cell.attrib.get(_VALUE_TYPE, "")
    if value_type in {"float", "currency", "percentage"}:
        raw = cell.attrib.get(_VALUE, "")
        try:
            return float(raw)
        except ValueError:
            return raw
    if value_type == "boolean":
        return cell.attrib.get(_VALUE, "false").casefold() == "true"
    if value_type == "date":
        return cell.attrib.get(_DATE_VALUE, "")
    if value_type == "time":
        return cell.attrib.get(_VALUE, "")
    paragraphs = ["".join(text.itertext()) for text in cell.findall("text:p", _NS)]
    if paragraphs:
        return "\n".join(paragraphs)
    return cell.attrib.get(_STRING_VALUE, "")


__all__ = ["MAX_SOURCE_BYTES", "ODSRowTable", "looks_like_ods", "read_ods_tables"]
