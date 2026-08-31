"""Adapters from canonical experiment envelopes to shared :class:`DataBlock`s.

The canonical experiment layer predates the AI platform and intentionally keeps
small compatibility ``Measurement`` objects in its JSON representation.  This
module provides the narrow bridge to the content-addressed, N-dimensional
``DataBlock`` contract without copying numerical arrays into a second model.

Adapters are deliberately reference-first:

* source bytes are represented by URI/sha256 references;
* dimensions and coordinates are recorded only when observed or explicitly
  supplied;
* an inferred filename condition is marked as such and cannot satisfy a
  quantitative axis gate;
* detector pixel indices are explicitly non-physical until a reviewed
  geometry calibration is supplied; and
* an NMR FID remains complex (real and imaginary channels are never projected
  to a real display spectrum here).

The existing ``convert_path`` and ``Measurement`` APIs remain unchanged.  Use
``CanonicalConverterRegistry.convert_data_blocks`` or the three technique
helpers below when an AI/GUI caller needs the shared N-D representation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from polynexus.core.ai_platform.contracts import (
    AxisProvenance,
    CalibrationRef,
    DataBlock,
    canonical_json_hash,
)

from .detector_image import convert_detector_image
from .ir_temperature_series import build_ir_temperature_series_template
from .models import CanonicalExperiment, ConversionOutcome, Measurement, ConversionRecord


_ADAPTER_STATUSES = frozenset({"ready", "review_required", "blocked", "needs_input"})
_FID_EXTENSIONS = frozenset({".fid", ".ser"})
_TABLE_EXTENSIONS = frozenset(
    {".csv", ".tsv", ".txt", ".dat", ".asc", ".xy", ".chi", ".xls", ".xlsx", ".xlsm"}
)
_IMAGE_EXTENSIONS = frozenset({".edf", ".cbf", ".tif", ".tiff", ".h5", ".hdf5", ".nxs"})
_TECHNIQUE_ALIASES = {
    "ftir": "ir",
    "infrared": "ir",
    "fourier_transform_infrared": "ir",
    "saxs2d": "saxs",
    "waxs2d": "waxs",
}

# These fields describe the representation produced by this adapter rather
# than caller-provided acquisition annotations.  Letting an arbitrary
# metadata mapping overwrite them would make a reference-only complex FID
# appear to be a different technique, representation, or storage layout.
_NMR_RESERVED_METADATA_KEYS = frozenset(
    {
        "technique",
        "measurement_family",
        "representation",
        "source_format",
        "raw_values_included",
        "imaginary_channel_preserved",
        "components",
        "complex_components",
        "channel_layout",
        "imaginary_channel",
        "storage",
        "source_path",
        "point_count",
        "nucleus",
    }
)


@dataclass(frozen=True)
class DataBlockAdapterResult:
    """Result of a canonical-to-``DataBlock`` adaptation.

    ``template`` and ``legacy_measurements`` are intentionally retained so a
    caller can render the current compatibility view while AI and GUI code
    consume the exact same ``data_blocks`` tuple.  A non-ready result never
    carries a fabricated block.
    """

    status: str
    data_blocks: tuple[DataBlock, ...] = ()
    template: CanonicalExperiment | None = None
    reason_codes: tuple[str, ...] = ()
    legacy_measurements: tuple[Measurement, ...] = ()
    conversion: ConversionOutcome | None = None

    def __post_init__(self) -> None:
        status = str(self.status)
        if status not in _ADAPTER_STATUSES:
            raise ValueError(f"Unsupported data-block adapter status: {status}")
        object.__setattr__(self, "status", status)
        blocks = tuple(self.data_blocks)
        if not all(isinstance(block, DataBlock) for block in blocks):
            raise TypeError("data_blocks must contain DataBlock values")
        if status in {"blocked", "needs_input"} and blocks:
            raise ValueError(f"{status} adapter results cannot contain DataBlocks")
        object.__setattr__(self, "data_blocks", blocks)
        object.__setattr__(self, "reason_codes", tuple(str(code) for code in self.reason_codes))
        measurements = tuple(self.legacy_measurements)
        if not all(isinstance(item, Measurement) for item in measurements):
            raise TypeError("legacy_measurements must contain Measurement values")
        if self.template is not None and not isinstance(self.template, CanonicalExperiment):
            raise TypeError("template must be a CanonicalExperiment or None")
        if self.conversion is not None and not isinstance(self.conversion, ConversionOutcome):
            raise TypeError("conversion must be a ConversionOutcome or None")
        object.__setattr__(self, "legacy_measurements", measurements)

    @property
    def data_block(self) -> DataBlock | None:
        """Return the sole block, or ``None`` for zero/multiple blocks."""

        return self.data_blocks[0] if len(self.data_blocks) == 1 else None

    @property
    def outcome(self) -> ConversionOutcome | None:
        """Compatibility alias for the underlying canonical conversion."""

        return self.conversion

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data_blocks": [block.to_dict() for block in self.data_blocks],
            "template": None if self.template is None else self.template.to_dict(),
            "reason_codes": list(self.reason_codes),
            "legacy_measurements": [item.to_dict() for item in self.legacy_measurements],
            "conversion": None if self.conversion is None else {
                "status": self.conversion.status,
                "record": self.conversion.record.to_dict(),
                "reason_codes": list(self.conversion.reason_codes),
            },
        }


# A shorter name is useful to callers that treat these as generic N-D routes.
NDAdapterResult = DataBlockAdapterResult


def _normalize_technique(value: object) -> str:
    normalized = str(value).strip().lower()
    return _TECHNIQUE_ALIASES.get(normalized, normalized)


def adapt_ir_temperature_series(
    paths: Sequence[str | Path],
    *,
    source_artifact_id: str,
    temperature_axis_provenance: AxisProvenance | Mapping[str, Any] | None = None,
) -> DataBlockAdapterResult:
    """Build one ``(temperature, wavenumber)`` matrix block from IR frames.

    Existing one-dimensional converters still produce the compatibility
    ``Measurement`` values.  The matrix block only stores a manifest of source
    references; it never duplicates the frame arrays.  A non-conformable
    wavenumber grid is reported as ``needs_input`` instead of interpolating.
    """

    try:
        outcome = build_ir_temperature_series_template(
            paths,
            source_artifact_id=source_artifact_id,
        )
    except (TypeError, ValueError):
        raise
    if outcome.status != "ready" or outcome.template is None:
        return _from_conversion(outcome)
    return adapt_ir_temperature_template(
        outcome.template,
        source_artifact_id=source_artifact_id,
        conversion=outcome,
        temperature_axis_provenance=temperature_axis_provenance,
    )


def adapt_ir_temperature_template(
    template: CanonicalExperiment,
    *,
    source_artifact_id: str | None = None,
    conversion: ConversionOutcome | None = None,
    temperature_axis_provenance: AxisProvenance | Mapping[str, Any] | None = None,
) -> DataBlockAdapterResult:
    """Adapt an already validated IR temperature template.

    This entry point supports replay from persisted canonical JSON.  It still
    requires source file references to be resolvable so the resulting array
    manifest has auditable raw hashes.
    """

    if not isinstance(template, CanonicalExperiment):
        raise TypeError("IR temperature adapter requires a CanonicalExperiment")
    if not template.template_id.startswith("ir.temperature_series"):
        return _local_failure(
            "blocked",
            source_artifact_id or template.source_artifact_id,
            "ir_temperature_template_unsupported",
            template=template,
            conversion=conversion,
        )
    artifact_id = source_artifact_id or template.source_artifact_id
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        raise ValueError("source_artifact_id must not be empty")
    measurements = tuple(template.measurements)
    frames_value = template.payload.get("frames", ())
    if not isinstance(frames_value, Sequence) or isinstance(frames_value, (str, bytes, bytearray)):
        return _local_failure("needs_input", artifact_id, "temperature_frames_missing", template=template, conversion=conversion)
    frames = tuple(frames_value)
    if len(frames) != len(measurements) or len(frames) < 2:
        return _local_failure("needs_input", artifact_id, "temperature_frames_invalid", template=template, conversion=conversion)

    temperatures: list[float] = []
    source_members: list[dict[str, Any]] = []
    first_x: tuple[float, ...] | None = None
    x_unit: str | None = None
    for index, (frame, measurement) in enumerate(zip(frames, measurements, strict=True)):
        if not isinstance(frame, Mapping):
            return _local_failure("needs_input", artifact_id, "temperature_frame_invalid", template=template, conversion=conversion)
        try:
            temperature = float(frame["temperature_C"])
        except (KeyError, TypeError, ValueError):
            return _local_failure("needs_input", artifact_id, "temperature_axis_unresolved", template=template, conversion=conversion)
        if not math.isfinite(temperature):
            return _local_failure("needs_input", artifact_id, "temperature_axis_nonfinite", template=template, conversion=conversion)
        temperatures.append(temperature)

        if not isinstance(measurement, Measurement):
            return _local_failure("needs_input", artifact_id, "frame_measurement_invalid", template=template, conversion=conversion)
        x_values = tuple(float(value) for value in measurement.channels["x"])
        if first_x is None:
            first_x = x_values
            x_unit = str(measurement.units.get("x", "unknown")) or "unknown"
        elif x_values != first_x:
            return _local_failure("needs_input", artifact_id, "temperature_series_grid_mismatch", template=template, conversion=conversion)

        raw_path = frame.get("source_path")
        if not isinstance(raw_path, str) or not raw_path:
            locator_path = measurement.source_locator.get("source_path")
            raw_path = locator_path if isinstance(locator_path, str) else ""
        if not raw_path:
            return _local_failure("needs_input", artifact_id, "source_reference_missing", template=template, conversion=conversion)
        path = Path(raw_path)
        digest = _file_sha256(path)
        if digest is None:
            return _local_failure("needs_input", artifact_id, "source_reference_unreadable", template=template, conversion=conversion)
        source_members.append(
            {
                "measurement_id": measurement.measurement_id,
                "uri": _path_uri(path),
                "sha256": digest,
                "temperature_C": temperature,
                "order": index,
            }
        )

    if first_x is None or x_unit is None:
        return _local_failure("needs_input", artifact_id, "temperature_wavenumber_axis_missing", template=template, conversion=conversion)
    if any(not math.isfinite(value) for value in first_x):
        return _local_failure("needs_input", artifact_id, "temperature_wavenumber_axis_nonfinite", template=template, conversion=conversion)

    duplicate_temperature = len(set(temperatures)) != len(temperatures)
    temperature_axis_reason = ("temperature_axis_inferred_from_filename",)
    if duplicate_temperature:
        temperature_axis_reason += ("temperature_axis_nonunique",)
    temperature_axis = _axis(
        temperature_axis_provenance,
        name="temperature",
        default_source="inferred",
        default_method="filename_condition",
        default_quantity="temperature",
        default_unit="degC",
        default_status="inferred",
        default_reason=temperature_axis_reason,
        source_locator={"template_id": template.template_id},
    )
    wavenumber_axis = AxisProvenance.create(
        name="wavenumber",
        source="observed",
        method="source_table_column",
        quantity="wavenumber",
        unit=x_unit,
        source_locator={"template_id": template.template_id},
    )
    array_manifest = {
        "kind": "matrix",
        "layout": ["temperature", "wavenumber"],
        "shape": [len(temperatures), len(first_x)],
        "members": source_members,
    }
    block = DataBlock.create(
        kind="matrix",
        shape=(len(temperatures), len(first_x)),
        dims=("temperature", "wavenumber"),
        coords={"temperature": tuple(temperatures), "wavenumber": first_x},
        coord_units={"temperature": "degC", "wavenumber": x_unit},
        array_ref={
            "uri": f"artifact://{artifact_id}/nd/ir-temperature-series",
            "sha256": canonical_json_hash(array_manifest),
            "role": "referenced_temperature_matrix",
            "members": source_members,
            "source_refs": source_members,
        },
        axis_provenance={"temperature": temperature_axis, "wavenumber": wavenumber_axis},
        source_artifact_id=artifact_id,
        metadata={
            "technique": "ir",
            "measurement_family": "spectrum_1d",
            "representation": "temperature_series_matrix",
            "source_template_id": template.template_id,
            "raw_arrays_included": False,
            "temperature_axis_source": temperature_axis.method,
            "temperature_axis_status": temperature_axis.status,
            "temperature_axis_unique": not duplicate_temperature,
            "frame_count": len(temperatures),
            "frame_references": source_members,
            "channel_mapping": {
                "coordinate": "wavenumber",
                "value": "intensity",
                "value_unit": str(measurements[0].units.get("intensity", "unknown")),
            },
        },
        quality_flags=tuple(
            flag
            for flag, enabled in (
                ("temperature_axis_inferred", temperature_axis.source in {"inferred", "synthetic"}),
                ("temperature_axis_nonunique", duplicate_temperature),
            )
            if enabled
        ),
    )
    return DataBlockAdapterResult(
        status="ready",
        data_blocks=(block,),
        template=template,
        reason_codes=tuple(template.conversion_record.reason_codes),
        legacy_measurements=measurements,
        conversion=conversion,
    )


def adapt_detector_image(
    path: str | Path,
    *,
    technique: str,
    source_artifact_id: str,
    mask_path: str | Path | None = None,
    mask_ref: Mapping[str, Any] | None = None,
    calibration_ref: CalibrationRef | Mapping[str, Any] | None = None,
) -> DataBlockAdapterResult:
    """Adapt a SAXS/WAXS detector image to a reference-only matrix block."""

    if mask_path is not None and mask_ref is not None:
        raise ValueError("mask_path and mask_ref are mutually exclusive")
    outcome = convert_detector_image(
        path,
        technique=technique,
        source_artifact_id=source_artifact_id,
    )
    if outcome.status != "ready" or outcome.template is None:
        return _from_conversion(outcome)
    template = outcome.template
    payload = template.payload
    shape_value = payload.get("shape")
    if not isinstance(shape_value, Sequence) or len(shape_value) != 2:
        return _local_failure("needs_input", source_artifact_id, "detector_image_shape_invalid", template=template, conversion=outcome)
    try:
        rows, columns = (int(shape_value[0]), int(shape_value[1]))
    except (TypeError, ValueError):
        return _local_failure("needs_input", source_artifact_id, "detector_image_shape_invalid", template=template, conversion=outcome)
    if rows < 2 or columns < 2:
        return _local_failure("needs_input", source_artifact_id, "detector_image_shape_invalid", template=template, conversion=outcome)
    source_payload = payload.get("source", {})
    source_digest = source_payload.get("sha256") if isinstance(source_payload, Mapping) else None
    if not isinstance(source_digest, str) or not _is_sha256(source_digest):
        return _local_failure("blocked", source_artifact_id, "detector_source_hash_missing", template=template, conversion=outcome)

    normalized_calibration: CalibrationRef | None = None
    if calibration_ref is not None:
        normalized_calibration = (
            calibration_ref
            if isinstance(calibration_ref, CalibrationRef)
            else CalibrationRef.from_dict(calibration_ref)
        )

    resolved_mask: Mapping[str, Any] | None = None
    mask_shape: tuple[int, int] | None = None
    if mask_path is not None:
        mask_source = Path(mask_path)
        mask_digest = _file_sha256(mask_source)
        if mask_digest is None:
            return _local_failure("needs_input", source_artifact_id, "detector_mask_unreadable", template=template, conversion=outcome)
        mask_shape = _array_shape(mask_source)
        if mask_shape != (rows, columns):
            return _local_failure("needs_input", source_artifact_id, "detector_mask_shape_mismatch", template=template, conversion=outcome)
        resolved_mask = {
            "uri": _path_uri(mask_source),
            "sha256": mask_digest,
            "role": "detector_mask",
            "shape": [rows, columns],
        }
    elif mask_ref is not None:
        resolved_mask = dict(mask_ref)
        declared_shape = resolved_mask.get("shape")
        if declared_shape is not None:
            try:
                mask_shape = (int(declared_shape[0]), int(declared_shape[1]))
            except (TypeError, ValueError, IndexError):
                return _local_failure("needs_input", source_artifact_id, "detector_mask_shape_invalid", template=template, conversion=outcome)
            if mask_shape != (rows, columns):
                return _local_failure("needs_input", source_artifact_id, "detector_mask_shape_mismatch", template=template, conversion=outcome)

    normalized_technique = _normalize_technique(technique)
    geometry = payload.get("geometry", {})
    if not isinstance(geometry, Mapping):
        geometry = {}
    geometry_metadata_status = str(geometry.get("metadata_status", "missing")).strip().lower()
    if normalized_calibration is not None:
        calibration_status = normalized_calibration.status
    elif geometry_metadata_status in {"complete", "partial"}:
        calibration_status = "header_unreviewed"
    else:
        calibration_status = "missing"
    pixel_axes = {
        "detector_y": AxisProvenance.create(
            name="detector_y",
            source="synthetic",
            method="array_index",
            quantity="pixel_index",
            unit="pixel",
            status="assumed",
            reason_codes=("pixel_index_not_physical_calibration",),
            source_locator={"template_id": template.template_id},
        ),
        "detector_x": AxisProvenance.create(
            name="detector_x",
            source="synthetic",
            method="array_index",
            quantity="pixel_index",
            unit="pixel",
            status="assumed",
            reason_codes=("pixel_index_not_physical_calibration",),
            source_locator={"template_id": template.template_id},
        ),
    }
    block = DataBlock.create(
        kind="matrix",
        shape=(rows, columns),
        dims=("detector_y", "detector_x"),
        coords={"detector_y": tuple(range(rows)), "detector_x": tuple(range(columns))},
        coord_units={"detector_y": "pixel", "detector_x": "pixel"},
        array_ref={
            "uri": f"artifact://{source_artifact_id}/nd/{normalized_technique}-detector-pixels",
            "sha256": source_digest,
            "role": "detector_pixels",
            "shape": [rows, columns],
            "hash_scope": "bytes",
            "pixel_ref": {
                "uri": f"artifact://{source_artifact_id}/nd/{normalized_technique}-detector-pixels",
                "sha256": source_digest,
            },
        },
        mask_ref=resolved_mask,
        axis_provenance=pixel_axes,
        source_artifact_id=source_artifact_id,
        metadata={
            "technique": normalized_technique,
            "measurement_family": "detector_image",
            "representation": "detector_pixel_matrix",
            "source_template_id": template.template_id,
            "raw_pixels_included": False,
            "mask_present": resolved_mask is not None,
            "mask_reference": resolved_mask,
            "mask_shape": None if mask_shape is None else list(mask_shape),
            "geometry": dict(geometry),
            "calibration_status": calibration_status,
            "calibration_reviewed": bool(
                normalized_calibration is not None
                and normalized_calibration.status in {"reviewed", "applied_unreviewed"}
            ),
            "calibrations": ()
            if normalized_calibration is None
            else (normalized_calibration.to_dict(),),
            "pixel_reference": {
                "uri": f"artifact://{source_artifact_id}/nd/{normalized_technique}-detector-pixels",
                "sha256": source_digest,
            },
        },
        non_physical_dims=("detector_y", "detector_x"),
        quality_flags=tuple(
            flag
            for flag, enabled in (
                ("detector_geometry_unreviewed", normalized_calibration is None),
                ("detector_geometry_header_only", normalized_calibration is None and geometry_metadata_status in {"complete", "partial"}),
            )
            if enabled
        ),
    )
    return DataBlockAdapterResult(
        status="ready",
        data_blocks=(block,),
        template=template,
        reason_codes=tuple(template.conversion_record.reason_codes),
        conversion=outcome,
    )


def adapt_nmr_fid(
    path: str | Path,
    *,
    source_artifact_id: str,
    dtype: str | np.dtype[Any] = ">i4",
    shape: Sequence[int] | None = None,
    dims: Sequence[str] | None = None,
    coords: Mapping[str, Sequence[Any]] | None = None,
    coord_units: Mapping[str, str] | None = None,
    axis_provenance: Mapping[str, AxisProvenance | Mapping[str, Any]] | None = None,
    nucleus: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> DataBlockAdapterResult:
    """Represent a raw NMR FID as a complex reference block.

    The default Bruker-compatible layout is interleaved big-endian int32
    ``real, imaginary, real, imaginary, ...``.  The adapter records the layout
    and byte hash but never runs FFT or phase correction, so the imaginary
    channel remains available to downstream deterministic capabilities.
    """

    source = Path(path)
    if not source.is_file():
        # A missing raw acquisition is an actionable input gap, not evidence
        # that the NMR capability itself is unavailable.  Preserve that
        # distinction for AI capability discovery.
        status = "needs_input" if not source.exists() else "blocked"
        return _local_failure(status, source_artifact_id, "nmr_fid_missing" if status == "needs_input" else "nmr_fid_unreadable")
    digest = _file_sha256(source)
    if digest is None:
        return _local_failure("blocked", source_artifact_id, "nmr_fid_unreadable")
    is_ser = source.name.casefold() == "ser" or source.suffix.casefold() == ".ser"
    if is_ser and shape is None:
        # Bruker ``ser`` stores an indirect acquisition dimension.  Byte
        # length alone cannot recover its shape, so never collapse it to a
        # synthetic one-dimensional FID.
        return _local_failure("needs_input", source_artifact_id, "nmr_ser_shape_required")
    try:
        np_dtype = np.dtype(dtype)
    except (TypeError, ValueError) as exc:
        raise ValueError("dtype must be a valid NumPy dtype") from exc
    if np_dtype.itemsize <= 0:
        raise ValueError("dtype must have a positive itemsize")
    byte_count = source.stat().st_size
    if byte_count == 0 or byte_count % np_dtype.itemsize:
        return _local_failure("needs_input", source_artifact_id, "nmr_fid_byte_alignment_invalid")
    scalar_count = byte_count // np_dtype.itemsize
    direct_complex = np_dtype.kind == "c"
    if direct_complex:
        complex_count = scalar_count
        interleaved = False
    else:
        if scalar_count % 2:
            return _local_failure("needs_input", source_artifact_id, "nmr_fid_interleaving_odd")
        complex_count = scalar_count // 2
        interleaved = True
    if complex_count < 1:
        return _local_failure("needs_input", source_artifact_id, "nmr_fid_empty")

    normalized_shape = _normalize_shape(shape, complex_count)
    if is_ser and len(normalized_shape) < 2:
        return _local_failure(
            "needs_input",
            source_artifact_id,
            "nmr_ser_shape_rank_invalid",
        )
    normalized_dims = _normalize_dims(dims, len(normalized_shape))
    if int(np.prod(normalized_shape, dtype=np.int64)) != complex_count:
        return _local_failure("needs_input", source_artifact_id, "nmr_fid_shape_mismatch")
    supplied_coords = {} if coords is None else dict(coords)
    supplied_units = {} if coord_units is None else dict(coord_units)
    supplied_axes = {} if axis_provenance is None else dict(axis_provenance)
    normalized_coords: dict[str, tuple[Any, ...]] = {}
    normalized_units: dict[str, str] = {}
    normalized_axes: dict[str, AxisProvenance] = {}
    non_physical: list[str] = []
    for index, dim in enumerate(normalized_dims):
        expected_length = normalized_shape[index]
        values = supplied_coords.get(dim)
        if values is None:
            values = tuple(range(expected_length))
            non_physical.append(dim)
        elif isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
            return _local_failure("needs_input", source_artifact_id, f"nmr_fid_coordinate_invalid:{dim}")
        elif len(values) != expected_length:
            return _local_failure("needs_input", source_artifact_id, f"nmr_fid_coordinate_length:{dim}")
        normalized_coords[dim] = tuple(values)
        unit = supplied_units.get(dim)
        if unit is None:
            unit = "index" if dim in non_physical else "unknown"
        if not isinstance(unit, str) or not unit:
            return _local_failure("needs_input", source_artifact_id, f"nmr_fid_coordinate_unit_missing:{dim}")
        normalized_units[dim] = unit
        provided_axis = supplied_axes.get(dim)
        if provided_axis is None:
            normalized_axes[dim] = AxisProvenance.create(
                name=dim,
                source="synthetic",
                method="sample_index",
                quantity=dim,
                unit=unit,
                status="assumed",
                reason_codes=("nmr_fid_axis_not_declared",),
                source_locator={"source_path": str(source.resolve())},
            )
            if dim not in non_physical:
                non_physical.append(dim)
        else:
            normalized_axes[dim] = (
                provided_axis
                if isinstance(provided_axis, AxisProvenance)
                else AxisProvenance.from_dict(provided_axis)
            )
            if normalized_axes[dim].name != dim:
                return _local_failure("needs_input", source_artifact_id, f"nmr_fid_axis_name_mismatch:{dim}")
            if normalized_axes[dim].source in {"synthetic", "inferred"} and dim not in non_physical:
                non_physical.append(dim)

    block_metadata: dict[str, Any] = {
        "technique": "nmr",
        "measurement_family": "fid",
        "representation": "complex_fid",
        "source_format": (
            "bruker_fid"
            if source.name.casefold() == "fid"
            else "bruker_ser"
            if is_ser
            else source.suffix.casefold().lstrip(".")
        ),
        "raw_values_included": False,
        "imaginary_channel_preserved": True,
        "components": ["real", "imaginary"],
        "complex_components": ["real", "imaginary"],
        "channel_layout": "interleaved" if not direct_complex else "native_complex",
        "imaginary_channel": {"preserved": True, "role": "quadrature"},
        "storage": {
            "dtype": np_dtype.str,
            "interleaved": interleaved,
            "component_count": 2,
            "complex_dtype": "native" if direct_complex else "interleaved",
            "component_offsets": {"real": 0, "imaginary": 0 if direct_complex else int(np_dtype.itemsize)},
            "component_stride_bytes": int(np_dtype.itemsize if direct_complex else 2 * np_dtype.itemsize),
        },
        "source_path": str(source.resolve()),
        "point_count": complex_count,
    }
    if nucleus is not None:
        if not isinstance(nucleus, str) or not nucleus.strip():
            raise ValueError("nucleus must be a nonempty string when supplied")
        block_metadata["nucleus"] = nucleus.strip()
    if metadata is not None:
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        metadata_values = dict(metadata)
        reserved = sorted(
            key for key in metadata_values if key in _NMR_RESERVED_METADATA_KEYS
        )
        if reserved:
            raise ValueError(
                "NMR metadata contains reserved fields and cannot override canonical "
                f"values: {', '.join(reserved)}"
            )
        block_metadata.update(metadata_values)
    block = DataBlock.create(
        kind="complex",
        shape=normalized_shape,
        dims=normalized_dims,
        coords=normalized_coords,
        coord_units=normalized_units,
        array_ref={
            "uri": f"artifact://{source_artifact_id}/nd/nmr-fid",
            "sha256": digest,
            "role": "complex_fid",
            "dtype": np_dtype.str,
            "interleaved": interleaved,
        },
        axis_provenance=normalized_axes,
        source_artifact_id=source_artifact_id,
        metadata=block_metadata,
        non_physical_dims=tuple(non_physical),
    )
    record = ConversionRecord.create(
        conversion_id="nmr.fid.v1",
        source_artifact_id=source_artifact_id,
        observed_columns=("real", "imaginary"),
        extracted_segments=(
            {
                "role": "complex_fid",
                "source_path": str(source.resolve()),
                "sha256": digest,
                "dtype": np_dtype.str,
                "interleaved": interleaved,
                "shape": list(normalized_shape),
            },
        ),
    )
    template = CanonicalExperiment.create(
        template_id="nmr.fid.v1",
        source_artifact_id=source_artifact_id,
        payload={
            "technique": "nmr",
            "representation": "complex_fid",
            "shape": list(normalized_shape),
            "dims": list(normalized_dims),
            "source": {"uri": _path_uri(source), "sha256": digest},
            "imaginary_channel_preserved": True,
        },
        conversion_record=record,
    )
    return DataBlockAdapterResult(
        status="ready",
        data_blocks=(block,),
        template=template,
        reason_codes=record.reason_codes,
        conversion=ConversionOutcome(status="ready", record=record, template=template),
    )


def adapt_conversion_outcome(
    outcome: ConversionOutcome,
    *,
    technique: str | None = None,
) -> DataBlockAdapterResult:
    """Adapt ordinary one-dimensional canonical measurements to series blocks."""

    if not isinstance(outcome, ConversionOutcome):
        raise TypeError("outcome must be a ConversionOutcome")
    if outcome.status != "ready" or outcome.template is None:
        return _from_conversion(outcome)
    template = outcome.template
    blocks: list[DataBlock] = []
    normalized_technique = str(technique or template.payload.get("technique", "")).strip().lower()
    for measurement in template.measurements:
        x_values = tuple(float(value) for value in measurement.channels["x"])
        x_unit = str(measurement.units.get("x", "unknown")) or "unknown"
        locator_path = measurement.source_locator.get("source_path")
        source_path = Path(locator_path) if isinstance(locator_path, str) and locator_path else None
        digest = _file_sha256(source_path) if source_path is not None else None
        if digest is None:
            digest = canonical_json_hash(measurement.to_dict())
            uri = f"artifact://{template.source_artifact_id}/measurement/{measurement.measurement_id}"
        else:
            uri = _path_uri(source_path) + f"#measurement={measurement.measurement_id}"
        axis_source = "observed"
        axis_status = "verified"
        if measurement.mapping is not None and measurement.mapping.source != "observed":
            axis_source = "user_confirmed"
            axis_status = "declared"
        axis = AxisProvenance.create(
            name="x",
            source=axis_source,
            method="source_table_column",
            quantity=measurement.mapping.x_kind if measurement.mapping is not None else "coordinate",
            unit=x_unit,
            status=axis_status,
            source_locator=dict(measurement.source_locator),
        )
        block = DataBlock.create(
            kind="series",
            shape=(len(x_values),),
            dims=("x",),
            coords={"x": x_values},
            coord_units={"x": x_unit},
            array_ref={"uri": uri, "sha256": digest, "role": "one_dimensional_measurement"},
            axis_provenance={"x": axis},
            source_artifact_id=template.source_artifact_id,
            metadata={
                "technique": normalized_technique,
                "measurement_family": measurement.family,
                "representation": "series",
                "measurement_id": measurement.measurement_id,
                "raw_values_included": False,
            },
            quality_flags=measurement.warnings,
        )
        blocks.append(block)
    return DataBlockAdapterResult(
        status="ready",
        data_blocks=tuple(blocks),
        template=template,
        reason_codes=tuple(template.conversion_record.reason_codes),
        legacy_measurements=template.measurements,
        conversion=outcome,
    )


# Explicitly named aliases make the adapter boundary easy to discover from
# API/tool schemas while retaining the concise ``adapt_*`` names above.
convert_ir_temperature_series_to_data_block = adapt_ir_temperature_series
convert_detector_image_to_data_block = adapt_detector_image
convert_nmr_fid_to_data_block = adapt_nmr_fid


def _from_conversion(outcome: ConversionOutcome) -> DataBlockAdapterResult:
    return DataBlockAdapterResult(
        status=outcome.status,
        data_blocks=(),
        template=outcome.template,
        reason_codes=outcome.reason_codes,
        legacy_measurements=() if outcome.template is None else outcome.template.measurements,
        conversion=outcome,
    )


def _local_failure(
    status: str,
    source_artifact_id: str,
    reason: str,
    *,
    template: CanonicalExperiment | None = None,
    conversion: ConversionOutcome | None = None,
) -> DataBlockAdapterResult:
    record = ConversionRecord.create(
        conversion_id="nd-adapter.v1",
        source_artifact_id=str(source_artifact_id or "unknown"),
        reason_codes=(str(reason),),
    )
    # A local adapter validation has its own reason record.  Do not reuse the
    # upstream conversion object here: its reason tuple would no longer match
    # the new status/reason and ``ConversionOutcome`` deliberately rejects
    # that mismatch.
    outcome = ConversionOutcome(
        status=status,
        record=record,
        template=None,
        reason_codes=(str(reason),),
    )
    return DataBlockAdapterResult(
        status=status,
        template=template,
        reason_codes=(str(reason),),
        legacy_measurements=() if template is None else template.measurements,
        conversion=outcome,
    )


def _axis(
    value: AxisProvenance | Mapping[str, Any] | None,
    *,
    name: str,
    default_source: str,
    default_method: str,
    default_quantity: str,
    default_unit: str,
    default_status: str,
    default_reason: Sequence[str],
    source_locator: Mapping[str, Any],
) -> AxisProvenance:
    if value is None:
        return AxisProvenance.create(
            name=name,
            source=default_source,
            method=default_method,
            quantity=default_quantity,
            unit=default_unit,
            status=default_status,
            reason_codes=default_reason,
            source_locator=source_locator,
        )
    axis = value if isinstance(value, AxisProvenance) else AxisProvenance.from_dict(value)
    if axis.name != name:
        raise ValueError(f"{name} axis provenance name must match its dimension")
    return axis


def _normalize_shape(shape: Sequence[int] | None, point_count: int) -> tuple[int, ...]:
    if shape is None:
        return (point_count,)
    if isinstance(shape, (str, bytes, bytearray)) or not isinstance(shape, Sequence):
        raise TypeError("shape must be a sequence of positive integers")
    values = tuple(shape)
    if not values or any(type(value) is not int or value <= 0 for value in values):
        raise ValueError("shape must contain positive integers")
    return values


def _normalize_dims(dims: Sequence[str] | None, rank: int) -> tuple[str, ...]:
    if dims is None:
        # Use NMR-native acquisition names for the first two dimensions so a
        # supplied 2-D FID can be discovered by the corresponding descriptor
        # without guessing a physical coordinate.  Additional dimensions stay
        # explicit, neutral acquisition dimensions.
        defaults = ("time", "indirect_time", "acquisition_3", "acquisition_4")
        return tuple(
            defaults[index] if index < len(defaults) else f"acquisition_{index + 1}"
            for index in range(rank)
        )
    if isinstance(dims, (str, bytes, bytearray)) or not isinstance(dims, Sequence):
        raise TypeError("dims must be a sequence of strings")
    values = tuple(dims)
    if len(values) != rank or any(not isinstance(value, str) or not value for value in values):
        raise ValueError("dims must contain one nonempty name per shape dimension")
    if len(set(values)) != len(values):
        raise ValueError("dims must be unique")
    return values


def _file_sha256(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _path_uri(path: Path) -> str:
    try:
        return path.resolve().as_uri()
    except (OSError, ValueError):
        return f"file://{path}"


def _is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _array_shape(path: Path) -> tuple[int, int] | None:
    """Read only shape metadata for a mask; never serialize its values."""

    suffix = path.suffix.casefold()
    try:
        if suffix == ".npy":
            array = np.load(path, mmap_mode="r", allow_pickle=False)
            return tuple(int(value) for value in array.shape) if array.ndim == 2 else None
        if suffix == ".npz":
            with np.load(path, mmap_mode="r", allow_pickle=False) as archive:
                if len(archive.files) != 1:
                    return None
                array = archive[archive.files[0]]
                return tuple(int(value) for value in array.shape) if array.ndim == 2 else None
        if suffix in {".tif", ".tiff", ".edf", ".cbf", ".h5", ".hdf5", ".nxs"}:
            from polynexus.core.saxs_engine.io import read_image

            array, _ = read_image(str(path))
            values = np.asarray(array)
            return tuple(int(value) for value in values.shape) if values.ndim == 2 else None
    except Exception:
        return None
    return None


__all__ = [
    "DataBlockAdapterResult",
    "NDAdapterResult",
    "adapt_ir_temperature_series",
    "adapt_ir_temperature_template",
    "adapt_detector_image",
    "adapt_nmr_fid",
    "adapt_conversion_outcome",
    "convert_ir_temperature_series_to_data_block",
    "convert_detector_image_to_data_block",
    "convert_nmr_fid_to_data_block",
]
