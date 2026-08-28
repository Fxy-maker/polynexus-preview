"""Deterministic conversion of Mettler multi-program DSC exports."""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from .models import CanonicalExperiment, ConversionOutcome, ConversionRecord


_CONVERTER_ID = "mettler.dsc-isothermal.v1"
_OBSERVED_COLUMNS = ("index", "time_s", "sample_temperature_C", "setpoint_C", "heat_flow_mW")
_MIN_DURATION_S = 60.0
_MAX_SAMPLE_OFFSET_C = 0.5
_MAX_SAMPLE_SPAN_C = 0.5
_MAX_SAMPLE_NOISE_C = 0.05


def convert_mettler_isothermal_text(
    text: str,
    *,
    source_artifact_id: str,
    template_id: str = "dsc.isothermal.v1",
) -> ConversionOutcome:
    """Convert one Mettler ASCII export into a validated thermal-program template.

    ``dsc.isothermal.v1`` remains the compatibility default for callers that
    explicitly use the original converter.  Registry-driven routes request the
    generic ``thermal_program.v1`` identity.
    """
    if template_id not in {"dsc.isothermal.v1", "thermal_program.v1"}:
        raise ValueError(f"Unsupported DSC template id: {template_id}")
    rows, sample_mass_mg, parse_reason = _parse_rows(text)
    if parse_reason:
        record = ConversionRecord.create(
            conversion_id=_CONVERTER_ID,
            source_artifact_id=source_artifact_id,
            observed_columns=_OBSERVED_COLUMNS if rows else (),
            reason_codes=(parse_reason,),
        )
        return ConversionOutcome(status="blocked", record=record, reason_codes=(parse_reason,))

    if template_id == "thermal_program.v1" and not _looks_like_isothermal_program(rows):
        return _convert_thermal_program_rows(
            rows,
            sample_mass_mg=sample_mass_mg,
            source_artifact_id=source_artifact_id,
        )

    accepted: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    rejected_ramp: list[tuple[int, float, float, float, float]] = []
    generic_mode = template_id == "thermal_program.v1"
    prepared = False
    for group in _setpoint_groups(rows):
        evidence = _group_evidence(group)
        reason = _invalid_group_reason(group)
        if generic_mode and reason in {
            "sample_temperature_outside_stability_tolerance",
            "sample_temperature_span_exceeds_tolerance",
            "sample_temperature_noise_exceeds_tolerance",
        }:
            reason = None
        if reason:
            if reason == "duration_below_minimum":
                rejected_ramp.extend(group)
            else:
                evidence["role"] = "rejected_program_segment"
                evidence["reason"] = reason
                excluded.append(evidence)
            continue
        if rejected_ramp:
            excluded.append(_ramp_evidence(rejected_ramp))
            rejected_ramp = []
        setpoint = evidence["setpoint_C"]
        if not generic_mode:
            if setpoint >= 200.0:
                evidence["role"] = "melt_hold"
                excluded.append(evidence)
                prepared = True
                continue
            if not prepared:
                evidence["role"] = "rejected_program_segment"
                evidence["reason"] = "missing_preparation_melt_hold"
                excluded.append(evidence)
                continue
        warnings = _group_quality_warnings(group)
        segment_id = f"iso-{setpoint:g}C-{len(accepted) + 1:03d}"
        segment = {
            "segment_id": segment_id,
            "role": "isothermal_crystallization",
            "setpoint_C": setpoint,
            "time_s": [float(row[1]) for row in group],
            "sample_temperature_C": [float(row[2]) for row in group],
            "heat_flow_mW": [float(row[4]) for row in group],
            "source_range": evidence["source_range"],
        }
        if warnings:
            segment["quality_warnings"] = warnings
            evidence["quality_warnings"] = warnings
        accepted.append(segment)
        evidence["role"] = "isothermal_crystallization"

    if rejected_ramp:
        excluded.append(_ramp_evidence(rejected_ramp))

    if generic_mode:
        accepted = _remove_inferred_preparation_holds(accepted, excluded)

    reasons = () if accepted else ("conversion_no_qualified_isothermal_hold",)
    record = ConversionRecord.create(
        conversion_id=_CONVERTER_ID,
        source_artifact_id=source_artifact_id,
        observed_columns=_OBSERVED_COLUMNS,
        extracted_segments=[
            {
                "segment_id": segment["segment_id"],
                "role": segment["role"],
                "setpoint_C": segment["setpoint_C"],
                "source_range": segment["source_range"],
            }
            for segment in accepted
        ],
        excluded_segments=excluded,
        reason_codes=reasons,
    )
    if not accepted:
        return ConversionOutcome(status="blocked", record=record, reason_codes=reasons)
    template = CanonicalExperiment.create(
        template_id=template_id,
        source_artifact_id=source_artifact_id,
        payload={
            "sample": {"mass_mg": sample_mass_mg},
            "segments": accepted,
        },
        conversion_record=record,
    )
    return ConversionOutcome(status="ready", record=record, template=template)


