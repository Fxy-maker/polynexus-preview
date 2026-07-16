from __future__ import annotations

from types import SimpleNamespace

from polynexus.core.engine import AnalysisResult
from polynexus.core.saxs_result_contract import publish_saxs_result_contract


def _analysis(**overrides):
    state = {
        "quality_flag": "OK",
        "validation_summary": "All checks passed",
        "effective_q_min": 0.1,
        "Q_star_valid": True,
        "Q_star_status": "valid",
        "Q_star_reasons": [],
        "final_parameters": {
            "lc_method": "raw",
            "calibrated_fallback_reason": "raw_value_retained",
            "fallback_applied_fields": [],
        },
    }
    state.update(overrides)
    return SimpleNamespace(**state)


def test_result_contract_uses_common_q_lower_bound_and_keeps_qstar_unknown_out() -> None:
    engine = SimpleNamespace(
        result=AnalysisResult(),
        _batch_results=[
            _analysis(effective_q_min=0.1, Q_star_valid=True),
            _analysis(effective_q_min=0.2, Q_star_valid=None),
        ],
        _batch_params=[{}, {}],
    )

    contract = publish_saxs_result_contract(engine)

    assert contract["effective_q_min"] == 0.2
    assert contract["Q_star_valid"] is True
    assert contract["fallback_provenance"]["mode"] == "sequence"
    assert len(contract["fallback_provenance"]["frames"]) == 2


def test_result_contract_reports_metadata_write_diagnostic() -> None:
    result = SimpleNamespace(
        parameters={},
        quality_flags=None,
        validation_passed=True,
        validation_summary="",
        effective_q_min=float("nan"),
        metadata=None,
        analysis_evidence={},
    )
    engine = SimpleNamespace(result=result, _analysis=_analysis(), _batch_results=[])

    contract = publish_saxs_result_contract(engine)

    assert contract["metadata_updated"] is False
    assert contract["write_diagnostics"]["metadata"] == "metadata_not_dict"
    assert result.quality_flags["saxs"] == "OK"
