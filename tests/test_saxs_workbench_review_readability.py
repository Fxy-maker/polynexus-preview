from copy import deepcopy

from polynexus.gui.saxs_results_table_service import build_saxs_results_presentation


def _diagnostic_metric() -> dict:
    return {
        "metric_name": "Porod",
        "frame_count": 2,
        "evidence_frame_count": 2,
        "usable_frame_count": 0,
        "diagnostic_frame_count": 2,
        "unusable_frame_count": 0,
        "missing_frame_count": 0,
        "coverage_fraction": 1.0,
        "level": "Diagnostic",
        "reason_codes": ["metric_reason"],
    }


def test_workbench_keeps_review_sources_ordered_on_separate_lines():
    params = {
        "batch_frames": 2,
        "_batch_data": [
            {"temperature_C": 20.0, "L_nm": 12.0},
            {"temperature_C": 40.0, "L_nm": 12.2},
        ],
        "metric_evidence": {"porod": _diagnostic_metric()},
        "guinier_sequence_evidence": {
            "frame_count": 2,
            "valid_frame_count": 0,
            "missing_frame_indices": [],
            "diagnostic_frame_indices": [0, 1],
            "frame_source_indices": [0, 1],
            "level": "Diagnostic",
            "reason_codes": ["sequence_reason"],
        },
    }
    original = deepcopy(params)

    presentation = build_saxs_results_presentation(
        params,
        submodule="temperature",
        language="en",
    )

    risk_lines = presentation.risk_text.splitlines()
    next_lines = presentation.next_text.splitlines()
    assert len(risk_lines) == 2
    assert risk_lines[0].startswith("Risk note | Porod:")
    assert risk_lines[1].startswith("Risk note | Rg sequence:")
    assert "metric_reason" in risk_lines[0]
    assert "sequence_reason" in risk_lines[1]
    assert len(next_lines) == 2
    assert next_lines[0].startswith("Next step | Review missing")
    assert next_lines[1].startswith("Next step | Use Rg sequence")
    assert params == original
