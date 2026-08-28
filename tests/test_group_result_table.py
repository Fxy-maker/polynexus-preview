from __future__ import annotations

import pytest

from polynexus.core.project_workflow.result_table import (
    ResultTableRow,
    build_group_result_table,
)


def _row(row_id: str, source: str, temperature: float, value: float) -> ResultTableRow:
    return ResultTableRow(
        row_id=row_id,
        technique="dsc",
        source=source,
        condition_key="temperature_C",
        condition_value=temperature,
        metrics={"DHm_Jg": value},
    )


def test_group_table_keeps_rows_and_aggregates_only_same_condition():
    table = build_group_result_table(
        "pa6-jw",
        [_row("r1", "a.txt", 180.0, 10.0), _row("r2", "b.txt", 180.0, 14.0), _row("r3", "c.txt", 185.0, 20.0)],
    )

    stats = table.statistics("DHm_Jg")
    at_180 = next(item for item in stats if item.condition_value == 180.0)
    assert len(table.rows) == 3
    assert at_180.count == 2
    assert at_180.mean == pytest.approx(12.0)
    assert at_180.std == pytest.approx(2.0)
    assert at_180.source_row_ids == ("r1", "r2")


def test_group_table_serializes_rows_and_statistics():
    table = build_group_result_table("pa6-jw", [_row("r1", "a.txt", 180.0, 10.0)])

    payload = table.to_dict()
    assert payload["group_id"] == "pa6-jw"
    assert payload["rows"][0]["source"] == "a.txt"
    assert payload["statistics"][0]["metric_key"] == "DHm_Jg"
    assert table.csv_rows()[0]["value"] == 10.0


def test_group_table_rejects_mixed_techniques_and_missing_conditions():
    with pytest.raises(ValueError, match="technique"):
        build_group_result_table(
            "mixed",
            [_row("r1", "a.txt", 180.0, 10.0), ResultTableRow("r2", "ftir", "b.txt", "temperature_C", 180.0, {"peak": 1.0})],
        )
    with pytest.raises(ValueError, match="condition"):
        build_group_result_table(
            "missing",
            [ResultTableRow("r1", "dsc", "a.txt", "", 180.0, {"DHm_Jg": 10.0})],
        )
