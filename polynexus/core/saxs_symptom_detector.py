from __future__ import annotations

from typing import Any


def _clean_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _string(value: Any) -> str:
    return str(value or "").strip()


def _non_empty_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = _string(value)
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _relative_spread(values: list[float]) -> float:
    finite = [float(value) for value in values if value is not None]
    if len(finite) < 2:
        return 0.0
    scale = max(max(abs(value) for value in finite), 1e-9)
    return (max(finite) - min(finite)) / scale


def _triggered_constraint_names(
    constraints: list[dict[str, Any]] | None,
    constraint_summary: dict[str, Any] | None,
) -> set[str]:
    names: set[str] = set()
    summary = constraint_summary if isinstance(constraint_summary, dict) else {}
    triggered = summary.get("triggered_names", {})
    if isinstance(triggered, dict):
        for items in triggered.values():
            if not isinstance(items, list):
                continue
            for item in items:
                text = _string(item)
                if text:
                    names.add(text)

    for item in constraints or []:
        if not isinstance(item, dict) or not item.get("triggered"):
            continue
        text = _string(item.get("name"))
        if text:
            names.add(text)
    return names


def _fit_region_map(output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    regions = output.get("fit_regions")
    mapped: dict[str, dict[str, Any]] = {}
    if not isinstance(regions, list):
        return mapped
    for region in regions:
        if not isinstance(region, dict):
            continue
        label = _string(region.get("region") or region.get("name")).lower()
        if label:
            mapped[label] = region
    return mapped


def _condition_values(output: dict[str, Any], batch_rows: list[dict[str, Any]], label: str) -> list[float]:
    values: list[float] = []
    if batch_rows:
        for row in batch_rows:
            if not isinstance(row, dict):
                continue
            value = _clean_float(row.get("condition_value"))
            if value is None and label == "temperature":
                value = _clean_float(row.get("temperature_C"))
            if value is None and label == "strain":
                value = _clean_float(row.get("strain_pct"))
            if value is not None:
                values.append(value)
        return values

    for key in ("condition_value", "temperature_C", "strain_pct"):
        value = _clean_float(output.get(key))
        if value is not None:
            values.append(value)
            break
    return values


def _batch_sample_markers(batch_rows: list[dict[str, Any]]) -> list[str]:
    markers: list[str] = []
    for row in batch_rows:
        if not isinstance(row, dict):
            continue
        for key in ("sample_id", "sample_name", "_sample_name", "sample"):
            marker = _string(row.get(key))
            if marker:
                markers.append(marker)
                break
    return _non_empty_strings(markers)


def _batch_numeric_values(batch_rows: list[dict[str, Any]], *keys: str) -> list[float]:
    values: list[float] = []
    for row in batch_rows:
        if not isinstance(row, dict):
            continue
        for key in keys:
            value = _clean_float(row.get(key))
            if value is not None:
                values.append(value)
                break
    return values


def _mean_finite(values: list[Any]) -> float | None:
    finite: list[float] = []
    for value in values:
        number = _clean_float(value)
        if number is not None:
            finite.append(number)
    if not finite:
        return None
    return sum(finite) / len(finite)


def _row_raw_structure(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    raw_snapshot = row.get("raw_snapshot")
    if isinstance(raw_snapshot, dict):
        raw_structure = raw_snapshot.get("structure")
        if isinstance(raw_structure, dict):
            return raw_structure
    raw_structure = row.get("raw_structure")
    return raw_structure if isinstance(raw_structure, dict) else {}


def _batch_calibration_report(batch_rows: list[dict[str, Any]]) -> dict[str, Any]:
    calibrated_lc_values: list[float] = []
    raw_lc_values: list[float] = []
    calibrated_L_values: list[float] = []
    raw_L_values: list[float] = []
    calibrated_phi_values: list[float] = []
    raw_phi_values: list[float] = []
    lc_gap_samples: list[float] = []
    L_gap_samples: list[float] = []
    phi_gap_samples: list[float] = []
    fallback_rows = 0
    raw_snapshot_rows = 0

    for row in batch_rows:
        if not isinstance(row, dict):
            continue

        raw_structure = _row_raw_structure(row)
        if raw_structure:
            raw_snapshot_rows += 1

        method = _string(row.get("lc_method")).lower()
        fallback_active = bool(row.get("calibrated_fallback_active")) or method in {"calibrated", "qstar_calibrated"}
        if fallback_active:
            fallback_rows += 1

        cal_lc = _clean_float(row.get("lc_nm_calibrated"))
        if cal_lc is None:
            cal_lc = _clean_float(row.get("lc_nm"))
        raw_lc = _clean_float(raw_structure.get("lc"))
        if cal_lc is not None:
            calibrated_lc_values.append(cal_lc)
        if raw_lc is not None:
            raw_lc_values.append(raw_lc)
        if cal_lc is not None and raw_lc is not None:
            lc_gap_samples.append(_relative_spread([cal_lc, raw_lc]))

        cal_L = _clean_float(row.get("L_nm"))
        raw_L = _clean_float(raw_structure.get("L"))
        if cal_L is not None:
            calibrated_L_values.append(cal_L)
        if raw_L is not None:
            raw_L_values.append(raw_L)
        if cal_L is not None and raw_L is not None:
            L_gap_samples.append(_relative_spread([cal_L, raw_L]))

        cal_phi = _clean_float(row.get("Xc_calibrated"))
        if cal_phi is None:
            cal_phi = _clean_float(row.get("Xc"))
        raw_phi = _clean_float(raw_structure.get("phi_c"))
        if cal_phi is not None:
            calibrated_phi_values.append(cal_phi)
        if raw_phi is not None:
            raw_phi_values.append(raw_phi)
        if cal_phi is not None and raw_phi is not None:
            phi_gap_samples.append(_relative_spread([cal_phi, raw_phi]))

    return {
        "fallback_rows": fallback_rows,
        "raw_snapshot_rows": raw_snapshot_rows,
        "row_count": sum(1 for row in batch_rows if isinstance(row, dict)),
        "raw_lc_spread": _relative_spread(raw_lc_values) if len(raw_lc_values) >= 2 else None,
        "calibrated_lc_spread": _relative_spread(calibrated_lc_values) if len(calibrated_lc_values) >= 2 else None,
        "raw_L_spread": _relative_spread(raw_L_values) if len(raw_L_values) >= 2 else None,
        "calibrated_L_spread": _relative_spread(calibrated_L_values) if len(calibrated_L_values) >= 2 else None,
        "raw_phi_spread": _relative_spread(raw_phi_values) if len(raw_phi_values) >= 2 else None,
        "calibrated_phi_spread": _relative_spread(calibrated_phi_values) if len(calibrated_phi_values) >= 2 else None,
        "lc_gap_mean": _mean_finite(lc_gap_samples),
        "L_gap_mean": _mean_finite(L_gap_samples),
        "phi_gap_mean": _mean_finite(phi_gap_samples),
    }


def _make_symptom(
    name: str,
    severity: str,
    summary: str,
    *,
    target_params: list[str] | None = None,
    confidence: float | None = None,
    evidence_keys: list[str] | None = None,
    expected_evidence_change: list[str] | None = None,
    source: str = "saxs_rule",
) -> dict[str, Any]:
    symptom: dict[str, Any] = {
        "name": name,
        "severity": severity,
        "summary": summary,
    }
    targets = _non_empty_strings(target_params or [])
    if targets:
        symptom["target_params"] = targets
    if confidence is not None:
        symptom["confidence"] = round(float(confidence), 2)
    evidence = _non_empty_strings(evidence_keys or [])
    if evidence:
        symptom["evidence_keys"] = evidence
    expected = _non_empty_strings(expected_evidence_change or [])
    if expected:
        symptom["expected_evidence_change"] = expected
    if source:
        symptom["source"] = source
    return symptom


def detect_saxs_symptoms(
    output_parameters: dict[str, Any] | None = None,
    residual_pattern: dict[str, Any] | None = None,
    validation_context: dict[str, Any] | None = None,
    *,
    constraints: list[dict[str, Any]] | None = None,
    constraint_summary: dict[str, Any] | None = None,
    signal_evidence: dict[str, Any] | None = None,
    peak_evidence: dict[str, Any] | None = None,
    transform_evidence: dict[str, Any] | None = None,
    structure_evidence: dict[str, Any] | None = None,
    batch_evidence: dict[str, Any] | None = None,
    condition_evidence: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    output = dict(output_parameters or {})
    residual = dict(residual_pattern or {})
    _ = dict(validation_context or {})
    signal = dict(signal_evidence or {})
    peak = dict(peak_evidence or {})
    transform = dict(transform_evidence or {})
    structure = dict(structure_evidence or {})
    batch = dict(batch_evidence or {})
    condition = dict(condition_evidence or {})

    batch_rows = output.get("_batch_data") if isinstance(output.get("_batch_data"), list) else []
    batch_frames = output.get("batch_frames")
    if batch_frames is None and batch.get("batch_frames") is not None:
        batch_frames = batch.get("batch_frames")
    total_frames = int(batch_frames) if isinstance(batch_frames, int) else len(batch_rows)
    condition_label = _string(condition.get("condition_label") or output.get("condition_label")).lower()
    condition_confidence = _clean_float(condition.get("condition_confidence"))
    if condition_confidence is None:
        condition_confidence = _clean_float(output.get("condition_confidence"))
    condition_missing_frames = output.get("condition_missing_frames")
    if condition_missing_frames is None:
        condition_missing_frames = condition.get("condition_missing_frames")
    try:
        missing_frames = int(condition_missing_frames)
    except (TypeError, ValueError):
        missing_frames = 0
    continuity = _clean_float(condition.get("condition_continuity_score"))
    if continuity is None:
        continuity = _clean_float(output.get("condition_continuity_score"))
    condition_values = _condition_values(output, batch_rows, condition_label)

    triggered_constraints = _triggered_constraint_names(constraints, constraint_summary)
    fit_regions = _fit_region_map(output)
    residual_type = _string(residual.get("residual_type")).lower()
    calibration_report = _batch_calibration_report(batch_rows)
    batch_structure_summary = batch.get("batch_structure_summary") if isinstance(batch.get("batch_structure_summary"), dict) else {}
    if not isinstance(batch_structure_summary, dict):
        batch_structure_summary = {}
    temperature_series = condition_label in {"temperature", "condition"}
    temperature_fallback_active = bool(
        temperature_series
        and (
            calibration_report.get("fallback_rows", 0)
            or structure.get("calibrated_fallback_active")
            or output.get("calibrated_fallback_active")
        )
    )

    symptoms: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    def add(symptom: dict[str, Any] | None) -> None:
        if not isinstance(symptom, dict):
            return
        name = _string(symptom.get("name"))
        if not name or name in seen_names:
            return
        seen_names.add(name)
        symptoms.append(symptom)

    has_series_axis = condition_label in {"temperature", "strain"} or total_frames > 1 or bool(condition_values)
    condition_axis_missing = False
    if "missing_condition_axis" in triggered_constraints:
        condition_axis_missing = True
    elif has_series_axis and total_frames > 1 and len(condition_values) < 2:
        condition_axis_missing = True
    elif has_series_axis and missing_frames and total_frames and missing_frames >= total_frames:
        condition_axis_missing = True

    if condition_axis_missing:
        add(
            _make_symptom(
                "condition_axis_missing",
                "error",
                "Condition values are missing or too sparse, so sequence trends are not trustworthy yet.",
                confidence=0.95,
                evidence_keys=[
                    "condition_evidence.condition_missing_frames",
                    "condition_evidence.condition_confidence",
                    "batch_evidence.frame_condition_values",
                ],
                expected_evidence_change=[
                    "condition_missing_frames should drop to 0",
                    "condition_confidence should rise after axis recovery",
                ],
            )
        )
    elif has_series_axis and (
        missing_frames > 0
        or (continuity is not None and continuity < 0.85)
        or (condition_confidence is not None and condition_confidence < 0.75)
    ):
        add(
            _make_symptom(
                "condition_axis_unstable",
                "warning",
                "Recovered condition values are still discontinuous, so sequence trends need manual review.",
                confidence=0.8 if continuity is not None else 0.72,
                evidence_keys=[
                    "condition_evidence.condition_continuity_score",
                    "condition_evidence.condition_missing_frames",
                    "condition_evidence.condition_confidence",
                ],
                expected_evidence_change=[
                    "condition_continuity_score should move closer to 1.0",
                    "condition_missing_frames should shrink",
                ],
            )
        )

    if "strain_axis_low_confidence" in triggered_constraints and condition_label == "strain":
        add(
            _make_symptom(
                "strain_axis_low_confidence",
                "warning",
                "Recovered strain values are present but still low-confidence, so strain trends should stay provisional.",
                confidence=0.78,
                evidence_keys=[
                    "condition_evidence.strain_axis_confidence",
                    "condition_evidence.condition_continuity_score",
                ],
                expected_evidence_change=[
                    "strain_axis_confidence should rise above the warning threshold",
                    "condition_continuity_score should approach 1.0",
                ],
            )
        )

    if "strain_sequence_nonmonotonic" in triggered_constraints:
        add(
            _make_symptom(
                "strain_sequence_nonmonotonic",
                "warning",
                "The strain sequence is not monotonic, so the ordering of the trend should not be trusted yet.",
                confidence=0.86,
                evidence_keys=[
                    "condition_evidence.strain_values",
                    "condition_evidence.sequence_direction",
                ],
                expected_evidence_change=[
                    "strain_values should become monotonic",
                    "sequence_direction should be increasing or decreasing",
                ],
            )
        )

    if "strain_duplicate_frames" in triggered_constraints:
        add(
            _make_symptom(
                "strain_duplicate_frames",
                "warning",
                "Duplicate strain frames weaken continuity and can fake a smooth trend.",
                confidence=0.84,
                evidence_keys=[
                    "condition_evidence.strain_duplicate_count",
                    "condition_evidence.strain_values",
                ],
                expected_evidence_change=[
                    "strain_duplicate_count should drop to 0",
                ],
            )
        )

    sample_markers = _batch_sample_markers(batch_rows)
    if len(sample_markers) > 1:
        add(
            _make_symptom(
                "batch_mixed_samples",
                "error",
                "Batch rows contain more than one sample identity, so one shared trend fit is misleading.",
                confidence=0.93,
                evidence_keys=["_batch_data.sample_name", "_batch_data.sample_id"],
                expected_evidence_change=[
                    "split batches should each resolve to one sample identity",
                ],
            )
        )

    if temperature_fallback_active:
        add(
            _make_symptom(
                "temperature_calibration_fallback_active",
                "info",
                "Temperature batch results are using calibrated fallback values, so the batch summary must stay labeled as fallback-derived.",
                evidence_keys=[
                    "structure_evidence.calibrated_fallback_active",
                    "structure_evidence.calibrated_fallback_reason",
                    "batch_evidence.batch_frames",
                    "raw_structure_evidence.raw_structure_available",
                ],
                expected_evidence_change=[
                    "calibrated_fallback_active should become false only after the raw frame evidence is trustworthy again",
                    "raw frame-level structure should remain visible alongside the batch summary",
                ],
            )
        )

    dominant_lc_status = _string(
        batch_structure_summary.get("dominant_lc_reliability_status")
        or structure.get("lc_reliability_status")
        or output.get("lc_reliability_status")
    ).lower()
    dominant_lc_reason = _string(
        batch_structure_summary.get("dominant_lc_reliability_reason")
        or structure.get("lc_reliability_reason")
        or output.get("lc_reliability_reason")
    )
    dominant_melting_status = _string(
        batch_structure_summary.get("dominant_melting_window_status")
        or structure.get("melting_window_status")
        or output.get("melting_window_status")
    ).lower()
    try:
        diagnostic_only_rows = int(
            batch_structure_summary.get("diagnostic_only_rows")
            if batch_structure_summary.get("diagnostic_only_rows") is not None
            else (1 if dominant_lc_status == "diagnostic_only" else 0)
        )
    except (TypeError, ValueError):
        diagnostic_only_rows = 1 if dominant_lc_status == "diagnostic_only" else 0
    try:
        within_window_rows = int(
            batch_structure_summary.get("within_window_rows")
            if batch_structure_summary.get("within_window_rows") is not None
            else (1 if dominant_melting_status == "within_window" else 0)
        )
    except (TypeError, ValueError):
        within_window_rows = 1 if dominant_melting_status == "within_window" else 0
    try:
        near_onset_rows = int(batch_structure_summary.get("near_onset_rows") or 0)
    except (TypeError, ValueError):
        near_onset_rows = 0

    if diagnostic_only_rows > 0 or dominant_lc_status == "diagnostic_only":
        add(
            _make_symptom(
                "diagnostic_lc_frames_present",
                "warning",
                "One or more SAXS frames are only diagnostic for lc, so the reported thickness values should not be treated as final structure parameters yet.",
                confidence=0.9 if diagnostic_only_rows > 0 else 0.78,
                evidence_keys=[
                    "structure_evidence.lc_reliability_status",
                    "structure_evidence.lc_reliability_reason",
                    "batch_evidence.batch_structure_summary",
                    "batch_evidence.frame_condition_values",
                ],
                expected_evidence_change=[
                    "diagnostic_only_rows should shrink as frame-level structure support improves",
                    "lc_reliability_status should move from diagnostic_only toward usable",
                ],
            )
        )

    if within_window_rows > 0 or near_onset_rows > 0 or dominant_melting_status in {"near_onset", "within_window", "post_end"}:
        add(
            _make_symptom(
                "temperature_sequence_near_melting_window",
                "info",
                "The temperature sequence is entering or passing a SAXS-derived melting window, so lc changes should be interpreted as transition-sensitive rather than purely solid-state structure evolution.",
                confidence=0.82,
                evidence_keys=[
                    "structure_evidence.melting_window_status",
                    "batch_evidence.batch_structure_summary",
                    "feature_evidence.thermal_event_evidence",
                ],
                expected_evidence_change=[
                    "melting_window_status should align with the tracked Bragg-intensity loss",
                    "transition frames should remain clearly separated from stable solid-state frames",
                ],
            )
        )

    if (diagnostic_only_rows > 0 or dominant_lc_status == "diagnostic_only") and within_window_rows <= 0 and dominant_melting_status not in {"within_window", "post_end"}:
        add(
            _make_symptom(
                "lc_unreliable_without_melting_proof",
                "warning",
                "lc extraction is unstable, but the current SAXS evidence still does not prove that the frame has entered the melting window.",
                confidence=0.88,
                evidence_keys=[
                    "structure_evidence.lc_reliability_status",
                    "structure_evidence.melting_window_status",
                    "batch_evidence.batch_structure_summary",
                ],
                expected_evidence_change=[
                    "either melting-window evidence should strengthen, or lc reliability should recover before drawing a phase conclusion",
                ],
            )
        )

    batch_conflict_triggered = False
    batch_conflict_score = max(
        value
        for value in (
            calibration_report.get("lc_gap_mean"),
            calibration_report.get("L_gap_mean"),
            calibration_report.get("phi_gap_mean"),
        )
        if value is not None
    ) if any(
        value is not None
        for value in (
            calibration_report.get("lc_gap_mean"),
            calibration_report.get("L_gap_mean"),
            calibration_report.get("phi_gap_mean"),
        )
    ) else 0.0
    calibrated_flattening = bool(
        calibration_report.get("raw_lc_spread") is not None
        and calibration_report.get("calibrated_lc_spread") is not None
        and float(calibration_report.get("raw_lc_spread", 0.0) or 0.0) >= 0.08
        and float(calibration_report.get("calibrated_lc_spread", 0.0) or 0.0) <= 0.02
    )
    if temperature_fallback_active and calibration_report.get("raw_snapshot_rows", 0) > 0:
        if batch_conflict_score >= 0.12 or calibrated_flattening:
            batch_conflict_triggered = True
            add(
                _make_symptom(
                    "batch_summary_conflicts_with_frame_evidence",
                    "warning",
                    "Batch-level calibrated values diverge from the raw frame evidence, so the smooth summary should not be treated as measured truth yet.",
                    evidence_keys=[
                        "_batch_data.raw_snapshot.structure.lc",
                        "_batch_data.raw_snapshot.structure.phi_c",
                        "_batch_data.lc_nm_calibrated",
                        "_batch_data.Xc_calibrated",
                        "structure_evidence.calibrated_fallback_reason",
                    ],
                    expected_evidence_change=[
                        "raw frame values and the batch summary should move closer together",
                        "the summary should clearly identify itself as fallback-derived until the raw evidence stabilizes",
                    ],
                )
            )

    beamstop = bool(signal.get("beam_stop_contaminated") or output.get("beam_stop_contaminated"))
    q_star_valid = signal.get("Q_star_valid")
    if q_star_valid is None:
        q_star_valid = output.get("Q_star_valid")
    mask_truncated = bool(signal.get("mask_truncated") or output.get("mask_truncated"))
    if beamstop or q_star_valid is False or mask_truncated:
        add(
            _make_symptom(
                "beamstop_or_low_q_contamination",
                "error" if beamstop else "warning",
                "Low-q evidence is contaminated or truncated, so long-period and invariant interpretation is not stable yet.",
                target_params=["q_bragg_min", "q_corr_min", "savgol_window"],
                confidence=0.92 if beamstop else 0.78,
                evidence_keys=[
                    "signal_evidence.beam_stop_contaminated",
                    "signal_evidence.Q_star_valid",
                    "signal_evidence.mask_truncated",
                ],
                expected_evidence_change=[
                    "beam_stop_contaminated should clear or be masked out",
                    "Q_star_valid should become True",
                ],
            )
        )

    q_star_rel = _clean_float(output.get("Q_star_rel_mean", output.get("Q_star_rel", output.get("Q_rel"))))
    q_star_rel_span = _clean_float(output.get("Q_star_rel_span"))
    phi_void = _clean_float(output.get("phi_void_mean", output.get("phi_void")))
    phi_void_span = _clean_float(output.get("phi_void_span"))
    porod_slope = _clean_float(output.get("porod_slope_mean", output.get("porod_slope")))
    has_void_rows = _clean_float(output.get("has_voids_row_count"))
    void_detected_frames = _clean_float(output.get("void_detected_frames"))
    has_voids = bool(output.get("has_voids")) or (has_void_rows is not None and has_void_rows > 0) or (void_detected_frames is not None and void_detected_frames > 0)
    if porod_slope is not None and porod_slope > -3.5:
        has_voids = True

    if has_voids and (
        (phi_void is not None and phi_void >= 0.02)
        or (phi_void_span is not None and phi_void_span >= 0.015)
        or (porod_slope is not None and porod_slope > -3.5)
        or beamstop
        or mask_truncated
        or q_star_valid is False
    ):
        add(
            _make_symptom(
                "low_q_void_dominant",
                "warning",
                "Low-q scattering is dominated by void or upturn behavior, so the lamellar chain should stay provisional.",
                target_params=["q_bragg_min", "q_corr_min", "q_corr_max", "savgol_window"],
                confidence=0.88,
                evidence_keys=[
                    "structure_evidence.has_voids",
                    "structure_evidence.phi_void",
                    "structure_evidence.porod_slope",
                    "signal_evidence.beam_stop_contaminated",
                    "signal_evidence.mask_truncated",
                ],
                expected_evidence_change=[
                    "has_voids should clear or drop sharply",
                    "phi_void should shrink and the Porod slope should move closer to -4",
                ],
            )
        )

    l_bragg = _clean_float(output.get("L_bragg"))
    l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
    l_best = _clean_float(output.get("L_best", output.get("L_nm")))
    l_support_values = [value for value in (l_bragg, l_corr, l_best) if value is not None]
    l_support_spread = _relative_spread(l_support_values)

    peak_region = fit_regions.get("peak", {})
    bragg_region = fit_regions.get("bragg_peak", fit_regions.get("bragg", {}))
    peak_r2 = _clean_float(peak_region.get("r_squared"))
    if peak_r2 is None:
        peak_r2 = _clean_float(bragg_region.get("r_squared"))
    peak_rmse = _clean_float(peak_region.get("rmse"))
    if peak_rmse is None:
        peak_rmse = _clean_float(bragg_region.get("rmse"))
    q_peak_diff = _clean_float(peak.get("q_peak_diff_pct"))
    if q_peak_diff is None:
        q_peak_diff = _clean_float(output.get("q_peak_diff_pct"))
    if q_peak_diff is None:
        q_peak_diff = _clean_float(output.get("pyfai_q_peak_diff_pct"))
    if residual_type == "peak_mismatch" or (peak_r2 is not None and peak_r2 < 0.35) or (peak_rmse is not None and peak_rmse > 0.25) or (q_peak_diff is not None and abs(q_peak_diff) > 2.5):
        add(
            _make_symptom(
                "peak_window_mismatch",
                "warning",
                "Bragg peak window or alignment looks unstable; tune the peak window before trusting lamellar spacing.",
                target_params=["q_bragg_min", "q_bragg_max", "savgol_window"],
                confidence=0.84,
                evidence_keys=[
                    "peak_evidence.fit_regions",
                    "peak_evidence.q_peak_diff_pct",
                    "residual_evidence.residual_type",
                ],
                expected_evidence_change=[
                    "peak-region residuals should weaken",
                    "q_peak_diff_pct should shrink",
                ],
            )
        )

    oscillation_regions: list[dict[str, Any]] = []
    for label in ("correlation", "correlation_function", "idf"):
        region = fit_regions.get(label, {})
        peak_count = _clean_float(region.get("peak_count"))
        zero_crossings = _clean_float(region.get("zero_crossings"))
        if (peak_count is not None and peak_count >= 8) or (zero_crossings is not None and zero_crossings >= 10):
            oscillation_regions.append(region)
    if "correlation_over_oscillation" in triggered_constraints or oscillation_regions:
        add(
            _make_symptom(
                "idf_artifact_regular_spacing",
                "warning",
                "Correlation or IDF curves oscillate too regularly, so the derived Lc or IDF trend is probably an artifact.",
                target_params=["q_corr_min", "q_corr_max", "savgol_window", "savgol_order"],
                confidence=0.86,
                evidence_keys=[
                    "peak_evidence.fit_regions",
                    "transform_evidence.lc_idf_nm",
                ],
                expected_evidence_change=[
                    "correlation/idf zero-crossings should drop",
                    "correlation-region fit should stop oscillating",
                ],
            )
        )

    lc_tangent = _clean_float(transform.get("lc_tangent_nm"))
    lc_gamma = _clean_float(transform.get("lc_gamma_min_nm"))
    lc_idf = _clean_float(transform.get("lc_idf_nm"))
    lc_values = [value for value in (lc_tangent, lc_gamma, lc_idf) if value is not None]
    lc_confidence = _clean_float(structure.get("lc_confidence"))
    lc_method = _string(structure.get("lc_method")).lower()
    if len(lc_values) >= 2:
        lc_spread = _relative_spread(lc_values)
        if lc_spread > 0.08 or (lc_confidence is not None and lc_confidence < 0.6) or "warn" in lc_method:
            add(
                _make_symptom(
                    "gamma_tangent_unstable",
                    "warning",
                    "Gamma, tangent, and IDF thickness estimates do not agree well enough to trust the crystal-thickness readout yet.",
                    target_params=["q_corr_min", "q_corr_max", "savgol_window"],
                    confidence=0.82,
                    evidence_keys=[
                        "transform_evidence.lc_tangent_nm",
                        "transform_evidence.lc_gamma_min_nm",
                        "transform_evidence.lc_idf_nm",
                        "structure_evidence.lc_confidence",
                    ],
                    expected_evidence_change=[
                        "lc_tangent_nm, lc_gamma_min_nm, and lc_idf_nm should move closer",
                        "lc_confidence should rise",
                    ],
                )
            )

    l_bragg = _clean_float(peak.get("L_bragg"))
    if l_bragg is None:
        l_bragg = _clean_float(output.get("L_bragg"))
    l_corr = _clean_float(transform.get("L_corr_peak"))
    if l_corr is None:
        l_corr = _clean_float(output.get("L_corr_peak", output.get("L_corr")))
    l_best = _clean_float(structure.get("L_best"))
    if l_best is None:
        l_best = _clean_float(output.get("L_best", output.get("L_nm")))
    long_period_values = [value for value in (l_bragg, l_corr, l_best) if value is not None]
    q_alignment_gap = _clean_float(output.get("pyfai_q_peak_diff_pct"))
    if q_alignment_gap is None:
        q_alignment_gap = _clean_float(output.get("q_peak_diff_pct"))
    if (
        "l_consistency" in triggered_constraints
        or _relative_spread(long_period_values) > 0.05
        or (q_alignment_gap is not None and abs(q_alignment_gap) > 2.0)
    ):
        add(
            _make_symptom(
                "multi_method_disagreement",
                "warning",
                "Independent long-period estimators disagree, so one polished number would overstate confidence.",
                target_params=["q_bragg_min", "q_bragg_max", "q_corr_min", "q_corr_max"],
                confidence=0.87,
                evidence_keys=[
                    "peak_evidence.L_bragg",
                    "transform_evidence.L_corr_peak",
                    "structure_evidence.L_best",
                ],
                expected_evidence_change=[
                    "L_bragg and L_corr_peak should move closer",
                    "L_confidence should rise as methods converge",
                ],
            )
        )

    q_star_rel_support = q_star_rel is not None
    if condition_label == "strain" and q_star_rel_support and (
        len(l_support_values) < 2 or l_support_spread is None or l_support_spread > 0.08
    ):
        add(
            _make_symptom(
                "qstar_rel_without_lamellar_support",
                "warning",
                "Q* relative tracking is present, but the long-period support is too weak to use it as a standalone lamellar argument.",
                target_params=["q_corr_min", "q_corr_max", "savgol_window"],
                confidence=0.84,
                evidence_keys=[
                    "structure_evidence.Q_star_rel",
                    "peak_evidence.L_bragg",
                    "transform_evidence.L_corr_peak",
                    "structure_evidence.L_best",
                ],
                expected_evidence_change=[
                    "L_bragg, L_corr_peak, and L_best should converge before Q* is treated as a robust strain axis",
                ],
            )
        )

    if condition_label == "strain" and (
        has_voids
        and (
            (phi_void is not None and phi_void >= 0.02)
            or (q_star_rel_span is not None and q_star_rel_span >= 0.05)
            or (l_support_spread is not None and l_support_spread > 0.05)
            or (porod_slope is not None and porod_slope > -3.5)
        )
    ):
        add(
            _make_symptom(
                "strain_void_lamellar_conflict",
                "warning",
                "Void growth and lamellar spacing are moving together in a way that makes one clean structural explanation too fragile.",
                target_params=["q_bragg_min", "q_corr_min", "q_corr_max", "savgol_window"],
                confidence=0.86,
                evidence_keys=[
                    "structure_evidence.phi_void",
                    "structure_evidence.Q_star_rel",
                    "peak_evidence.L_bragg",
                    "transform_evidence.L_corr_peak",
                    "structure_evidence.L_best",
                ],
                expected_evidence_change=[
                    "void metrics should separate from the lamellar chain",
                    "L_bragg, L_corr_peak, and L_best should settle before comparing strain frames",
                ],
            )
        )

    if condition_label == "strain" and (
        len(l_support_values) < 2 or l_support_spread is None or l_support_spread > 0.10
    ) and (
        has_voids or beamstop or mask_truncated or q_star_valid is False
    ):
        add(
            _make_symptom(
                "lamellar_anchor_lost_under_strain",
                "warning",
                "The lamellar anchor is too unstable across the strain series to use as a reliable comparison baseline.",
                target_params=["q_bragg_min", "q_bragg_max", "q_corr_min", "q_corr_max"],
                confidence=0.87,
                evidence_keys=[
                    "peak_evidence.L_bragg",
                    "transform_evidence.L_corr_peak",
                    "structure_evidence.L_best",
                    "signal_evidence.beam_stop_contaminated",
                    "signal_evidence.mask_truncated",
                ],
                expected_evidence_change=[
                    "one stable long-period anchor should emerge before strain comparison is promoted",
                ],
            )
        )

    f_herman_values = _batch_numeric_values(
        batch_rows,
        "f_Herman",
        "f_herman",
    )
    if not f_herman_values:
        f_herman_mean = _clean_float(output.get("f_Herman_mean", output.get("f_Herman", output.get("f_herman"))))
        if f_herman_mean is not None:
            f_herman_values = [f_herman_mean]
    f_herman_span = _clean_float(output.get("f_Herman_span"))
    if f_herman_span is None and len(f_herman_values) >= 2:
        f_herman_span = max(f_herman_values) - min(f_herman_values)
    if condition_label == "strain" and f_herman_span is not None and f_herman_span > 0.35 and (
        q_star_rel_span is None or q_star_rel_span > 0.03
    ):
        add(
            _make_symptom(
                "orientation_shift_breaks_lamellar_comparison",
                "warning",
                "Orientation shifts are large enough to weaken direct frame-to-frame lamellar comparison.",
                target_params=["q_corr_min", "q_corr_max", "savgol_window"],
                confidence=0.82,
                evidence_keys=[
                    "structure_evidence.f_Herman",
                    "structure_evidence.f_Herman_span",
                    "structure_evidence.Q_star_rel_span",
                ],
                expected_evidence_change=[
                    "f_Herman should stop swinging widely across the strain series",
                    "orientation and lamellar support should line up before the trend is promoted",
                ],
            )
        )

    if temperature_fallback_active and (
        batch_conflict_triggered
        or "beamstop_or_low_q_contamination" in seen_names
        or "peak_window_mismatch" in seen_names
        or "idf_artifact_regular_spacing" in seen_names
        or "gamma_tangent_unstable" in seen_names
        or "multi_method_disagreement" in seen_names
    ):
        add(
            _make_symptom(
                "thickness_chain_unreliable",
                "error" if "beamstop_or_low_q_contamination" in seen_names else "warning",
                "Temperature thickness estimates are not trustworthy yet because the fallback summary and the frame evidence do not agree enough to support one clean chain.",
                target_params=["q_bragg_min", "q_bragg_max", "q_corr_min", "q_corr_max", "savgol_window"],
                confidence=0.93,
                evidence_keys=[
                    "signal_evidence.beam_stop_contaminated",
                    "signal_evidence.Q_star_valid",
                    "structure_evidence.calibrated_fallback_active",
                    "batch_evidence.batch_frames",
                    "batch_evidence.frame_condition_values",
                ],
                expected_evidence_change=[
                    "beam_stop_contaminated should clear or be isolated",
                    "batch_summary_conflicts_with_frame_evidence should disappear",
                    "L_bragg, L_corr_peak, and L_best should converge",
                ],
            )
        )

    return symptoms


def symptom_bridge_lines(symptom: dict[str, Any] | None) -> list[str]:
    if not isinstance(symptom, dict):
        return []

    name = _string(symptom.get("name")).lower()
    targets = _non_empty_strings(symptom.get("target_params") if isinstance(symptom.get("target_params"), list) else [])
    expected = _non_empty_strings(symptom.get("expected_evidence_change") if isinstance(symptom.get("expected_evidence_change"), list) else [])

    if name == "condition_axis_missing":
        lead = "series_condition_axis_missing -> stop tuning sequence plots until temperature/strain values are recovered"
    elif name == "condition_axis_unstable":
        lead = "condition_axis_unstable -> review recovered condition continuity before trusting sequence trends"
    elif name == "strain_axis_low_confidence":
        lead = "strain_axis_low_confidence -> review recovered strain continuity before trusting the sequence trend"
    elif name == "strain_sequence_nonmonotonic":
        lead = "strain_sequence_nonmonotonic -> re-order or split the strain series before trusting the trend"
    elif name == "strain_duplicate_frames":
        lead = "strain_duplicate_frames -> remove duplicated strain conditions before fitting the sequence"
    elif name == "batch_mixed_samples":
        lead = "batch_mixed_samples -> split or regroup frames before fitting one sequence trend"
    elif name == "temperature_calibration_fallback_active":
        lead = "temperature_calibration_fallback_active -> keep the raw frame evidence visible; this batch summary is fallback-derived"
    elif name == "diagnostic_lc_frames_present":
        lead = "diagnostic_lc_frames_present -> do not treat flagged lc values as final structure parameters before frame-level support recovers"
    elif name == "temperature_sequence_near_melting_window":
        lead = "temperature_sequence_near_melting_window -> interpret the affected frames as transition-sensitive, not as ordinary solid-state lc evolution"
    elif name == "lc_unreliable_without_melting_proof":
        lead = "lc_unreliable_without_melting_proof -> do not call this melting yet; structure extraction is unstable before the melting window is proven"
    elif name == "batch_summary_conflicts_with_frame_evidence":
        lead = "batch_summary_conflicts_with_frame_evidence -> compare raw_snapshot values against the batch summary before trusting the temperature trend"
    elif name == "thickness_chain_unreliable":
        lead = "thickness_chain_unreliable -> stabilize low-q and correlation windows before trusting lc / la / Xc"
    elif name == "idf_artifact_regular_spacing":
        lead = "correlation_curve_over_oscillating -> inspect low-q range, smoothing, and correlation window before trusting Lc/IDF plots"
    elif name == "peak_window_mismatch":
        lead = "peak_window_mismatch -> " + (" / ".join(targets) if targets else "inspect the Bragg window before trusting lamellar spacing")
    elif name == "beamstop_or_low_q_contamination":
        lead = "beamstop_or_low_q_contamination -> " + (" / ".join(targets) if targets else "stabilize low-q preprocessing")
    elif name == "low_q_void_dominant":
        lead = "low_q_void_dominant -> " + (" / ".join(targets) if targets else "separate void-dominated low-q evidence before trusting lamellar thickness")
    elif name == "strain_void_lamellar_conflict":
        lead = "strain_void_lamellar_conflict -> " + (" / ".join(targets) if targets else "separate void growth from lamellar comparison before the next round")
    elif name == "lamellar_anchor_lost_under_strain":
        lead = "lamellar_anchor_lost_under_strain -> " + (" / ".join(targets) if targets else "recover a stable long-period anchor before reading the strain trend")
    elif name == "qstar_rel_without_lamellar_support":
        lead = "qstar_rel_without_lamellar_support -> " + (" / ".join(targets) if targets else "do not use Q* normalization alone to argue for a lamellar trend")
    elif name == "orientation_shift_breaks_lamellar_comparison":
        lead = "orientation_shift_breaks_lamellar_comparison -> " + (" / ".join(targets) if targets else "compare orientation and lamellar support together before trusting the strain series")
    elif name == "gamma_tangent_unstable":
        lead = "gamma_tangent_unstable -> " + (" / ".join(targets) if targets else "stabilize correlation and tangent preprocessing")
    elif name == "multi_method_disagreement":
        lead = "multi_method_disagreement -> " + (" / ".join(targets) if targets else "reconcile Bragg and correlation windows")
    else:
        summary = _string(symptom.get("summary"))
        if targets:
            lead = f"{name} -> {' / '.join(targets)}"
        elif summary:
            lead = f"{name} -> {summary}"
        else:
            return []

    lines = [lead]
    lines.extend(f"expected evidence change: {item}" for item in expected)
    return lines
