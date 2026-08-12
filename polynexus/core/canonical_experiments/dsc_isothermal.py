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
_MELT_PREPARATION_C = 200.0


def convert_mettler_isothermal_text(text: str, *, source_artifact_id: str) -> ConversionOutcome:
    """Convert one Mettler ASCII export into the DSC isothermal canonical template."""
    rows, sample_mass_mg, parse_reason = _parse_rows(text)
    if parse_reason:
        record = ConversionRecord.create(
            conversion_id=_CONVERTER_ID,
            source_artifact_id=source_artifact_id,
            observed_columns=_OBSERVED_COLUMNS if rows else (),
            reason_codes=(parse_reason,),
        )
        return ConversionOutcome(status="blocked", record=record, reason_codes=(parse_reason,))

    accepted: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    rejected_ramp: list[tuple[int, float, float, float, float]] = []
    prepared = False
    for group in _setpoint_groups(rows):
        evidence = _group_evidence(group)
        reason = _invalid_group_reason(group)
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
        if setpoint >= _MELT_PREPARATION_C:
            evidence["role"] = "melt_hold"
            excluded.append(evidence)
            prepared = True
            continue
        if not prepared:
            evidence["role"] = "rejected_program_segment"
            evidence["reason"] = "missing_preparation_melt_hold"
            excluded.append(evidence)
            continue
        segment_id = f"iso-{setpoint:g}C-{len(accepted) + 1:03d}"
        accepted.append(
            {
                "segment_id": segment_id,
                "role": "isothermal_crystallization",
                "setpoint_C": setpoint,
                "time_s": [float(row[1]) for row in group],
                "sample_temperature_C": [float(row[2]) for row in group],
                "heat_flow_mW": [float(row[4]) for row in group],
                "source_range": evidence["source_range"],
            }
        )
        evidence["role"] = "isothermal_crystallization"
        accepted_evidence = evidence
        # Preserve the explicit preparation requirement for every later hold.
        accepted_evidence["preparation_melt_observed"] = True

    if rejected_ramp:
        excluded.append(_ramp_evidence(rejected_ramp))

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
        template_id="dsc.isothermal.v1",
        source_artifact_id=source_artifact_id,
        payload={
            "sample": {"mass_mg": sample_mass_mg},
            "segments": accepted,
        },
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
