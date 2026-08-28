import numpy as np
import pytest

from polynexus.core.canonical_experiments import (
    CanonicalExperiment,
    ConversionRecord,
    convert_mettler_isothermal_text,
)
from polynexus.core.dsc import DSCEngine
from polynexus.core.dsc_engine.core import DSCResult
from polynexus.core.dsc_engine.dsc_kinetics import (
    AvramiResult,
    _baseline_variant,
    analyze_isothermal_scans,
    avrami_candidates_from_dsc,
    avrami_from_dsc,
    detect_isothermal_segments,
)
from polynexus.core.dsc_engine.io import DSCScan
from polynexus.core.dsc_engine.figure_isothermal import build_isothermal_dsc_figure_definitions


def _avrami_heat_flow(t, n=3.0, k=0.025, scale=1.0, baseline=0.02):
    tt = np.maximum(t, 1e-9)
    dXdt = n * k * tt ** (n - 1) * np.exp(-k * tt ** n)
    return baseline + scale * dXdt


def test_avrami_from_dsc_recovers_synthetic_parameters():
    t = np.linspace(0.0, 30.0, 1500)
    HF = _avrami_heat_flow(t, n=3.0, k=0.025)

    result = avrami_from_dsc(t, HF)

    assert abs(result.n - 3.0) < 0.08
    assert abs(result.k - 0.025) < 0.003
    assert result.r_squared > 0.999
    assert result.crystallisation_enthalpy_Jg > 0


def test_avrami_from_dsc_ignores_material_neutral_switching_transient():
    """A fast hold-entry transient must not become the crystallisation event."""
    t = np.linspace(0.0, 12.0, 721)
    # A generic instrument transition decays immediately after the hold starts;
    # the actual exotherm begins only after the transition has settled.
    transient = 8.0 * np.exp(-t / 0.12)
    crystallisation = _avrami_heat_flow(np.maximum(t - 1.0, 0.0), n=2.8, k=0.13, scale=2.0)
    heat = 0.15 + transient + np.where(t >= 1.0, crystallisation - 0.02, 0.0)

    result = avrami_from_dsc(t, heat)

    assert result.start_time_min >= 0.8
    assert result.t_half_min > 1.0
    assert abs(result.n - 2.8) < 0.35


def test_avrami_fit_defaults_to_five_to_eighty_percent_conversion_window():
    t = np.linspace(0.0, 30.0, 1500)
    result = avrami_from_dsc(t, _avrami_heat_flow(t, n=3.0, k=0.025))

    assert result.quality_flags.count("fit_xt_5_to_80") == 1


def test_avrami_uses_endpoint_linear_baseline_and_retains_tail_variant():
    t = np.linspace(0.0, 12.0, 721)
    transient = 8.0 * np.exp(-t / 0.12)
    crystallisation = _avrami_heat_flow(np.maximum(t - 1.0, 0.0), n=2.8, k=0.13, scale=2.0)
    heat = 0.15 + transient + np.where(t >= 1.0, crystallisation - 0.02, 0.0)

    result = avrami_from_dsc(t, heat)

    assert result.baseline_method == "endpoint_linear"
    assert result.baseline_variants
    assert {item["method"] for item in result.baseline_variants} >= {
        "endpoint_linear", "tail_constant"
    }
    assert result.baseline_selection_reason
    assert np.isfinite(result.baseline_slope_Wg_per_min)


def test_avrami_falls_back_to_tail_baseline_without_pre_event_window():
    t = np.linspace(0.0, 10.0, 501)
    heat = _avrami_heat_flow(t, n=2.4, k=0.08, scale=1.5)

    result = avrami_from_dsc(t, heat)

    assert np.isfinite(result.n)
    assert result.baseline_method == "tail_constant"
    assert "endpoint_baseline_unavailable" in result.quality_flags


def test_tail_baseline_records_its_actual_segment_end_window_and_zero_slope():
    t = np.linspace(0.0, 10.0, 101)
    heat = np.exp(-((t - 5.0) / 1.5) ** 2)
    heat[81:] = -0.5

    variant = _baseline_variant(t, heat, 20, 80, 1.0, "tail_constant")

    assert variant["available"] is True
    assert variant["baseline_window_start_index"] == 91
    assert variant["baseline_window_end_index"] == 100
    assert variant["baseline_start_value_Wg"] == pytest.approx(variant["baseline_end_value_Wg"])
    assert variant["baseline_slope_Wg_per_min"] == 0.0


