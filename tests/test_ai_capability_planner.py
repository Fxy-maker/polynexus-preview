from __future__ import annotations

from collections.abc import Mapping

import pytest

from polynexus.core.ai_platform.capabilities import (
    CapabilityDescriptor,
    CapabilityDescriptorRegistry,
    default_descriptor_registry,
)
from polynexus.core.ai_platform.contracts import AxisProvenance, ComputationState, DataBlock
from polynexus.core.ai_platform.planner import CapabilityPlanItem, CapabilityPlanner


def matrix_block(
    *,
    calibrations: tuple[str, ...] = (),
    axis_source: str = "observed",
    technique: str = "saxs",
    family: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> DataBlock:
    q_axis = AxisProvenance.create(
        name="q",
        source=axis_source,
        method="detector_geometry" if axis_source != "synthetic" else "frame_index",
        quantity="scattering_vector",
        unit="1/nm",
    )
    intensity_axis = AxisProvenance.create(
        name="intensity",
        source="observed",
        method="detector_counts",
        quantity="intensity",
        unit="count",
    )
    return DataBlock.create(
        kind="matrix",
        shape=(2, 3),
        dims=("q", "intensity"),
        coords={"q": (0.1, 0.2), "intensity": (1.0, 2.0, 3.0)},
        coord_units={"q": "1/nm", "intensity": "count"},
        array_ref={"uri": "artifact://array/matrix", "sha256": "a" * 64},
        axis_provenance={"q": q_axis, "intensity": intensity_axis},
        source_artifact_id="artifact-matrix",
        metadata={
            "technique": technique,
            **({"measurement_family": family} if family is not None else {}),
            "calibrations": [
                value if isinstance(value, dict) else {
                    "scope": value,
                    "status": "reviewed",
                    "record_locator": f"calibrations/{value}",
                    "record_sha256": "a" * 64,
                }
                for value in calibrations
            ],
            **({} if metadata is None else dict(metadata)),
        },
    )


def constrained_matrix_block(
    *,
    q_coords: tuple[float, ...] = (0.1, 0.2, 0.3),
    q_unit: str = "1/nm",
    q_quantity: str = "scattering_vector",
) -> DataBlock:
    q_axis = AxisProvenance.create(
        name="q",
        source="observed",
        method="detector_geometry",
        quantity=q_quantity,
        unit=q_unit,
    )
    intensity_axis = AxisProvenance.create(
        name="intensity",
        source="observed",
        method="detector_counts",
        quantity="intensity",
        unit="count",
    )
    return DataBlock.create(
        kind="matrix",
        shape=(len(q_coords), 3),
        dims=("q", "intensity"),
        coords={"q": q_coords, "intensity": (1.0, 2.0, 3.0)},
        coord_units={"q": q_unit, "intensity": "count"},
        array_ref={"uri": "artifact://array/constrained", "sha256": "c" * 64},
        axis_provenance={"q": q_axis, "intensity": intensity_axis},
        source_artifact_id="artifact-constrained",
        metadata={"technique": "saxs", "measurement_family": "detector_image"},
    )


def test_descriptor_validation_and_roundtrip_preserve_versioned_contract() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.absolute_intensity.v1",
        techniques=("SAXS",),
        input_contract={"kind": "matrix", "required_calibrations": ["q"]},
        output_schema={"absolute_intensity": {"unit": "1/cm"}},
        status="available",
        executor_key="saxs.absolute_intensity",
    )

    restored = CapabilityDescriptor.from_dict(descriptor.to_dict())

    assert restored == descriptor
    assert descriptor.version == "1"
    assert descriptor.techniques == ("saxs",)
    assert descriptor.content_hash == restored.content_hash


def test_descriptor_rejects_invalid_status_and_non_mapping_contracts() -> None:
    with pytest.raises(ValueError, match="Unsupported capability descriptor status"):
        CapabilityDescriptor.create(
            capability_id="bad.v1",
            techniques=("saxs",),
            input_contract={},
            output_schema={},
            status="fabricated",
        )
    with pytest.raises(TypeError, match="input_contract"):
        CapabilityDescriptor.create(
            capability_id="bad.v1",
            techniques=("saxs",),
            input_contract=("matrix",),
            output_schema={},
            status="available",
        )


