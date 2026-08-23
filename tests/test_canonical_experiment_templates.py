from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

from polynexus.core.canonical_experiments import (
    CanonicalExperiment,
    ConversionOutcome,
    ConversionRecord,
    MappingProposal,
    MappingSelection,
    Measurement,
)


def _legacy_content_hash(serialized: dict[str, object]) -> str:
    identity = {
        key: serialized[key]
        for key in (
            "template_id",
            "source_artifact_id",
            "payload",
            "conversion_record",
            "contract_version",
        )
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _measurement(*, mapping: MappingSelection | None = None) -> Measurement:
    return Measurement(
        measurement_id="measurement-1",
        family="spectrum_1d",
        role="primary",
        channels={"x": (4000.0, 2000.0), "intensity": (0.1, 0.2)},
        units={"x": "cm^-1", "intensity": "a.u."},
        source_locator={
            "source_path": "raw/spectrum.csv",
            "sheet_name": None,
            "sheet_index": None,
            "table_index": 0,
            "header_row": 1,
            "data_row_start": 2,
            "data_row_end": 3,
            "point_start": 0,
            "point_end": 1,
        },
        mapping=mapping,
    )


def _ai_mapping_selection() -> MappingSelection:
    return MappingSelection(
        measurement_id="measurement-1",
        sheet_name=None,
        sheet_index=None,
        table_index=0,
        header_row=1,
        data_row_start=2,
        data_row_end=3,
        x_column="Wavenumber",
        intensity_column="Absorbance",
        x_kind="wavenumber",
        x_unit="cm^-1",
        intensity_unit="a.u.",
        source="AI proposal",
    )


def _template_with_new_contract_fields() -> CanonicalExperiment:
    selection = _ai_mapping_selection()
    proposal = MappingProposal.create(
        source_artifact_id="raw-sha256",
        technique="IR",
        source="AI proposal",
        selections=(selection,),
    )
    return CanonicalExperiment.create(
        template_id="template.v1",
        source_artifact_id="raw-sha256",
        payload={},
        conversion_record=ConversionRecord.create(
            conversion_id="converter.v1",
            source_artifact_id="raw-sha256",
        ),
        measurements=(_measurement(mapping=selection),),
        mapping_proposal=proposal,
    )


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


def test_new_canonical_template_rejects_tampered_content_with_original_hash() -> None:
    record = ConversionRecord.create(
        conversion_id="converter.v1",
        source_artifact_id="raw-sha256",
    )
    template = CanonicalExperiment.create(
        template_id="template.v1",
        source_artifact_id="raw-sha256",
        payload={"segments": []},
        conversion_record=record,
    )
    payload = template.to_dict()
    payload["payload"] = {"segments": ["tampered"]}

    with pytest.raises(ValueError, match="content hash"):
        CanonicalExperiment.from_dict(payload)


def test_new_canonical_template_hashes_measurements_and_mapping_proposal() -> None:
    template = _template_with_new_contract_fields()
    tampered_measurements = deepcopy(template.to_dict())
    tampered_measurements["measurements"][0]["channels"]["intensity"][0] = 0.3
    replacement_proposal = MappingProposal.create(
        source_artifact_id="raw-sha256",
        technique="IR",
        source="AI proposal",
        selections=(_ai_mapping_selection(),),
        warnings=("tampered",),
    )
    tampered_mapping_proposal = deepcopy(template.to_dict())
    tampered_mapping_proposal["mapping_proposal"] = replacement_proposal.to_dict()

    with pytest.raises(ValueError, match="content hash"):
        CanonicalExperiment.from_dict(tampered_measurements)
    with pytest.raises(ValueError, match="content hash"):
        CanonicalExperiment.from_dict(tampered_mapping_proposal)


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


def test_legacy_canonical_template_replays_its_original_serialized_hash_shape() -> None:
    record = ConversionRecord.create(
        conversion_id="legacy.converter.v1",
        source_artifact_id="legacy-sha",
    )
    template = CanonicalExperiment.create(
        template_id="legacy.template.v1",
        source_artifact_id="legacy-sha",
        payload={"segments": [{"setpoint_C": 180.0, "time_s": [0.0, 1.0]}]},
        conversion_record=record,
    )
    legacy_payload = template.to_dict()
    legacy_payload.pop("measurements")
    legacy_payload.pop("mapping_proposal")
    legacy_payload["content_hash"] = _legacy_content_hash(legacy_payload)

    restored = CanonicalExperiment.from_dict(legacy_payload)

    assert restored.content_hash == legacy_payload["content_hash"]
    assert restored.to_dict() == legacy_payload


def test_legacy_canonical_template_rejects_tampered_content_with_original_hash() -> None:
    record = ConversionRecord.create(
        conversion_id="legacy.converter.v1",
        source_artifact_id="legacy-sha",
    )
    template = CanonicalExperiment.create(
        template_id="legacy.template.v1",
        source_artifact_id="legacy-sha",
        payload={"segments": [{"setpoint_C": 180.0, "time_s": [0.0, 1.0]}]},
        conversion_record=record,
    )
    legacy_payload = template.to_dict()
    legacy_payload.pop("measurements")
    legacy_payload.pop("mapping_proposal")
    legacy_payload["content_hash"] = _legacy_content_hash(legacy_payload)
    tampered_payload = deepcopy(legacy_payload)
    tampered_payload["payload"]["segments"][0]["setpoint_C"] = 181.0

    with pytest.raises(ValueError, match="content hash"):
        CanonicalExperiment.from_dict(tampered_payload)


def test_legacy_canonical_template_cannot_gain_new_hash_bearing_fields() -> None:
    record = ConversionRecord.create(
        conversion_id="legacy.converter.v1",
        source_artifact_id="legacy-sha",
    )
    template = CanonicalExperiment.create(
        template_id="legacy.template.v1",
        source_artifact_id="legacy-sha",
        payload={},
        conversion_record=record,
    )
    legacy_payload = template.to_dict()
    legacy_payload.pop("measurements")
    legacy_payload.pop("mapping_proposal")
    legacy_payload["content_hash"] = _legacy_content_hash(legacy_payload)
    legacy = CanonicalExperiment.from_dict(legacy_payload)

    with pytest.raises(ValueError, match="legacy serialization"):
        replace(legacy, measurements=(_measurement(),))


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
