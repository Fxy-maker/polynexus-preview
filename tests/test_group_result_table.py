from __future__ import annotations

from types import SimpleNamespace

import pytest

from polynexus.core.ai_platform.contracts import ComputationState
from polynexus.core.project_workflow.result_table import (
    ResultTableRow,
    build_group_result_table,
    build_result_tables_from_runs,
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
    assert at_180.minimum == pytest.approx(10.0)
    assert at_180.maximum == pytest.approx(14.0)
    assert at_180.source_row_ids == ("r1", "r2")


def test_group_table_exposes_sorted_trend_and_repeatability_summary():
    table = build_group_result_table(
        "pa6-jw",
        [_row("r1", "a.txt", 181.0, 12.0), _row("r2", "b.txt", 180.0, 10.0), _row("r3", "c.txt", 180.0, 14.0)],
    )

    trend = table.condition_trend("DHm_Jg")
    repeatability = table.repeatability("DHm_Jg")

    assert [item["condition_value"] for item in trend] == [180.0, 181.0]
    assert trend[0]["mean"] == pytest.approx(12.0)
    assert repeatability["condition_key"] == "temperature_C"
    assert repeatability["conditions"][0]["cv"] == pytest.approx(2 / 12)
    assert repeatability["conditions"][0]["status"] == "available"


def test_group_table_serializes_rows_and_statistics():
    table = build_group_result_table("pa6-jw", [_row("r1", "a.txt", 180.0, 10.0)])

    payload = table.to_dict()
    assert payload["group_id"] == "pa6-jw"
    assert payload["rows"][0]["source"] == "a.txt"
    assert payload["statistics"][0]["metric_key"] == "DHm_Jg"
    assert payload["statistics"][0]["minimum"] == 10.0
    assert payload["trends"]["DHm_Jg"][0]["mean"] == 10.0
    assert payload["repeatability"]["DHm_Jg"]["conditions"][0]["status"] == "insufficient_replicates"
    assert table.csv_rows()[0]["value"] == 10.0
    assert table.statistics_csv_rows()[0]["minimum"] == 10.0


def test_group_table_round_trips_from_dict_without_losing_traceability():
    table = build_group_result_table(
        "pa6-jw",
        [_row("r1", "a.txt", 180.0, 10.0), _row("r2", "b.txt", 180.0, 14.0)],
    )

    restored = type(table).from_dict(table.to_dict())

    assert restored == table
    assert restored.statistics("DHm_Jg")[0].source_row_ids == ("r1", "r2")


def test_group_table_from_dict_preserves_persisted_statistics_snapshot():
    table = build_group_result_table("pa6-jw", [_row("r1", "a.txt", 180.0, 10.0)])
    payload = table.to_dict()
    payload["statistics"][0]["mean"] = 999.0

    restored = type(table).from_dict(payload)

    assert restored.statistics("DHm_Jg")[0].mean == 999.0


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


def test_shared_result_table_skips_values_with_noncomputed_state():
    state = ComputationState.create(
        data_availability="canonical",
        computability="needs_input",
        validity="not_assessed",
        promotion="diagnostic_only",
    )
    run = SimpleNamespace(
        run_id="run-blocked",
        analysis_run=SimpleNamespace(steps=(SimpleNamespace(
            step_id="tm",
            technique="dsc",
            reason_codes=(),
            compute_run={
                "status": "completed",
                "computation_state": state.to_dict(),
                "artifact": {"path": "sample.csv"},
                "result": {
                    "warnings": [],
                    "metric_manifest": [{
                        "path": "Tm_C",
                        "kind": "scalar",
                        "value": 220.0,
                        "status": "computed",
                        "computation_state": state.to_dict(),
                    }],
                },
            },
        ),)),
    )

    assert build_result_tables_from_runs((run,)) == ()
