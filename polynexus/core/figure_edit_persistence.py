"""Transactional persistence for the canonical Origin figure edit bundle."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from .figure_document import figure_document_path, normalize_figure_document
from .plot_edits import figure_state_key, figure_state_path


@dataclass(frozen=True)
class SaveBundleResult:
    ok: bool
    target_path: Path
    document_path: Path
    compatibility_path: Path | None
    error_code: str = ""
    message: str = ""


def _bundle_paths(target_path: str | Path) -> tuple[Path, Path, Path]:
    target = Path(target_path).resolve()
    return target, figure_document_path(str(target)), figure_state_path(str(target))


def _compatibility_document(
    target_path: Path,
    document_path: Path,
    compatibility_path: Path,
    legacy_style: dict | None,
    legacy_annotations: list[dict] | None,
) -> dict:
    data: dict = {"version": 1, "files": {}}
    if compatibility_path.exists():
        with compatibility_path.open("r", encoding="utf-8") as handle:
            existing = json.load(handle)
        if isinstance(existing, dict):
            data = deepcopy(existing)
    files = data.get("files")
    if not isinstance(files, dict):
        files = {}
        data["files"] = files
    key = figure_state_key(str(target_path))
    entry = files.get(key)
    if not isinstance(entry, dict):
        entry = {}
    entry["relative_path"] = key
    entry["source_path"] = str(target_path)
    entry["figure_document_path"] = str(document_path)
    if legacy_style is not None:
        entry["style"] = deepcopy(legacy_style)
    if legacy_annotations is not None:
        entry["annotations"] = deepcopy(legacy_annotations)
    files[key] = entry
    data["version"] = max(int(data.get("version", 1) or 1), 2)
    return data


def _write_temp(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_bytes(payload)
    return temporary


def _restore_previous(final_paths: list[Path], previous: dict[Path, bytes | None]) -> None:
    for path in final_paths:
        old = previous.get(path)
        try:
            if old is None:
                if path.exists():
                    path.unlink()
            else:
                path.write_bytes(old)
        except OSError:
            # Preserve the original error; a best-effort rollback is safer than
            # masking the save failure with cleanup noise.
            continue


def _save_bundle(
    target_path: str | Path,
    document: dict,
    rendered_bytes: bytes,
    legacy_style: dict | None,
    legacy_annotations: list[dict] | None,
) -> SaveBundleResult:
    target, document_path, compatibility_path = _bundle_paths(target_path)
    normalized = normalize_figure_document(document)
    rendered = bytes(rendered_bytes)
    document_bytes = json.dumps(
        normalized,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ).encode("utf-8")
    compatibility_bytes = json.dumps(
        _compatibility_document(
            target,
            document_path,
            compatibility_path,
            legacy_style,
            legacy_annotations,
        ),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ).encode("utf-8")

    temporary_paths: list[Path] = []
    final_paths = [target, document_path, compatibility_path]
    previous = {
        path: path.read_bytes() if path.exists() else None for path in final_paths
    }
    try:
        asset_temp = _write_temp(target, rendered)
        document_temp = _write_temp(document_path, document_bytes)
        compatibility_temp = _write_temp(compatibility_path, compatibility_bytes)
        temporary_paths.extend((asset_temp, document_temp, compatibility_temp))

        with document_temp.open("r", encoding="utf-8") as handle:
            json.load(handle)

        # Canonical files become durable before the compatibility sidecar is
        # published, so legacy readers never become the edit authority.
        asset_temp.replace(target)
        document_temp.replace(document_path)
        compatibility_temp.replace(compatibility_path)
        temporary_paths.clear()
    except Exception:
        _restore_previous(final_paths, previous)
        raise
    finally:
        for temporary in temporary_paths:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    return SaveBundleResult(
        ok=True,
        target_path=target,
        document_path=document_path,
        compatibility_path=compatibility_path,
    )


def save_edit_bundle(
    target_path: str | Path,
    document: dict,
    rendered_bytes: bytes,
    legacy_style: dict | None = None,
    legacy_annotations: list[dict] | None = None,
) -> SaveBundleResult:
    """Save an asset, canonical document, and compatibility sidecar together."""

    target, document_path, compatibility_path = _bundle_paths(target_path)
    try:
        return _save_bundle(
            target,
            document,
            rendered_bytes,
            legacy_style,
            legacy_annotations,
        )
    except Exception as exc:
        return SaveBundleResult(
            ok=False,
            target_path=target,
            document_path=document_path,
            compatibility_path=compatibility_path,
            error_code="save_failed",
            message=str(exc),
        )


def try_save_edit_bundle(
    target_path: str | Path,
    document: dict,
    rendered_bytes: bytes,
    legacy_style: dict | None = None,
    legacy_annotations: list[dict] | None = None,
) -> SaveBundleResult:
    """Non-raising save entry point for UI callers."""

    return save_edit_bundle(
        target_path,
        document,
        rendered_bytes,
        legacy_style,
        legacy_annotations,
    )


__all__ = ["SaveBundleResult", "save_edit_bundle", "try_save_edit_bundle"]
