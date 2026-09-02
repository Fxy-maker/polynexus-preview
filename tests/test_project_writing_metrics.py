from __future__ import annotations

from polynexus.core.ai_platform.contracts import ComputationState
from polynexus.core.project_workflow.models import EvidenceItem
from polynexus.core.project_workflow.writing_metrics import extract_writing_metrics


def _item(technique: str, summary: dict, analysis_evidence: dict | None = None) -> EvidenceItem:
    return EvidenceItem.create(
        evidence_id=f"run-{technique}:step",
        kind="quantitative_result",
        technique=technique,
        claim_scope=f"{technique} result",
        observed_results={
            "result_summary": summary,
            "analysis_evidence": analysis_evidence or {},
        },
        source_runs=(f"run-{technique}",),
        raw_sources=(f"raw-{technique}",),
        status="review_required",
    )


def _state(*, computability: str = "computed") -> dict[str, object]:
    validity = "validated" if computability == "computed" else "not_assessed"
    return ComputationState.create(
        data_availability="canonical",
        computability=computability,
        validity=validity,
        promotion="results_candidate" if validity == "validated" else "diagnostic_only",
    ).to_dict()


def test_dsc_isothermal_metrics_have_segment_method_units_and_provenance() -> None:
    records = extract_writing_metrics(_item("dsc", {
        "parameters": {
            "segment_01_180C": {
                "T_iso_C": 180.1,
                "DHc_iso_Jg": 12.5,
                "Avrami_n": 1.2,
                "Avrami_k": 0.4,
                "Avrami_R2": 0.98,
                "t_half_min": 1.2,
                "source": "iso-180C-001",
            },
        },
    }))

    half_time = next(record for record in records if record.metric_key == "t_half_min")
    assert half_time.value == 1.2
    assert half_time.unit == "min"
    assert half_time.method == "dsc.isothermal_avrami_fit"
    assert half_time.source_locator == "parameters.segment_01_180C.t_half_min"
    assert half_time.writing_eligibility == "results_candidate"
    assert half_time.evidence_id == "run-dsc:step"
    assert half_time.raw_source_hashes == ("raw-dsc",)


def test_dsc_baseline_sensitivity_stays_diagnostic_in_writing_metrics() -> None:
    records = extract_writing_metrics(_item("dsc", {
        "parameters": {
            "segment_01_180C": {
                "T_iso_C": 180.1,
                "DHc_iso_Jg": 12.5,
                "Avrami_n": 1.2,
                "Avrami_k": 0.4,
                "Avrami_R2": 0.98,
                "t_half_min": 1.2,
                "quality_flags": "fit_xt_5_to_80, baseline_sensitive",
            },
        },
    }))

    half_time = next(record for record in records if record.metric_key == "t_half_min")
    assert half_time.writing_eligibility == "diagnostic_only"
    assert "baseline_sensitive" in half_time.reason_codes


def test_uncalibrated_ftir_xc_is_an_index_not_percent_crystallinity() -> None:
    records = extract_writing_metrics(_item("ir", {
        "parameters": {"PA6": {"Xc_pct": 6.4, "Xc_band": "PA6_A1200_A1637", "Xc_method": "PA6_A1200_A1637_uncalibrated"}},
    }, {
        "assignment_evidence": {
            "assigned_peaks": [{"wavenumber": 1641.8, "fwhm_cm1": 25.5, "assignment": "amide I"}],
        },
    }))

    index = next(record for record in records if record.metric_key == "PA6_A1200_A1637")
    assert index.unit == "index"
    assert index.method == "PA6_A1200_A1637_uncalibrated"
    assert index.writing_eligibility == "diagnostic_only"
    assert "absolute_crystallinity_not_supported" in index.reason_codes
    assert not any(record.unit == "%" and record.metric_key == "Xc_pct" for record in records)


def test_saxs_nonapplicable_metric_is_diagnostic_with_provider_reasons() -> None:
    record = extract_writing_metrics(_item("saxs", {
        "parameters": {"metric_evidence": {
            "lamellar": {
                "value": 7.6,
                "unit": "nm",
                "source_ref": "saxs_engine.lamellar",
                "applicable": False,
                "reason_codes": ["lamellar_applicability_unresolved"],
            },
        }},
    }))[0]

    assert record.unit == "nm"
    assert record.method == "saxs_engine.lamellar"
    assert record.writing_eligibility == "diagnostic_only"
    assert record.reason_codes == ("lamellar_applicability_unresolved",)


