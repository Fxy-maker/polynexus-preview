from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.dsc_engine.figure_common import (
    DSCScanView,
    classify_dsc_scan_eligibility,
    scan_views_from_engine,
)
from polynexus.core.dsc_engine.figure_standard import build_standard_dsc_figure_definitions


def _view(*, quality_score: float = 0.9, quality_flags: tuple[str, ...] = ()) -> DSCScanView:
    return DSCScanView(
        index=0,
        label="scan-0",
        temperature_C=(20.0, 40.0, 60.0, 80.0, 100.0),
        heat_flow_W_g=(0.1, 0.2, 0.8, 0.4, 0.1),
        parameters={"Tm_peak_C": 60.0},
        quality_score=quality_score,
        quality_flags=quality_flags,
    )


def _engine_with_results(*views: DSCScanView) -> SimpleNamespace:
    results = []
    for view in views:
        results.append(
            SimpleNamespace(
                label=view.label,
                T=np.asarray(view.temperature_C, dtype=float),
                HF=np.asarray(view.heat_flow_W_g, dtype=float),
                parameters=dict(view.parameters),
                quality_score=view.quality_score,
                quality_flags=list(view.quality_flags),
            )
        )
    return SimpleNamespace(_results=results)


def test_single_scan_standard_recipe_has_editable_thermogram_main() -> None:
    definitions = build_standard_dsc_figure_definitions(_engine_with_results(_view()))
    main = next(item for item in definitions if item.figure_id == "dsc.standard.thermogram")
    assert main.publication_role == "main"
    assert {panel.panel_id for panel in main.layout.panels} == {"thermogram", "quantitative"}
    assert {obj["type"] for obj in main.objects} >= {"plot_series", "line"}


def test_multi_scan_recipe_promotes_comparison_and_keeps_rejected_evidence_diagnostic() -> None:
    rejected = _view(quality_flags=("contains_nan_inf",))
    definitions = build_standard_dsc_figure_definitions(
        _engine_with_results(_view(), _view(), rejected)
    )
    comparison = next(item for item in definitions if item.figure_id == "dsc.comparison.thermal-events")
    assert comparison.publication_role == "main"
    assert any(item.figure_id == "dsc.standard.integration.diagnostic" and item.publication_role == "diagnostic" for item in definitions)


def test_invalid_xc_is_not_rendered_as_a_quantitative_main_label() -> None:
    view = _view()
    view = DSCScanView(
        index=view.index,
        label=view.label,
        temperature_C=view.temperature_C,
        heat_flow_W_g=view.heat_flow_W_g,
        parameters={"Tm_peak_C": 60.0, "Xc_pct": np.nan},
        quality_score=view.quality_score,
        quality_flags=view.quality_flags,
    )
    main = next(item for item in build_standard_dsc_figure_definitions(_engine_with_results(view)) if item.figure_id == "dsc.standard.thermogram")
    assert all(obj.get("name") != "Xc" for obj in main.objects)


def test_quality_ok_scan_is_main_eligible() -> None:
    decision = classify_dsc_scan_eligibility(_view())
    assert decision.highest_role == "main"
    assert "quality_ok" in decision.reasons


def test_analysis_quality_failure_is_diagnostic() -> None:
    decision = classify_dsc_scan_eligibility(
        _view(quality_flags=("baseline_unstable",))
    )
    assert decision.highest_role == "diagnostic"


def test_invalid_emitted_quality_flags_cannot_be_promoted_to_main() -> None:
    assert classify_dsc_scan_eligibility(_view(quality_flags=("contains_nan_inf",))).highest_role == "diagnostic"
    assert classify_dsc_scan_eligibility(_view(quality_flags=("low_snr",))).highest_role == "si"


def test_low_quality_scan_is_si_not_main() -> None:
    decision = classify_dsc_scan_eligibility(_view(quality_score=0.35))
    assert decision.highest_role == "si"


def test_low_quality_takes_priority_over_insufficient_curve_points() -> None:
    view = DSCScanView(
        index=0,
        label="short-low-quality",
        temperature_C=(20.0, 40.0),
        heat_flow_W_g=(0.1, 0.2),
        parameters={},
        quality_score=0.2,
        quality_flags=(),
    )
    assert classify_dsc_scan_eligibility(view).highest_role == "si"


