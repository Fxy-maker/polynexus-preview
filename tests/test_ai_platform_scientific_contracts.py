from __future__ import annotations

import pytest

from polynexus.core.ai_platform import (
    CapabilityPlanner,
    ProviderResultInput,
    default_descriptor_registry,
)


SHA = "a" * 64


def test_provider_result_input_roundtrip_preserves_metric_manifest_and_hash() -> None:
    value = ProviderResultInput.create(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"Tm_peak_C": 185.2},
        metric_manifest=(
            {
                "path": "Tm_peak_C",
                "kind": "scalar",
                "status": "computed",
                "value": 185.2,
                "unit": "degC",
            },
        ),
        provenance={"source": "provider"},
    )

    restored = ProviderResultInput.from_dict(value.to_dict())

    assert restored == value
    assert restored.content_hash == value.content_hash
    assert restored.metric_manifest[0]["path"] == "Tm_peak_C"


def test_provider_result_input_rejects_manifest_without_matching_metric_value() -> None:
    with pytest.raises(ValueError, match="metric_manifest.*metrics"):
        ProviderResultInput.create(
            source_artifact_id="artifact-1",
            technique="dsc",
            metrics={"Tm_peak_C": 185.2},
            metric_manifest=(
                {
                    "path": "Tg_C",
                    "kind": "scalar",
                    "status": "computed",
                    "value": 80.0,
                },
            ),
        )


def test_provider_result_input_rejects_invalid_manifest_path_or_hash() -> None:
    with pytest.raises(ValueError, match="metric path"):
        ProviderResultInput.create(
            source_artifact_id="artifact-1",
            technique="dsc",
            metrics={"Tm_peak_C": 185.2},
            metric_manifest=(
                {"path": "", "kind": "scalar", "status": "computed", "value": 185.2},
            ),
        )

    with pytest.raises(ValueError, match="source_artifact_id"):
        ProviderResultInput.create(
            source_artifact_id="",
            technique="dsc",
            metrics={"Tm_peak_C": 185.2},
            metric_manifest=(
                {"path": "Tm_peak_C", "kind": "scalar", "status": "computed", "value": 185.2},
            ),
        )


def test_provider_result_input_only_marks_computed_rows_as_available() -> None:
    value = ProviderResultInput.create(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"Tm_peak_C": 185.2, "Tg_C": None},
        metric_manifest=(
            {"path": "Tm_peak_C", "kind": "scalar", "status": "computed", "value": 185.2},
            {"path": "Tg_C", "kind": "scalar", "status": "unavailable"},
        ),
    )

    assert value.available_metric_paths == ("Tm_peak_C",)


def test_provider_result_input_resolves_metric_paths_when_field_names_contain_dots() -> None:
    value = ProviderResultInput.create(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"segment_01_180.1C": {"Avrami_R2": 0.99}},
        metric_manifest=(
            {
                "path": "segment_01_180.1C.Avrami_R2",
                "kind": "scalar",
                "status": "computed",
                "value": 0.99,
            },
        ),
    )

    assert value.available_metric_paths == ("segment_01_180.1C.Avrami_R2",)


def test_provider_result_input_hash_uses_normalized_manifest_identity() -> None:
    value = ProviderResultInput.create(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"Tm_peak_C": 185.2},
        metric_manifest=(
            {
                "path": " Tm_peak_C ",
                "kind": "scalar",
                "status": " COMPUTED ",
                "value": 185.2,
            },
        ),
    )

    assert value.available_metric_paths == ("Tm_peak_C",)


def test_provider_descriptor_plans_against_formal_metric_manifest_input() -> None:
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
    descriptor = default_descriptor_registry().get("dsc.Tm.v1")

    item = CapabilityPlanner((descriptor,)).inspect(
        provider_results=(provider_input,),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert descriptor.input_contract["input_type"] == "provider_result"
    assert "kind" not in descriptor.input_contract
    assert item.outcome == "executable"
    assert item.selected_input_id == provider_input.input_id
    assert item.selected_data_block_id is None


def test_provider_descriptor_requires_one_declared_computed_metric_path() -> None:
    provider_input = ProviderResultInput.create(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"Tg_C": 80.0},
        metric_manifest=(
            {"path": "Tg_C", "kind": "scalar", "status": "computed", "value": 80.0},
        ),
    )
    descriptor = default_descriptor_registry().get("dsc.Tm.v1")

    item = CapabilityPlanner((descriptor,)).inspect(
        provider_results=(provider_input.to_dict(),),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert item.outcome == "needs_input"
    assert item.state.missing_inputs == ("provider_metric:Tm_peak_C|Tm_C|Tm",)


def test_provider_result_subclass_cannot_forge_available_metric_paths() -> None:
    legitimate = ProviderResultInput.create(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"Tg_C": 80.0},
        metric_manifest=(
            {"path": "Tg_C", "kind": "scalar", "status": "computed", "value": 80.0},
        ),
    )

    class ForgedProviderResult(ProviderResultInput):
        @property
        def available_metric_paths(self) -> tuple[str, ...]:
            return ("Tm_peak_C",)

    forged = ForgedProviderResult(
        input_id=legitimate.input_id,
        source_artifact_id=legitimate.source_artifact_id,
        technique=legitimate.technique,
        metrics=legitimate.metrics,
        metric_manifest=legitimate.metric_manifest,
        descriptor_id=legitimate.descriptor_id,
        computation_state=legitimate.computation_state,
        provenance=legitimate.provenance,
        uncertainty=legitimate.uncertainty,
        schema_version=legitimate.schema_version,
    )
    descriptor = default_descriptor_registry().get("dsc.Tm.v1")

    with pytest.raises(TypeError, match="ProviderResultInput values"):
        CapabilityPlanner((descriptor,)).inspect(
            provider_results=(forged,),
            target_capabilities=(descriptor.capability_id,),
        )


def test_provider_executor_rejects_provider_result_subclass_at_input_boundary() -> None:
    legitimate = ProviderResultInput.create(
        source_artifact_id="artifact-1",
        technique="dsc",
        metrics={"Tm_peak_C": 185.2, "Tg_C": -20.0},
        metric_manifest=(
            {"path": "Tm_peak_C", "kind": "scalar", "status": "computed", "value": 185.2},
        ),
    )

    class ForgedProviderResult(ProviderResultInput):
        @property
        def available_metric_paths(self) -> tuple[str, ...]:
            return ("Tm_peak_C", "Tg_C")

    forged = ForgedProviderResult(
        input_id=legitimate.input_id,
        source_artifact_id=legitimate.source_artifact_id,
        technique=legitimate.technique,
        metrics=legitimate.metrics,
        metric_manifest=legitimate.metric_manifest,
        descriptor_id=legitimate.descriptor_id,
        computation_state=legitimate.computation_state,
        provenance=legitimate.provenance,
        uncertainty=legitimate.uncertainty,
        schema_version=legitimate.schema_version,
    )

    with pytest.raises(TypeError, match="ProviderResultInput"):
        from polynexus.core.canonical_experiments.capabilities import CapabilityExecutor

        CapabilityExecutor().execute_provider_result(provider_input=forged)
