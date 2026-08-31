import math

import pytest

from polynexus.core.ai_platform.contracts import (
    AxisProvenance,
    CapabilityResultStatus,
    CalibrationRef,
    ComputationState,
    DataBlock,
    MissingnessPolicy,
    UncertaintyRef,
    axis_allows_quantitative,
    canonical_json_hash,
)


SHA = "a" * 64


def test_matrix_roundtrip_preserves_dims_units_mask_and_hash():
    axes = {"q": AxisProvenance.create("q", "observed", "instrument"), "r": AxisProvenance.create("r", "observed", "instrument")}
    block = DataBlock.create(
        "matrix",
        (2, 3),
        ("q", "r"),
        {"q": [1.0, 2.0], "r": [10, 20, 30]},
        {"q": "nm", "r": "nm"},
        {"uri": "data/matrix.npy", "sha256": SHA, "inline": False},
        mask_ref={"uri": "data/mask.npy", "sha256": SHA},
        axis_provenance=axes,
    )
    restored = DataBlock.from_dict(block.to_dict())
    assert restored == block
    assert restored.dims == ("q", "r")
    assert restored.coord_units == {"q": "nm", "r": "nm"}
    assert restored.mask_ref["uri"] == "data/mask.npy"
    assert restored.block_id == block.block_id


def test_complex_block_preserves_shape_and_dims():
    block = DataBlock.create(
        kind="complex",
        shape=(4,),
        dims=("frequency",),
        coords={"frequency": [1, 2, 3, 4]},
        coord_units={"frequency": "Hz"},
        array_ref={"uri": "complex.bin", "sha256": SHA},
        axis_provenance={"frequency": AxisProvenance.create("frequency", "observed", "instrument")},
    )
    assert DataBlock.from_dict(block.to_dict()).shape == (4,)
    assert block.dims == ("frequency",)


def test_synthetic_axis_disallows_quantitative_values():
    axis = AxisProvenance.create("temperature", "synthetic", "simulated")
    assert axis.status == "assumed"
    assert axis_allows_quantitative(axis) is False
    assert axis.accepts_quantitative is False


def test_computation_state_four_axis_roundtrip_and_stable_lists():
    state = ComputationState.create(
        "partial",
        "needs_input",
        "diagnostic",
        "review_required",
        missing_inputs=("z", "a", "z"),
        reason_codes=("quality", "missing", "quality"),
        preconditions=("b", "a"),
        next_actions=("review", "review", "supply"),
    )
    restored = ComputationState.from_dict(state.to_dict())
    assert restored == state
    assert restored.missing_inputs == ("a", "z")
    assert restored.reason_codes == ("missing", "quality")
    assert restored.preconditions == ("a", "b")
    assert restored.next_actions == ("review", "supply")


def test_reviewed_calibration_and_uncertainty_roundtrip():
    calibration = CalibrationRef.create(
        "cal-1", "detector", "dark-current", "lab-record", "reviewed", {"offset": 0.1},
        record_locator="records/cal-1.json", record_sha256=SHA,
    )
    uncertainty = UncertaintyRef.create(
        "std", inline={"value": 0.2, "unit": "nm"},
    )
    assert CalibrationRef.from_dict(calibration.to_dict()) == calibration
    assert UncertaintyRef.from_dict(uncertainty.to_dict()) == uncertainty


def test_schema_version_and_content_tampering_are_rejected():
    block = DataBlock.create("scalar", (), (), {}, {}, {"uri": "x", "sha256": SHA})
    payload = block.to_dict()
    assert payload["schema_version"] == "1"
    assert block.content_hash == block.block_id
    missing = dict(payload)
    missing.pop("schema_version")
    with pytest.raises(ValueError, match="schema"):
        DataBlock.from_dict(missing)
    unknown = dict(payload)
    unknown["schema_version"] = "2"
    with pytest.raises(ValueError, match="schema"):
        DataBlock.from_dict(unknown)
    tampered = dict(payload)
    tampered["kind"] = "series"
    with pytest.raises(ValueError, match="hash"):
        DataBlock.from_dict(tampered)


def test_artifact_refs_are_strict_and_uncertainty_is_exclusive():
    with pytest.raises(ValueError, match="sha256"):
        DataBlock.create("scalar", (), (), {}, {}, {"uri": "x", "sha256": "bad"})
    with pytest.raises(ValueError, match="mask_ref"):
        DataBlock.create("scalar", (), (), {}, {}, {"uri": "x", "sha256": SHA}, mask_ref={"uri": "m"})
    with pytest.raises(ValueError, match="exactly one"):
        UncertaintyRef.create("std", {"uri": "u", "sha256": SHA}, {"value": 1})
    with pytest.raises(ValueError, match="sha256"):
        UncertaintyRef.create("std", {"uri": "u", "sha256": "bad"})


def test_calibration_and_axis_require_reviewed_reference_when_calibrated():
    with pytest.raises(ValueError, match="record"):
        CalibrationRef.create("c", "s", "m", "src", "reviewed")
    with pytest.raises(ValueError, match="record"):
        CalibrationRef.create("c", "s", "m", "src", "applied_unreviewed")
    with pytest.raises(ValueError, match="calibration"):
        AxisProvenance.create("q", "calibrated", "m")
    ref = CalibrationRef.create("c", "s", "m", "src", "applied_unreviewed", record_locator="r", record_sha256=SHA)
    assert AxisProvenance.create("q", "calibrated", "m", calibration_ref=ref).accepts_quantitative