def test_endpoint_baseline_requires_a_closed_event_end_window():
    t = np.linspace(0.0, 10.0, 101)
    heat = np.exp(-((t - 8.0) / 4.0) ** 2)

    variant = _baseline_variant(t, heat, 20, len(t) - 1, 1.0, "endpoint_linear")

    assert variant["available"] is False
    assert variant["reason"] == "no_post_event_baseline_window"


def test_avrami_marks_baseline_sensitivity_as_a_quality_flag():
    t = np.linspace(0.0, 12.0, 721)
    transient = 8.0 * np.exp(-t / 0.12)
    crystallisation = _avrami_heat_flow(np.maximum(t - 1.0, 0.0), n=2.8, k=0.13, scale=2.0)
    heat = 0.15 + transient + np.where(t >= 1.0, crystallisation - 0.02, 0.0) + 0.03 * t

    result = avrami_from_dsc(t, heat)

    assert result.baseline_sensitive is True
    assert "baseline_sensitive" in result.quality_flags


def test_avrami_candidate_projection_retains_transient_and_primary_events():
    t = np.linspace(0.0, 12.0, 721)
    transient = 8.0 * np.exp(-t / 0.12)
    crystallisation = _avrami_heat_flow(np.maximum(t - 1.0, 0.0), n=2.8, k=0.13, scale=2.0)
    heat = 0.15 + transient + np.where(t >= 1.0, crystallisation - 0.02, 0.0)

    candidates = avrami_candidates_from_dsc(t, heat)

    assert {item.candidate_kind for item in candidates} >= {"transient", "primary_exotherm"}
    primary = next(item for item in candidates if item.candidate_kind == "primary_exotherm")
    assert primary.start_time_min >= 0.8
    assert primary.transient_excluded is True
    transient_result = next(item for item in candidates if item.candidate_kind == "transient")
    assert transient_result.transient_excluded is False


def test_isothermal_figure_gate_accepts_informational_fit_window_flag():
    t = np.linspace(0.0, 30.0, 1500)
    engine = type("Engine", (), {})()
    engine._kinetics_data = {"avrami": avrami_from_dsc(t, _avrami_heat_flow(t, n=3.0, k=0.025))}

    definitions = build_isothermal_dsc_figure_definitions(engine)

    assert any(item.figure_id == "dsc.isothermal.avrami" for item in definitions)


def test_detect_isothermal_hold_inside_cooling_scan():
    t_ramp = np.linspace(0.0, 6.0, 300)
    T_ramp = np.linspace(255.0, 180.0, len(t_ramp))
    t_hold = np.linspace(6.02, 18.0, 700)
    T_hold = np.full_like(t_hold, 180.05)
    T = np.concatenate([T_ramp, T_hold])
    t = np.concatenate([t_ramp, t_hold])
    HF = np.concatenate([
        np.zeros_like(t_ramp),
        _avrami_heat_flow(t_hold - t_hold[0], n=2.2, k=0.08, scale=1.5),
    ])
    scan = DSCScan(
        label="cooling_program",
        T_C=T,
        HF_Wg=HF,
        HF_mW=HF,
        t_min=t,
        rate_K_per_min=-10.0,
    )

    segments = detect_isothermal_segments(scan)

    assert len(segments) == 1
    assert abs(segments[0].temperature_C - 180.05) < 0.1
    assert segments[0].duration_min > 10


def test_analyze_isothermal_scans_uses_cooling_holds():
    hold_t = np.linspace(0.0, 12.0, 900)
    heat_scan = DSCScan(
        label="program/heat 80-255C",
        T_C=np.full_like(hold_t, 255.0),
        HF_Wg=np.full_like(hold_t, 0.01),
        HF_mW=np.full_like(hold_t, 0.01),
        t_min=hold_t,
        rate_K_per_min=10.0,
    )
    cool_scan = DSCScan(
        label="program/cool 255-180C",
        T_C=np.full_like(hold_t, 180.0),
        HF_Wg=_avrami_heat_flow(hold_t, n=2.0, k=0.12, scale=1.2),
        HF_mW=_avrami_heat_flow(hold_t, n=2.0, k=0.12, scale=1.2),
        t_min=hold_t,
        rate_K_per_min=-10.0,
    )

    result = analyze_isothermal_scans([heat_scan, cool_scan])

    assert len(result.avrami_results) == 1
    assert abs(result.best.temperature_C - 180.0) < 0.1
    assert abs(result.best.n - 2.0) < 0.1