def test_planner_returns_needs_input_for_missing_calibration_without_running_provider() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.absolute_intensity.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_calibrations": ["q"]},
        output_schema={"absolute_intensity": {"unit": "1/cm"}},
        status="available",
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(calibrations=()),),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert item.outcome == "needs_input"
    assert item.state.computability == "needs_input"
    assert item.state.missing_inputs == ("calibration:q",)
    assert "calibration:q" in item.next_actions[0]


def test_planner_treats_single_calibration_string_as_one_requirement() -> None:
    """A scalar descriptor calibration name must not be iterated character-by-character."""

    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.absolute_intensity.scalar_calibration.v1",
        techniques=("saxs",),
        input_contract={
            "kind": "matrix",
            "required_calibrations": "q_calibration",
        },
        output_schema={"absolute_intensity": {"unit": "1/cm"}},
        status="available",
    )

    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(calibrations=("q_calibration",)),),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert item.outcome == "executable"
    assert item.calibration_hashes == ("a" * 64,)


def test_planner_rejects_dependency_admission_from_different_descriptor_registry() -> None:
    """A trusted admission must match the target registry's descriptor identity."""

    dependency_a = CapabilityDescriptor.create(
        capability_id="dependency.registry_bound.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"value": {"type": "scalar"}},
        uncertainty_policy={"mode": "registry-a"},
    )
    dependency_b = CapabilityDescriptor.create(
        capability_id=dependency_a.capability_id,
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"value": {"type": "scalar"}},
        uncertainty_policy={"mode": "registry-b"},
    )
    consumer = CapabilityDescriptor.create(
        capability_id="consumer.registry_bound.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"value": {"type": "scalar"}},
        dependencies=(dependency_a.capability_id,),
    )
    source = matrix_block()
    admission = CapabilityPlanner((dependency_a, consumer)).inspect(
        data_blocks=(source,),
        target_capabilities=(dependency_a.capability_id,),
    )[0]

    target = CapabilityPlanner((dependency_b, consumer)).inspect(
        data_blocks=(source,),
        target_capabilities=(consumer.capability_id,),
        available_capabilities={dependency_a.capability_id: admission},
    )[0]

    assert target.outcome == "needs_input"
    assert "dependency:dependency.registry_bound.v1" in target.state.missing_inputs


def test_planner_blocks_unreviewed_calibration_when_descriptor_requires_review() -> None:
    """An applied-but-unreviewed calibration cannot satisfy a reviewed gate."""

    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.reviewed_calibration.v1",
        techniques=("saxs",),
        input_contract={
            "kind": "matrix",
            "required_calibrations": ("q",),
        },
        output_schema={"value": {"type": "scalar"}},
        evidence_policy={"requires_reviewed_calibration": True},
    )
    block = matrix_block(
        calibrations=(
            {
                "scope": "q",
                "status": "applied_unreviewed",
                "record_locator": "calibrations/q",
                "record_sha256": "b" * 64,
            },
        )
    )

    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(block,),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert item.outcome == "blocked"
    assert "calibration_not_reviewed:q" in item.state.reason_codes


def test_planner_rejects_synthetic_axis_for_absolute_capability() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.absolute_intensity.v1",
        techniques=("saxs",),
        input_contract={
            "kind": "matrix",
            "required_calibrations": ["q"],
            "axis_requirements": {"q": {"quantitative": True}},
        },
        output_schema={"absolute_intensity": {"unit": "1/cm"}},
        status="available",
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(axis_source="synthetic"),),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert item.outcome == "blocked"
    assert item.state.computability == "blocked"
    assert "axis_provenance_not_accepted:q" in item.state.reason_codes


def test_planner_marks_ready_existing_generic_capability_executable() -> None:
    planner = CapabilityPlanner(default_descriptor_registry())
    item = planner.inspect(
        data_blocks=(matrix_block(calibrations=("q",)),),
        target_capabilities=("curve.summary.v1",),
    )[0]

    assert item.outcome == "executable"
    assert item.state.computability == "computed"
    assert item.data_block_ids == (matrix_block(calibrations=("q",)).block_id,)


def test_ir_and_ftir_resolve_to_one_descriptor_namespace() -> None:
    registry = default_descriptor_registry()
    assert registry.for_technique("ir") == registry.for_technique("ftir")