def test_dsc_scan_parameters_are_recursively_immutable() -> None:
    view = DSCScanView(
        index=0,
        label="nested",
        temperature_C=(20.0, 40.0, 60.0, 80.0, 100.0),
        heat_flow_W_g=(0.1, 0.2, 0.8, 0.4, 0.1),
        parameters={"nested": {"values": [1.0]}},
        quality_score=0.9,
        quality_flags=(),
    )
    try:
        view.parameters["nested"]["values"].append(2.0)
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("nested DSC parameters must be immutable")


def test_scan_views_copy_emitted_result_fields_without_reanalysis() -> None:
    analysis = SimpleNamespace(
        label="result-0",
        T=np.asarray([10.0, 20.0, 30.0]),
        HF=np.asarray([1.0, 2.0, 3.0]),
        parameters={"Tm_peak_C": 177.0},
        quality_score=0.82,
        quality_flags=["quality_ok"],
    )
    engine = SimpleNamespace(_results=[analysis])

    views = scan_views_from_engine(engine)

    assert len(views) == 1
    assert views[0].label == "result-0"
    assert views[0].temperature_C == (10.0, 20.0, 30.0)
    assert views[0].heat_flow_W_g == (1.0, 2.0, 3.0)
    assert views[0].parameters["Tm_peak_C"] == 177.0


def test_scan_views_preserve_heating_or_cooling_direction_for_publication() -> None:
    analysis = SimpleNamespace(
        label="cooling-run",
        technique="cooling",
        T=np.asarray([120.0, 100.0, 80.0, 60.0, 40.0]),
        HF=np.asarray([0.0, 0.4, 0.8, 0.3, 0.0]),
        parameters={"Tc_peak_C": 80.0},
        quality_score=0.9,
        quality_flags=[],
    )
    view = scan_views_from_engine(SimpleNamespace(_results=[analysis]))[0]
    assert view.direction == "cooling"
    main = next(item for item in build_standard_dsc_figure_definitions(SimpleNamespace(_results=[analysis])) if item.publication_role == "main")
    assert main.recipe["parameters"]["scan_direction"] == "cooling"


def test_scan_views_preserve_temperature_heat_flow_positions() -> None:
    analysis = SimpleNamespace(
        label="gapped",
        T=np.asarray([10.0, np.nan, 30.0]),
        HF=np.asarray([1.0, 2.0, np.nan]),
        parameters={},
        quality_score=0.8,
        quality_flags=(),
    )
    view = scan_views_from_engine(SimpleNamespace(_results=[analysis]))[0]
    assert np.isnan(view.temperature_C[1])
    assert np.isnan(view.heat_flow_W_g[2])


def test_nan_pairs_do_not_count_as_curve_points_without_quality_flag() -> None:
    view = DSCScanView(
        index=0,
        label="nan-gapped",
        temperature_C=(10.0, np.nan, 30.0, np.nan, 50.0),
        heat_flow_W_g=(1.0, 2.0, np.nan, np.nan, 5.0),
        parameters={},
        quality_score=0.9,
        quality_flags=(),
    )
    assert classify_dsc_scan_eligibility(view).highest_role == "diagnostic"


def test_misaligned_temperature_and_heat_flow_are_diagnostic() -> None:
    view = DSCScanView(
        index=0,
        label="misaligned",
        temperature_C=(10.0, 20.0, 30.0, 40.0, 50.0),
        heat_flow_W_g=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
        parameters={},
        quality_score=0.9,
        quality_flags=(),
    )
    assert classify_dsc_scan_eligibility(view).highest_role == "diagnostic"


def test_no_main_standard_pack_records_publication_fallback_reason() -> None:
    view = _view(quality_flags=("baseline_unstable",))
    definitions = build_standard_dsc_figure_definitions(_engine_with_results(view))
    diagnostic = next(item for item in definitions if item.publication_role == "diagnostic")
    parameters = diagnostic.recipe["parameters"]
    assert parameters["no_publication_ready_figure"] is True
    assert parameters["reason"] == "no_reliable_main"