def test_dsc_isothermal_parameters_show_avrami_rows_first():
    engine = DSCEngine()
    engine.active_submodule = "dsc.isothermal"
    engine._results = [DSCResult(label="standard_scan")]
    av = AvramiResult(
        n=2.5,
        k=0.03,
        log_k=-1.52,
        t_half_min=3.4,
        temperature_C=183.0,
        crystallisation_enthalpy_Jg=120.0,
        r_squared=0.99,
        label="program/cool/iso 183C",
        baseline_method="endpoint_linear",
        baseline_variants=[{"method": "endpoint_linear", "available": True}],
        baseline_selection_reason="endpoint_linear_available",
    )
    engine._kinetics_data = {"avrami": av, "avrami_series": [av]}

    params = engine.get_parameters()

    assert list(params)[0] == "best_avrami"
    assert params["best_avrami"]["Avrami_n"] == 2.5
    assert params["best_avrami"]["Avrami_k"] == 0.03
    assert params["best_avrami"]["Avrami_R2"] == 0.99
    assert params["best_avrami"]["baseline_method"] == "endpoint_linear"
    assert params["best_avrami"]["baseline_variants"][0]["method"] == "endpoint_linear"


def test_legacy_isothermal_summary_preserves_complete_baseline_projection():
    engine = DSCEngine()
    engine._results = [DSCResult(label="standard_scan")]
    av = AvramiResult(
        n=2.5,
        k=0.03,
        log_k=-1.52,
        t_half_min=3.4,
        temperature_C=183.0,
        crystallisation_enthalpy_Jg=120.0,
        r_squared=0.99,
        baseline_method="endpoint_linear",
        baseline_start_value_Wg=0.12,
        baseline_end_value_Wg=0.08,
        baseline_slope_Wg_per_min=-0.01,
        baseline_window_start_index=10,
        baseline_window_end_index=90,
    )
    engine._kinetics_data = {"avrami": av, "avrami_series": [av]}

    summary = engine.get_parameters()["isothermal_kinetics"]

    assert summary["baseline_start_value_Wg"] == 0.12
    assert summary["baseline_end_value_Wg"] == 0.08
    assert summary["baseline_slope_Wg_per_min"] == -0.01
    assert summary["baseline_window_start_index"] == 10
    assert summary["baseline_window_end_index"] == 90


def test_dsc_engine_runs_existing_isothermal_kinetics_from_canonical_template():
    rows = []
    rows.append("Sample Weight: 5.95 mg")
    for index in range(121):
        rows.append(f"{index} {index} 255.02 255.0 1.0")
    for index in range(121, 302):
        elapsed = index - 121
        rows.append(f"{index} {index} 180.05 180.0 {_avrami_heat_flow(elapsed / 60.0):.8f}")
    template = convert_mettler_isothermal_text("\n".join(rows), source_artifact_id="raw-sha256").template

    engine = DSCEngine()
    result = engine.run_isothermal_template(template)

    assert template is not None
    assert result["canonical_provenance"]["template_hash"] == template.content_hash
    assert result["canonical_provenance"]["conversion_hash"] == template.conversion_record.conversion_hash
    assert len(result["avrami_series"]) == 1
    assert [item.label for item in result["avrami_series"]] == ["iso-180C-001"]
    assert "segment_01_180.1C" in engine.get_parameters()


