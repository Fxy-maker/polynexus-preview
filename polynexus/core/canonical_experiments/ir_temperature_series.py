"""Canonical conversion for IR temperature/time spectral sequences."""

from __future__ import annotations

from pathlib import Path
import re
from dataclasses import replace
from typing import Sequence

from .models import CanonicalExperiment, ConversionOutcome, ConversionRecord
from .one_dimensional import convert_one_dimensional_table


_TEMPERATURE_PATTERNS = (
    re.compile(r"(?P<temperature>\d+(?:\.\d+)?)\s*[-_ ]*for\s*(?P<time>\d+(?:\.\d+)?)\s*min", re.I),
    re.compile(r"-(?:sw|jw)-(?P<temperature>\d+(?:\.\d+)?)", re.I),
    re.compile(r"(?:^|[-_ ])t?(?P<temperature>\d{2,3}(?:\.\d+)?)(?:c|degc)?(?:$|[-_ ])", re.I),
)


def build_ir_temperature_series_template(
    paths: Sequence[str | Path],
    *,
    source_artifact_id: str,
) -> ConversionOutcome:
    """Convert multiple 1-D spectra into one condition-series template.

    The individual spectra retain the existing ``Measurement`` contract.  The
    sequence metadata records the condition axis and ordering source without
    embedding duplicated raw data in the canonical JSON.
    """

    if len(paths) < 2:
        raise ValueError("IR temperature series requires at least two frames")
    if not str(source_artifact_id).strip():
        raise ValueError("source_artifact_id must not be empty")

    entries: list[tuple[Path, float, float | None, ConversionOutcome]] = []
    for raw_path in paths:
        path = Path(raw_path)
        temperature, time_min = _parse_condition(path)
        if temperature is None:
            return _blocked(source_artifact_id, "temperature_axis_unresolved")
        outcome = convert_one_dimensional_table(
            path,
            technique="ir",
            source_artifact_id=f"{source_artifact_id}:{path.name}",
        )
        if outcome.status != "ready" or outcome.template is None:
            return _blocked(
                source_artifact_id,
                *(outcome.reason_codes or ("frame_conversion_failed",)),
                status=outcome.status,
            )
        entries.append((path, temperature, time_min, outcome))

    entries.sort(key=lambda item: (item[1], item[0].name.casefold()))
    measurements = tuple(
        _relabel_measurement(entry[3].template.measurements[0], index)
        for index, entry in enumerate(entries)
        if entry[3].template is not None and len(entry[3].template.measurements) == 1
    )
    if len(measurements) != len(entries):
        return _blocked(source_artifact_id, "frame_measurement_invalid")

    frames = [
        {
            "measurement_id": measurement.measurement_id,
            "source_path": str(path),
            "temperature_C": temperature,
            "time_min": time_min,
            "order": index,
            "order_source": "temperature_then_filename",
        }
        for index, (measurement, (path, temperature, time_min, _)) in enumerate(
            zip(measurements, entries, strict=True)
        )
    ]
    record = ConversionRecord.create(
        conversion_id="ir.temperature-series.v1",
        source_artifact_id=source_artifact_id,
        observed_columns=("wavenumber", "absorbance", "temperature_C", "time_min"),
        extracted_segments=tuple(
            {
                "measurement_id": measurement.measurement_id,
                "source_path": str(path),
                "temperature_C": temperature,
                "time_min": time_min,
            }
            for measurement, (path, temperature, time_min, _) in zip(
                measurements, entries, strict=True
            )
        ),
    )
    template = CanonicalExperiment.create(
        template_id="ir.temperature_series.v1",
        source_artifact_id=source_artifact_id,
        payload={
            "technique": "ir",
            "axis_names": ["frame", "wavenumber"],
            "axis_units": {"frame": "condition", "wavenumber": "cm^-1"},
            "frames": frames,
        },
        conversion_record=record,
        measurements=measurements,
    )
    return ConversionOutcome(status="ready", record=record, template=template)


def _parse_condition(path: Path) -> tuple[float | None, float | None]:
    stem = path.stem.lower()
    for pattern in _TEMPERATURE_PATTERNS:
        match = pattern.search(stem)
        if match is None:
            continue
        temperature = float(match.group("temperature"))
        time_value = match.groupdict().get("time")
        return temperature, None if time_value is None else float(time_value)
    return None, None


def _relabel_measurement(measurement: object, index: int):
    """Make per-file table IDs unique inside the combined sequence."""
    measurement_id = f"frame-{index:03d}"
    mapping = getattr(measurement, "mapping", None)
    if mapping is not None:
        mapping = replace(mapping, measurement_id=measurement_id)
    return replace(measurement, measurement_id=measurement_id, mapping=mapping)


def _blocked(
    source_artifact_id: str,
    *reason_codes: str,
    status: str = "needs_input",
) -> ConversionOutcome:
    record = ConversionRecord.create(
        conversion_id="ir.temperature-series.v1",
        source_artifact_id=source_artifact_id,
        reason_codes=tuple(dict.fromkeys(str(code) for code in reason_codes)),
    )
    return ConversionOutcome(
        status=status if status in {"blocked", "needs_input"} else "needs_input",
        record=record,
        reason_codes=record.reason_codes,
    )


__all__ = ["build_ir_temperature_series_template"]
