from __future__ import annotations

from polynexus.core.compute.capability_catalog import default_capability_catalog


def test_capability_catalog_lists_requested_technique_outputs_and_shared_projection():
    catalog = default_capability_catalog()
    waxs = catalog.for_technique("waxs")

    assert {item.capability_id for item in waxs} >= {
        "peak_decomposition",
        "crystallinity",
        "crystallite_size",
        "lattice_parameters",
        "williamson_hall",
    }
    assert all(item.shared_projection == "result.metric_manifest" for item in waxs)
    assert catalog.to_dict()["techniques"]["nmr"][0]["status"] == "provider_result"


def test_capability_catalog_normalizes_ir_and_ftir_aliases():
    catalog = default_capability_catalog()
    assert catalog.for_technique("ir") == catalog.for_technique("ftir")
