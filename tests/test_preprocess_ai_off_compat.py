from __future__ import annotations

import numpy as np

from polynexus.core.dsc_engine.preprocess import smooth_profile as dsc_smooth
from polynexus.core.ir_engine.preprocess import smooth_profile as ir_smooth
from polynexus.core.nmr_engine.preprocess import apodization_exponential
from polynexus.core.preprocess_optimization import get_preprocess_adapter, get_preprocess_policy
from polynexus.core.report import generate_report, preprocess_export_metadata
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.preprocess import smooth_profile as saxs_smooth
from polynexus.core.waxs_engine.preprocess import smooth_profile as waxs_smooth


def _scientific_payload():
    x = np.linspace(0.1, 1.0, 101)
    signal = np.exp(-((x - 0.5) / 0.08) ** 2) + 0.01 * np.sin(80 * x)
    return {
        "DSC": dsc_smooth(signal, method="savgol", window=11, order=3),
        "IR": ir_smooth(signal, method="savgol", window=7, order=3),
        "WAXS": waxs_smooth(signal, method="savgol", window=9, order=3),
        "SAXS": saxs_smooth(
            x,
            signal,
            SAXSConfig(smooth_method="savgol", savgol_window=7, savgol_order=2),
        ),
        "NMR": apodization_exponential(signal.astype(complex), lb_hz=10.0, sweep_width_hz=1000.0),
    }


def test_ai_off_scientific_payload_is_byte_equivalent() -> None:
    before = _scientific_payload()
    for technique in ("DSC", "IR", "WAXS", "SAXS", "NMR"):
        get_preprocess_policy(technique)
        get_preprocess_adapter(technique)
    after = _scientific_payload()

    for technique in before:
        assert before[technique].tobytes() == after[technique].tobytes()


def test_ai_off_report_has_no_optimizer_metadata() -> None:
    assert preprocess_export_metadata({}) == {}
    html = generate_report(project_name="AI off")
    assert "Preprocessing optimization" not in html


def test_invoked_optimizer_export_contains_versioned_decision_metadata() -> None:
    report = {
        "best_config": {"smooth_window": 15},
        "preprocess_decision": {
            "decision": "request_confirmation",
            "confidence_band": "medium",
            "user_decision": "accepted",
        },
        "decision_record": {
            "schema_version": "1.0",
            "policy_version": "dsc-preprocess-v1",
            "core_version": "1.0.0",
            "prompt_version": "preprocess-intent-v1",
            "evidence_refs": ["c1"],
        },
    }

    metadata = preprocess_export_metadata(report)

    assert metadata["schema_version"] == "1.0"
    assert metadata["final_config_hash"]
    assert metadata["decision"] == "request_confirmation"
    assert metadata["evidence_refs"] == ["c1"]
