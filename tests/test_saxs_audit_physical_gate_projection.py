from __future__ import annotations

import copy
import json

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    build_saxs_scientific_acceptance_audit,
)


def test_audit_projects_existing_physical_checks_and_passing_method_gate():
    parameters = {
        "metric_evidence": {
            "guinier": {
                "level": "Trend",
                "applicable": True,
                "physical_checks": {
                    "qrg_gate": True,
                    "method_gate_passed": True,
                },
            }
        }
    }

    audit = build_saxs_scientific_acceptance_audit(True, parameters)

    assert audit["physical_gate_evidence"]["metric:guinier"] == [
        {"qrg_gate": True, "method_gate_passed": True}
    ]
    assert audit["method_gate_status"]["metric:guinier"] == [True]
    assert "method_gate_failed" not in audit["reason_codes"]


def test_audit_records_failed_gate_without_mutating_metric_payload():
    parameters = {
        "metric_evidence": {
            "porod": {
                "level": "Diagnostic",
                "applicable": False,
                "physical_checks": {
                    "method_gate_passed": False,
                    "slope_supported": False,
                },
            }
        }
    }
    before = copy.deepcopy(parameters)

    audit = build_saxs_scientific_acceptance_audit(True, parameters)

    assert audit["method_gate_status"]["metric:porod"] == [False]
    assert "method_gate_failed" in audit["reason_codes"]
    assert parameters == before


def test_applicable_metric_without_gate_is_not_treated_as_passed():
    audit = build_saxs_scientific_acceptance_audit(
        True,
        {
            "metric_evidence": {
                "kratky": {
                    "level": "Trend",
                    "applicable": True,
                    "physical_checks": {},
                }
            }
        },
    )

    assert audit["method_gate_status"]["metric:kratky"] == [None]
    assert "method_gate_not_assessed" in audit["reason_codes"]
    assert audit["status"] == "review_required"


def test_non_boolean_method_gate_is_recorded_as_unknown():
    audit = build_saxs_scientific_acceptance_audit(
        True,
        {
            "metric_evidence": {
                "lamellar": {
                    "level": "Trend",
                    "physical_checks": {"method_gate_passed": "yes"},
                }
            }
        },
    )

    assert audit["method_gate_status"]["metric:lamellar"] == [None]
    assert "method_gate_not_assessed" in audit["reason_codes"]


def test_physical_gate_projection_is_strict_json_safe():
    audit = build_saxs_scientific_acceptance_audit(
        True,
        {
            "metric_evidence": {
                "invariant": {
                    "level": "Trend",
                    "physical_checks": {"finite": True},
                }
            }
        },
    )

    json.dumps(audit, allow_nan=False)