def test_dsc_engine_routes_mixed_thermal_program_roles_in_one_call():
    from polynexus.core.canonical_experiments.models import CanonicalExperiment, ConversionRecord

    record = ConversionRecord.create(
        conversion_id="thermal-program.v1",
        source_artifact_id="raw-sha256",
    )
    heating_t = list(range(81))
    cooling_t = list(range(81, 162))
    template = CanonicalExperiment.create(
        template_id="thermal_program.v1",
        source_artifact_id="raw-sha256",
        conversion_record=record,
        payload={
            "sample": {"mass_mg": 5.0},
            "segments": [
                {
                    "segment_id": "heat-001",
                    "role": "heating",
                    "setpoint_C": 240.0,
                    "time_s": heating_t,
                    "sample_temperature_C": [25.0 + i * 2.5 for i in range(81)],
                    "heat_flow_mW": [1.0 + i * 0.01 for i in range(81)],
                    "source_range": {"start_row": 0, "end_row": 80},
                    "rate_K_per_min": 10.0,
                },
                {
                    "segment_id": "cool-001",
                    "role": "cooling",
                    "setpoint_C": 40.0,
                    "time_s": cooling_t,
                    "sample_temperature_C": [225.0 - i * 2.5 for i in range(81)],
                    "heat_flow_mW": [1.8 - i * 0.01 for i in range(81)],
                    "source_range": {"start_row": 81, "end_row": 161},
                    "rate_K_per_min": -10.0,
                },
            ],
        },
    )

    engine = DSCEngine()
    result = engine.run_thermal_program_template(template)

    assert result["canonical_provenance"]["template_id"] == "thermal_program.v1"
    assert result["thermal_program_segments"] == [
        {"segment_id": "heat-001", "role": "heating"},
        {"segment_id": "cool-001", "role": "cooling"},
    ]
    assert [scan.label for scan in engine.scans] == ["heat-001", "cool-001"]


def test_dsc_engine_accepts_generic_thermal_program_template():
    rows = ["Sample Weight: 5.95 mg"]
    rows.extend(f"{index} {index} 255.02 255.0 1.0" for index in range(61))
    rows.extend(
        f"{index} {index} 180.05 180.0 {_avrami_heat_flow((index - 61) / 60.0):.8f}"
        for index in range(61, 242)
    )
    template = convert_mettler_isothermal_text(
        "\n".join(rows), source_artifact_id="raw-sha256", template_id="thermal_program.v1"
    ).template

    result = DSCEngine().run_isothermal_template(template)

    assert template is not None
    assert template.template_id == "thermal_program.v1"
    assert result["canonical_provenance"]["template_id"] == "thermal_program.v1"
    assert len(result["avrami_series"]) == 2


def test_dsc_engine_rejects_canonical_template_without_sample_mass():
    record = ConversionRecord.create(
        conversion_id="mettler.dsc-isothermal.v1",
        source_artifact_id="raw-sha256",
    )
    template = CanonicalExperiment.create(
        template_id="dsc.isothermal.v1",
        source_artifact_id="raw-sha256",
        conversion_record=record,
        payload={
            "sample": {"mass_mg": None},
            "segments": [{
                "segment_id": "iso-180C-001",
                "role": "isothermal_crystallization",
                "setpoint_C": 180.0,
                "time_s": list(range(61)),
                "sample_temperature_C": [180.05] * 61,
                "heat_flow_mW": [1.0] * 61,
                "source_range": {},
            }],
        },
    )

    with pytest.raises(ValueError, match="sample mass"):
        DSCEngine().run_isothermal_template(template)


def test_dsc_engine_rejects_canonical_template_below_kinetic_minimums():
    record = ConversionRecord.create(
        conversion_id="mettler.dsc-isothermal.v1",
        source_artifact_id="raw-sha256",
    )
    template = CanonicalExperiment.create(
        template_id="dsc.isothermal.v1",
        source_artifact_id="raw-sha256",
        conversion_record=record,
        payload={
            "sample": {"mass_mg": 5.95},
            "segments": [{
                "segment_id": "iso-180C-001",
                "role": "isothermal_crystallization",
                "setpoint_C": 180.0,
                "time_s": [0.0, 1.0],
                "sample_temperature_C": [180.05, 180.05],
                "heat_flow_mW": [1.0, 1.0],
                "source_range": {},
            }],
        },
    )

    with pytest.raises(ValueError, match="does not meet canonical kinetic qualification"):
        DSCEngine().run_isothermal_template(template)


def test_dsc_engine_accepts_stable_canonical_hold_with_point_noise():
    record = ConversionRecord.create(
        conversion_id="mettler.dsc-isothermal.v1",
        source_artifact_id="raw-sha256",
    )
    time_s = list(range(61))
    temperatures = [180.05 + (0.04 if index % 2 else -0.04) + index * 0.001 for index in time_s]
    template = CanonicalExperiment.create(
        template_id="dsc.isothermal.v1",
        source_artifact_id="raw-sha256",
        conversion_record=record,
        payload={
            "sample": {"mass_mg": 5.95},
            "segments": [{
                "segment_id": "iso-180C-001",
                "role": "isothermal_crystallization",
                "setpoint_C": 180.0,
                "time_s": time_s,
                "sample_temperature_C": temperatures,
                "heat_flow_mW": [1.0] * 61,
                "source_range": {},
            }],
        },
    )

    result = DSCEngine().run_isothermal_template(template)

    assert len(result["avrami_series"]) == 1