def _looks_like_isothermal_program(rows: list[tuple[int, float, float, float, float]]) -> bool:
    """Recognize the historical repeated-setpoint isothermal export shape."""
    groups = _setpoint_groups(rows)
    if len(groups) < 2:
        return False
    stable = [group for group in groups if len(group) >= 2]
    return len(stable) >= 2


def _convert_thermal_program_rows(
    rows: list[tuple[int, float, float, float, float]],
    *,
    sample_mass_mg: float | None,
    source_artifact_id: str,
) -> ConversionOutcome:
    """Map one complete thermal program without discarding monotonic ramps.

    The historical converter intentionally retained only qualified isothermal
    holds.  ``thermal_program.v1`` is the shared container, so its converter
    keeps heating/cooling ramps as well and leaves role-specific calculations to
    the DSC executor.
    """
    if len(rows) < 2:
        record = ConversionRecord.create(
            conversion_id=_CONVERTER_ID,
            source_artifact_id=source_artifact_id,
            observed_columns=_OBSERVED_COLUMNS,
            reason_codes=("conversion_columns_missing",),
        )
        return ConversionOutcome(status="blocked", record=record, reason_codes=record.reason_codes)

    values = np.asarray([row[2] for row in rows], dtype=float)
    times = np.asarray([row[1] for row in rows], dtype=float)
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(times)):
        record = ConversionRecord.create(
            conversion_id=_CONVERTER_ID,
            source_artifact_id=source_artifact_id,
            observed_columns=_OBSERVED_COLUMNS,
            reason_codes=("conversion_numeric_row_invalid",),
        )
        return ConversionOutcome(status="blocked", record=record, reason_codes=record.reason_codes)

    delta = np.diff(values)
    direction = np.zeros(len(delta), dtype=int)
    direction[delta > 0.02] = 1
    direction[delta < -0.02] = -1
    nonzero = np.flatnonzero(direction)
    if len(nonzero) == 0:
        direction[:] = 0
    else:
        direction[: nonzero[0]] = direction[nonzero[0]]
        last = direction[nonzero[0]]
        for index in range(nonzero[0], len(direction)):
            if direction[index] == 0:
                direction[index] = last
            else:
                last = direction[index]

    breaks = [0]
    for index in range(1, len(direction)):
        if direction[index] != direction[index - 1]:
            breaks.append(index)
    breaks.append(len(rows) - 1)

    segments: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for ordinal, (start, end) in enumerate(zip(breaks[:-1], breaks[1:]), start=1):
        stop = end + 1
        group = rows[start:stop]
        if len(group) < 2:
            continue
        start_temp = float(group[0][2])
        end_temp = float(group[-1][2])
        span = abs(end_temp - start_temp)
        duration = float(group[-1][1] - group[0][1])
        setpoint = float(np.nanmedian([row[3] for row in group]))
        source_range = {
            "start_row": int(group[0][0]),
            "end_row": int(group[-1][0]),
            "start_time_s": float(group[0][1]),
            "end_time_s": float(group[-1][1]),
        }
        evidence: dict[str, Any] = {
            "setpoint_C": setpoint,
            "source_range": source_range,
            "point_count": len(group),
        }

        if span < 0.5 and duration >= _MIN_DURATION_S:
            role = "isothermal_crystallization"
            segment_id = f"iso-{setpoint:g}C-{len(segments) + 1:03d}"
        elif span >= 2.0:
            role = "heating" if end_temp > start_temp else "cooling"
            segment_id = f"{role}-{ordinal:03d}"
        else:
            evidence.update(role="rejected_program_segment", reason="segment_too_short")
            excluded.append(evidence)
            continue

        segment: dict[str, Any] = {
            "segment_id": segment_id,
            "role": role,
            "setpoint_C": setpoint,
            "time_s": [float(row[1]) for row in group],
            "sample_temperature_C": [float(row[2]) for row in group],
            "heat_flow_mW": [float(row[4]) for row in group],
            "source_range": source_range,
        }
        warnings = _group_quality_warnings(group)
        if warnings:
            segment["quality_warnings"] = warnings
            evidence["quality_warnings"] = warnings
        if len(group) > 1 and duration > 0:
            segment["rate_K_per_min"] = float((end_temp - start_temp) / duration * 60.0)
        segments.append(segment)

    segments = _remove_inferred_preparation_holds(segments, excluded)

    if not segments:
        reasons = ("conversion_no_qualified_thermal_segments",)
        record = ConversionRecord.create(
            conversion_id=_CONVERTER_ID,
            source_artifact_id=source_artifact_id,
            observed_columns=_OBSERVED_COLUMNS,
            excluded_segments=excluded,
            reason_codes=reasons,
        )
        return ConversionOutcome(status="blocked", record=record, reason_codes=reasons)

    record = ConversionRecord.create(
        conversion_id=_CONVERTER_ID,
        source_artifact_id=source_artifact_id,
        observed_columns=_OBSERVED_COLUMNS,
        extracted_segments=[
            {
                "segment_id": segment["segment_id"],
                "role": segment["role"],
                "setpoint_C": segment["setpoint_C"],
                "source_range": segment["source_range"],
            }
            for segment in segments
        ],
        excluded_segments=excluded,
    )
    template = CanonicalExperiment.create(
        template_id="thermal_program.v1",
        source_artifact_id=source_artifact_id,
        payload={"sample": {"mass_mg": sample_mass_mg}, "segments": segments},
        conversion_record=record,
    )
    return ConversionOutcome(status="ready", record=record, template=template)


