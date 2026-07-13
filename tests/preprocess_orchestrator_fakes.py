from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from types import MethodType, SimpleNamespace
from typing import Any

from polynexus.core.preprocess_optimization import get_preprocess_policy
from polynexus.orchestrator import ParameterOrchestrator


@dataclass
class FakeDSCConfig:
    baseline_corr: str = "auto"
    smooth_window: int = 11
    smooth_order: int = 3

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FakeDSCEngine:
    def __init__(
        self,
        config: FakeDSCConfig | None = None,
        *,
        destroy_candidate_enthalpy: bool = False,
    ) -> None:
        self._dsc_config = deepcopy(config or FakeDSCConfig())
        self.destroy_candidate_enthalpy = destroy_candidate_enthalpy
        self.result = SimpleNamespace(parameters={})
        self.residual_pattern: dict[str, Any] = {}
        self.analyze_calls = 0

    def run_pipeline(self, _data_file: str, output_dir: str = "") -> Any:
        del output_dir
        self.preprocess()
        self.analyze()
        return self.result

    def preprocess(self) -> bool:
        return True

    def analyze(self) -> bool:
        self.analyze_calls += 1
        cfg = self._dsc_config
        baseline_gain = 0.0 if cfg.baseline_corr == "auto" else 0.20
        smoothing_gain = min(abs(cfg.smooth_window - 11) / 20.0, 0.20)
        changed = cfg.baseline_corr != "auto" or cfg.smooth_window != 11
        enthalpy = 50.0 if changed and self.destroy_candidate_enthalpy else 99.0
        shift = baseline_gain * 0.5 + smoothing_gain * 0.2
        self.result.parameters = {
            "peak_components": [
                {
                    "temperature": 180.0 + shift,
                    "fwhm_C": 8.02,
                    "area": enthalpy,
                    "height": 10.0,
                },
                {
                    "temperature": 215.0 + shift,
                    "fwhm_C": 5.02,
                    "area": 11.9,
                    "height": 1.0,
                },
            ],
            "DHm_Jg": enthalpy,
            "Tg_C": 55.0 + shift,
            "Tm_peak_C": 215.0 + shift,
            "Xc_pct": 43.0,
            "negative_fraction": 0.0,
            "baseline_stability_score": 0.70 + baseline_gain,
        }
        self.residual_pattern = {
            "rmse": 1.0 - baseline_gain - smoothing_gain,
            "residual_autocorrelation": 0.05,
        }
        return True

    def get_parameters(self) -> dict[str, Any]:
        return deepcopy(self.result.parameters)


def preprocess_intent(target: str = "smoothing") -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "analysis_id": "fake-dsc-1",
        "technique": "DSC",
        "target": target,
        "direction": "strengthen",
        "desired_effect": "medium",
        "protected_features": ["weak_peaks", "integrated_area", "thermal_events"],
        "target_symptoms": ["noise_dominant"],
        "rationale_code": "noise",
        "human_summary": "Reduce noise while preserving thermal events.",
    }


def build_fake_dsc_orchestrator() -> ParameterOrchestrator:
    orchestrator = ParameterOrchestrator.__new__(ParameterOrchestrator)
    orchestrator.technique = "dsc"
    orchestrator.data_file = "fake-dsc.csv"
    orchestrator.workspace_context = {
        "instrument_fingerprint": "fake-dsc-v1",
        "sample_family": "synthetic-polymer",
    }
    orchestrator.preprocess_policy = get_preprocess_policy("DSC")
    orchestrator.destroy_candidate_enthalpy = False
    orchestrator.created_trial_engines = []
    engine = FakeDSCEngine()
    engine.analyze()
    orchestrator._engine = engine
    orchestrator._best_config = deepcopy(engine._dsc_config)
    orchestrator._best_output = deepcopy(engine.result.parameters)
    orchestrator._best_record = None

    orchestrator._engine_config = MethodType(
        lambda self, target: target._dsc_config,
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
            "baseline_evidence": {
                "baseline_stability_score": output.get("baseline_stability_score")
            }
        },
        orchestrator,
    )

    def create_trial(self: ParameterOrchestrator, config: FakeDSCConfig) -> FakeDSCEngine:
        trial = FakeDSCEngine(
            config,
            destroy_candidate_enthalpy=self.destroy_candidate_enthalpy,
        )
        self.created_trial_engines.append(trial)
        return trial

    orchestrator._create_preprocess_engine = MethodType(create_trial, orchestrator)
    return orchestrator
