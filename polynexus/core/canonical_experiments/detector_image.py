"""Canonical envelopes for calibrated-or-reviewable 2D detector images."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from polynexus.core.saxs_engine.io import (
    SUPPORTED_2D_EXTENSIONS,
    normalize_edf_detector_metadata,
    read_image,
)

from .models import CanonicalExperiment, ConversionOutcome, ConversionRecord


_CONVERTER_ID = "detector-image.v1"
_SUPPORTED_TECHNIQUES = frozenset({"saxs", "waxs"})


def convert_detector_image(
    path: str | Path,
    *,
    technique: str,
    source_artifact_id: str,
) -> ConversionOutcome:
    """Describe one 2D detector image without serializing its pixel matrix.

    Geometry values are only copied when present in the source header; this
    conversion never supplies defaults or considers a calibration reviewed.
    """

    source = Path(path)
    normalized_technique = str(technique).strip().lower()
    if normalized_technique not in _SUPPORTED_TECHNIQUES:
        return _outcome("blocked", source_artifact_id, "detector_image_technique_unsupported")
    if not source.is_file() or source.suffix.casefold() not in SUPPORTED_2D_EXTENSIONS:
        return _outcome("blocked", source_artifact_id, "detector_image_format_unsupported")
    try:
        image, header = read_image(str(source))
    except Exception:
        return _outcome("blocked", source_artifact_id, "detector_image_unreadable")
    array = np.asarray(image)
    if array.ndim != 2 or min(array.shape, default=0) < 2:
        return _outcome("needs_input", source_artifact_id, "detector_image_shape_invalid")
    try:
        source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    except OSError:
        return _outcome("blocked", source_artifact_id, "canonical_source_unreadable")

    geometry = _geometry_payload(header, suffix=source.suffix.casefold())
    finite_fraction = float(np.isfinite(array).mean())
    record = ConversionRecord.create(
        conversion_id=_CONVERTER_ID,
        source_artifact_id=source_artifact_id,
        observed_columns=("detector_y", "detector_x"),
        extracted_segments=(
            {
                "role": "detector_image",
                "source_path": source.name,
                "sha256": source_sha256,
                "shape": [int(array.shape[0]), int(array.shape[1])],
            },
        ),
    )
    template = CanonicalExperiment.create(
        template_id=f"{normalized_technique}.detector_image.v1",
        source_artifact_id=source_artifact_id,
        payload={
            "technique": normalized_technique.upper(),
            "source": {
                "filename": source.name,
                "format": source.suffix.casefold().lstrip("."),
                "sha256": source_sha256,
            },
            "shape": [int(array.shape[0]), int(array.shape[1])],
            "axis_names": ["detector_y", "detector_x"],
            "axis_units": ["pixel", "pixel"],
            "image_metadata": {
                "dtype": str(array.dtype),
                "finite_fraction": finite_fraction,
                "raw_pixels_included": False,
            },
            "geometry": geometry,
        },
        conversion_record=record,
    )
    return ConversionOutcome(status="ready", record=record, template=template)


def _geometry_payload(header: Mapping[str, Any] | None, *, suffix: str) -> dict[str, Any]:
    geometry = dict(normalize_edf_detector_metadata(header))
    if suffix != ".edf":
        geometry["metadata_source"] = "image_header" if header else "none"
        if not header or not any(
            geometry.get(key) is not None
            for key in ("wavelength_m", "pixel_size_m", "sample_distance_m", "beam_center_x_px", "beam_center_y_px")
        ):
            geometry["metadata_status"] = "missing"
    geometry["calibration_reviewed"] = False
    geometry["calibration_review_scope"] = "saxs.detector_calibration"
    return {key: _public_scalar(value) for key, value in geometry.items()}


def _public_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return str(value)


def _outcome(status: str, source_artifact_id: str, reason: str) -> ConversionOutcome:
    record = ConversionRecord.create(
        conversion_id=_CONVERTER_ID,
        source_artifact_id=source_artifact_id,
        reason_codes=(reason,),
    )
    return ConversionOutcome(status=status, record=record, reason_codes=(reason,))


__all__ = ["convert_detector_image"]
