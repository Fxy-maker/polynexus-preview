from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from polynexus.core.canonical_experiments import (
    MappingProposal,
    MappingSelection,
    convert_one_dimensional_table,
)


def test_ir_csv_curve_preserves_order_units_and_source_rows(tmp_path: Path) -> None:
    path = tmp_path / "curve.csv"
    path.write_text("Wavenumber cm-1,Absorbance a.u.\n4000,0.1\n2000,0.3\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id="artifact-1")

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "spectrum_1d.v1"
    measurement = outcome.template.measurements[0]
    assert measurement.family == "spectrum_1d"
    assert measurement.role == "raw_curve"
    assert measurement.channels == {"x": (4000.0, 2000.0), "intensity": (0.1, 0.3)}
    assert measurement.units == {"x": "cm^-1", "intensity": "a.u."}
    assert measurement.mapping is not None
    assert measurement.mapping.source == "observed"
    assert measurement.source_locator["data_row_start"] == 1
    assert measurement.source_locator["data_row_end"] == 2
    assert (measurement.source_locator["point_start"], measurement.source_locator["point_end"]) == (0, 1)
    assert outcome.record.observed_columns == ("flat:Wavenumber cm-1", "flat:Absorbance a.u.")


def test_flat_file_locator_uses_physical_lines_with_comments(tmp_path: Path) -> None:
    path = tmp_path / "commented.csv"
    path.write_text(
        "# instrument preamble\nWavenumber,Absorbance\n4000,0.1\n# between rows\n2000,0.3\n",
        encoding="utf-8",
    )

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id="artifact-comments")

    assert outcome.status == "ready"
    assert outcome.template is not None
    measurement = outcome.template.measurements[0]
    assert measurement.mapping is not None
    assert measurement.mapping.header_row == 1
    assert (measurement.mapping.data_row_start, measurement.mapping.data_row_end) == (2, 4)
    assert measurement.source_locator["header_row"] == 1
    assert (measurement.source_locator["data_row_start"], measurement.source_locator["data_row_end"]) == (2, 4)


@pytest.mark.parametrize("suffix", (".csv", ".xlsx"))
def test_duplicate_intensity_headers_need_mapping_input(tmp_path: Path, suffix: str) -> None:
    path = tmp_path / f"duplicate{suffix}"
    if suffix == ".csv":
        path.write_text("Wavenumber,Absorbance,Absorbance\n4000,0.1,0.2\n2000,0.3,0.4\n", encoding="utf-8")
    else:
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame([["Wavenumber", "Absorbance", "Absorbance"], [4000, 0.1, 0.2], [2000, 0.3, 0.4]]).to_excel(
                writer, index=False, header=False
            )

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id=f"artifact-duplicate-{suffix}")

    assert outcome.status == "needs_input"
    assert outcome.reason_codes == ("conversion_mapping_ambiguous",)
    prefix = "flat" if suffix == ".csv" else "Sheet1"
    assert outcome.record.observed_columns[-2:] == (f"{prefix}:Absorbance", f"{prefix}:Absorbance")


