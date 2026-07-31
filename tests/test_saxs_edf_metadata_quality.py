from __future__ import annotations

import json
import struct

import numpy as np


def _header() -> dict[str, str]:
    return {
        "DetectorModel": "Dectris EIGER2 Si 500K, S/N E-01-0419",
        "Center_1": "255.5735",
        "Center_2": "549.7194",
        "PSize_1": "7.5e-05",
        "PSize_2": "7.5e-05",
        "SampleDistance": "0.450001",
        "Wavelength": "1.541891e-10",
        "ExposureTime": "300",
        "ThresholdSetting": "4023.88989258",
        "CountCutoff": "1530250",
        "Saturation": "0",
        "FlatField": "Corrected",
        "Dummy": "-1.5",
        "DDummy": "0.6",
        "BackgroundCorrectionConstant": "0.0024174",
    }


def _write_edf(path, image: np.ndarray, header: dict[str, str]) -> None:
    fields = {
        "EDF_DataBlockID": "0.Image.Psd",
        "EDF_BinarySize": str(int(image.size * 4)),
        "EDF_HeaderSize": "2560",
        "ByteOrder": "LowByteFirst",
        "DataType": "FloatValue",
        "Dim_1": str(image.shape[1]),
        "Dim_2": str(image.shape[0]),
        **header,
    }
    text = "{\n" + "\n".join(f"{key} = {value} ;" for key, value in fields.items()) + "\n"
    encoded = text.encode("latin-1")
    encoded += b" " * (2558 - len(encoded))
    encoded += b"}\n"
    path.write_bytes(encoded + struct.pack(f"<{image.size}f", *image.ravel()))


def _config():
    from polynexus.core.saxs_engine.config import SAXSConfig

    return SAXSConfig(
        is_isotropic=True,
        n_pt=4,
        q_min=0.01,
        q_max=1.0,
        smooth_method="none",
    )


def test_edf_header_metadata_is_exposed_without_promoting_calibration() -> None:
    from polynexus.core.saxs_engine.io import extract_geometry_from_header
    from polynexus.core.saxs_engine.preprocess import preprocess_pipeline

    header = _header()
    cfg = extract_geometry_from_header(header, _config())
    image = np.asarray(
        [[-0.0024174, -2.0], [1.0, 9.0]],
        dtype=np.float64,
    )

    report = preprocess_pipeline(image, cfg, detector_header=header)[
        "detector_quality_report"
    ]

    metadata = report["detector_metadata"]
    assert metadata["metadata_status"] == "complete"
    assert metadata["metadata_source"] == "edf_header"
    assert metadata["detector_model"] == header["DetectorModel"]
    assert metadata["detector_serial_number"] == "E-01-0419"
    assert metadata["count_cutoff"] == 1530250.0
    assert metadata["threshold_setting"] == 4023.88989258
    assert metadata["flat_field_status"] == "Corrected"
    assert metadata["dummy_value"] == -1.5
    assert metadata["dummy_tolerance"] == 0.6
    assert metadata["background_correction_constant"] == 0.0024174
    assert report["geometry_provenance"]["validity"] == "not_assessed"
    assert report["mask_provenance"]["validity"] == "not_assessed"
    json.dumps(report, allow_nan=False)


def test_processed_negative_pixels_are_classified_without_hiding_raw_count() -> None:
    from polynexus.core.saxs_engine.saxs_quality_contracts import (
        build_detector_quality_report,
    )

    image = np.asarray(
        [[-0.0024174, -0.0024174, -2.0], [-16.0, 1.0, 2.0]],
        dtype=np.float64,
    )
    mask = np.asarray(
        [[False, False, True], [False, False, False]],
        dtype=bool,
    )

    report = build_detector_quality_report(
        image,
        mask=mask,
        source_kind="raw_detector",
        background_floor_value=-0.0024174,
    )

    assert report.nonpositive_pixel_count == 4
    assert report.background_floor_pixel_count == 2
    assert report.masked_sentinel_pixel_count == 1
    assert report.unexpected_negative_pixel_count == 1


def test_zero_saturation_field_is_unresolved_but_positive_threshold_still_works() -> None:
    from polynexus.core.saxs_engine.preprocess import preprocess_pipeline

    image = np.asarray([[0.0, 9.0], [1.0, 2.0]], dtype=np.float64)
    zero_status_header = {
        "Center_1": "0.5",
        "Center_2": "0.5",
        "Saturation": "0",
        "ThresholdSetting": "4023.88989258",
    }
    unresolved = preprocess_pipeline(
        image,
        _config(),
        detector_header=zero_status_header,
    )["detector_quality_report"]
    assert unresolved["saturation_detection_available"] is False
    assert unresolved["saturated_pixel_count"] == 0
    assert "detector_saturation_unknown" in unresolved["reason_codes"]

    explicit = preprocess_pipeline(
        image,
        _config(),
        detector_header={**zero_status_header, "Saturation": "9"},
    )["detector_quality_report"]
    assert explicit["saturation_detection_available"] is True
    assert explicit["saturated_pixel_count"] == 1


def test_four_edf_frames_keep_independent_metadata_and_quality_counts(tmp_path, monkeypatch) -> None:
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.config import SAXSConfig
    from polynexus.core.saxs_engine.io import extract_geometry_from_header, read_image

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    header = _header()
    images = [
        np.asarray([[-0.0024174, 1.0], [2.0, 3.0]], dtype=np.float32),
        np.asarray([[-0.0024174, -0.0024174], [2.0, 3.0]], dtype=np.float32),
        np.asarray([[-2.0, 1.0], [2.0, 3.0]], dtype=np.float32),
        np.asarray([[-16.0, -0.0024174], [2.0, 3.0]], dtype=np.float32),
    ]
    paths = []
    for index, image in enumerate(images):
        path = tmp_path / f"610-{index:03d}-S_0_00000.edf"
        _write_edf(path, image, header)
        paths.append(path)

    reports = []
    for path in paths:
        image, parsed_header = read_image(str(path))
        cfg = extract_geometry_from_header(parsed_header, SAXSConfig())
        payload = preprocess_module.preprocess_pipeline(
            image,
            cfg,
            detector_header=parsed_header,
        )
        reports.append(payload["detector_quality_report"])

    assert len(reports) == 4
    assert [item["detector_metadata"]["detector_serial_number"] for item in reports] == [
        "E-01-0419"
    ] * 4
    assert [item["background_floor_pixel_count"] for item in reports] == [1, 2, 0, 1]
    assert [item["unexpected_negative_pixel_count"] for item in reports] == [0, 0, 0, 1]