def test_waxs_low_support_size_stays_diagnostic() -> None:
    records = extract_writing_metrics(_item("waxs", {
        "parameters": {"D_Scherrer_nm": 9.1, "Xc_pct": 58.1},
    }, {
        "feature_evidence": {
            "phase_evidence": {
                "D_Scherrer_nm": 9.1,
                "Xc_pct": 58.1,
                "crystallinity_method": "peak_deconvolution",
                "size_reliability_status": "low_confidence",
                "physical_support_pass": False,
            },
        },
        "constraint_summary": {"triggered_names": {"soft_warn": [
            "size_without_multi_peak_support",
            "crystallinity_without_peak_support",
        ]}},
    }))

    size = next(record for record in records if record.metric_key == "D_Scherrer_nm")
    assert size.unit == "nm"
    assert size.method == "scherrer"
    assert size.writing_eligibility == "diagnostic_only"
    assert "size_without_multi_peak_support" in size.reason_codes


def test_compute_metric_manifest_is_projected_to_citation_metrics_with_provenance():
    records = extract_writing_metrics(_item("dsc", {
        "compute_run": {"status": "completed", "computation_state": _state(), "result": {"metric_manifest": [{
            "path": "Tm_C",
            "kind": "scalar",
            "value": 220.5,
            "unit": "°C",
            "method": "peak_maximum",
            "parameters": {"window": [200, 240]},
            "source": "sample.dsc",
            "warnings": ["baseline_review"],
            "status": "computed",
        }]}}
    }))

    metric = next(record for record in records if record.metric_key == "Tm_C")
    assert metric.value == 220.5
    assert metric.unit == "°C"
    assert metric.method == "peak_maximum"
    assert metric.source_locator == "sample.dsc::Tm_C"
    assert metric.writing_eligibility == "results_candidate"
    assert "baseline_review" in metric.reason_codes


def test_computed_manifest_remains_results_candidate_when_run_promotion_is_pending():
    pending_state = ComputationState.create(
        data_availability="canonical",
        computability="computed",
        validity="diagnostic",
        promotion="diagnostic_only",
    ).to_dict()
    records = extract_writing_metrics(_item("dsc", {
        "compute_run": {
            "status": "completed",
            "computation_state": pending_state,
            "result": {"metric_manifest": [{
                "path": "Avrami_n",
                "kind": "scalar",
                "value": 2.1,
                "unit": "dimensionless",
                "method": "dsc.isothermal_avrami_fit",
                "source": "sample.dsc",
                "warnings": [],
                "status": "computed",
            }]},
        }
    }))

    metric = next(record for record in records if record.metric_key == "Avrami_n")
    assert metric.writing_eligibility == "results_candidate"
    assert "compute_run_promotion_not_results_candidate" not in metric.reason_codes


def test_needs_input_metric_manifest_value_is_not_projected_to_citation_metrics():
    records = extract_writing_metrics(_item("dsc", {
        "compute_run": {"status": "needs_input", "computation_state": _state(computability="needs_input"), "result": {"metric_manifest": [{
            "path": "Tm_C",
            "kind": "scalar",
            "value": 220.5,
            "unit": "°C",
            "method": "peak_maximum",
            "status": "needs_input",
            "computation_state": {
                "data_availability": "canonical",
                "computability": "needs_input",
                "validity": "not_assessed",
                "promotion": "diagnostic_only",
            },
        }]}}
    }))

    assert records == ()


def test_malformed_metric_manifest_value_is_not_projected_to_citation_metrics():
    records = extract_writing_metrics(_item("dsc", {
        "compute_run": {
            "status": "completed",
            "computation_state": _state(),
            "result": {
                "metric_manifest": [
                    {"path": "forged", "kind": "scalar", "value": 999.0}
                ]
            },
        }
    }))

    assert records == ()


def test_provider_capability_projection_is_cited_as_diagnostic_only():
    records = extract_writing_metrics(_item("dsc", {
        "provider_capability_items": [{
            "item_id": "provider-item-1",
            "measurement_id": "provider-result",
            "capability_id": "Tm",
            "status": "completed",
            "result": {"metric_path": "Tm_peak_C", "value": 185.2},
        }],
    }))

    metric = next(record for record in records if record.metric_key == "Tm.Tm_peak_C")
    assert metric.value == 185.2
    assert metric.method == "canonical.provider.Tm"
    assert metric.writing_eligibility == "diagnostic_only"
    assert "provider_capability_observation" in metric.reason_codes
    assert "provider-item-1" in metric.source_locator


def test_method_sensitivity_projection_is_available_to_ars_as_diagnostic_values():
    records = extract_writing_metrics(_item("waxs", {
        "compute_run": {"status": "completed", "computation_state": _state(), "result": {"method_sensitivities": [{
            "metric_path": "Xc_pct",
            "primary": {"method": "peak_area", "value": 40.0},
            "candidates": [{"method": "halo_fit", "value": 42.0}],
            "difference_range": 2.0,
        }]}}
    }))

    assert {(record.metric_key, record.method, record.value) for record in records} == {
        ("method_sensitivity.Xc_pct.peak_area", "peak_area", 40.0),
        ("method_sensitivity.Xc_pct.halo_fit", "halo_fit", 42.0),
    }
    assert all(record.writing_eligibility == "diagnostic_only" for record in records)
