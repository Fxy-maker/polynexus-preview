from __future__ import annotations

import json
from dataclasses import replace

import pytest

from polynexus.core.preprocess_optimization import get_preprocess_policy
from polynexus.core.preprocess_optimization.calibration import (
    PolicyConfigError,
    calibrate_cases,
    load_policy_config,
    report_sha256,
    write_calibration_report,
)


def _saxs_case(**overrides: object) -> dict[str, object]:
    case: dict[str, object] = {
        "case_schema_version": "1.0",
        "case_id": "saxs-static-1",
        "mode": "static",
        "source_ref": "synthetic:saxs-noisy",
        "original_config_hash": "original-hash",
        "effective_config_hash": "candidate-hash",
        "selected": True,
        "hard_guard_violation": False,
        "expert_accept": True,
        "expert_reason": "Preserves the Guinier and peak evidence.",
        "evidence_coverage": 1.0,
        "confidence_band": "high",
        "metric_drifts": {"peak_shift": 0.01},
    }
    case.update(overrides)
    return case


def test_calibration_report_cannot_promote_with_hard_guard_false_accept() -> None:
    report = calibrate_cases(
        [
            {
                "case_id": "bad-1",
                "selected": True,
                "hard_guard_violation": True,
                "expert_accept": False,
                "evidence_coverage": 1.0,
            }
        ],
        policy=get_preprocess_policy("DSC"),
    )

    assert report.promotion_allowed is False
    assert "hard_guard_false_accept" in report.blockers


def test_policy_loader_requires_matching_report_hash(tmp_path) -> None:
    config = {
        "schema_version": "1.0",
        "generator_version": "1",
        "core_major_version": "1",
        "profiles": {
            "DSC": {
                "policy_version": "dsc-preprocess-v1",
                "automation_state": "tiered_auto",
                "calibrated": True,
                "calibration_report": "",
                "calibration_report_sha256": "",
            }
        },
    }
    path = tmp_path / "policies.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(PolicyConfigError, match="calibration report"):
        load_policy_config(path, base_policies={"DSC": get_preprocess_policy("DSC")})


def test_loader_accepts_only_matching_technique_and_versions(tmp_path) -> None:
    policy = get_preprocess_policy("DSC")
    report = calibrate_cases(
        [
            {
                "case_id": f"good-{index}",
                "selected": True,
                "hard_guard_violation": False,
                "expert_accept": True,
                "evidence_coverage": 1.0,
                "confidence_band": "high",
                "metric_drifts": {"peak_shift": 0.01},
            }
            for index in range(5)
        ],
        policy=policy,
    )
    report_path = tmp_path / "dsc-report.json"
    write_calibration_report(report_path, report)
    config = {
        "schema_version": "1.0",
        "generator_version": "1",
        "core_major_version": "1",
        "profiles": {
            "DSC": {
                "policy_version": policy.policy_version,
                "automation_state": "tiered_auto",
                "calibrated": True,
                "calibration_report": report_path.name,
                "calibration_report_sha256": report_sha256(report_path),
            }
        },
    }
    config_path = tmp_path / "policies.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    loaded = load_policy_config(config_path, base_policies={"DSC": policy})

    assert loaded["DSC"].automation_state == "tiered_auto"
    assert loaded["DSC"].calibrated is True

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["technique"] = "IR"
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    config["profiles"]["DSC"]["calibration_report_sha256"] = report_sha256(report_path)
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(PolicyConfigError, match="technique"):
        load_policy_config(config_path, base_policies={"DSC": policy})


def test_good_report_promotes_only_its_own_technique_and_versions() -> None:
    policy = replace(get_preprocess_policy("DSC"), calibrated=False)
    report = calibrate_cases(
        [
            {
                "case_id": f"good-{index}",
                "selected": index % 2 == 0,
                "hard_guard_violation": False,
                "expert_accept": index % 2 == 0,
                "evidence_coverage": 0.98,
                "confidence_band": "medium",
                "metric_drifts": {"peak_shift": 0.01 * index},
            }
            for index in range(5)
        ],
        policy=policy,
    )

    assert report.technique == "DSC"
    assert report.schema_version == "1.0"
    assert report.policy_version == "dsc-preprocess-v1"
    assert report.promotion_allowed is True


def test_saxs_calibration_requires_a_versioned_expert_case_reason() -> None:
    report = calibrate_cases(
        [
            {
                "case_schema_version": "1.0",
                "case_id": "saxs-static-1",
                "mode": "static",
                "source_ref": "synthetic:saxs-noisy",
                "original_config_hash": "original-hash",
                "effective_config_hash": "candidate-hash",
                "selected": True,
                "hard_guard_violation": False,
                "expert_accept": True,
                "evidence_coverage": 1.0,
                "confidence_band": "high",
                "metric_drifts": {"peak_shift": 0.01},
            }
        ],
        policy=get_preprocess_policy("SAXS"),
    )

    assert report.promotion_allowed is False
    assert "invalid_case_contract" in report.blockers


def test_saxs_calibration_accepts_a_complete_expert_case() -> None:
    report = calibrate_cases([_saxs_case()], policy=get_preprocess_policy("SAXS"))

    assert report.promotion_allowed is True
    assert report.blockers == ()


def test_saxs_calibration_blocks_low_coverage_and_expert_disagreement() -> None:
    report = calibrate_cases(
        [
            _saxs_case(evidence_coverage=0.5),
            _saxs_case(case_id="saxs-static-2", selected=False, expert_accept=True),
        ],
        policy=get_preprocess_policy("SAXS"),
    )

    assert report.promotion_allowed is False
    assert "insufficient_evidence_coverage" in report.blockers
    assert "insufficient_expert_agreement" in report.blockers
