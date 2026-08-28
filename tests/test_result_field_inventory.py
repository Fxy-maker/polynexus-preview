from __future__ import annotations

from polynexus.core.compute.result_inventory import build_result_field_inventory
from polynexus.core.compute.models import ComputeResult


def test_inventory_lists_scalar_series_and_nested_fields_without_dropping_values():
    fields = build_result_field_inventory(
        {
            "Tm_C": 185.2,
            "curve": [1.0, 2.0, 3.0],
            "fit": {"r_squared": 0.98},
        }
    )

    assert [item.path for item in fields] == ["Tm_C", "curve", "fit.r_squared"]
    assert fields[0].kind == "scalar"
    assert fields[0].value == 185.2
    assert fields[1].kind == "series"
    assert fields[1].item_count == 3
    assert fields[2].path == "fit.r_squared"


def test_inventory_records_declared_but_missing_fields_explicitly():
    fields = build_result_field_inventory(
        {"n_peaks": 4}, declared_paths=("n_peaks", "Xc_pct")
    )

    missing = next(item for item in fields if item.path == "Xc_pct")
    assert missing.kind == "missing"
    assert missing.present is False


def test_inventory_rejects_non_mapping_metrics():
    try:
        build_result_field_inventory([1, 2, 3])
    except TypeError as exc:
        assert "mapping" in str(exc).lower()
    else:
        raise AssertionError("expected a TypeError")


def test_compute_result_metric_manifest_attaches_uniform_metadata_without_inference():
    result = ComputeResult(
        metrics={"Tm_C": 220.5, "peaks": [{"x": 1.0}]},
        metadata={
            "units": {"Tm_C": "°C"},
            "methods": {"Tm_C": "peak_maximum"},
            "parameters": {"Tm_C": {"window": [200, 240]}},
            "source": "sample.dsc",
        },
        warnings=("baseline_review",),
    )

    manifest = result.metric_manifest()

    melting = next(item for item in manifest if item["path"] == "Tm_C")
    assert melting == {
        "path": "Tm_C",
        "kind": "scalar",
        "value": 220.5,
        "unit": "°C",
        "method": "peak_maximum",
        "parameters": {"window": [200, 240]},
        "source": "sample.dsc",
        "warnings": ["baseline_review"],
        "status": "computed",
    }
    assert next(item for item in manifest if item["path"] == "peaks")["status"] == "computed"
    assert result.metric_manifest_csv_rows()[0]["source"] == "sample.dsc"
