from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from polynexus.core.ai_platform import (
    CalibrationRef,
    CapabilityDescriptor,
    CapabilityPlanner,
)
from polynexus.core.ai_platform import default_descriptor_registry
from polynexus.core.canonical_experiments.nd_adapters import (
    adapt_detector_image,
    adapt_ir_temperature_series,
    adapt_nmr_fid,
)
from polynexus.core.canonical_experiments.registry import default_converter_registry


def _write_ir(path: Path, offset: float) -> None:
    path.write_text(
        "wavenumber,absorbance\n"
        f"1000,{offset}\n"
        f"1010,{offset + 0.1}\n"
        f"1020,{offset + 0.2}\n",
        encoding="utf-8",
    )


def test_ir_temperature_adapter_creates_one_matrix_block_and_keeps_measurements(tmp_path: Path) -> None:
    first = tmp_path / "PA6-100C.csv"
    second = tmp_path / "PA6-120C.csv"
    _write_ir(first, 0.2)
    _write_ir(second, 0.4)

    adapted = adapt_ir_temperature_series(
        [first, second], source_artifact_id="ir-series-artifact"
    )

    assert adapted.status == "ready"
    assert len(adapted.data_blocks) == 1
    block = adapted.data_blocks[0]
    assert block.kind == "matrix"
    assert block.shape == (2, 3)
    assert block.dims == ("temperature", "wavenumber")
    assert tuple(block.coords["temperature"]) == (100.0, 120.0)
    assert tuple(block.coords["wavenumber"]) == (1000.0, 1010.0, 1020.0)
    assert block.metadata["raw_arrays_included"] is False
    assert block.axis_provenance["temperature"].source == "inferred"
    assert adapted.template is not None
    assert len(adapted.template.measurements) == 2
    assert adapted.legacy_measurements == adapted.template.measurements


def test_ir_temperature_adapter_rejects_nonconformable_grids_without_interpolation(tmp_path: Path) -> None:
    first = tmp_path / "PA6-100C.csv"
    second = tmp_path / "PA6-120C.csv"
    _write_ir(first, 0.2)
    second.write_text(
        "wavenumber,absorbance\n1000,0.4\n1015,0.5\n1020,0.6\n",
        encoding="utf-8",
    )

    adapted = adapt_ir_temperature_series(
        [first, second], source_artifact_id="ir-series-artifact"
    )

    assert adapted.status == "needs_input"
    assert adapted.data_blocks == ()
    assert "temperature_series_grid_mismatch" in adapted.reason_codes


