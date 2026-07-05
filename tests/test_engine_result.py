from __future__ import annotations

from polynexus.core.engine import AnalysisResult


def test_analysis_result_to_dict_includes_validation_state() -> None:
    result = AnalysisResult(
        technique="dsc",
        validation_passed=False,
        quality_flags={"scan1/Tg": "WARN"},
        validation_warnings=["scan1/Tg"],
    )

    payload = result.to_dict()

    assert payload["validation_passed"] is False
    assert payload["quality_flags"] == {"scan1/Tg": "WARN"}
    assert payload["validation_warnings"] == ["scan1/Tg"]
