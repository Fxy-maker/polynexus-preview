from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from polynexus.core.preprocess_optimization import stable_config_hash
from polynexus.core.saxs_engine.saxs_ai_rescue import (
    assess_saxs_confirmed_rerun,
    build_saxs_confirmed_rerun_evidence,
    validate_saxs_confirmation_report,
)
from polynexus.gui.preprocess_transaction_service import PreprocessTransactionService


def _frame(
    *,
    source_index: int = 0,
    level: str = "Quantitative",
    quality_flag: str = "OK",
    orientation: dict[str, Any] | None = None,
    strain_pct: float | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        source_index=source_index,
        data_quality_report={"level": level, "source_id": f"frame-{source_index}"},
        guinier_evidence={"level": level, "rg_nm": 4.0, "value": np.nan},
        metric_evidence={"porod": {"level": level, "value": 1.2}},
        detector_quality_report={"level": level, "source_kind": "sector_map"},
        orientation_evidence=orientation or {"level": level, "metric_name": "Herman"},
        quality_flag=quality_flag,
        Q_star_valid=True,
        strain_pct=strain_pct,
    )


def _static_result(*, level: str = "Quantitative", quality_flag: str = "OK") -> SimpleNamespace:
    return _frame(level=level, quality_flag=quality_flag)


def _temperature_result(*, level: str = "Quantitative") -> SimpleNamespace:
    points = [_frame(source_index=1, level=level), _frame(source_index=0, level=level)]
    return SimpleNamespace(
        temp_points=points,
        guinier_sequence_evidence={
            "level": "Trend",
            "frame_source_indices": [1, 0],
            "valid_frame_count": 2,
        },
        metric_evidence={"porod": {"level": "Trend", "frame_count": 2}},
        detector_quality_report={"level": "Trend"},
        orientation_evidence={"level": "Trend", "metric_name": "Herman"},
    )


def _strain_result(*, level: str = "Quantitative") -> SimpleNamespace:
    points = [
        _frame(source_index=0, level=level, strain_pct=0.0),
        _frame(source_index=1, level=level, strain_pct=2.0),
    ]
    return SimpleNamespace(
        strain_points=points,
        metric_evidence={"porod": {"level": "Trend", "frame_count": 2}},
        detector_quality_report={"level": "Trend"},
        orientation_evidence={"level": "Trend", "metric_name": "Herman"},
    )


def _report(*, mode: str = "static", candidate_id: str = "candidate-1", config: dict[str, Any] | None = None) -> dict[str, Any]:
    current = config or {"smooth_window": 11}
    return {
        "mode": mode,
        "preprocess_decision": {
            "decision": "request_confirmation",
            "hard_guard_results": {"negative_fraction": True, "physical_parameters": True},
        },
        "selected_candidate_id": candidate_id,
        "selected_preprocess_config": {"smooth_window": 15},
        "original_preprocess_config": deepcopy(current),
        "preprocess_candidates": [
            {
                "candidate_id": candidate_id,
                "base_config_hash": stable_config_hash(current),
                "config_delta": {"smooth_window": 15},
            }
        ],
        "experience_proposal": {"experience_id": "experience-1"},
    }


def test_confirmed_rerun_evidence_is_detached_and_strict_json_safe() -> None:
    result = _static_result()
    payload = build_saxs_confirmed_rerun_evidence(result, mode="static")

    json.dumps(payload, allow_nan=False)
    assert payload["frames"][0]["guinier_evidence"]["value"] is None
    result.metric_evidence["porod"]["level"] = "Unusable"
    assert payload["frames"][0]["metric_evidence"]["porod"]["level"] == "Quantitative"
    assert '"q":' not in json.dumps(payload)


@pytest.mark.parametrize(
    ("mode", "result"),
    [
        ("static", _static_result()),
        ("temperature", _temperature_result()),
        ("strain", _strain_result()),
    ],
)
def test_existing_saxs_gates_accept_all_three_modes(mode: str, result: Any) -> None:
    assessment = assess_saxs_confirmed_rerun(result, mode=mode)

    assert assessment["accepted"] is True
    assert assessment["physical_gate_status"] == "passed"
    assert assessment["quality_gate_status"] == "passed"


def test_temperature_keeps_source_indices_and_does_not_promote_trend() -> None:
    payload = build_saxs_confirmed_rerun_evidence(_temperature_result(), mode="temperature")

    assert [row["source_index"] for row in payload["frames"]] == [1, 0]
    assert payload["series"]["guinier_sequence_evidence"]["frame_source_indices"] == [1, 0]
    assert payload["frames"][0]["data_quality_report"]["level"] == "Quantitative"


def test_strain_keeps_orientation_separate_from_metric_evidence() -> None:
    payload = build_saxs_confirmed_rerun_evidence(_strain_result(), mode="strain")

    assert "orientation_evidence" in payload["series"]
    assert "orientation" not in payload["series"].get("metric_evidence", {})
    assert [row["strain_pct"] for row in payload["frames"]] == [0.0, 2.0]


@pytest.mark.parametrize(
    "mutator",
    [
        lambda report: report.update({"selected_candidate_id": "other"}),
        lambda report: report["preprocess_candidates"][0].update({"base_config_hash": "wrong"}),
        lambda report: report["preprocess_decision"]["hard_guard_results"].update({"physical_parameters": False}),
        lambda report: report["preprocess_decision"].update({"decision": "keep_original"}),
        lambda report: report["selected_preprocess_config"].update({"smooth_window": 17}),
    ],
)
def test_confirmation_identity_rejects_mismatch_before_rerun(mutator) -> None:
    report = _report()
    mutator(report)

    with pytest.raises(ValueError):
        validate_saxs_confirmation_report(
            report,
            current_config={"smooth_window": 11},
            mode="static",
        )