def test_detector_adapter_preserves_pixel_and_external_mask_references(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.tif"
    mask_path = tmp_path / "mask.tif"
    Image.fromarray(np.arange(12, dtype=np.uint16).reshape(3, 4)).save(image_path)
    Image.fromarray(np.ones((3, 4), dtype=np.uint8)).save(mask_path)

    adapted = adapt_detector_image(
        image_path,
        technique="saxs",
        source_artifact_id="detector-artifact",
        mask_path=mask_path,
    )

    assert adapted.status == "ready"
    block = adapted.data_block
    assert block is not None
    assert block.kind == "matrix"
    assert block.shape == (3, 4)
    assert block.mask_ref is not None
    assert block.mask_ref["sha256"] == hashlib.sha256(mask_path.read_bytes()).hexdigest()
    assert block.metadata["raw_pixels_included"] is False
    assert block.metadata["mask_present"] is True
    assert block.metadata["geometry"]["calibration_reviewed"] is False
    assert set(block.non_physical_dims) == {"detector_y", "detector_x"}


def test_nmr_fid_adapter_keeps_interleaved_imaginary_channel_reference(tmp_path: Path) -> None:
    fid_path = tmp_path / "fid"
    raw = np.asarray([1, 10, 2, 20, 3, 30, 4, 40], dtype=">i4")
    fid_path.write_bytes(raw.tobytes())

    adapted = adapt_nmr_fid(fid_path, source_artifact_id="nmr-fid-artifact")

    assert adapted.status == "ready"
    block = adapted.data_block
    assert block is not None
    assert block.kind == "complex"
    assert block.shape == (4,)
    assert block.metadata["imaginary_channel_preserved"] is True
    assert tuple(block.metadata["components"]) == ("real", "imaginary")
    assert block.metadata["storage"]["interleaved"] is True
    assert block.array_ref["sha256"] == hashlib.sha256(fid_path.read_bytes()).hexdigest()
    assert block.metadata["raw_values_included"] is False


def test_nmr_fid_adapter_accepts_explicit_nd_shape_without_inventing_physical_axes(tmp_path: Path) -> None:
    fid_path = tmp_path / "fid"
    raw = np.asarray(
        [1, 10, 2, 20, 3, 30, 4, 40, 5, 50, 6, 60, 7, 70, 8, 80],
        dtype=">i4",
    )
    fid_path.write_bytes(raw.tobytes())

    adapted = adapt_nmr_fid(
        fid_path,
        source_artifact_id="nmr-2d-fid",
        shape=(2, 4),
    )

    assert adapted.status == "ready"
    assert adapted.data_block is not None
    assert adapted.data_block.shape == (2, 4)
    assert adapted.data_block.dims == ("time", "indirect_time")
    assert set(adapted.data_block.non_physical_dims) == {"time", "indirect_time"}
    assert all(
        axis.source == "synthetic"
        for axis in adapted.data_block.axis_provenance.values()
    )


def test_default_nmr_fid_capabilities_do_not_execute_from_synthetic_axes_alone(
    tmp_path: Path,
) -> None:
    fid_path = tmp_path / "fid"
    raw = np.asarray([1, 10, 2, 20, 3, 30, 4, 40], dtype=">i4")
    fid_path.write_bytes(raw.tobytes())
    adapted = adapt_nmr_fid(fid_path, source_artifact_id="nmr-fid-artifact")
    assert adapted.data_block is not None

    plans = CapabilityPlanner(default_descriptor_registry()).inspect(
        data_blocks=(adapted.data_block,),
        target_capabilities=(
            "nmr.fid_fft.v1",
            "nmr.t1_from_fid.v1",
            "nmr.t2_from_fid.v1",
        ),
    )

    assert all(item.outcome == "needs_input" for item in plans)
    assert (
        "one_of:dwell_time|sampling_interval|spectral_width"
        in plans[0].state.missing_inputs
    )
    assert (
        "one_of:chemical_shift_calibration|chemical_shift_reference|ppm_reference"
        in plans[0].state.missing_inputs
    )
    assert "relaxation_delays" in plans[1].state.missing_inputs
    assert "relaxation_delays" in plans[2].state.missing_inputs


def test_nmr_fid_fft_needs_ppm_reference_even_when_sampling_is_explicit(
    tmp_path: Path,
) -> None:
    fid_path = tmp_path / "fid"
    raw = np.asarray([1, 10, 2, 20, 3, 30, 4, 40], dtype=">i4")
    fid_path.write_bytes(raw.tobytes())
    adapted = adapt_nmr_fid(
        fid_path,
        source_artifact_id="nmr-fid-artifact",
        metadata={"available_inputs": {"dwell_time": {"value": 1e-6, "unit": "s"}}},
    )
    assert adapted.data_block is not None
    descriptor = default_descriptor_registry().get("nmr.fid_fft.v1")
    planner = CapabilityPlanner((descriptor,))

    without_reference = planner.inspect(
        data_blocks=(adapted.data_block,),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    with_reference = planner.inspect(
        data_blocks=(adapted.data_block,),
        target_capabilities=(descriptor.capability_id,),
        available_inputs={
            "chemical_shift_reference": {
                "value": 0.0,
                "unit": "ppm",
                "reference": "declared",
            }
        },
    )[0]

    assert descriptor.output_schema["spectrum"]["unit"] == "ppm"
    assert without_reference.outcome == "needs_input"
    assert without_reference.state.missing_inputs == (
        "one_of:chemical_shift_calibration|chemical_shift_reference|ppm_reference",
    )
    assert with_reference.outcome == "executable"


def test_nmr_relaxation_capabilities_need_sampling_and_delays_but_not_ppm_reference(
    tmp_path: Path,
) -> None:
    fid_path = tmp_path / "fid"
    raw = np.asarray([1, 10, 2, 20, 3, 30, 4, 40], dtype=">i4")
    fid_path.write_bytes(raw.tobytes())
    adapted = adapt_nmr_fid(
        fid_path,
        source_artifact_id="nmr-relaxation-fid",
        metadata={
            "available_inputs": {
                "dwell_time": {"value": 1e-6, "unit": "s"},
                "relaxation_delays": {"value": (0.01, 0.1, 1.0), "unit": "s"},
            }
        },
    )
    assert adapted.data_block is not None

    plans = CapabilityPlanner(default_descriptor_registry()).inspect(
        data_blocks=(adapted.data_block,),
        target_capabilities=("nmr.t1_from_fid.v1", "nmr.t2_from_fid.v1"),
    )

    assert all(item.outcome == "executable" for item in plans)


def test_nmr_2d_complex_fid_matches_descriptor_with_explicit_axis_inputs(
    tmp_path: Path,
) -> None:
    fid_path = tmp_path / "ser"
    raw = np.asarray(
        [1, 10, 2, 20, 3, 30, 4, 40, 5, 50, 6, 60, 7, 70, 8, 80],
        dtype=">i4",
    )
    fid_path.write_bytes(raw.tobytes())
    adapted = adapt_nmr_fid(
        fid_path,
        source_artifact_id="nmr-2d-fid",
        shape=(2, 4),
        metadata={
            "available_inputs": {
                "spectral_width": {"value": 20_000.0, "unit": "Hz"},
                "indirect_dwell_time": {"value": 0.001, "unit": "s"},
            }
        },
    )
    assert adapted.data_block is not None
    descriptor = default_descriptor_registry().get("nmr.2d_fft.v1")

    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(adapted.data_block,),
        target_capabilities=(descriptor.capability_id,),
    )[0]

    assert adapted.data_block.kind == "complex"
    assert adapted.data_block.shape == (2, 4)
    assert adapted.data_block.dims == ("time", "indirect_time")
    assert "complex" in descriptor.input_contract["kinds"]
    assert item.outcome == "executable"


def test_missing_nmr_fid_is_actionable_input_not_unsupported_capability(tmp_path: Path) -> None:
    missing = tmp_path / "missing.fid"

    adapted = default_converter_registry().convert_data_blocks(
        missing,
        technique="nmr",
        source_artifact_id="missing-nmr",
    )

    assert adapted.status == "needs_input"
    assert adapted.data_blocks == ()
    assert adapted.reason_codes == ("nmr_fid_missing",)


def test_registry_data_block_route_and_missing_detector_calibration_are_explicit(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.tif"
    Image.fromarray(np.arange(12, dtype=np.uint16).reshape(3, 4)).save(image_path)
    adapted = default_converter_registry().convert_data_blocks(
        image_path,
        technique="saxs",
        source_artifact_id="detector-artifact",
    )
    assert adapted.data_block is not None

    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.radial_profile.v1",
        techniques=("saxs",),
        input_contract={
            "kinds": ("matrix",),
            "required_dims": ("detector_y", "detector_x"),
            "required_calibrations": ("saxs.detector_calibration",),
        },
        output_schema={"profile": {"type": "series"}},
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(adapted.data_block,),
        target_capabilities=(descriptor.capability_id,),
    )[0]
    assert item.outcome == "needs_input"
    assert item.state.computability == "needs_input"
    assert item.state.missing_inputs == ("calibration:saxs.detector_calibration",)


def test_detector_reviewed_calibration_reference_satisfies_only_the_declared_gate(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.tif"
    Image.fromarray(np.arange(12, dtype=np.uint16).reshape(3, 4)).save(image_path)
    calibration = CalibrationRef.create(
        "cal-1",
        "saxs.detector_calibration",
        "reviewed_geometry",
        "beamline_record",
        "reviewed",
        record_locator="artifact://calibration/1",
        record_sha256="a" * 64,
    )
    adapted = adapt_detector_image(
        image_path,
        technique="saxs",
        source_artifact_id="detector-artifact",
        calibration_ref=calibration,
    )
    assert adapted.data_block is not None
    descriptor = CapabilityDescriptor.create(
        capability_id="saxs.radial_profile.v1",
        techniques=("saxs",),
        input_contract={
            "kinds": ("matrix",),
            "required_dims": ("detector_y", "detector_x"),
            "required_calibrations": ("saxs.detector_calibration",),
        },
        output_schema={"profile": {"type": "series"}},
    )
    item = CapabilityPlanner((descriptor,)).inspect(
        data_blocks=(adapted.data_block,), target_capabilities=(descriptor.capability_id,)
    )[0]
    assert item.outcome == "executable"


def test_nd_capability_inventory_declares_schemas_without_placeholder_values() -> None:
    registry = default_descriptor_registry()
    expected = {
        "ir.temperature_matrix.v1",
        "ir.correlation_2d.v1",
        "saxs.detector_radial_profile.v1",
        "saxs.detector_azimuthal_profile.v1",
        "waxs.detector_radial_profile.v1",
        "nmr.fid_fft.v1",
        "nmr.t1_from_fid.v1",
        "nmr.t2_from_fid.v1",
        "nmr.2d_fft.v1",
    }
    assert expected.issubset(set(registry.ids))
    for capability_id in expected:
        descriptor = registry.get(capability_id)
        assert descriptor.status == "experimental"
        assert descriptor.output_schema
        assert descriptor.executor_key
    for capability_id in (
        "dma.master_curve.v1",
        "rheology.viscosity.v1",
        "tga.mass_loss_stages.v1",
        "sec.molecular_weight.v1",
        "mechanics.tensile.v1",
    ):
        descriptor = registry.get(capability_id)
        assert descriptor.status == "unsupported"
        assert descriptor.executor_key is None


def test_registry_nmr_metadata_is_forwarded_to_fid_block(tmp_path: Path) -> None:
    fid_path = tmp_path / "fid"
    fid_path.write_bytes(np.asarray([1, 2, 3, 4], dtype=">i4").tobytes())

    adapted = default_converter_registry().convert_data_blocks(
        fid_path,
        technique="nmr",
        source_artifact_id="nmr-metadata",
        nmr_metadata={
            "available_inputs": {
                "dwell_time": {"value": 1e-6, "unit": "s"},
                "chemical_shift_reference": {"value": 0.0, "unit": "ppm"},
            }
        },
    )

    assert adapted.data_block is not None
    assert adapted.data_block.metadata["available_inputs"]["dwell_time"]["unit"] == "s"