def test_existing_provider_capability_is_adapted_with_stable_namespaced_id() -> None:
    descriptor = default_descriptor_registry().get("dsc.Tg.v1")

    assert descriptor.status == "available"
    assert descriptor.executor_key == "provider_result"
    assert "dsc" in descriptor.techniques
    assert default_descriptor_registry().get("Tg", technique="dsc") == descriptor


def test_ftir_provider_alias_is_present_in_canonical_ir_descriptor_namespace() -> None:
    registry = default_descriptor_registry()
    descriptor = registry.get("ir.peak_position.v1")
    assert descriptor.techniques == ("ir",)
    assert registry.get("peak_position", technique="ftir") == descriptor


def test_common_polymer_family_descriptor_is_explicitly_unsupported_not_fabricated() -> None:
    descriptor = default_descriptor_registry().get("dma.master_curve.v1")

    assert descriptor.status == "unsupported"
    assert descriptor.executor_key is None
    item = CapabilityPlanner(default_descriptor_registry()).inspect(
        data_blocks=(matrix_block(),),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    assert item.outcome == "not_applicable"
    assert item.state.computability == "not_applicable"
    assert item.state.reason_codes == ("capability_unsupported",)


def test_registry_rejects_duplicate_descriptor_ids_and_unknown_capabilities() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="curve.summary.v1",
        techniques=("ir",),
        input_contract={"kind": "series"},
        output_schema={},
        status="available",
    )
    registry = CapabilityDescriptorRegistry((descriptor,))
    with pytest.raises(ValueError, match="Unknown capability"):
        registry.get("missing.v1")
    with pytest.raises(ValueError, match="unique"):
        CapabilityDescriptorRegistry((descriptor, descriptor))


def test_descriptor_needs_input_status_never_becomes_executable() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="rheology.pending.v1",
        techniques=("rheology",),
        input_contract={"kind": "matrix"},
        output_schema={},
        status="needs_input",
        missing_input_actions=("provide_frequency_sweep",),
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(technique="rheology"),),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    assert item.outcome == "needs_input"
    assert item.state.computability == "needs_input"


def test_planner_selects_an_executable_candidate_when_first_candidate_is_blocked() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.absolute.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_calibrations": ("q",), "axis_requirements": {"q": {"quantitative": True}}},
        output_schema={},
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(axis_source="synthetic"), matrix_block(calibrations=("q",))),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    assert item.outcome == "executable"
    assert item.selected_data_block_id == item.data_block_ids[1]
    assert len(item.data_block_ids) == 2


def test_planner_rejects_non_json_metadata_and_preserves_structured_actions() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.pending.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_calibrations": ("q",)},
        output_schema={},
        missing_input_actions=({"action": "provide_calibration", "name": "q"},),
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(),), target_capabilities=(descriptor.capability_id,)
    )[0]
    structured = next(action for action in item.state.next_actions if isinstance(action, Mapping))
    assert structured["action"] == "provide_calibration"
    structured_public = next(action for action in item.to_dict()["next_actions"] if isinstance(action, Mapping))
    assert structured_public["name"] == "q"
    with pytest.raises(TypeError, match="JSON"):
        CapabilityPlanItem(
            capability_id="bad.v1", descriptor_version="1", outcome="needs_input",
            state=ComputationState.create("missing", "needs_input", "not_assessed", "diagnostic_only"),
            metadata={"bad": object()},
        )


def test_planner_requires_validated_calibration_metadata_and_checks_measurement_family() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="curve.spectrum.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "measurement_families": ("spectrum_1d",), "required_calibrations": ("q",)},
        output_schema={},
    )
    invalid_cal = matrix_block(calibrations=({"scope": "q", "status": "missing"},))
    wrong_family = matrix_block(calibrations=("q",), family="scattering_1d")
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(invalid_cal,), target_capabilities=(descriptor.capability_id,)
    )[0]
    assert item.outcome == "needs_input"
    item2 = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(wrong_family,), target_capabilities=(descriptor.capability_id,)
    )[0]
    assert item2.outcome == "needs_input"


