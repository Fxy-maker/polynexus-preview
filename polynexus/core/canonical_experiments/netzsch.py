"""Canonical conversion adapters for the observed NETZSCH NGB readers."""

from __future__ import annotations

from pathlib import Path
import struct

from ...readers.netzsch_ngb_reader import (
    READER_VERSION,
    read_netzsch_dsc,
    read_netzsch_tga,
)
from .models import CanonicalExperiment, ConversionOutcome, ConversionRecord, MappingSelection, Measurement


def convert_netzsch_dsc(path: str | Path, *, source_artifact_id: str) -> ConversionOutcome:
    try:
        decoded = read_netzsch_dsc(path)
    except (OSError, ValueError, struct.error) as exc:
        return _blocked(source_artifact_id, "netzsch_dsc_reader_failed", str(exc))
    segments = []
    extracted = []
    for segment in decoded.segments:
        segment_id = f"netzsch-dsc-segment-{segment.index + 1:03d}"
        temperature = segment.temperature_c
        if len(temperature) < 2:
            return _blocked(source_artifact_id, "netzsch_dsc_segment_invalid", "too_few_points")
        delta = temperature[-1] - temperature[0]
        role = "heating" if delta > 2.0 else "cooling" if delta < -2.0 else "thermal_program_segment"
        segments.append(
            {
                "segment_id": segment_id,
                "role": role,
                "setpoint_C": None,
                "time_s": [value * 60.0 for value in segment.time_min],
                "sample_temperature_C": list(segment.temperature_c),
                "heat_flow_mW_per_mg": list(segment.dsc_mw_per_mg),
                "heat_flow_unit": "mW/mg",
                "extra_channels": [list(values) for values in segment.extra_channels],
                "source_range": {
                    "stream": decoded.source_stream,
                    "block_offsets": list(segment.source_offsets),
                },
            }
        )
        extracted.append({"segment_id": segment_id, "source_range": segments[-1]["source_range"]})
    record = ConversionRecord.create(
        conversion_id=f"{READER_VERSION}.dsc",
        source_artifact_id=source_artifact_id,
        observed_columns=("time /min, all segments", "Temperature /°C", "DSC /(mW/mg) exo+", "unassigned channel 1", "unassigned channel 2"),
        extracted_segments=extracted,
        warnings=("sample_mass_not_present_in_source", "extra_channels_retained_unassigned"),
    )
    template = CanonicalExperiment.create(
        template_id="thermal_program.v1",
        source_artifact_id=source_artifact_id,
        payload={
            "technique": "DSC",
            "sample": {"mass_mg": None},
            "heat_flow_unit": "mW/mg",
            "segments": segments,
            "source_format": "netzsch_ngb_sd7",
            "reader_version": READER_VERSION,
            "source_labels": list(decoded.labels),
        },
        conversion_record=record,
    )
    return ConversionOutcome(status="ready", record=record, template=template)


def convert_netzsch_tga(path: str | Path, *, source_artifact_id: str) -> ConversionOutcome:
    try:
        decoded = read_netzsch_tga(path)
    except (OSError, ValueError, struct.error) as exc:
        return _blocked(source_artifact_id, "netzsch_tga_reader_failed", str(exc))
    measurements = []
    extracted = []
    for segment in decoded.segments:
        measurement_id = f"netzsch-tga-segment-{segment.index + 1:03d}"
        mapping = MappingSelection(
            measurement_id=measurement_id,
            sheet_name=None,
            sheet_index=None,
            table_index=segment.index,
            header_row=0,
            data_row_start=0,
            data_row_end=len(segment.temperature_c) - 1,
            x_column="Temperature /°C",
            intensity_column="TG /mg",
            x_kind="temperature",
            x_unit="°C",
            intensity_unit="mg",
            source="observed",
        )
        locator = {
            "source_path": str(Path(path).resolve()),
            "sheet_name": None,
            "sheet_index": None,
            "table_index": segment.index,
            "header_row": 0,
            "data_row_start": 0,
            "data_row_end": len(segment.temperature_c) - 1,
            "point_start": 0,
            "point_end": len(segment.temperature_c) - 1,
        }
        measurements.append(
            Measurement(
                measurement_id=measurement_id,
                family="thermal_1d",
                role="raw_curve",
            channels={"x": segment.temperature_c, "intensity": segment.tg_mg},
                units={"x": "°C", "intensity": "mg"},
                source_locator=locator,
                acquisition_metadata={
                    "axis_kind": "temperature",
                    "signal_kind": "tg_reported_mass",
                    "signal_semantics": "instrument_reported_TG_channel",
                    "absolute_mass_available": False,
                    "reader_version": READER_VERSION,
                    "source_format": "netzsch_ngb_ds1",
                    "time_min": list(segment.time_min),
                    "source_offsets": list(segment.source_offsets),
                    "extra_channels": [list(values) for values in segment.extra_channels],
                    "source_labels": list(decoded.labels),
                },
                mapping=mapping,
            )
        )
        extracted.append({"measurement_id": measurement_id, "source_locator": locator})
    record = ConversionRecord.create(
        conversion_id=f"{READER_VERSION}.tga",
        source_artifact_id=source_artifact_id,
        observed_columns=("time /min, all segments", "Temperature /°C", "TG /mg", "Gas /ml/min", "unassigned channels"),
        extracted_segments=extracted,
        warnings=(
            "unassigned_channels_retained_in_acquisition_metadata",
            "tg_channel_may_be_signed_or_zero_referenced",
        ),
    )
    template = CanonicalExperiment.create(
        template_id="thermal_curve_1d.v1",
        source_artifact_id=source_artifact_id,
        payload={
            "technique": "TGA",
            "measurement_family": "thermal_1d",
            "source_format": "netzsch_ngb_ds1",
            "reader_version": READER_VERSION,
            "source_labels": list(decoded.labels),
        },
        conversion_record=record,
        measurements=measurements,
    )
    return ConversionOutcome(status="ready", record=record, template=template)


def _blocked(source_artifact_id: str, prefix: str, detail: str) -> ConversionOutcome:
    reason = prefix if not detail else f"{prefix}:{detail.replace(' ', '_').lower()}"
    record = ConversionRecord.create(
        conversion_id=f"{READER_VERSION}.failed",
        source_artifact_id=source_artifact_id,
        reason_codes=(reason,),
    )
    return ConversionOutcome(status="needs_input", record=record, reason_codes=(reason,))


__all__ = ["convert_netzsch_dsc", "convert_netzsch_tga"]