def _parse_rows(text: str) -> tuple[list[tuple[int, float, float, float, float]], float | None, str | None]:
    rows: list[tuple[int, float, float, float, float]] = []
    sample_mass_mg = _sample_mass_mg(text)
    malformed_numeric = False
    invalid_numeric_row = False
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        try:
            numeric = [float(value) for value in parts]
        except ValueError:
            if len(parts) >= 5 and _looks_like_measurement(parts):
                invalid_numeric_row = True
            continue
        if len(numeric) < 5:
            malformed_numeric = True
            continue
        rows.append((int(numeric[0]), numeric[1], numeric[2], numeric[3], numeric[4]))
    if invalid_numeric_row:
        return rows, sample_mass_mg, "conversion_numeric_row_invalid"
    if malformed_numeric or not rows:
        return rows, sample_mass_mg, "conversion_columns_missing"
    return rows, sample_mass_mg, None


def _looks_like_measurement(parts: list[str]) -> bool:
    try:
        float(parts[0])
        float(parts[1])
    except ValueError:
        return False
    return True


def _sample_mass_mg(text: str) -> float | None:
    match = re.search(r"(?:sample\s*(?:weight|size|mass)?|weight)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*(mg|g)\b", text, re.I)
    if not match:
        match = re.search(r"^\s*[^\n,]+,\s*([0-9]+(?:\.[0-9]+)?)\s*(mg|g)\b", text, re.I | re.M)
    if not match:
        return None
    mass = float(match.group(1))
    return mass * 1000.0 if match.group(2).lower() == "g" else mass


