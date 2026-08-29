from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from polynexus.core.canonical_experiments import default_converter_registry


def _image(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.arange(12, dtype=np.uint16).reshape(3, 4)).save(path)
    return path


def test_saxs_detector_image_template_records_shape_axes_and_geometry(tmp_path: Path) -> None:
    source = _image(tmp_path / "raw" / "SAXS" / "frame.tif")

    outcome = default_converter_registry().convert_path(
        source,
        technique="saxs",
        source_artifact_id="raw-saxs-frame",
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "saxs.detector_image.v1"
    assert outcome.template.measurements == ()
    assert outcome.template.payload["axis_names"] == ("detector_y", "detector_x")
    assert outcome.template.payload["axis_units"] == ("pixel", "pixel")
    assert outcome.template.payload["shape"] == (3, 4)
    assert outcome.template.payload["geometry"]["metadata_status"] == "missing"
    assert "pixels" not in outcome.template.payload


def test_waxs_detector_image_template_uses_source_hash_and_no_default_geometry(tmp_path: Path) -> None:
    source = _image(tmp_path / "raw" / "WAXS" / "frame.tiff")

    outcome = default_converter_registry().convert_path(
        source,
        technique="waxs",
        source_artifact_id="raw-waxs-frame",
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "waxs.detector_image.v1"
    assert outcome.template.payload["source"]["sha256"] == outcome.record.extracted_segments[0]["sha256"]
    assert outcome.template.payload["geometry"]["calibration_reviewed"] is False
