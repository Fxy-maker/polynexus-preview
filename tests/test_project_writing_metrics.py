from __future__ import annotations

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
