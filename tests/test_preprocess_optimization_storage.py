from __future__ import annotations

import json

import pytest

from polynexus.core.preprocess_optimization import DecisionRecord
from polynexus.core.preprocess_optimization.audit import (
    AuditLogError,
    DecisionAuditLog,
)
from polynexus.core.preprocess_optimization.experience import (
    ExperienceKey,
    ExperienceRecord,
    ExperienceStore,
    ExperienceStoreError,
)


def _key(instrument: str = "inst-a") -> ExperienceKey:
    return ExperienceKey(
        technique="DSC",
        instrument_fingerprint=instrument,
        sample_family="PA6",
        schema_version="1.0",
        core_major_version="1",
    )


def _experience(experience_id: str = "exp-1") -> ExperienceRecord:
    return ExperienceRecord(
        experience_id=experience_id,
        key=_key(),
        config_delta={"smooth_window": 9},
        accepted_by="user_confirmed",
        evidence_summary={"noise_reduction": 0.2, "weak_peak_retention": 1.0},
        intent_summary={"target": "smoothing", "desired_effect": "medium"},
        symptom_names=("noise_dominant",),
    )


def _decision() -> DecisionRecord:
    return DecisionRecord(
        schema_version="1.0",
        analysis_id="case-1",
        original_config_hash="hash-1",
        selected_candidate_id="candidate-1",
        decision="request_confirmation",
        confidence_band="medium",
        score_components={"signal_preservation": 0.95},
        hard_guard_results={"coverage": True},
        evidence_refs=("candidate-1",),
        policy_version="dsc-v1",
        core_version="1",
        reason_codes=("confirmation_required",),
    )


def test_experience_is_scoped_and_revocation_removes_it_from_retrieval(tmp_path) -> None:
    store = ExperienceStore(tmp_path / "experience.json")
    store.accept(_experience())

    assert [item.experience_id for item in store.retrieve(_key())] == ["exp-1"]
    assert store.retrieve(_key("inst-b")) == []

    assert store.revoke("exp-1") is True
    assert store.retrieve(_key()) == []
    assert store.all_records()[0].revoked is True


def test_experience_scope_normalization_is_case_and_space_insensitive(tmp_path) -> None:
    store = ExperienceStore(tmp_path / "experience.json")
    store.accept(_experience())

    equivalent = ExperienceKey(" dsc ", " INST-A ", " pa6 ", "1.0", "1")

    assert [item.experience_id for item in store.retrieve(equivalent)] == ["exp-1"]


def test_experience_rejects_unconfirmed_positive_memory(tmp_path) -> None:
    store = ExperienceStore(tmp_path / "experience.json")
    record = ExperienceRecord(
        experience_id="exp-bad",
        key=_key(),
        config_delta={"smooth_window": 9},
        accepted_by="llm_suggested",
    )

    with pytest.raises(ExperienceStoreError, match="accepted_by"):
        store.accept(record)


def test_corrupt_experience_file_fails_closed(tmp_path) -> None:
    path = tmp_path / "experience.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ExperienceStoreError, match="corrupt"):
        ExperienceStore(path).retrieve(_key())


def test_experience_write_is_atomic_and_leaves_no_temp_file(tmp_path) -> None:
    path = tmp_path / "experience.json"
    ExperienceStore(path).accept(_experience())

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["records"][0]["experience_id"] == "exp-1"
    assert list(tmp_path.glob("*.tmp")) == []


def test_audit_append_survives_reopen(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    DecisionAuditLog(path).append(_decision())

    rows = DecisionAuditLog(path).read_all()

    assert rows[0]["analysis_id"] == "case-1"
    assert rows[0]["reason_codes"] == ["confirmation_required"]


def test_audit_log_rejects_corrupt_lines(tmp_path) -> None:
    path = tmp_path / "audit.jsonl"
    path.write_text('{"analysis_id":"ok"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(AuditLogError, match="line 2"):
        DecisionAuditLog(path).read_all()
