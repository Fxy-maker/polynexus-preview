from __future__ import annotations

import pytest

from polynexus.core.canonical_experiments import CanonicalExperiment, ConversionOutcome, ConversionRecord


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


def test_canonical_template_reads_legacy_payload_without_new_contract_fields() -> None:
    legacy_payload = {
        "template_id": "legacy.template.v1",
        "source_artifact_id": "legacy-sha",
        "payload": {"segments": [{"setpoint_C": 180.0, "time_s": [0.0, 1.0]}]},
        "conversion_record": {
            "conversion_id": "legacy.converter.v1",
            "source_artifact_id": "legacy-sha",
            "contract_version": "1",
            "observed_columns": [],
            "extracted_segments": [],
            "excluded_segments": [],
            "warnings": [],
            "reason_codes": [],
            "conversion_hash": "db5e0644ef8c717cf311cb219ee351d2e322c1285e9beb7648dff15e2567f88a",
        },
        "contract_version": "1",
        "content_hash": "240497ca9b9b41d04bee4c3f4dbb0d1aae47adf7e569930d6400d80085bcb4ca",
    }

    restored = CanonicalExperiment.from_dict(legacy_payload)

    assert restored.to_dict()["payload"] == legacy_payload["payload"]
    assert restored.measurements == ()
    assert restored.mapping_proposal is None


@pytest.mark.parametrize("removed_key", ("measurements", "mapping_proposal"))
def test_new_canonical_template_rejects_removal_of_serialized_contract_fields(removed_key: str) -> None:
    record = ConversionRecord.create(
        conversion_id="converter.v1",
        source_artifact_id="raw-sha256",
    )
    template = CanonicalExperiment.create(
        template_id="template.v1",
        source_artifact_id="raw-sha256",
        payload={},
        conversion_record=record,
    )
    serialized = template.to_dict()
    serialized.pop(removed_key)

    with pytest.raises(ValueError, match="contract fields"):
        CanonicalExperiment.from_dict(serialized)


def test_legacy_canonical_template_requires_both_new_contract_fields_to_be_absent() -> None:
    legacy_payload = {
        "template_id": "legacy.template.v1",
        "source_artifact_id": "legacy-sha",
        "payload": {"segments": [{"setpoint_C": 180.0, "time_s": [0.0, 1.0]}]},
        "conversion_record": {
            "conversion_id": "legacy.converter.v1",
            "source_artifact_id": "legacy-sha",
            "contract_version": "1",
            "observed_columns": [],
            "extracted_segments": [],
            "excluded_segments": [],
            "warnings": [],
            "reason_codes": [],
            "conversion_hash": "db5e0644ef8c717cf311cb219ee351d2e322c1285e9beb7648dff15e2567f88a",
        },
        "contract_version": "1",
        "content_hash": "240497ca9b9b41d04bee4c3f4dbb0d1aae47adf7e569930d6400d80085bcb4ca",
    }
    legacy_payload["measurements"] = []

    with pytest.raises(ValueError, match="contract fields"):
        CanonicalExperiment.from_dict(legacy_payload)


def test_needs_input_conversion_cannot_contain_a_template() -> None:
    record = ConversionRecord.create(
        conversion_id="converter.v1",
        source_artifact_id="raw-sha256",
    )
    template = CanonicalExperiment.create(
        template_id="template.v1",
        source_artifact_id="raw-sha256",
        payload={},
        conversion_record=record,
    )

    assert ConversionOutcome(status="needs_input", record=record).status == "needs_input"
    with pytest.raises(ValueError, match="needs_input"):
        ConversionOutcome(status="needs_input", record=record, template=template)


@pytest.mark.parametrize("status", ("ready", "review_required", "blocked", "needs_input"))
def test_conversion_outcome_requires_record_reason_codes_to_match(status: str) -> None:
    record = ConversionRecord.create(
        conversion_id="converter.v1",
        source_artifact_id="raw-sha256",
        reason_codes=("record_reason",),
    )

    with pytest.raises(ValueError, match="reason codes"):
        ConversionOutcome(status=status, record=record, reason_codes=("outcome_reason",))