@dataclass
class _Harness:
    config: dict[str, Any]
    result: Any
    rerun_result: Any
    rerun_calls: int = 0
    persisted: int = 0
    persist_failure: bool = False
    restore_failure: bool = False

    def __post_init__(self) -> None:
        self.original_result = self.result
        self.applied: list[dict[str, Any]] = []
        self.service = PreprocessTransactionService(
            capture_config=lambda keys: {key: self.config[key] for key in keys},
            apply_config=self._apply,
            get_result=lambda: self.result,
            set_result=self._set_result,
            rerun=self._rerun,
            persist_experience=self._persist,
            revoke_experience=lambda _experience_id: True,
            technique="SAXS",
            validate_confirmation=validate_saxs_confirmation_report,
            validate_rerun=lambda result: assess_saxs_confirmed_rerun(result, mode="static"),
        )

    def _apply(self, config: dict[str, Any]) -> None:
        if self.restore_failure and config.get("smooth_window") == 11:
            raise RuntimeError("restore failed")
        self.applied.append(deepcopy(config))
        self.config.update(config)

    def _persist(self, *_args, **_kwargs) -> str:
        return "" if self.persist_failure else "experience-1"

    def _set_result(self, result: Any) -> None:
        self.result = result

    def _rerun(self) -> None:
        self.rerun_calls += 1
        self.result = self.rerun_result


def test_transaction_persists_only_after_post_gate_and_records_audit() -> None:
    harness = _Harness({"smooth_window": 11}, _static_result(), _static_result())

    assert harness.service.begin_confirmation(_report(), accepted_by="user_confirmed")
    assert harness.rerun_calls == 1
    assert harness.service.finalize_success(harness.rerun_result) is True
    assert harness.service.state.phase == "applied"
    assert harness.service.state.apply_performed is True
    assert harness.service.state.audit["physical_gate_status"] == "passed"


@pytest.mark.parametrize("level", ["Diagnostic", "Unusable"])
def test_missing_or_weak_evidence_rolls_back_without_experience(level: str) -> None:
    harness = _Harness({"smooth_window": 11}, _static_result(), _static_result(level=level))

    assert harness.service.begin_confirmation(_report(), accepted_by="user_confirmed")
    assert harness.service.finalize_success(harness.rerun_result) is False
    assert harness.config == {"smooth_window": 11}
    assert harness.result is harness.original_result
    assert harness.service.state.apply_performed is False


def test_candidate_config_delta_is_bound_to_selected_config() -> None:
    report = _report()
    report["preprocess_candidates"][0]["config_delta"] = {"smooth_window": 17}

    with pytest.raises(ValueError, match="config mismatch"):
        validate_saxs_confirmation_report(
            report,
            current_config={"smooth_window": 11},
            mode="static",
        )


def test_selected_config_hash_drift_rolls_back_and_never_persists() -> None:
    harness = _Harness({"smooth_window": 11}, _static_result(), _static_result())

    assert harness.service.begin_confirmation(_report(), accepted_by="user_confirmed")
    harness.config["smooth_window"] = 17
    assert harness.service.finalize_success(harness.rerun_result) is False
    assert harness.config == {"smooth_window": 11}
    assert harness.service.state.apply_performed is False


def test_existing_physical_gate_failure_rolls_back_without_persisting() -> None:
    failed = _static_result(quality_flag="ERROR:qstar_contaminated")
    harness = _Harness({"smooth_window": 11}, _static_result(), failed)

    assert harness.service.begin_confirmation(_report(), accepted_by="user_confirmed")
    assert harness.service.finalize_success(failed) is False
    assert harness.config == {"smooth_window": 11}
    assert harness.result is harness.original_result
    assert harness.service.state.audit["apply_performed"] is False
    json.dumps(harness.service.state.audit, allow_nan=False)


def test_restore_failure_is_not_reported_as_a_successful_apply() -> None:
    failed = _static_result(level="Diagnostic")
    harness = _Harness(
        {"smooth_window": 11},
        _static_result(),
        failed,
        restore_failure=True,
    )

    assert harness.service.begin_confirmation(_report(), accepted_by="user_confirmed")
    assert harness.service.finalize_success(failed) is False
    assert harness.service.state.audit["phase"] == "failed"
    assert harness.service.state.audit["apply_performed"] is False
    assert harness.service.state.audit["rollback_reason"].startswith("restore_failed")


def test_experience_persistence_failure_is_explicitly_audited() -> None:
    harness = _Harness(
        {"smooth_window": 11},
        _static_result(),
        _static_result(),
        persist_failure=True,
    )

    assert harness.service.begin_confirmation(_report(), accepted_by="user_confirmed")
    assert harness.service.finalize_success(harness.rerun_result) is True
    assert harness.service.state.apply_performed is True
    assert harness.service.state.experience_id == ""
    assert harness.service.state.audit["rollback_reason"] == "experience_persistence_failed"


def test_undo_revokes_experience_only_after_valid_undo_rerun() -> None:
    harness = _Harness({"smooth_window": 11}, _static_result(), _static_result())

    assert harness.service.begin_confirmation(_report(), accepted_by="user_confirmed")
    assert harness.service.finalize_success(harness.rerun_result)
    assert harness.service.undo()
    assert harness.service.state.phase == "undo_pending"
    assert harness.service.finalize_success(harness.rerun_result)
    assert harness.service.state.phase == "undone"
    assert harness.service.state.apply_performed is False
