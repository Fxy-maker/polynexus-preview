from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import MethodType, SimpleNamespace

import pytest

from polynexus.core.preprocess_optimization import get_preprocess_policy
from tests.preprocess_orchestrator_fakes import FakeDSCEngine, build_fake_dsc_orchestrator, preprocess_intent


class _FailingAudit:
    def append(self, record):
        del record
        raise OSError("disk full")


class _BrokenEngine(FakeDSCEngine):
    failure = "false"

    def run_pipeline(self, data_file, output_dir=""):
        del data_file, output_dir
        if self.failure == "exception":
            raise RuntimeError("engine boom")
        self.result = SimpleNamespace(parameters={})
        self.residual_pattern = {}
        return self.result


@pytest.mark.parametrize("failure", ["invalid_intent", "candidate_timeout", "engine_false", "engine_exception", "audit_write_failed"])
def test_failure_never_replaces_control_or_creates_positive_experience(failure) -> None:
    orchestrator = build_fake_dsc_orchestrator()
    before_config = deepcopy(orchestrator._config_to_dict(orchestrator._best_config))
    before_output = deepcopy(orchestrator._best_output)
    payload = preprocess_intent("baseline")

    if failure == "invalid_intent":
        payload["desired_effect"] = "maximum"
    elif failure == "candidate_timeout":
        orchestrator.preprocess_policy = replace(orchestrator.preprocess_policy, candidate_timeout_s=1e-12)
    elif failure in {"engine_false", "engine_exception"}:
        mode = "exception" if failure == "engine_exception" else "false"

        def create(self, config):
            trial = _BrokenEngine(config)
            trial.failure = mode
            self.created_trial_engines.append(trial)
            return trial

        orchestrator._create_preprocess_engine = MethodType(create, orchestrator)
    elif failure == "audit_write_failed":
        orchestrator.preprocess_policy = replace(get_preprocess_policy("DSC"), calibrated=True, automation_state="tiered_auto")
        orchestrator.preprocess_audit_log = _FailingAudit()

    report = orchestrator.run_preprocess_intent(payload)

    assert orchestrator._config_to_dict(orchestrator._best_config) == before_config
    assert orchestrator._best_output == before_output
    assert report.get("experience_proposal", {}) == {}
    assert report["preprocess_decision"]["decision"] == "keep_original"
    if failure == "audit_write_failed":
        assert report["decision_record"]["decision"] == "keep_original"


def test_config_hash_change_at_commit_keeps_original() -> None:
    orchestrator = build_fake_dsc_orchestrator()
    orchestrator.preprocess_policy = replace(get_preprocess_policy("DSC"), calibrated=True, automation_state="tiered_auto")
    original = deepcopy(orchestrator._config_to_dict(orchestrator._best_config))
    real_commit = orchestrator._commit_preprocess_candidate

    def changed(engine, candidate, expected_hash):
        orchestrator._best_config.smooth_window = 13
        return real_commit(engine, candidate, expected_hash)

    orchestrator._commit_preprocess_candidate = changed
    report = orchestrator.run_preprocess_intent(preprocess_intent("baseline"))

    assert report["preprocess_decision"]["decision"] == "keep_original"
    assert "config_hash_changed" in report["preprocess_decision"]["reason_codes"]
    orchestrator._best_config.smooth_window = original["smooth_window"]
    assert orchestrator._config_to_dict(orchestrator._best_config) == original
