from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from polynexus.core.preprocess_optimization import get_preprocess_policy
from polynexus.core.preprocess_optimization.audit import DecisionAuditLog
from tests.preprocess_orchestrator_fakes import (
    build_fake_dsc_orchestrator,
    preprocess_intent,
)


def calibrated_policy(state: str):
    return replace(
        get_preprocess_policy("DSC"),
        calibrated=True,
        automation_state=state,
    )


def test_missing_instrument_metadata_disables_experience_and_caps_confidence() -> None:
    orchestrator = build_fake_dsc_orchestrator()
    orchestrator.workspace_context = {}

    report = orchestrator.run_preprocess_intent(preprocess_intent("baseline"))

    assert report["preprocess_experience"]["retrieval_used"] is False
    assert report["preprocess_decision"]["confidence_band"] != "high"


def test_confirm_only_returns_pending_config_without_mutating_best() -> None:
    orchestrator = build_fake_dsc_orchestrator()
    orchestrator.preprocess_policy = calibrated_policy("confirm_only")
    before = orchestrator._config_to_dict(orchestrator._best_config)

    report = orchestrator.run_preprocess_intent(preprocess_intent("smoothing"))

    assert report["preprocess_decision"]["decision"] == "request_confirmation"
    assert report["pending_preprocess_config"]
    assert orchestrator._config_to_dict(orchestrator._best_config) == before


def test_tiered_high_confidence_commits_only_after_hash_recheck(tmp_path) -> None:
    orchestrator = build_fake_dsc_orchestrator()
    orchestrator.preprocess_policy = calibrated_policy("tiered_auto")
    orchestrator.preprocess_audit_log = DecisionAuditLog(tmp_path / "decisions.jsonl")

    report = orchestrator.run_preprocess_intent(preprocess_intent("baseline"))

    assert report["preprocess_decision"]["decision"] == "auto_accept"
    assert report["best_config"] == report["selected_preprocess_config"]
    assert orchestrator.preprocess_audit_log.read_all()[0]["decision"] == "auto_accept"
    assert report["experience_proposal"]


def test_hash_change_prevents_auto_commit_and_preserves_best(tmp_path) -> None:
    orchestrator = build_fake_dsc_orchestrator()
    orchestrator.preprocess_policy = calibrated_policy("tiered_auto")
    orchestrator.preprocess_audit_log = DecisionAuditLog(tmp_path / "decisions.jsonl")
    original_commit = orchestrator._commit_preprocess_candidate
    before = deepcopy(orchestrator._config_to_dict(orchestrator._best_config))

    def mutate_before_commit(engine, candidate, expected_hash):
        orchestrator._best_config.smooth_window = 13
        return original_commit(engine, candidate, expected_hash)

    orchestrator._commit_preprocess_candidate = mutate_before_commit
    report = orchestrator.run_preprocess_intent(preprocess_intent("baseline"))

    assert report["preprocess_decision"]["decision"] == "keep_original"
    assert "config_hash_changed" in report["preprocess_decision"]["reason_codes"]
    # Restore the injected concurrent mutation to compare the accepted snapshot.
    orchestrator._best_config.smooth_window = before["smooth_window"]
    assert orchestrator._config_to_dict(orchestrator._best_config) == before


def test_invalid_intent_is_also_audited(tmp_path) -> None:
    orchestrator = build_fake_dsc_orchestrator()
    orchestrator.preprocess_audit_log = DecisionAuditLog(tmp_path / "decisions.jsonl")
    payload = preprocess_intent()
    payload["desired_effect"] = "maximum"

    report = orchestrator.run_preprocess_intent(payload)

    rows = orchestrator.preprocess_audit_log.read_all()
    assert len(rows) == 1
    assert rows[0]["decision"] == "keep_original"
    assert report["decision_record"]["reason_codes"]