def _setpoint_groups(rows: list[tuple[int, float, float, float, float]]) -> list[list[tuple[int, float, float, float, float]]]:
    groups: list[list[tuple[int, float, float, float, float]]] = []
    for row in rows:
        if not groups or not np.isclose(row[3], groups[-1][-1][3], atol=1e-9, rtol=0.0):
            groups.append([row])
        else:
            groups[-1].append(row)
    return groups


def _group_evidence(group: list[tuple[int, float, float, float, float]]) -> dict[str, Any]:
    return {
        "setpoint_C": float(group[0][3]),
        "source_range": {
            "start_row": int(group[0][0]),
            "end_row": int(group[-1][0]),
            "start_time_s": float(group[0][1]),
            "end_time_s": float(group[-1][1]),
        },
        "point_count": len(group),
    }


def _ramp_evidence(rows: list[tuple[int, float, float, float, float]]) -> dict[str, Any]:
    evidence = _group_evidence(rows)
    evidence["role"] = "ramp"
    evidence["reason"] = "duration_below_minimum"
    return evidence


def _invalid_group_reason(group: list[tuple[int, float, float, float, float]]) -> str | None:
    array = np.asarray([row[1:] for row in group], dtype=float)
    if not np.all(np.isfinite(array)):
        return "nonfinite_measurement"
    time_s = array[:, 0]
    if len(time_s) < 2:
        return "duration_below_minimum"
    if np.any(np.diff(time_s) <= 0):
        return "time_not_strictly_increasing"
    if float(time_s[-1] - time_s[0]) < _MIN_DURATION_S:
        return "duration_below_minimum"
    if np.max(np.abs(array[:, 1] - array[:, 2])) > _MAX_SAMPLE_OFFSET_C:
        return "sample_temperature_outside_stability_tolerance"
    if float(np.ptp(array[:, 1])) > _MAX_SAMPLE_SPAN_C:
        return "sample_temperature_span_exceeds_tolerance"
    if float(np.std(array[:, 1])) > _MAX_SAMPLE_NOISE_C:
        return "sample_temperature_noise_exceeds_tolerance"
    return None


def _group_quality_warnings(group: list[tuple[int, float, float, float, float]]) -> list[str]:
    """Return soft temperature diagnostics without discarding calculable data."""
    array = np.asarray([row[1:] for row in group], dtype=float)
    warnings: list[str] = []
    if np.max(np.abs(array[:, 1] - array[:, 2])) > _MAX_SAMPLE_OFFSET_C:
        warnings.append("sample_temperature_outside_stability_tolerance")
    if float(np.ptp(array[:, 1])) > _MAX_SAMPLE_SPAN_C:
        warnings.append("sample_temperature_span_exceeds_tolerance")
    if float(np.std(array[:, 1])) > _MAX_SAMPLE_NOISE_C:
        warnings.append("sample_temperature_noise_exceeds_tolerance")
    return warnings


def _remove_inferred_preparation_holds(
    segments: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove repeated highest holds as file-local preparation provenance.

    This intentionally uses only the observed program, never a material
    database or fixed temperature threshold.
    """
    holds = [segment for segment in segments if segment["role"] == "isothermal_crystallization"]
    if not holds:
        return segments
    max_hold = max(float(segment["setpoint_C"]) for segment in holds)
    max_count = sum(
        np.isclose(float(segment["setpoint_C"]), max_hold, atol=1e-9, rtol=0.0)
        for segment in holds
    )
    if max_count < 2:
        return segments
    retained: list[dict[str, Any]] = []
    for segment in segments:
        if (
            segment["role"] == "isothermal_crystallization"
            and np.isclose(float(segment["setpoint_C"]), max_hold, atol=1e-9, rtol=0.0)
        ):
            excluded.append({
                "setpoint_C": float(segment["setpoint_C"]),
                "source_range": dict(segment["source_range"]),
                "point_count": len(segment["time_s"]),
                "role": "melt_hold",
                **(
                    {"quality_warnings": list(segment["quality_warnings"])}
                    if segment.get("quality_warnings")
                    else {}
                ),
            })
        else:
            retained.append(segment)
    return retained