def test_dsc_engine_runs_hold_with_soft_temperature_warning():
    record = ConversionRecord.create(
        conversion_id="mettler.dsc-isothermal.v1",
        source_artifact_id="raw-sha256",
    )
    time_s = list(range(181))
    temperatures = [180.0 + 0.35 * np.sin(index / 12.0) for index in time_s]
    template = CanonicalExperiment.create(
        template_id="thermal_program.v1",
        source_artifact_id="raw-sha256",
        conversion_record=record,
        payload={
            "sample": {"mass_mg": 5.95},
            "segments": [{
                "segment_id": "iso-180C-001",
                "role": "isothermal_crystallization",
                "setpoint_C": 180.0,
                "time_s": time_s,
                "sample_temperature_C": temperatures,
                "heat_flow_mW": [1.0 + index / 1000 for index in time_s],
                "source_range": {},
            }],
        },
    )

    result = DSCEngine().run_thermal_program_template(template)

    assert len(result["avrami_series"]) == 1
    assert "sample_temperature_noise_exceeds_tolerance" in result["avrami_series"][0].quality_flags


def test_dsc_engine_accepts_canonical_hold_with_excessive_temperature_span():
    record = ConversionRecord.create(
        conversion_id="mettler.dsc-isothermal.v1",
        source_artifact_id="raw-sha256",
    )
    template = CanonicalExperiment.create(
        template_id="dsc.isothermal.v1",
        source_artifact_id="raw-sha256",
        conversion_record=record,
        payload={
            "sample": {"mass_mg": 5.95},
            "segments": [{
                "segment_id": "iso-180C-001",
                "role": "isothermal_crystallization",
                "setpoint_C": 180.0,
                "time_s": list(range(61)),
                "sample_temperature_C": [179.6 if index % 2 else 180.4 for index in range(61)],
                "heat_flow_mW": [1.0] * 61,
                "source_range": {},
            }],
        },
    )

    result = DSCEngine().run_isothermal_template(template)
    assert len(result["avrami_series"]) == 1
    assert "sample_temperature_span_exceeds_tolerance" in result["avrami_series"][0].quality_flags


def test_dsc_engine_accepts_high_frequency_canonical_temperature_oscillation():
    record = ConversionRecord.create(
        conversion_id="mettler.dsc-isothermal.v1",
        source_artifact_id="raw-sha256",
    )
    template = CanonicalExperiment.create(
        template_id="dsc.isothermal.v1",
        source_artifact_id="raw-sha256",
        conversion_record=record,
        payload={
            "sample": {"mass_mg": 5.95},
            "segments": [{
                "segment_id": "iso-180C-001",
                "role": "isothermal_crystallization",
                "setpoint_C": 180.0,
                "time_s": list(range(61)),
                "sample_temperature_C": [179.8 if index % 2 else 180.2 for index in range(61)],
                "heat_flow_mW": [1.0] * 61,
                "source_range": {},
            }],
        },
    )

    result = DSCEngine().run_isothermal_template(template)
    assert len(result["avrami_series"]) == 1
    assert "sample_temperature_noise_exceeds_tolerance" in result["avrami_series"][0].quality_flags


def test_dsc_engine_accepts_narrow_high_frequency_temperature_oscillation():
    record = ConversionRecord.create(
        conversion_id="mettler.dsc-isothermal.v1",
        source_artifact_id="raw-sha256",
    )
    template = CanonicalExperiment.create(
        template_id="dsc.isothermal.v1",
        source_artifact_id="raw-sha256",
        conversion_record=record,
        payload={
            "sample": {"mass_mg": 5.95},
            "segments": [{
                "segment_id": "iso-180C-001",
                "role": "isothermal_crystallization",
                "setpoint_C": 180.0,
                "time_s": list(range(61)),
                "sample_temperature_C": [179.94 if index % 2 else 180.06 for index in range(61)],
                "heat_flow_mW": [1.0] * 61,
                "source_range": {},
            }],
        },
    )

    result = DSCEngine().run_isothermal_template(template)
    assert len(result["avrami_series"]) == 1
    assert "sample_temperature_noise_exceeds_tolerance" in result["avrami_series"][0].quality_flags