def test_planner_requires_complete_hashed_calibration_records() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.absolute.strict.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix", "required_calibrations": ("q",)},
        output_schema={},
    )
    incomplete = matrix_block(calibrations=({"scope": "q", "status": "reviewed"},))
    bad_hash = matrix_block(calibrations=({
        "scope": "q", "status": "reviewed", "record_locator": "cal/q.json", "record_sha256": "z" * 64,
    },))
    for block in (incomplete, bad_hash):
        item = CapabilityPlanner((descriptor,)).inspect(
            data_blocks=(block,), target_capabilities=(descriptor.capability_id,)
        )[0]
        assert item.outcome == "needs_input"


def test_descriptor_rejects_non_string_sequence_values_and_alias_collisions() -> None:
    with pytest.raises(TypeError):
        CapabilityDescriptor.create(
            capability_id="bad.v1", techniques=("saxs",), input_contract={}, output_schema={}, aliases=(1,)
        )
    first = CapabilityDescriptor.create(
        capability_id="first.v1", techniques=("saxs",), input_contract={}, output_schema={}, aliases=("second.v1",)
    )
    second = CapabilityDescriptor.create(
        capability_id="second.v1", techniques=("saxs",), input_contract={}, output_schema={}
    )
    with pytest.raises(ValueError, match="alias"):
        CapabilityDescriptorRegistry((first, second))


def test_required_inputs_are_a_gate_for_an_existing_matching_data_block() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="nmr.relaxation.v1",
        techniques=("nmr",),
        input_contract={"kind": "matrix", "required_inputs": ("relaxation_delays",)},
        output_schema={"T1": {"type": "scalar", "unit": "s"}},
    )

    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(technique="nmr"),),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert item.outcome == "needs_input"
    assert item.state.missing_inputs == ("relaxation_delays",)
    assert item.state.reason_codes == ("missing_input:relaxation_delays",)


@pytest.mark.parametrize(
    "planner_kwargs",
    (
        {"available_inputs": {"relaxation_delays": (0.01, 0.1, 1.0)}},
        {"input_declarations": {"relaxation_delays": {"status": "available"}}},
        {"context": {"available_inputs": {"relaxation_delays": True}}},
    ),
)
def test_required_inputs_accept_only_explicit_planner_declarations(
    planner_kwargs: Mapping[str, object],
) -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="nmr.relaxation.v1",
        techniques=("nmr",),
        input_contract={"kind": "matrix", "required_inputs": ("relaxation_delays",)},
        output_schema={"T1": {"type": "scalar", "unit": "s"}},
    )

    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(technique="nmr"),),
        target_capabilities=(descriptor.capability_id,),
        **planner_kwargs,
    )[0]

    assert item.outcome == "executable"


@pytest.mark.parametrize(
    ("status", "expected_outcome"),
    (
        ("planned", "needs_input"),
        ("executable", "needs_input"),
        ("computed", "executable"),
        ("completed", "executable"),
    ),
)
def test_required_inputs_only_accept_materialized_statuses(
    status: str, expected_outcome: str
) -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="nmr.relaxation_status_gate.v1",
        techniques=("nmr",),
        input_contract={"kind": "matrix", "required_inputs": ("relaxation_delays",)},
        output_schema={"T1": {"type": "scalar", "unit": "s"}},
    )

    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(technique="nmr"),),
        target_capabilities=(descriptor.capability_id,),
        available_inputs={"relaxation_delays": {"status": status}},
    )[0]

    assert item.outcome == expected_outcome


