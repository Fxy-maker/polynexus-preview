from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from types import MethodType, SimpleNamespace
from typing import Any

from polynexus.core.preprocess_optimization import get_preprocess_policy
from polynexus.core.saxs_export_bundle import _quality_evidence_payload
from polynexus.orchestrator import ParameterOrchestrator


PROTECTED = [
    "weak_peaks",
    "integrated_area",
    "guinier_region",
    "beamstop_boundaries",
    "peak_position",
    "peak_width",
    "physical_parameters",
]


@dataclass
class FakeSAXSConfig:
    smooth_method: str = "savgol"
    savgol_window: int = 7
    savgol_order: int = 2
    background_file: str = ""
    bg_scale_method: str = "auto"
    bg_scale_value: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FakeSAXSEngine:
    def __init__(self, config: FakeSAXSConfig | None = None) -> None:
        self.cfg = deepcopy(config or FakeSAXSConfig())
        self.result = SimpleNamespace(parameters={}, metadata={})
        self.residual_pattern: dict[str, Any] = {}

    def analyze(self) -> bool:
        changed = self.cfg.savgol_window != 7
        self.result.parameters = {
            "q_peak": 0.5,
            "q_peak_fwhm": 0.04,
            "q_peak_area": 10.0,
            "L_bragg": 12.566,
            "L_corr_peak": 12.5,
            "L_nm": 12.6,
            "lc_nm": 10.0,
            "Rg": 4.0,
            "Q_invariant": 20.0,
            "negative_fraction": 0.0,
            "baseline_stability_score": 0.85 if changed else 0.70,
        }
        self.residual_pattern = {
            "rmse": 0.70 if changed else 1.0,
            "residual_autocorrelation": 0.05,
        }
        return True

    def run_pipeline(self, _data_file: str, output_dir: str = "") -> Any:
        del output_dir
        self.analyze()
        return self.result


def saxs_intent(**overrides: Any) -> dict[str, Any]:
    payload = {
        "schema_version": "1.0",
        "analysis_id": "fake-saxs-ai-1",
        "technique": "SAXS",
        "target": "smoothing",
        "direction": "strengthen",
        "desired_effect": "medium",
        "protected_features": list(PROTECTED),
        "target_symptoms": ["noise_dominant"],
        "rationale_code": "quality_report_noise",
        "human_summary": "Reduce profile noise while preserving SAXS features.",
    }
    payload.update(overrides)
    return payload


def build_fake_saxs_orchestrator() -> ParameterOrchestrator:
    orchestrator = ParameterOrchestrator.__new__(ParameterOrchestrator)
    orchestrator.technique = "saxs"
    orchestrator.data_file = "fake-saxs.edf"
    orchestrator.workspace_context = {
        "instrument_fingerprint": "fake-saxs-v1",
        "sample_family": "synthetic-polymer",
    }
    orchestrator.preprocess_policy = get_preprocess_policy("SAXS")
    orchestrator.created_trial_engines = []
    engine = FakeSAXSEngine()
    engine.analyze()
    orchestrator._engine = engine
    orchestrator._best_config = deepcopy(engine.cfg)
    orchestrator._best_output = deepcopy(engine.result.parameters)
    orchestrator._best_record = None

    orchestrator._engine_config = MethodType(
        lambda self, target: target.cfg,
        orchestrator,
    )
    orchestrator._config_to_dict = MethodType(
        lambda self, config: deepcopy(config.to_dict()),
        orchestrator,
    )
    orchestrator._output_parameters = MethodType(
        lambda self, target: deepcopy(target.result.parameters),
        orchestrator,
    )
    orchestrator._residual_pattern = MethodType(
        lambda self, target: deepcopy(target.residual_pattern),
        orchestrator,
    )
    orchestrator._analysis_evidence = MethodType(
        lambda self, output, residual: {
            "background_evidence": {
                "baseline_stability_score": output["baseline_stability_score"],
            },
            "residual": deepcopy(residual),
        },
        orchestrator,
    )

    def create_trial(self: ParameterOrchestrator, config: FakeSAXSConfig) -> FakeSAXSEngine:
        trial = FakeSAXSEngine(config)
        self.created_trial_engines.append(trial)
        return trial

    orchestrator._create_preprocess_engine = MethodType(create_trial, orchestrator)
    return orchestrator


def test_invalid_saxs_protected_field_fails_before_trial_creation() -> None:
    orchestrator = build_fake_saxs_orchestrator()

    report = orchestrator.run_preprocess_intent(
        saxs_intent(protected_features=PROTECTED[:-1])
    )

    assert orchestrator.created_trial_engines == []
    assert report["preprocess_decision"]["decision"] == "keep_original"
    assert any(
        code.startswith("invalid_intent:")
        for code in report["preprocess_decision"]["reason_codes"]
    )
    assert "saxs_ai_rescue_plan" not in report


def test_valid_saxs_shadow_report_and_engine_carry_json_safe_rescue_audit() -> None:
    orchestrator = build_fake_saxs_orchestrator()

    report = orchestrator.run_preprocess_intent(saxs_intent())

    plan = report["saxs_ai_rescue_plan"]
    decision = report["saxs_ai_rescue_decision"]
    assert plan["candidate_only"] is True
    assert plan["original_preserved"] is True
    assert plan["intent"]["technique"] == "SAXS"
    assert plan["candidates"]
    assert decision["decision"] == "keep_original"
    assert decision["apply_allowed"] is False
    assert report["preprocess_decision"]["decision"] == "keep_original"
    assert orchestrator._engine.saxs_ai_rescue_plan == plan
    assert orchestrator._engine.saxs_ai_rescue_decision == decision
    json.dumps(plan, allow_nan=False)
    json.dumps(decision, allow_nan=False)

    export_quality = _quality_evidence_payload(orchestrator._engine, "static")
    assert export_quality["ai_rescue"]["plan"] == plan
    assert export_quality["ai_rescue"]["decision"] == decision


def test_saxs_audit_failure_synchronizes_report_and_engine_decisions() -> None:
    orchestrator = build_fake_saxs_orchestrator()
    orchestrator.preprocess_policy = replace(
        get_preprocess_policy("SAXS"),
        calibrated=True,
        automation_state="tiered_auto",
    )

    class FailingAudit:
        def append(self, _record: object) -> None:
            raise RuntimeError("audit unavailable")

    orchestrator.preprocess_audit_log = FailingAudit()
    report = orchestrator.run_preprocess_intent(saxs_intent())

    assert report["preprocess_decision"]["decision"] == "keep_original"
    assert report["saxs_ai_rescue_decision"] == report["preprocess_decision"]
    assert orchestrator._engine.saxs_ai_rescue_decision == report["preprocess_decision"]
