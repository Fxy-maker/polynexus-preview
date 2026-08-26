"""Persistence helpers for GUI analysis runs.

This module keeps SampleDB-facing analysis run persistence out of the main
window. It intentionally has no Qt dependency so it can be tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..utils import detect_polymer_type


@dataclass(frozen=True)
class AnalysisRunPersistenceContext:
    technique: str = ""
    submodule: str = ""
    data_file: str = ""
    output_dir: str = ""
    project_label: str = ""
    current_sample_name: str = ""
    current_sample_id: str = ""
    current_batch_id: str = ""
    current_batch_label: str = ""
    ai_tuned: bool = False
    confirmed: bool = False
    history_context: dict[str, Any] = field(default_factory=dict)
    # Shared deterministic run produced by ComputeRunService.  The legacy
    # result remains the display-compatible adapter, while this projection is
    # the canonical persistence contract for new GUI runs.
    compute_run: Any = None


def to_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return to_jsonable(to_dict())
        except Exception:
            pass
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "tolist"):
        try:
            return to_jsonable(value.tolist())
        except Exception:
            pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def result_payload(result) -> dict[str, Any]:
    if isinstance(result, dict):
        payload = to_jsonable(result)
    elif hasattr(result, "to_dict"):
        payload = to_jsonable(result.to_dict())
    else:
        payload = to_jsonable(getattr(result, "__dict__", {}))
    return payload if isinstance(payload, dict) else {}


def extract_result_r2(payload: dict[str, Any]) -> float:
    candidates = (
        payload.get("r2"),
        payload.get("r_squared"),
        payload.get("R2"),
    )
    parameters = payload.get("parameters")
    if isinstance(parameters, dict):
        candidates += (
            parameters.get("r2"),
            parameters.get("r_squared"),
            parameters.get("R2"),
        )
    for candidate in candidates:
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue
    return float("nan")


def _metadata_polymer_name(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return ""
    return str(metadata.get("polymer_name") or "").strip()


def _resolve_polymer_name(payload: dict[str, Any], context: AnalysisRunPersistenceContext, data_file: Path | None) -> str:
    if context.current_sample_name.strip():
        return context.current_sample_name.strip()
    metadata_name = _metadata_polymer_name(payload)
    if metadata_name:
        return metadata_name
    if context.project_label.strip():
        return context.project_label.strip()
    if data_file is not None:
        return data_file.stem
    return (context.technique or "unknown").upper()


def _resolve_sample_id(db, polymer_name: str, technique: str, resolved_data_file: str) -> str:
    existing_sample = db.find_sample_by_name(polymer_name)
    if existing_sample is not None:
        return existing_sample.get("id", "")
    return db.create_sample(
        polymer_name,
        tags=["gui_analysis", technique],
        metadata={
            "source": "gui_analysis",
            "data_file": resolved_data_file,
        },
        temp=False,
    )


def _resolve_batch_id(
    db,
    sample_id: str,
    batch_label: str,
    technique: str,
    submodule: str,
    resolved_data_file: str,
    context: AnalysisRunPersistenceContext,
) -> str:
    existing_batch = None
    current_batch_id = context.current_batch_id.strip()
    if current_batch_id:
        current_batch = db.get_batch(current_batch_id)
        if isinstance(current_batch, dict) and str(current_batch.get("sample_id", "") or "").strip() == sample_id:
            existing_batch = current_batch
    if existing_batch is None:
        existing_batch = db.find_batch_for_source(
            sample_id,
            batch_label,
            technique=technique,
            file_path=resolved_data_file,
        )
    if existing_batch is not None:
        return existing_batch.get("id", "")

    condition_values = {
        "technique": technique,
        "submodule": submodule,
    }
    if context.current_sample_id:
        condition_values["sample_id"] = str(context.current_sample_id)
    if context.current_batch_id:
        condition_values["batch_id"] = str(context.current_batch_id)
    if context.current_sample_name:
        condition_values["sample_name"] = str(context.current_sample_name)
    if context.current_batch_label:
        condition_values["batch_label"] = str(context.current_batch_label)

    return db.create_batch(
        sample_id,
        label=batch_label,
        instrument="PolyNexus GUI",
        condition_type="analysis",
        condition_values=condition_values,
    )


def _ensure_data_file(db, batch_id: str, data_file: Path | None, resolved_data_file: str, technique: str, submodule: str) -> None:
    if data_file is None:
        return
    existing_files = db.get_data_files(batch_id)
    has_file = any(
        str(item.get("file_path", "")).strip() == resolved_data_file
        and str(item.get("technique", "")).strip().lower() == technique.lower()
        for item in existing_files
    )
    if has_file:
        return
    db.add_data_file(
        batch_id,
        resolved_data_file,
        technique,
        submodule=submodule,
        file_type=data_file.suffix.lower().lstrip("."),
        import_order=len(existing_files),
    )


def persist_analysis_run(db, result, context: AnalysisRunPersistenceContext) -> str:
    payload = result_payload(result)
    analysis_evidence = (
        payload.get("analysis_evidence")
        if isinstance(payload.get("analysis_evidence"), dict)
        else {}
    )

    technique = str(payload.get("technique") or context.technique or "unknown")
    submodule = str(context.submodule or "")
    data_file = Path(context.data_file) if context.data_file else None
    resolved_data_file = str(data_file.resolve()) if data_file is not None else ""
    polymer_name = _resolve_polymer_name(payload, context, data_file)

    sample_id = _resolve_sample_id(db, polymer_name, technique, resolved_data_file)
    batch_label = data_file.stem if data_file is not None else polymer_name
    batch_id = _resolve_batch_id(
        db,
        sample_id,
        batch_label,
        technique,
        submodule,
        resolved_data_file,
        context,
    )
    _ensure_data_file(db, batch_id, data_file, resolved_data_file, technique, submodule)

    parameters = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    parameters = dict(parameters)
    polymer_type = str(parameters.get("polymer_type") or "").strip()
    if not polymer_type:
        polymer_type = detect_polymer_type(polymer_name)
    parameters["polymer_type"] = polymer_type

    summary = {
        "technique": technique,
        "submodule": submodule,
        "data_file": resolved_data_file,
        "project_label": context.project_label.strip(),
        "sample_id": str(context.current_sample_id or ""),
        "sample_name": polymer_name,
        "batch_id": str(context.current_batch_id or ""),
        "batch_label": str(context.current_batch_label or ""),
        "status": "completed",
        "result": payload,
        "r2": extract_result_r2(payload),
        "polymer_type": polymer_type,
        "ai_tuned": bool(context.ai_tuned),
        "result_origin": "controlled_optimization_rerun" if bool(context.ai_tuned) else "manual_run",
        "confirmed": bool(context.confirmed),
        "history_context": to_jsonable(context.history_context),
    }
    if context.compute_run is not None:
        compute_run_payload = to_jsonable(context.compute_run)
        if isinstance(compute_run_payload, dict):
            summary["compute_run"] = compute_run_payload

    return db.create_analysis_run(
        batch_id,
        technique,
        submodule=submodule,
        parameters=to_jsonable(parameters),
        results_summary=to_jsonable(summary),
        analysis_evidence=to_jsonable(analysis_evidence),
        output_dir=context.output_dir,
        ai_tuned=bool(context.ai_tuned),
        confirmed=bool(context.confirmed),
    )
