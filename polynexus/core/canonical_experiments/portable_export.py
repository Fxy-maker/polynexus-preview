"""Source-bound DTO for vendor-file portable exports."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import stat


MAX_EXPORT_BYTES = 1 * 1024 * 1024 * 1024
_SUPPORTED_EXPORTS = frozenset({".csv", ".tsv", ".txt", ".dat", ".asc", ".xy", ".chi", ".xls", ".xlsx", ".xlsm", ".ods"})


@dataclass(frozen=True)
class PortableExportBinding:
    """A hash-bound relationship between an opaque raw file and its export."""

    raw_source_path: str
    raw_source_sha256: str
    export_path: str
    export_sha256: str
    export_format: str
    exporter: str

    @classmethod
    def create(
        cls,
        raw_source: str | Path,
        export_path: str | Path,
        *,
        exporter: str,
    ) -> "PortableExportBinding":
        raw = _validated_path(raw_source, "raw source", allow_directory=True)
        export = _validated_path(export_path, "portable export", allow_directory=False)
        if export.suffix.casefold() not in _SUPPORTED_EXPORTS:
            raise ValueError("portable export format is not supported")
        exporter_name = str(exporter).strip()
        if not exporter_name:
            raise ValueError("exporter must be nonempty")
        return cls(
            raw_source_path=str(raw),
            raw_source_sha256=_sha256(raw),
            export_path=str(export),
            export_sha256=_sha256(export),
            export_format=export.suffix.casefold().lstrip("."),
            exporter=exporter_name,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "raw_source_path": self.raw_source_path,
            "raw_source_sha256": self.raw_source_sha256,
            "export_path": self.export_path,
            "export_sha256": self.export_sha256,
            "export_format": self.export_format,
            "exporter": self.exporter,
        }


def _validated_path(value: str | Path, label: str, *, allow_directory: bool) -> Path:
    source = Path(value).expanduser()
    try:
        info = source.lstat()
    except OSError as exc:
        raise ValueError(f"{label} is unreadable") from exc
    if stat.S_ISLNK(info.st_mode):
        raise ValueError(f"{label} must not be a symlink")
    resolved = source.resolve(strict=True)
    if resolved.is_dir() and not allow_directory:
        raise ValueError(f"{label} must be a file")
    if not resolved.is_file() and not resolved.is_dir():
        raise ValueError(f"{label} is not a regular file or directory")
    if resolved.is_file() and resolved.stat().st_size > MAX_EXPORT_BYTES:
        raise ValueError(f"{label} exceeds the bounded size")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    for child in sorted(path.rglob("*"), key=lambda item: str(item).casefold()):
        if child.is_file():
            digest.update(str(child.relative_to(path)).replace("\\", "/").encode("utf-8"))
            with child.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
    return digest.hexdigest()


__all__ = ["MAX_EXPORT_BYTES", "PortableExportBinding"]
