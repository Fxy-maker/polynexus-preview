"""Read-only artifact inspection for agent workflows."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re

from polynexus.core.engine import check_file_format

from polynexus.core.artifacts import directory_manifest_entries, directory_manifest_sha256, raw_artifact_id

from .models import InputArtifact


_EDF_REQUIRED_GEOMETRY = (
    "center_1",
    "center_2",
    "psize_1",
    "psize_2",
    "sampledistance",
    "wavelength",
)
# Directory identity inspection is shared by the Agent/Codex workflow and
# ComputeRun.  SAXS/WAXS directory providers already own frame discovery, so
# this boundary only hashes the directory and must not reject their input
# before the provider can run.  NMR remains outside this migration because it
# has no registered canonical directory converter yet.
_DIRECTORY_TECHNIQUES = frozenset({"dsc", "ir", "saxs", "waxs"})


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_id(
    path: Path,
    sha256: str | None,
    *,
    technique: str,
    format: str,
    observed_facts: dict[str, object] | None = None,
) -> str:
    return raw_artifact_id(
        path,
        technique=technique,
        format=format,
        sha256=sha256,
        observed_facts=observed_facts,
    )


def _directory_sha256(path: Path) -> tuple[str, int]:
    """Hash sorted relative paths and content hashes without copying raw data."""
    entries = directory_manifest_entries(path)
    # Keep the directory content hash byte-for-byte aligned with
    # ``RawArtifact.from_path`` so Agent recipes and ComputeRun share one
    # source identity across entry points.
    return directory_manifest_sha256(entries), len(entries)


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

    if source.is_dir():
        if technique_key not in _DIRECTORY_TECHNIQUES:
            return InputArtifact(
                artifact_id=_artifact_id(resolved, None, technique=technique_key, format="directory"), path=str(resolved), technique=technique_key,
                format="directory", sha256=None, inspection_status="blocked",
                reason_codes=("directory_unsupported",),
            )
        try:
            check_file_format(technique_key, str(source))
            source_hash, file_count = _directory_sha256(source)
        except ValueError:
            return InputArtifact(
                artifact_id=_artifact_id(resolved, None, technique=technique_key, format="directory"), path=str(resolved), technique=technique_key,
                format="directory", sha256=None, inspection_status="blocked",
                reason_codes=("format_unsupported",),
            )
        except OSError:
            return InputArtifact(
                artifact_id=_artifact_id(resolved, None, technique=technique_key, format="directory"), path=str(resolved), technique=technique_key,
                format="directory", sha256=None, inspection_status="blocked",
                reason_codes=("directory_unreadable_or_empty",),
            )
        return InputArtifact(
            artifact_id=_artifact_id(resolved, source_hash, technique=technique_key, format="directory"), path=str(resolved), technique=technique_key,
            format="directory", sha256=source_hash, header_facts={"directory_file_count": file_count},
        )

    if not source.is_file():
        return InputArtifact(
            artifact_id=_artifact_id(resolved, None, technique=technique_key, format=suffix),
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
            artifact_id=_artifact_id(resolved, None, technique=technique_key, format=suffix),
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
            artifact_id=_artifact_id(resolved, None, technique=technique_key, format=suffix),
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
                artifact_id=_artifact_id(resolved, source_hash, technique=technique_key, format=suffix),
                path=str(resolved),
                technique=technique_key,
                format=suffix,
                sha256=source_hash,
                inspection_status="blocked",
                reason_codes=("header_unreadable",),
            )

    return InputArtifact(
        artifact_id=_artifact_id(resolved, source_hash, technique=technique_key, format=suffix),
        path=str(resolved),
        technique=technique_key,
        format=suffix,
        sha256=source_hash,
        header_facts=header_facts,
        inspection_status=status,
        reason_codes=reasons,
    )