def test_required_inputs_use_namespaced_data_block_metadata_not_similar_fields() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="nmr.relaxation.v1",
        techniques=("nmr",),
        input_contract={"kind": "matrix", "required_inputs": ("relaxation_delays",)},
        output_schema={"T1": {"type": "scalar", "unit": "s"}},
    )
    planner = CapabilityPlanner((descriptor,))

    inferred = planner.inspect(
        data_blocks=(
            matrix_block(
                technique="nmr",
                metadata={"relaxation_delays": (0.01, 0.1, 1.0)},
            ),
        ),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    declared = planner.inspect(
        data_blocks=(
            matrix_block(
                technique="nmr",
                metadata={
                    "available_inputs": {
                        "relaxation_delays": (0.01, 0.1, 1.0),
                    }
                },
            ),
        ),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert inferred.outcome == "needs_input"
    assert declared.outcome == "executable"


def test_required_any_inputs_requires_one_declared_member_from_every_group() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="nmr.2d_axis.v1",
        techniques=("nmr",),
        input_contract={
            "kind": "matrix",
            "required_any_inputs": (
                ("dwell_time", "spectral_width"),
                ("indirect_dwell_time", "indirect_spectral_width"),
            ),
        },
        output_schema={"spectrum": {"type": "matrix"}},
    )
    planner = CapabilityPlanner((descriptor,))

    partial = planner.inspect(
        data_blocks=(matrix_block(technique="nmr"),),
        target_capabilities=(descriptor.capability_id,),
        available_inputs={"spectral_width": 20_000.0},
    )[0]
    complete = planner.inspect(
        data_blocks=(matrix_block(technique="nmr"),),
        target_capabilities=(descriptor.capability_id,),
        available_inputs={
            "spectral_width": 20_000.0,
            "indirect_dwell_time": 0.001,
        },
    )[0]

    assert partial.outcome == "needs_input"
    assert partial.state.missing_inputs == (
        "one_of:indirect_dwell_time|indirect_spectral_width",
    )
    assert complete.outcome == "executable"


@pytest.mark.parametrize(
    "value",
    (
        "dwell_time",
        ("dwell_time",),
        ((),),
        (("dwell_time", 1),),
    ),
)
def test_required_any_inputs_schema_fails_closed(value: object) -> None:
    with pytest.raises((TypeError, ValueError), match="required_any_inputs"):
        CapabilityDescriptor.create(
            capability_id="nmr.invalid_any_input.v1",
            techniques=("nmr",),
            input_contract={"kind": "complex", "required_any_inputs": value},
            output_schema={},
        )


def test_planner_does_not_match_unlabelled_block_to_technique_descriptor():
    axis = AxisProvenance.create("q", "observed", "instrument")
    block = DataBlock.create(
        kind="matrix",
        shape=(2, 2),
        dims=("q", "intensity"),
        coords={"q": (0.1, 0.2), "intensity": (1.0, 2.0)},
        coord_units={"q": "1/nm", "intensity": "count"},
        array_ref={"uri": "artifact://unlabelled", "sha256": "a" * 64},
        axis_provenance={
            "q": axis,
            "intensity": AxisProvenance.create("intensity", "observed", "instrument"),
        },
    )
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.matrix.summary.v1",
        techniques=("saxs",),
        input_contract={
            "kind": "matrix",
            "measurement_families": ("detector_image",),
        },
        output_schema={"value": {"type": "scalar"}},
    )

    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(block,), target_capabilities=(descriptor.capability_id,)
    )[0]
    assert item.outcome == "needs_input"
    assert item.state.reason_codes == ("data_block_missing",)


