"""Deterministic, bounded raw-format inspection.

This module only identifies containers and registered reader capabilities. It
does not execute plugins or claim that scientific columns have been mapped.
"""

from __future__ import annotations

from collections.abc import Iterable
import hashlib
from pathlib import Path
import zipfile

from ..artifacts import directory_manifest_entries, directory_manifest_sha256
from ...readers.ta_dma_reader import looks_like_ta_dma
from .models import FormatInspection, FormatPluginDescriptor


_TABLE_EXTENSIONS = (".csv", ".tsv", ".txt", ".dat", ".asc", ".xy", ".chi", ".xls", ".xlsx", ".xlsm")
_IMAGE_EXTENSIONS = (".edf", ".cbf", ".tif", ".tiff", ".h5", ".hdf5", ".nxs")


class FormatPluginRegistry:
    """Closed registry of declarative reader descriptors."""

    def __init__(self, descriptors: Iterable[FormatPluginDescriptor] = ()) -> None:
        values = tuple(descriptors)
        ids = [item.plugin_id for item in values]
        if len(set(ids)) != len(ids):
            raise ValueError("format plugin IDs must be unique")
        self._descriptors = values

    @property
    def descriptors(self) -> tuple[FormatPluginDescriptor, ...]:
        return self._descriptors

    def with_plugin(self, descriptor: FormatPluginDescriptor) -> "FormatPluginRegistry":
        """Return a registry with one explicitly trusted descriptor added.

        Plugin discovery/loading is deliberately outside this API. Callers
        must construct a validated descriptor in application code; no module
        path, entry point, or user-supplied executable is imported here.
        """

        if not isinstance(descriptor, FormatPluginDescriptor):
            raise TypeError("format plugin registry accepts FormatPluginDescriptor values")
        if self.descriptor(descriptor.plugin_id) is not None:
            raise ValueError(f"format plugin ID already registered: {descriptor.plugin_id}")
        return FormatPluginRegistry((*self._descriptors, descriptor))

    def descriptor(self, plugin_id: str) -> FormatPluginDescriptor | None:
        return next((item for item in self._descriptors if item.plugin_id == plugin_id), None)

    def inspect(
        self,
        path: str | Path,
        *,
        technique: str = "unknown",
        source_sha256: str | None = None,
    ) -> FormatInspection:
        source = Path(path).expanduser()
        declared = _normalize_technique(technique)
        extension = "" if source.is_dir() else source.suffix.casefold()
        source_kind = "directory" if source.is_dir() else "file"
        source_sha = (
            str(source_sha256)
            if isinstance(source_sha256, str)
            else _content_hash(source)
        )
        facts: dict[str, object] = {}
        plugin: FormatPluginDescriptor | None = None
        reasons: tuple[str, ...] = ()
        status = "unknown"
        next_actions: tuple[str, ...] = ("select_reader_plugin", "export_portable_table")

        if source.is_dir():
            if _looks_like_bruker(source):
                plugin = self.descriptor("bruker.nmr.v1")
                facts.update(
                    {
                        "fid_present": (source / "fid").is_file(),
                        "ser_present": (source / "ser").is_file(),
                        "acquisition_metadata_present": any(
                            (source / name).is_file() for name in ("acqu", "acqus")
                        ),
                    }
                )
            else:
                facts["file_count"] = sum(1 for item in source.iterdir() if item.is_file())
        else:
            plugin, probe_facts = self._match_file(source, extension)
            facts.update(probe_facts)

        if plugin is not None:
            if plugin.plugin_id == "vendor.dma.001.v1" and facts.get("ta_dma_probe") == "incomplete_signature":
                status = "needs_reader"
                reasons = ("format_signature_unrecognized",)
                next_actions = ("provide_verified_ta_dma_export", "export_portable_table")
            elif plugin.reader_availability == "available":
                status = "ready"
                next_actions = ()
            elif plugin.reader_availability == "external":
                status = "needs_reader"
                reasons = ("external_reader_required",)
                next_actions = plugin.next_actions
            else:
                status = "needs_reader"
                reasons = ("format_reader_missing",)
                next_actions = plugin.next_actions
            if plugin.plugin_id == "portable.ods.v1" and declared != "unknown":
                reasons = tuple(dict.fromkeys((*reasons, "technique_confirmation_required")))
                next_actions = ("confirm_technique",) + next_actions
            if declared not in plugin.techniques and declared != "unknown":
                # A technique mismatch is a scientific-mapping question, but
                # it must not weaken a stricter missing-reader boundary.  In
                # particular, an opaque Origin or vendor file labelled with
                # the wrong technique still has no safe route to a provider.
                reasons = tuple(dict.fromkeys((*reasons, "technique_confirmation_required")))
                next_actions = ("confirm_technique",) + plugin.next_actions
                if plugin.reader_availability == "available":
                    status = "needs_mapping"
        inspection = FormatInspection.create(
            source_sha256=source_sha,
            source_kind=source_kind,
            declared_technique=declared,
            extension=extension,
            container_kind=plugin.container_kind if plugin is not None else _container_kind(source, extension),
            status=status,
            plugin_id=plugin.plugin_id if plugin is not None else None,
            reader_availability=plugin.reader_availability if plugin is not None else "unknown",
            canonical_conversion=plugin.canonical_conversion if plugin is not None else "unavailable",
            scientific_mapping="unassessed",
            observed_facts=facts,
            reason_codes=reasons,
            next_actions=next_actions,
        )
        return inspection

    def _match_file(
        self, source: Path, extension: str
    ) -> tuple[FormatPluginDescriptor | None, dict[str, object]]:
        facts: dict[str, object] = {}
        try:
            prefix = source.read_bytes()[:4096]
        except OSError:
            return None, {"probe_status": "unreadable"}
        facts["probe_bytes"] = len(prefix)
        for descriptor in self._descriptors:
            if extension not in descriptor.extensions:
                continue
            if descriptor.plugin_id == "netzsch.dsc.container.v1" and not prefix.startswith(b"PK"):
                # The extension is vendor-specific.  Preserve the declared
                # missing-reader route even for a truncated/corrupt container
                # instead of falling through to an executable legacy path.
                facts["archive_probe"] = "not_zip_signature"
            if descriptor.plugin_id == "netzsch.ta.v1" and b"Netzsch TA file" not in prefix:
                continue
            if descriptor.plugin_id == "vendor.dma.001.v1" and not looks_like_ta_dma(prefix):
                if b"CLOSED" not in prefix.upper() and not prefix.startswith((b"\xff\xfe", b"\xfe\xff")):
                    continue
                facts["ta_dma_probe"] = "incomplete_signature"
            if descriptor.plugin_id == "origin.project.v1" and not prefix.startswith(b"CPYUA"):
                continue
            if descriptor.plugin_id == "rigaku.raw.v1" and not prefix.startswith(b"RAW1.01\x00"):
                continue
            if descriptor.plugin_id == "portable.ods.v1" and not _is_ods(source, prefix):
                continue
            if descriptor.plugin_id == "detector.image.v1" and extension in {".tif", ".tiff"} and not (
                prefix.startswith((b"II*\x00", b"MM\x00*"))
            ):
                continue
            if descriptor.plugin_id == "portable.table.v1" and extension in {".csv", ".tsv", ".txt", ".dat", ".asc", ".xy", ".chi"}:
                facts["text_probe"] = prefix.decode("utf-8", errors="replace")[:512]
            if descriptor.plugin_id == "netzsch.dsc.container.v1":
                try:
                    with zipfile.ZipFile(source) as archive:
                        members = archive.infolist()[:256]
                    facts["archive_member_count"] = len(members)
                    facts["stream_table_count"] = sum(item.filename.casefold().endswith(".table") for item in members)
                except (OSError, zipfile.BadZipFile):
                    facts["archive_probe"] = "invalid"
            return descriptor, facts
        return None, facts


