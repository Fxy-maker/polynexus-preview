"""Read-only artifact inspection for agent workflows."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re

from polynexus.core.engine import check_file_format

from .models import InputArtifact, canonical_json


_EDF_REQUIRED_GEOMETRY = (
    "center_1",
    "center_2",
    "psize_1",
    "psize_2",
    "sampledistance",
    "wavelength",
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_id(path: Path, sha256: str | None) -> str:
    return hashlib.sha256(
        canonical_json({"path": str(path.resolve()), "sha256": sha256}).encode("utf-8")
    ).hexdigest()


def _edf_header_facts(path: Path) -> tuple[dict[str, object], tuple[str, ...]]:
    header = path.read_bytes()[:16384].decode("latin-1", errors="replace")
    values: dict[str, float] = {}
    for key, value in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;\r\n}]+)", header):
        try:
            values[key.lower()] = float(value.strip())
        except ValueError:
            continue

    complete_geometry = all(
        key in values and math.isfinite(values[key]) and values[key] > 0
        for key in _EDF_REQUIRED_GEOMETRY
    )
    facts: dict[str, object] = {
        "header_source": "edf",
        "geometry_calibrated": complete_geometry,
    }
    if complete_geometry:
        facts.update(
            {
                "beam_center_px": [values["center_1"], values["center_2"]],
                "pixel_size_m": [values["psize_1"], values["psize_2"]],
                "sample_distance_m": values["sampledistance"],
                "wavelength_m": values["wavelength"],
            }
        )
    reasons = ("background_unknown",) if complete_geometry else ("geometry_incomplete",)
    return facts, reasons


def inspect_artifact(path: str | Path, *, technique: str = "unknown") -> InputArtifact:
    """Return direct file/header facts as a structured, non-throwing artifact."""
    source = Path(path).expanduser()
    technique_key = str(technique or "unknown").lower()
    suffix = source.suffix.lower().lstrip(".")
    resolved = source.resolve()

    if not source.is_file():
        return InputArtifact(
            artifact_id=_artifact_id(resolved, None),
            path=str(resolved),
            technique=technique_key,
            format=suffix,
            sha256=None,
            inspection_status="blocked",
            reason_codes=("file_missing",),
        )

    try:
        if technique_key != "unknown":
            check_file_format(technique_key, str(source))
    except ValueError:
        return InputArtifact(
            artifact_id=_artifact_id(resolved, None),
            path=str(resolved),
            technique=technique_key,
            format=suffix,
            sha256=None,
            inspection_status="blocked",
            reason_codes=("format_unsupported",),
        )

    try:
        source_hash = _file_sha256(source)
    except OSError:
        return InputArtifact(
            artifact_id=_artifact_id(resolved, None),
            path=str(resolved),
            technique=technique_key,
            format=suffix,
            sha256=None,
            inspection_status="blocked",
            reason_codes=("file_unreadable",),
        )

    header_facts: dict[str, object] = {}
    reasons: tuple[str, ...] = ()
    status = "ready"
    if suffix == "edf":
        try:
            header_facts, reasons = _edf_header_facts(source)
            status = "review_required"
        except OSError:
            return InputArtifact(
                artifact_id=_artifact_id(resolved, source_hash),
                path=str(resolved),
                technique=technique_key,
                format=suffix,
                sha256=source_hash,
                inspection_status="blocked",
                reason_codes=("header_unreadable",),
            )

    return InputArtifact(
        artifact_id=_artifact_id(resolved, source_hash),
        path=str(resolved),
        technique=technique_key,
        format=suffix,
        sha256=source_hash,
        header_facts=header_facts,
        inspection_status=status,
        reason_codes=reasons,
    )