def test_blank_header_needs_mapping_input_without_pandas_alias(tmp_path: Path) -> None:
    path = tmp_path / "blank.csv"
    path.write_text("Wavenumber,,Absorbance\n4000,0.1,0.2\n2000,0.3,0.4\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id="artifact-blank")

    assert outcome.status == "needs_input"
    assert outcome.reason_codes == ("conversion_mapping_ambiguous",)
    assert outcome.record.observed_columns == ("flat:Wavenumber", "flat:", "flat:Absorbance")


@pytest.mark.parametrize(
    ("header", "expected_unit"),
    (("Intensity (counts)", "counts"), ("Intensity (cps)", "cps"), ("Intensity (a.u.)", "a.u.")),
)
def test_intensity_header_unit_suffix_is_mapped_and_preserved(
    tmp_path: Path, header: str, expected_unit: str
) -> None:
    path = tmp_path / "intensity.csv"
    path.write_text(f"Wavenumber,{header}\n4000,1\n2000,2\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id=f"artifact-{expected_unit}")

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.measurements[0].units["intensity"] == expected_unit


def test_leading_whitespace_comment_keeps_physical_locator(tmp_path: Path) -> None:
    path = tmp_path / "whitespace-comment.csv"
    path.write_text("  # preamble\nWavenumber,Absorbance\n4000,0.1\n2000,0.2\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id="artifact-whitespace-comment")

    assert outcome.status == "ready"
    assert outcome.template is not None
    locator = outcome.template.measurements[0].source_locator
    assert (locator["header_row"], locator["data_row_start"], locator["data_row_end"]) == (1, 2, 3)


def test_quoted_multiline_field_keeps_its_physical_record_range(tmp_path: Path) -> None:
    path = tmp_path / "quoted.csv"
    path.write_text("Wavenumber,Absorbance,Note\n4000,0.1,\"first line\ncontinued\"\n2000,0.2,done\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id="artifact-quoted")

    assert outcome.status == "ready"
    assert outcome.template is not None
    locator = outcome.template.measurements[0].source_locator
    assert (locator["header_row"], locator["data_row_start"], locator["data_row_end"]) == (0, 1, 3)


def test_saxs_q_without_unit_retains_raw_values_and_warns(tmp_path: Path) -> None:
    path = tmp_path / "curve.tsv"
    path.write_text("q\tintensity\n0.3\t8\n0.1\t4\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(path, technique="SAXS", source_artifact_id="artifact-2")

    assert outcome.status == "ready"
    assert outcome.template is not None
    measurement = outcome.template.measurements[0]
    assert measurement.family == "scattering_1d"
    assert measurement.role == "raw_curve"
    assert measurement.channels["x"] == (0.3, 0.1)
    assert measurement.units["x"] == "unknown"
    assert "coordinate_unit_unknown" in measurement.warnings
    assert measurement.acquisition_metadata == {
        "background_state": "unknown",
        "normalization_state": "unknown",
    }


def test_waxs_workbook_keeps_sheet_order_and_sheet_locators(tmp_path: Path) -> None:
    path = tmp_path / "curves.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"2theta deg": [10.0, 20.0], "counts": [4.0, 5.0]}).to_excel(
            writer, sheet_name="first", index=False
        )
        pd.DataFrame({"q nm-1": [0.2, 0.1], "cps": [9.0, 8.0]}).to_excel(
            writer, sheet_name="second", index=False
        )

    outcome = convert_one_dimensional_table(path, technique="WAXS", source_artifact_id="artifact-3")

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "scattering_1d.v1"
    first, second = outcome.template.measurements
    assert (first.source_locator["sheet_name"], first.source_locator["sheet_index"]) == ("first", 0)
    assert (second.source_locator["sheet_name"], second.source_locator["sheet_index"]) == ("second", 1)
    assert (first.mapping.x_kind, first.units["x"]) == ("two_theta", "deg")
    assert (second.mapping.x_kind, second.units["x"]) == ("q", "nm^-1")


def test_ambiguous_ir_columns_needs_mapping_input(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.csv"
    path.write_text("A,B,C\n1,2,3\n4,5,6\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id="artifact-4")

    assert outcome.status == "needs_input"
    assert outcome.template is None
    assert outcome.reason_codes == ("conversion_mapping_ambiguous",)
    assert outcome.record.reason_codes == outcome.reason_codes


def test_valid_ai_proposal_resolves_ambiguous_table(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.csv"
    path.write_text("A,B,C\n1,2,3\n4,5,6\n", encoding="utf-8")
    selection = MappingSelection(
        measurement_id="sheet-0-table-0",
        sheet_name=None,
        sheet_index=None,
        table_index=0,
        header_row=0,
        data_row_start=1,
        data_row_end=2,
        x_column="A",
        intensity_column="B",
        x_kind="wavenumber",
        x_unit="unknown",
        intensity_unit="unknown",
        source="AI proposal",
    )
    proposal = MappingProposal.create(
        source_artifact_id="artifact-5", technique="IR", source="AI proposal", selections=(selection,)
    )

    outcome = convert_one_dimensional_table(
        path, technique="IR", source_artifact_id="artifact-5", mapping_proposal=proposal
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.mapping_proposal == proposal
    assert outcome.template.measurements[0].mapping == selection


def test_valid_ai_proposal_binds_physical_rows_in_commented_flat_table(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.csv"
    path.write_text("# preamble\nA,B,C\n1,2,3\n# between rows\n4,5,6\n", encoding="utf-8")
    selection = MappingSelection(
        measurement_id="sheet-0-table-0", sheet_name=None, sheet_index=None, table_index=0,
        header_row=1, data_row_start=2, data_row_end=4, x_column="A", intensity_column="B",
        x_kind="wavenumber", x_unit="unknown", intensity_unit="unknown", source="AI proposal",
    )
    proposal = MappingProposal.create(
        source_artifact_id="artifact-comment-proposal", technique="IR", source="AI proposal", selections=(selection,)
    )

    outcome = convert_one_dimensional_table(
        path, technique="IR", source_artifact_id="artifact-comment-proposal", mapping_proposal=proposal
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.measurements[0].mapping == selection


def test_proposal_for_an_unambiguous_table_is_invalid(tmp_path: Path) -> None:
    path = tmp_path / "curve.csv"
    path.write_text("Wavenumber,Absorbance\n4000,0.1\n2000,0.3\n", encoding="utf-8")
    selection = MappingSelection(
        measurement_id="sheet-0-table-0", sheet_name=None, sheet_index=None, table_index=0,
        header_row=0, data_row_start=1, data_row_end=2, x_column="Wavenumber", intensity_column="Absorbance",
        x_kind="wavenumber", x_unit="unknown", intensity_unit="absorbance", source="AI proposal",
    )
    proposal = MappingProposal.create(
        source_artifact_id="artifact-observed", technique="IR", source="AI proposal", selections=(selection,)
    )

    outcome = convert_one_dimensional_table(
        path, technique="IR", source_artifact_id="artifact-observed", mapping_proposal=proposal
    )

    assert outcome.status == "needs_input"
    assert outcome.template is None
    assert outcome.reason_codes == ("conversion_mapping_proposal_invalid",)


def test_mixed_workbook_proposal_must_match_an_observed_table(tmp_path: Path) -> None:
    path = tmp_path / "mixed.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"Wavenumber": [4000.0, 2000.0], "Absorbance": [0.1, 0.2]}).to_excel(
            writer, sheet_name="observed", index=False
        )
        pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0]}).to_excel(
            writer, sheet_name="ambiguous", index=False
        )
    selections = (
        MappingSelection(
            measurement_id="sheet-0-table-0", sheet_name="observed", sheet_index=0, table_index=0,
            header_row=0, data_row_start=1, data_row_end=2, x_column="Wavenumber", intensity_column="Absorbance",
            x_kind="wavenumber", x_unit="unknown", intensity_unit="unknown", source="AI proposal",
        ),
        MappingSelection(
            measurement_id="sheet-1-table-0", sheet_name="ambiguous", sheet_index=1, table_index=0,
            header_row=0, data_row_start=1, data_row_end=2, x_column="A", intensity_column="B",
            x_kind="wavenumber", x_unit="unknown", intensity_unit="unknown", source="AI proposal",
        ),
    )
    proposal = MappingProposal.create(
        source_artifact_id="artifact-mixed", technique="IR", source="AI proposal", selections=selections
    )

    outcome = convert_one_dimensional_table(
        path, technique="IR", source_artifact_id="artifact-mixed", mapping_proposal=proposal
    )

    assert outcome.status == "needs_input"
    assert outcome.template is None
    assert outcome.reason_codes == ("conversion_mapping_proposal_invalid",)


def test_invalid_proposal_missing_column_needs_input(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.csv"
    path.write_text("A,B,C\n1,2,3\n4,5,6\n", encoding="utf-8")
    selection = MappingSelection(
        measurement_id="sheet-0-table-0", sheet_name=None, sheet_index=None, table_index=0,
        header_row=0, data_row_start=1, data_row_end=2, x_column="missing", intensity_column="B",
        x_kind="wavenumber", x_unit="unknown", intensity_unit="unknown", source="AI proposal",
    )
    proposal = MappingProposal.create(
        source_artifact_id="artifact-6", technique="IR", source="AI proposal", selections=(selection,)
    )

    outcome = convert_one_dimensional_table(
        path, technique="IR", source_artifact_id="artifact-6", mapping_proposal=proposal
    )

    assert outcome.status == "needs_input"
    assert outcome.template is None
    assert outcome.reason_codes == ("conversion_mapping_proposal_invalid",)


def test_unsupported_format_is_blocked(tmp_path: Path) -> None:
    path = tmp_path / "curve.bin"
    path.write_bytes(b"not a table")

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id="artifact-7")

    assert outcome.status == "blocked"
    assert outcome.reason_codes == ("conversion_unsupported_format",)
    assert outcome.record.reason_codes == outcome.reason_codes


def test_unreadable_supported_source_is_blocked(tmp_path: Path) -> None:
    path = tmp_path / "unreadable.csv"
    path.mkdir()

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id="artifact-read-error")

    assert outcome.status == "blocked"
    assert outcome.reason_codes == ("conversion_source_unreadable",)
    assert outcome.record.reason_codes == outcome.reason_codes


def test_bad_proposal_artifact_technique_or_selection_source_is_invalid(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.csv"
    path.write_text("A,B,C\n1,2,3\n4,5,6\n", encoding="utf-8")
    base = dict(
        measurement_id="sheet-0-table-0", sheet_name=None, sheet_index=None, table_index=0,
        header_row=0, data_row_start=1, data_row_end=2, x_column="A", intensity_column="B",
        x_kind="wavenumber", x_unit="unknown", intensity_unit="unknown",
    )
    wrong_artifact = MappingProposal.create(
        source_artifact_id="other", technique="IR", source="AI proposal",
        selections=(MappingSelection(**base, source="AI proposal"),),
    )
    wrong_technique = MappingProposal.create(
        source_artifact_id="artifact-8", technique="SAXS", source="AI proposal",
        selections=(MappingSelection(**base, source="AI proposal"),),
    )
    wrong_selection_source = MappingProposal.create(
        source_artifact_id="artifact-8", technique="IR", source="user",
        selections=(MappingSelection(**base, source="user"),),
    )
    object.__setattr__(wrong_selection_source.selections[0], "source", "AI proposal")

    for proposal in (wrong_artifact, wrong_technique, wrong_selection_source):
        outcome = convert_one_dimensional_table(
            path, technique="IR", source_artifact_id="artifact-8", mapping_proposal=proposal
        )
        assert outcome.status == "needs_input"
        assert outcome.reason_codes == ("conversion_mapping_proposal_invalid",)


def test_nonfinite_rows_are_dropped_but_locator_covers_original_rows(tmp_path: Path) -> None:
    path = tmp_path / "curve.csv"
    path.write_text("Wavenumber,Absorbance\n4000,0.1\nbad,0.2\n2000,inf\n1000,0.3\n", encoding="utf-8")

    outcome = convert_one_dimensional_table(path, technique="IR", source_artifact_id="artifact-9")

    assert outcome.status == "ready"
    assert outcome.template is not None
    measurement = outcome.template.measurements[0]
    assert measurement.channels["x"] == (4000.0, 1000.0)
    assert measurement.source_locator["data_row_start"] == 1
    assert measurement.source_locator["data_row_end"] == 4