def _content_hash(source: Path) -> str:
    try:
        if source.is_dir():
            return directory_manifest_sha256(directory_manifest_entries(source))
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return ""


def _normalize_technique(value: object) -> str:
    normalized = str(value or "unknown").strip().casefold() or "unknown"
    return {"ftir": "ir", "gpc": "sec", "sec/gpc": "sec"}.get(normalized, normalized)


def _looks_like_bruker(source: Path) -> bool:
    return any((source / name).is_file() for name in ("fid", "ser", "acqu", "acqus"))


def _is_ods(source: Path, prefix: bytes) -> bool:
    if not prefix.startswith(b"PK"):
        return False
    try:
        with zipfile.ZipFile(source) as archive:
            return archive.read("mimetype")[:128] == b"application/vnd.oasis.opendocument.spreadsheet"
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def _container_kind(source: Path, extension: str) -> str:
    if source.is_dir():
        return "directory"
    if extension in _TABLE_EXTENSIONS:
        return "delimited_or_workbook_table"
    if extension in _IMAGE_EXTENSIONS:
        return "detector_or_hdf5_image"
    return "opaque_file"


_DEFAULT_REGISTRY = FormatPluginRegistry(
    (
        FormatPluginDescriptor(
            plugin_id="portable.table.v1", version="1", container_kind="delimited_table",
            techniques=("dsc", "ir", "nmr", "saxs", "waxs", "tga", "dma", "rheology", "sec", "mechanics"),
            extensions=_TABLE_EXTENSIONS, reader_availability="available", canonical_conversion="candidate",
        ),
        FormatPluginDescriptor(
            plugin_id="portable.ods.v1", version="1", container_kind="open_document_spreadsheet",
            techniques=("dsc", "ir", "nmr", "saxs", "waxs", "tga", "dma", "rheology", "sec", "mechanics", "unknown"),
            extensions=(".ods",), reader_availability="external",
            canonical_conversion="candidate", next_actions=("install_or_enable_reader:portable.ods.v1", "export_portable_table"),
        ),
        FormatPluginDescriptor(
            plugin_id="detector.image.v1", version="1", container_kind="detector_image",
            techniques=("saxs", "waxs"), extensions=_IMAGE_EXTENSIONS, reader_availability="available", canonical_conversion="candidate",
        ),
        FormatPluginDescriptor(
            plugin_id="bruker.nmr.v1", version="1", container_kind="bruker_directory",
            techniques=("nmr",), extensions=(), reader_availability="available", canonical_conversion="candidate",
        ),
        FormatPluginDescriptor(
            plugin_id="rigaku.raw.v1", version="1", container_kind="rigaku_raw_binary",
            techniques=("waxs", "saxs"), extensions=(".raw",), reader_availability="available", canonical_conversion="candidate",
        ),
        FormatPluginDescriptor(
            plugin_id="netzsch.dsc.container.v1", version="1", container_kind="netzsch_dsc_container",
            techniques=("dsc",), extensions=(".ngb-sd7",), reader_availability="missing", canonical_conversion="unavailable",
            next_actions=("install_or_enable_reader:netzsch.dsc.container.v1", "export_portable_table"),
        ),
        FormatPluginDescriptor(
            plugin_id="netzsch.ta.v1", version="1", container_kind="netzsch_ta_binary",
            techniques=("tga",), extensions=(".ngb-ds1",), reader_availability="missing", canonical_conversion="unavailable",
            next_actions=("install_or_enable_reader:netzsch.ta.v1", "export_portable_table"),
        ),
        FormatPluginDescriptor(
            plugin_id="vendor.dma.001.v1", version="1", container_kind="vendor_dma_binary",
            techniques=("dma",), extensions=(".001", ".002", ".003", ".004", ".005"), reader_availability="available", canonical_conversion="candidate",
            next_actions=(), description="Bounded TA Instruments DMA Q800 binary export reader for the verified CLOSED/Nsig/SigN layout.",
        ),
        FormatPluginDescriptor(
            plugin_id="origin.project.v1", version="1", container_kind="origin_project",
            techniques=("sec", "mechanics", "rheology", "unknown"), extensions=(".opju",), reader_availability="external", canonical_conversion="candidate",
            next_actions=("install_or_enable_reader:origin.project.v1", "export_portable_table"),
        ),
    )
)


def default_format_registry() -> FormatPluginRegistry:
    return _DEFAULT_REGISTRY


def inspect_format(
    path: str | Path,
    *,
    technique: str = "unknown",
    source_sha256: str | None = None,
) -> FormatInspection:
    return _DEFAULT_REGISTRY.inspect(
        path,
        technique=technique,
        source_sha256=source_sha256,
    )


__all__ = ["FormatPluginRegistry", "default_format_registry", "inspect_format"]
