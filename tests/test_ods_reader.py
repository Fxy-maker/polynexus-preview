from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from polynexus.core.canonical_experiments import default_converter_registry
from polynexus.core.compute import ComputeRunService
from polynexus.core.input_formats import inspect_format
from polynexus.readers.ods_reader import read_ods_tables


_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 office:version="1.3">
 <office:body><office:spreadsheet>
  <table:table table:name="IR curve">
   <table:table-row>
    <table:table-cell office:value-type="string"><text:p>Wavenumber (cm^-1)</text:p></table:table-cell>
    <table:table-cell office:value-type="string"><text:p>Absorbance</text:p></table:table-cell>
   </table:table-row>
   <table:table-row>
    <table:table-cell office:value-type="float" office:value="1700"/><table:table-cell office:value-type="float" office:value="0.4"/>
   </table:table-row>
   <table:table-row table:number-rows-repeated="2">
    <table:table-cell office:value-type="float" office:value="1600"/><table:table-cell office:value-type="float" office:value="0.8"/>
   </table:table-row>
  </table:table>
 </office:spreadsheet></office:body>
</office:document-content>"""


def _write_ods(path: Path, content: str = _CONTENT) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet", compress_type=zipfile.ZIP_STORED)
        archive.writestr("content.xml", content)
    return path


def test_ods_reader_expands_repeated_rows_and_preserves_sheet_name(tmp_path: Path) -> None:
    source = _write_ods(tmp_path / "curve.ods")

    tables = read_ods_tables(source)

    assert len(tables) == 1
    assert tables[0].sheet_name == "IR curve"
    assert tables[0].rows[0] == ("Wavenumber (cm^-1)", "Absorbance")
    assert tables[0].rows[-1] == (1600.0, 0.8)
    assert len(tables[0].rows) == 4


def test_ods_routes_through_canonical_and_compute_run(tmp_path: Path) -> None:
    source = _write_ods(tmp_path / "curve.ods")

    inspection = inspect_format(source, technique="ir")
    outcome = default_converter_registry().convert_path(
        source, technique="ir", source_artifact_id="ods-artifact"
    )

    assert inspection.status == "needs_mapping"
    assert inspection.plugin_id == "portable.ods.v1"
    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.measurements[0].source_locator["sheet_name"] == "IR curve"
    assert outcome.template.measurements[0].channels["x"] == (1700.0, 1600.0, 1600.0)

    run = ComputeRunService().run_direct(technique="ir", path=source, output_dir="")
    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.template_id == "spectrum_1d.v1"


def test_ods_reader_rejects_malformed_or_unsafe_archives(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.ods"
    malformed.write_bytes(b"PK-not-an-archive")
    with pytest.raises(ValueError, match="ODS"):
        read_ods_tables(malformed)

    unsafe = tmp_path / "unsafe.ods"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        archive.writestr("../content.xml", _CONTENT)
    with pytest.raises(ValueError, match="unsafe"):
        read_ods_tables(unsafe)
