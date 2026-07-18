"""Reproducible export bundle for all SAXS analysis modes."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

import numpy as np

from .saxs_config_binding import saxs_config_snapshot


@dataclass(frozen=True)
class SAXSExportBundle:
    """Status and index for one SAXS export operation."""

    status: str
    mode: str
    root: str
    files: dict[str, str]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "mode": self.mode,
            "root": self.root,
            "files": dict(self.files),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return _jsonable(value.to_dict())
        except Exception:
            pass
    return str(value)


def _write_json(root: Path, relative: str, payload: Any) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return relative.replace("\\", "/")


def _mode(engine: Any) -> str:
    if getattr(engine, "_temperature_result", None) is not None:
        return "temperature"
    if getattr(engine, "_strain_result", None) is not None:
        return "strain"
    experiment_type = str(
        getattr(getattr(engine, "cfg", None), "experiment_type", "") or ""
    ).strip().lower()
    if experiment_type in {"temperature", "cooling", "heating", "isothermal"}:
        return "temperature"
    if experiment_type == "strain":
        return "strain"
    return "static"


def _result_payload(result: Any) -> dict[str, Any]:
    if result is None:
        return {}
    to_dict = getattr(result, "to_dict", None)
    payload = to_dict() if callable(to_dict) else dict(getattr(result, "__dict__", {}) or {})
    return _jsonable(payload)


def _series_rows(series: Any) -> list[dict[str, Any]]:
    if series is None:
        return []
    to_dataframe = getattr(series, "to_dataframe", None)
    if not callable(to_dataframe):
        return []
    frame = to_dataframe()
    to_dict = getattr(frame, "to_dict", None)
    if not callable(to_dict):
        return []
    return _jsonable(to_dict(orient="records"))


def _parameter_payload(engine: Any, mode: str) -> dict[str, Any]:
    result = getattr(engine, "result", None)
    if mode == "temperature":
        rows = _series_rows(getattr(engine, "_temperature_result", None))
    elif mode == "strain":
        rows = _series_rows(getattr(engine, "_strain_result", None))
    else:
        rows = []
        analyses = list(getattr(engine, "_batch_results", ()) or ())
        if not analyses and getattr(engine, "_analysis", None) is not None:
            analyses = [engine._analysis]
        try:
            from .saxs_engine.saxs_output_helpers import _result_to_params_dict
        except ImportError:
            _result_to_params_dict = None
        for analysis in analyses:
            if _result_to_params_dict is not None:
                try:
                    rows.append(_result_to_params_dict(analysis))
                    continue
                except Exception:
                    pass
            rows.append(dict(getattr(analysis, "final_parameters", {}) or {}))
        if not rows and isinstance(getattr(result, "parameters", None), dict):
            rows = [dict(result.parameters)]
    return {
        "mode": mode,
        "summary": dict(getattr(result, "parameters", {}) or {}),
        "rows": rows,
        "quality_flags": dict(getattr(result, "quality_flags", {}) or {}),
        "validation_warnings": list(getattr(result, "validation_warnings", []) or []),
    }


def _profile_items(engine: Any) -> list[dict[str, Any]]:
    processed = list(getattr(engine, "_processed_list", ()) or ())
    q_list = list(getattr(engine, "_q_list", ()) or ())
    intensity_list = list(getattr(engine, "_I_list", ()) or ())
    file_list = list(getattr(engine, "_file_list", ()) or ())
    items: list[dict[str, Any]] = []

    if q_list and intensity_list:
        for index, (q_values, intensity) in enumerate(zip(q_list, intensity_list)):
            profile = processed[index] if index < len(processed) else None
            items.append(
                {
                    "index": index,
                    "label": Path(str(file_list[index])).stem if index < len(file_list) else f"frame_{index:03d}",
                    "q": q_values,
                    "raw": getattr(profile, "raw", intensity),
                    "corrected": getattr(profile, "corrected", None),
                    "normalized": getattr(profile, "normalized", None),
                    "smoothed": getattr(profile, "smoothed", None),
                    "provenance": getattr(profile, "provenance", {}) if profile is not None else {},
                    "quality_status": getattr(profile, "quality_status", "unknown") if profile is not None else "unknown",
                    "diagnostics": getattr(profile, "diagnostics", {}) if profile is not None else {},
                }
            )
        return items

    analyses = list(getattr(engine, "_batch_results", ()) or ())
    if not analyses and getattr(engine, "_analysis", None) is not None:
        analyses = [engine._analysis]
    for index, analysis in enumerate(analyses):
        q_values = getattr(analysis, "q", None)
        intensity = getattr(analysis, "I", None)
        if q_values is None or intensity is None:
            continue
        items.append(
            {
                "index": index,
                "label": getattr(analysis, "label", "") or f"frame_{index:03d}",
                "q": q_values,
                "raw": intensity,
                "corrected": None,
                "normalized": None,
                "smoothed": getattr(analysis, "I_smooth", None),
                "provenance": {},
                "quality_status": getattr(analysis, "quality_flag", "unknown"),
                "diagnostics": {},
            }
        )

    if not items:
        raw_data = getattr(getattr(engine, "result", None), "raw_data", {}) or {}
        if raw_data.get("q") is not None and raw_data.get("I") is not None:
            items.append(
                {
                    "index": 0,
                    "label": "frame_000",
                    "q": raw_data["q"],
                    "raw": raw_data["I"],
                    "corrected": raw_data.get("I_corrected"),
                    "normalized": raw_data.get("Iq_norm"),
                    "smoothed": raw_data.get("I_smooth"),
                    "provenance": {},
                    "quality_status": "unknown",
                    "diagnostics": {},
                }
            )
    return items


def _write_profiles(
    root: Path, items: list[dict[str, Any]]
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    files: dict[str, str] = {}
    provenance: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        relative = f"data/profiles/profile_{index:03d}.csv"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        q_values = np.asarray(item["q"], dtype=float).ravel()
        layers = {
            "I_raw_au": item.get("raw"),
            "I_corrected_au": item.get("corrected"),
            "I_normalized_au": item.get("normalized"),
            "I_smooth_au": item.get("smoothed"),
        }
        arrays = {
            key: (np.asarray(value, dtype=float).ravel() if value is not None else None)
            for key, value in layers.items()
        }
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["q_nm_inv", *layers])
            writer.writeheader()
            for row_index, q_value in enumerate(q_values):
                row: dict[str, Any] = {"q_nm_inv": q_value if np.isfinite(q_value) else ""}
                for key, values in arrays.items():
                    if values is None or row_index >= len(values):
                        row[key] = ""
                    else:
                        value = values[row_index]
                        row[key] = value if np.isfinite(value) else ""
                writer.writerow(row)
        files[f"profile_{index:03d}"] = relative
        provenance.append(
            {
                "index": index,
                "label": item.get("label", ""),
                "path": relative,
                "raw": {"available": item.get("raw") is not None, "source": "canonical.raw"},
                "effective": {
                    "available": item.get("smoothed") is not None
                    or item.get("normalized") is not None
                    or item.get("corrected") is not None,
                    "source": "canonical.smoothed_or_normalized_or_corrected",
                },
                "calibrated": {
                    "available": item.get("corrected") is not None,
                    "source": "canonical.corrected",
                },
                "quality_status": item.get("quality_status", "unknown"),
                "provenance": item.get("provenance", {}),
                "diagnostics": item.get("diagnostics", {}),
            }
        )
    return files, provenance


def _write_figure_index(root: Path, result: Any) -> tuple[str, str | None]:
    metadata = dict(getattr(result, "metadata", {}) or {})
    source_value = metadata.get("figure_manifest", "")
    source = Path(str(source_value)) if source_value else None
    copied = None
    resources: list[dict[str, Any]] = []
    manifest_status = "unavailable"
    if source is not None and source.exists():
        copied_path = root / "figures" / "figure_manifest.json"
        copied_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, copied_path)
        copied = "figures/figure_manifest.json"
        manifest_status = "copied"
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            for figure in payload.get("figures", []):
                if not isinstance(figure, dict):
                    continue
                paths = [figure.get("document", ""), *figure.get("data_sources", [])]
                paths.extend(dict(figure.get("assets", {})).values())
                for item in paths:
                    if not item:
                        continue
                    candidate = Path(str(item))
                    if not candidate.is_absolute():
                        candidate = source.parent / candidate
                    resources.append(
                        {
                            "figure_id": figure.get("figure_id", ""),
                            "source": str(candidate),
                            "exists": candidate.exists(),
                        }
                    )
        except (OSError, ValueError, TypeError):
            manifest_status = "copied_unreadable"
    index = {
        "status": manifest_status,
        "source_manifest": str(source) if source is not None else "",
        "copied_manifest": copied or "",
        "resources": resources,
    }
    relative = _write_json(root, "figures/index.json", index)
    return relative, copied


def _bundle_manifest(
    *,
    status: str,
    mode: str,
    root: Path,
    files: dict[str, str],
    warnings: list[str],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": status,
        "technique": "saxs",
        "mode": mode,
        "files": files,
        "warnings": warnings,
        "errors": errors,
        "root": str(root),
    }


def export_saxs_bundle(engine: Any, output_dir: str) -> SAXSExportBundle:
    """Write one reproducible SAXS export package for static/series modes."""
    root = Path(output_dir).resolve()
    mode = _mode(engine)
    files: dict[str, str] = {}
    warnings: list[str] = []
    errors: list[str] = []
    result = getattr(engine, "result", None)

    try:
        try:
            profile_items = _profile_items(engine)
        except Exception as exc:
            profile_items = []
            warnings.append(f"profile_collection_failed:{exc}")

        has_analysis = bool(
            getattr(engine, "_analysis", None)
            or getattr(engine, "_batch_results", None)
            or getattr(engine, "_temperature_result", None)
            or getattr(engine, "_strain_result", None)
            or profile_items
        )
        if not has_analysis:
            root.mkdir(parents=True, exist_ok=True)
            errors.append("no_analysis_result")
            files["bundle_manifest"] = "bundle_manifest.json"
            _write_json(root, "bundle_manifest.json", _bundle_manifest(
                status="empty", mode=mode, root=root, files=files,
                warnings=warnings, errors=errors,
            ))
            return SAXSExportBundle("empty", mode, str(root), files, tuple(warnings), tuple(errors))

        root.mkdir(parents=True, exist_ok=True)
        files["analysis_result"] = _write_json(root, "analysis_result.json", _result_payload(result))
        files["metadata"] = _write_json(root, "metadata.json", getattr(result, "metadata", {}))
        files["evidence"] = _write_json(root, "evidence.json", getattr(result, "analysis_evidence", {}))
        files["config_snapshot"] = _write_json(root, "config_snapshot.json", saxs_config_snapshot(getattr(engine, "cfg", None)))
        parameter_payload = _parameter_payload(engine, mode)
        files["parameters"] = _write_json(root, "parameters.json", parameter_payload)
        files["parameters_csv"] = "data/parameters.csv"
        parameter_rows = parameter_payload.get("rows", []) or [parameter_payload.get("summary", {})]
        parameters_path = root / files["parameters_csv"]
        parameters_path.parent.mkdir(parents=True, exist_ok=True)
        keys = sorted({str(key) for row in parameter_rows if isinstance(row, Mapping) for key in row})
        with parameters_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys or ["status"])
            writer.writeheader()
            for row in parameter_rows:
                data = row if isinstance(row, Mapping) else {}
                writer.writerow({key: _jsonable(data.get(key, "")) for key in writer.fieldnames})

        profile_files, profile_provenance = _write_profiles(root, profile_items)
        files.update(profile_files)
        result_parameters = dict(getattr(result, "parameters", {}) or {})
        provenance = {
            "raw": {"source": "canonical profile raw layer", "profiles": len(profile_provenance)},
            "effective": {"source": "canonical processed layer", "profiles": len(profile_provenance)},
            "calibrated": {
                "source": "canonical corrected layer",
                "available": any(item["calibrated"]["available"] for item in profile_provenance),
            },
            "fallback": result_parameters.get("fallback_provenance", {}),
            "diagnostic_only": result_parameters.get("diagnostic_only", {}),
            "profiles": profile_provenance,
        }
        files["provenance"] = _write_json(root, "provenance.json", provenance)
        figure_index, copied_manifest = _write_figure_index(root, result)
        files["figure_index"] = figure_index
        if copied_manifest:
            files["figure_manifest"] = copied_manifest
        elif getattr(result, "metadata", {}).get("figure_manifest"):
            warnings.append("figure_manifest_unavailable")
        files["bundle_manifest"] = "bundle_manifest.json"
        _write_json(root, "bundle_manifest.json", _bundle_manifest(
            status="ok", mode=mode, root=root, files=files,
            warnings=warnings, errors=errors,
        ))
        return SAXSExportBundle("ok", mode, str(root), files, tuple(warnings), tuple(errors))
    except Exception as exc:
        errors.append(f"export_failed:{exc}")
        try:
            root.mkdir(parents=True, exist_ok=True)
            files["bundle_manifest"] = "bundle_manifest.json"
            _write_json(root, "bundle_manifest.json", _bundle_manifest(
                status="failed", mode=mode, root=root, files=files,
                warnings=warnings, errors=errors,
            ))
        except Exception:
            pass
        return SAXSExportBundle("failed", mode, str(root), files, tuple(warnings), tuple(errors))


__all__ = ["SAXSExportBundle", "export_saxs_bundle"]