def test_planner_enforces_descriptor_axis_units_quantity_order_and_shape() -> None:
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.strict_profile.v1",
        techniques=("saxs",),
        input_contract={
            "kind": "matrix",
            "measurement_families": ("detector_image",),
            "axis_requirements": {
                "q": {
                    "unit": "1/nm",
                    "quantity": "scattering_vector",
                    "monotonic": True,
                    "unique": True,
                    "required": True,
                }
            },
            "shape_requirements": {
                "rank": 2,
                "dimensions": {"q": {"min_size": 3}},
            },
        },
        output_schema={"profile": {"type": "series"}},
    )
    planner = CapabilityPlanner((descriptor,))

    valid = planner.inspect(
        data_blocks=(constrained_matrix_block(),),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    wrong_unit = planner.inspect(
        data_blocks=(constrained_matrix_block(q_unit="angstrom^-1"),),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    duplicate_axis = planner.inspect(
        data_blocks=(constrained_matrix_block(q_coords=(0.1, 0.1, 0.3)),),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    short_shape = planner.inspect(
        data_blocks=(constrained_matrix_block(q_coords=(0.1, 0.2)),),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert valid.outcome == "executable"
    assert wrong_unit.state.reason_codes == ("axis_unit_mismatch:q",)
    assert duplicate_axis.state.reason_codes == ("axis_not_unique:q",)
    assert short_shape.state.reason_codes == ("shape_dimension_too_short:q",)


def test_planner_requires_declared_capability_dependencies() -> None:
    dependency = CapabilityDescriptor.create(
        capability_id="saxs.detector_radial_profile.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
    )
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.dependent_profile.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
        dependencies=("saxs.detector_radial_profile.v1",),
    )
    planner = CapabilityPlanner((dependency, descriptor))
    block = matrix_block(family="detector_image")

    missing = planner.inspect(
        data_blocks=(block,), target_capabilities=(descriptor.capability_id,)
    )[0]
    available = planner.inspect(
        data_blocks=(block,),
        target_capabilities=(descriptor.capability_id,),
        available_capabilities={
            dependency.capability_id: planner.inspect(
                data_blocks=(block,),
                target_capabilities=(dependency.capability_id,),
            )[0]
        },
    )[0]

    assert missing.outcome == "needs_input"
    assert missing.state.missing_inputs == (
        "dependency:saxs.detector_radial_profile.v1",
    )
    assert available.outcome == "executable"


@pytest.mark.parametrize(
    "declaration",
    (
        True,
        {"status": "completed"},
        {"computability": "computed"},
        {"state": {"computability": "computed"}},
    ),
)
def test_planner_rejects_unattested_capability_completion_declarations(
    declaration: object,
) -> None:
    """A dependency must be proved by a Core-issued admission, not metadata."""

    dependency_id = "saxs.detector_radial_profile.v1"
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.dependent_profile.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
        dependencies=(dependency_id,),
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(),),
        target_capabilities=(descriptor.capability_id,),
        available_capabilities={dependency_id: declaration},
    )[0]

    assert item.outcome == "needs_input"
    assert item.state.missing_inputs == (f"dependency:{dependency_id}",)


def test_planner_accepts_only_a_matching_core_issued_dependency_admission() -> None:
    dependency = CapabilityDescriptor.create(
        capability_id="saxs.detector_radial_profile.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
    )
    target = CapabilityDescriptor.create(
        capability_id="saxs.dependent_profile.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
        dependencies=(dependency.capability_id,),
    )
    planner = CapabilityPlanner((dependency, target))
    block = matrix_block()
    dependency_admission = planner.inspect(
        data_blocks=(block,), target_capabilities=(dependency.capability_id,)
    )[0]

    item = planner.inspect(
        data_blocks=(block,),
        target_capabilities=(target.capability_id,),
        available_capabilities={dependency.capability_id: dependency_admission},
    )[0]

    assert dependency_admission.is_trusted_admission is True
    assert item.outcome == "executable"
    assert item.dependency_bindings == (
        {
            "capability_id": dependency.capability_id,
            "descriptor_version": dependency.version,
            "descriptor_hash": dependency.content_hash,
            "admission_hash": dependency_admission.admission_hash,
        },
    )


@pytest.mark.parametrize("status", ("planned", "executable", "needs_input", "blocked", "failed"))
def test_planner_does_not_treat_noncompleted_capability_state_as_available(status: str) -> None:
    dependency_id = "saxs.detector_radial_profile.v1"
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.dependent_profile.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"profile": {"type": "series"}},
        dependencies=(dependency_id,),
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(),),
        target_capabilities=(descriptor.capability_id,),
        available_capabilities={dependency_id: {"status": status}},
    )[0]

    assert item.outcome == "needs_input"
    assert item.state.missing_inputs == (f"dependency:{dependency_id}",)


def test_planner_can_optionally_require_experimental_executor_binding():
    descriptor = default_descriptor_registry().get("nmr.fid_fft.v1")
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(),
        target_capabilities=(descriptor.capability_id,),
        require_executor=True,
    )[0]
    assert item.outcome == "needs_input"
    assert item.state.reason_codes == ("executor_unavailable",)


def test_planner_item_is_an_in_process_admission_and_serialized_copy_is_not():
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.admission_probe.v1",
        techniques=("saxs",),
        input_contract={"kind": "matrix"},
        output_schema={"value": {"type": "scalar"}},
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(matrix_block(),), target_capabilities=(descriptor.capability_id,)
    )[0]

    assert item.outcome == "executable"
    assert item.is_trusted_admission is True
    assert item.as_admission() is item
    restored = CapabilityPlanItem.from_dict(item.to_dict())
    assert restored.is_trusted_admission is False
    with pytest.raises(ValueError, match="not issued"):
        restored.as_admission()
