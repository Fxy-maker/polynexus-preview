from __future__ import annotations

import json

import pytest

from polynexus.core.canonical_experiments import (
    CanonicalExperiment,
    CapabilityExecutor,
    CapabilityRegistry,
    CapabilitySpec,
    Measurement,
    default_capability_registry,
    default_provider_capability_registry,
)
from polynexus.core.canonical_experiments.registry import default_converter_registry


def _measurement(*, measurement_id: str = "m-1", family: str = "spectrum_1d") -> Measurement:
    return Measurement(
        measurement_id=measurement_id,
        family=family,
        role="raw_curve",
        channels={"x": (10.0, 20.0, 30.0), "intensity": (2.0, -1.0, 4.0)},
        units={"x": "a.u.", "intensity": "a.u."},
        source_locator={
            "source_path": "raw/curve.csv",
            "sheet_name": None,
            "sheet_index": None,
            "table_index": 0,
            "header_row": 0,
            "data_row_start": 1,
            "data_row_end": 3,
            "point_start": 0,
            "point_end": 2,
        },
    )


def _template(*measurements: Measurement) -> CanonicalExperiment:
    from polynexus.core.canonical_experiments import ConversionRecord

    record = ConversionRecord.create(
        conversion_id="test.v1",
        source_artifact_id="artifact-1",
    )
    return CanonicalExperiment.create(
        template_id="spectrum_1d.v1",
        source_artifact_id="artifact-1",
        payload={"technique": "IR"},
        conversion_record=record,
        measurements=measurements,
    )


def test_default_registry_is_closed_and_calculates_all_supported_items() -> None:
    registry = default_capability_registry()
    assert registry.ids == ("curve.extrema.v1", "curve.summary.v1")
    template = _template(_measurement())

    results = CapabilityExecutor(registry).execute(template)

    assert [item.capability_id for item in results] == [
        "curve.extrema.v1",
        "curve.summary.v1",
    ]
    assert results[0].status == "completed"
    assert results[0].result["minimum"]["x"] == 20.0
    assert results[1].result == {
        "point_count": 3,
        "x_min": 10.0,
        "x_max": 30.0,
        "intensity_min": -1.0,
        "intensity_max": 4.0,
        "intensity_range": 5.0,
        "units": {"x": "a.u.", "intensity": "a.u."},
    }
    assert results[0].item_id == CapabilityExecutor(registry).execute(template)[0].item_id
    json.dumps([item.to_dict() for item in results], allow_nan=False)


def test_executor_isolates_unsupported_and_failed_items() -> None:
    def fail(_: Measurement) -> dict[str, object]:
        raise RuntimeError("test failure")

    registry = CapabilityRegistry(
        (
            CapabilitySpec("failing.v1", ("spectrum_1d",), fail),
            CapabilitySpec("spectrum-only.v1", ("spectrum_1d",), lambda _: {"ok": True}),
        )
    )
    template = _template(_measurement(family="scattering_1d"), _measurement(measurement_id="m-2"))

    results = CapabilityExecutor(registry).execute(template)

    assert [item.status for item in results] == [
        "not_applicable",
        "not_applicable",
        "failed",
        "completed",
    ]
    assert results[0].reason_codes == ("capability_family_unsupported",)
    assert results[2].reason_codes == ("capability_execution_failed",)
    assert results[3].result == {"ok": True}


def test_unknown_requested_capability_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown capability"):
        CapabilityExecutor().execute(_template(_measurement()), capability_ids=("missing.v1",))


def test_registry_executes_finite_items_for_a_ready_generic_template(tmp_path) -> None:
    path = tmp_path / "curve.csv"
    path.write_text("Wavenumber,Absorbance\n1700,0.4\n1600,0.8\n", encoding="utf-8")

    outcome = default_converter_registry().convert_path(
        path,
        technique="ir",
        source_artifact_id="source-sha256",
    )

    assert outcome.template is not None
    items = default_converter_registry().execute_capabilities(outcome.template)
    assert [item.capability_id for item in items] == ["curve.extrema.v1", "curve.summary.v1"]
    assert all(item.status == "completed" for item in items)


def test_capability_spec_rejects_a_single_family_string() -> None:
    with pytest.raises(TypeError, match="sequence of family strings"):
        CapabilitySpec("invalid.v1", "spectrum_1d", lambda _: {})


def test_provider_capability_executor_projects_registered_metrics_without_fabrication() -> None:
    registry = default_provider_capability_registry()
    executor = CapabilityExecutor(provider_registry=registry)

    items = executor.execute_provider_result(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"Tm_peak_C": 185.2, "DHm_Jg": 42.0},
    )

    by_id = {item.capability_id: item for item in items}
    assert by_id["Tm"].status == "completed"
    assert by_id["Tm"].result == {"metric_path": "Tm_peak_C", "value": 185.2}
    assert by_id["enthalpy"].status == "completed"
    assert by_id["Tg"].status == "needs_input"
    assert by_id["Tg"].reason_codes == ("provider_metric_unavailable",)


def test_provider_capability_executor_accepts_shared_provider_result_input() -> None:
    from polynexus.core.ai_platform import ProviderResultInput

    provider_input = ProviderResultInput.create(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"Tm_peak_C": 185.2},
        metric_manifest=(
            {
                "path": "Tm_peak_C",
                "kind": "scalar",
                "status": "computed",
                "value": 185.2,
            },
        ),
    )

    items = CapabilityExecutor().execute_provider_result(provider_input=provider_input)

    tm = next(item for item in items if item.capability_id == "Tm")
    assert tm.status == "completed"
    assert tm.result == {"metric_path": "Tm_peak_C", "value": 185.2}


def test_provider_capability_executor_finds_nested_engine_parameters() -> None:
    items = CapabilityExecutor().execute_provider_result(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"segment_01_180C": {"Avrami_n": 1.8}},
    )

    avrami = next(item for item in items if item.capability_id == "Avrami")
    assert avrami.status == "completed"
    assert avrami.result == {
        "metric_path": "segment_01_180C.Avrami_n",
        "value": 1.8,
    }


def test_provider_capability_executor_skips_null_alias_and_uses_later_alias() -> None:
    items = CapabilityExecutor().execute_provider_result(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"heating-001": {"Tc_C": None, "Tc_peak_C": 182.4}},
    )

    tc = next(item for item in items if item.capability_id == "Tc")
    assert tc.status == "completed"
    assert tc.result == {
        "metric_path": "heating-001.Tc_peak_C",
        "value": 182.4,
    }

    unavailable = CapabilityExecutor().execute_provider_result(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"heating-001": {"Tc_C": None}},
    )
    tc_unavailable = next(item for item in unavailable if item.capability_id == "Tc")
    assert tc_unavailable.status == "needs_input"


def test_provider_capability_projection_does_not_infer_nmr_phase_from_xc_alone() -> None:
    items = CapabilityExecutor().execute_provider_result(
        source_artifact_id="artifact-1",
        technique="nmr",
        metrics={"Xc_pct": 25.0},
    )

    phase = next(item for item in items if item.capability_id == "solid_13C_phase")
    assert phase.status == "needs_input"
