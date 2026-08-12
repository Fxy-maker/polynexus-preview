from __future__ import annotations

import pytest

from polynexus.core.canonical_experiments import CanonicalExperiment, ConversionRecord


def test_canonical_template_is_frozen_and_has_stable_content_hash() -> None:
    record = ConversionRecord.create(
        conversion_id="mettlertoledo.dsc-isothermal.v1",
        source_artifact_id="raw-sha256",
        observed_columns=("time_s", "sample_temperature_C", "setpoint_C", "heat_flow_mW"),
    )
    template = CanonicalExperiment.create(
        template_id="dsc.isothermal.v1",
        source_artifact_id="raw-sha256",
        payload={"segments": [{"setpoint_C": 180.0, "time_s": [0.0, 1.0]}]},
        conversion_record=record,
    )

    restored = CanonicalExperiment.from_dict(template.to_dict())

    assert restored.content_hash == template.content_hash
    with pytest.raises(TypeError):
        template.payload["segments"] = ()
    with pytest.raises(TypeError):
        template.payload["segments"][0]["setpoint_C"] = 181.0


def test_canonical_template_rejects_a_tampered_content_hash() -> None:
    record = ConversionRecord.create(
        conversion_id="mettlertoledo.dsc-isothermal.v1",
        source_artifact_id="raw-sha256",
    )
    template = CanonicalExperiment.create(
        template_id="dsc.isothermal.v1",
        source_artifact_id="raw-sha256",
        payload={"segments": []},
        conversion_record=record,
    )
    payload = template.to_dict()
    payload["content_hash"] = "not-the-real-hash"

    with pytest.raises(ValueError, match="content hash"):
        CanonicalExperiment.from_dict(payload)