def test_results_candidate_requires_computed_and_validated():
    for computability, validity in (("needs_input", "validated"), ("computed", "diagnostic")):
        with pytest.raises(ValueError, match="results_candidate"):
            ComputationState.create("canonical", computability, validity, "results_candidate")


def test_strict_keys_and_physical_axis_requirements():
    with pytest.raises(TypeError, match="string keys"):
        canonical_json_hash({1: "bad"})
    with pytest.raises(ValueError, match="coord_units"):
        DataBlock.create("series", (2,), ("x",), {"x": [1, 2]}, {}, {"uri": "x", "sha256": SHA})
    with pytest.raises(ValueError, match="axis"):
        DataBlock.create("series", (2,), ("x",), {"x": [1, 2]}, {"x": "u"}, {"uri": "x", "sha256": SHA})
    with pytest.raises(ValueError, match="name"):
        DataBlock.create("series", (2,), ("x",), {"x": [1, 2]}, {"x": "u"}, {"uri": "x", "sha256": SHA}, axis_provenance={"x": AxisProvenance.create("y", "observed", "m")})


def test_source_artifact_and_capability_status_constants_roundtrip():
    block = DataBlock.create("scalar", (), (), {}, {}, {"uri": "x", "sha256": SHA}, source_artifact_id="artifact-1")
    assert DataBlock.from_dict(block.to_dict()).source_artifact_id == "artifact-1"
    assert CapabilityResultStatus.COMPLETED == "completed"
    assert set(CapabilityResultStatus.ALL) == {"completed", "needs_input", "failed", "not_applicable"}


def test_invalid_shape_nonfinite_and_hash_are_rejected():
    with pytest.raises(ValueError, match="shape"):
        DataBlock.create("matrix", (2, -1), ("x", "y"), {}, {}, {"uri": "x", "sha256": SHA})
    with pytest.raises(ValueError, match="finite"):
        DataBlock.create(
            "series", (1,), ("x",), {"x": [math.inf]}, {"x": "u"}, {"uri": "x", "sha256": SHA}
        )
    block = DataBlock.create(
        "scalar", (), (), {}, {}, {"uri": "x", "sha256": SHA}
    )
    payload = block.to_dict()
    payload["block_id"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        DataBlock.from_dict(payload)


def test_array_reference_requires_string_uri():
    with pytest.raises(ValueError, match="uri"):
        DataBlock.create("scalar", (), (), {}, {}, {"uri": 123, "sha256": SHA})


def test_unsafe_promotion_combination_is_rejected():
    with pytest.raises(ValueError, match="results_candidate"):
        ComputationState.create("canonical", "computed", "not_assessed", "results_candidate")


def test_canonical_json_hash_is_stable_and_json_safe():
    assert canonical_json_hash({"b": 2, "a": 1}) == canonical_json_hash({"a": 1, "b": 2})
    with pytest.raises(ValueError, match="finite"):
        canonical_json_hash({"bad": math.nan})


def test_datablock_requires_physical_axes_and_declares_missingness_quality():
    with pytest.raises(ValueError, match="coordinate"):
        DataBlock.create(
            "matrix", (2, 3), ("temperature", "wavenumber"), {}, {},
            {"uri": "matrix", "sha256": SHA},
        )

    axis = AxisProvenance.create("x", "observed", "instrument")
    block = DataBlock.create(
        "series", (2,), ("x",), {"x": (1.0, 2.0)}, {"x": "a.u."},
        {"uri": "series", "sha256": SHA},
        axis_provenance={"x": axis},
        missingness=MissingnessPolicy.create("mask"),
        mask_ref={"uri": "mask", "sha256": SHA},
        quality_flags=("masked_points",),
    )
    assert block.missingness.strategy == "mask"
    assert block.quality_flags == ("masked_points",)
    assert DataBlock.from_dict(block.to_dict()) == block


def test_datablock_rejects_malformed_coordinates_and_normalizes_before_hashing():
    axis = AxisProvenance.create("x", "observed", "instrument")
    with pytest.raises(ValueError, match="coordinate"):
        DataBlock.create(
            "series", (2,), ("x",), {"x": "not-an-axis"}, {"x": "u"},
            {"uri": "series", "sha256": SHA}, axis_provenance={"x": axis},
        )
    with pytest.raises(ValueError, match="coordinate"):
        DataBlock.create(
            "series", (2,), ("x",), {"x": (1.0,)}, {"x": "u"},
            {"uri": "series", "sha256": SHA}, axis_provenance={"x": axis},
        )
    with pytest.raises(TypeError, match="dims"):
        DataBlock.create(
            "series", (2,), (1,), {"1": (1.0, 2.0)}, {"1": "u"},
            {"uri": "series", "sha256": SHA},
            axis_provenance={"1": AxisProvenance.create("1", "observed", "instrument")},
        )


def test_state_lists_and_axis_transforms_are_typed_and_replayable():
    with pytest.raises(TypeError, match="sequence"):
        ComputationState.create("raw", "needs_input", "not_assessed", "diagnostic_only", missing_inputs="q")
    with pytest.raises(ValueError, match="nonempty"):
        ComputationState.create("raw", "needs_input", "not_assessed", "diagnostic_only", missing_inputs=("",))
    axis = AxisProvenance.create(
        "q", "inferred", "calibrated_from_reference",
        transform_chain=({"method": "scale", "parameters": {"factor": 2.0}},),
    )
    restored = AxisProvenance.from_dict(axis.to_dict())
    assert restored == axis
    assert restored.transform_chain[0]["method"] == "scale"
