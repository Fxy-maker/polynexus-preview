from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from polynexus.gui.result_table_models import (
    HeroMetric,
    ResultTableSection,
    ResultsTablePresentation,
    TableCell,
    TableColumn,
    format_table_value,
    normalize_table_scalar,
)


def test_table_cell_defaults_are_explicit_and_immutable():
    cell = TableCell()

    assert cell.raw is None
    assert cell.display == "—"
    assert cell.status == "neutral"
    with pytest.raises(FrozenInstanceError):
        cell.display = "changed"


def test_table_column_header_includes_unit_only_when_present():
    assert TableColumn("temperature", "Temperature", unit="°C").header == "Temperature / °C"
    assert TableColumn("sample", "Sample").header == "Sample"


def test_table_contracts_preserve_raw_display_and_section_defaults():
    cell = TableCell(raw=np.float32(0.126), display="0.13", status="good")
    hero = HeroMetric("score", "Score", np.int64(3), "3")
    section = ResultTableSection(columns=(TableColumn("score", "Score"),), rows=((cell,),))
    presentation = ResultsTablePresentation("single", section, ResultTableSection.empty(), ResultTableSection.empty())

    assert cell.raw == pytest.approx(0.126)
    assert type(cell.raw) is float
    assert hero.raw == 3
    assert type(hero.raw) is int
    assert presentation.primary.rows[0][0].display == "0.13"
    assert ResultTableSection.empty().rows == ()


def test_section_and_presentation_copy_nested_sequences_to_immutable_tuples():
    column = TableColumn("score", "Score")
    cell = TableCell(raw=1, display="1")
    hero = HeroMetric("score", "Score", 1, "1")
    columns = [column]
    rows = [[cell]]
    hero_metrics = [hero]

    section = ResultTableSection(columns=columns, rows=rows)
    presentation = ResultsTablePresentation(
        "single",
        section,
        ResultTableSection.empty(),
        ResultTableSection.empty(),
        hero_metrics=hero_metrics,
    )

    columns.append(TableColumn("other", "Other"))
    rows[0].append(TableCell(raw=2, display="2"))
    hero_metrics.append(HeroMetric("other", "Other", 2, "2"))

    assert section.columns == (column,)
    assert section.rows == ((cell,),)
    assert presentation.hero_metrics == (hero,)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(np.float32(1.25), 1.25), (np.int64(7), 7), (np.bool_(True), True), (np.str_("sample-a"), "sample-a")],
)
def test_normalize_table_scalar_converts_numpy_scalars(value, expected):
    assert normalize_table_scalar(value) == expected


@pytest.mark.parametrize("raw", [[], {}, {1}, (1, 2), np.array([1.0, 2.0])])
def test_table_contracts_reject_nested_raw_values(raw):
    with pytest.raises(TypeError):
        TableCell(raw=raw)


def test_format_table_value_classifies_missing_boolean_and_nonfinite_values():
    assert format_table_value(None) == "—"
    assert format_table_value("") == "—"
    assert format_table_value(True) == "是"
    assert format_table_value(42) == "42"
    assert format_table_value(float("nan")) == "不可用"
    assert format_table_value(1.25, digits=3) == "1.250"


def test_format_table_value_rejects_invalid_digits_only_for_finite_float_formatting():
    assert format_table_value(None, digits=True) == "—"
    with pytest.raises(TypeError):
        format_table_value(1.25, digits=True)
    with pytest.raises(ValueError):
        format_table_value(1.25, digits=-1)
