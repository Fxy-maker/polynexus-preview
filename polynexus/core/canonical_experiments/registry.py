"""Closed deterministic converter registry for project technique inputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .capabilities import CapabilityExecutor
from .dsc_isothermal import convert_mettler_isothermal_text
from .models import CanonicalExperiment, ConversionOutcome, ConversionRecord
from .one_dimensional import convert_one_dimensional_table


_STATIC_TEMPLATE_IDS = {
    "ir": "ir.spectrum.v1",
    "saxs": "saxs.profile.v1",
    "waxs": "waxs.profile.v1",
}
_GENERIC_TABLE_EXTENSIONS = frozenset({
    ".csv", ".tsv", ".txt", ".dat", ".asc", ".xy", ".chi",
    ".xls", ".xlsx", ".xlsm",
})
_GENERIC_TECHNIQUES = frozenset({"ir", "saxs", "waxs"})


class CanonicalConverterRegistry:
    """Resolve only registered source-to-template conversions."""

    def convert_path(
        self,
        path: str | Path,
        *,
        technique: str,
        source_artifact_id: str,
    ) -> ConversionOutcome:
        source = Path(path)
        normalized_technique = str(technique).lower()
        if normalized_technique == "dsc":
            try:
                text = source.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return self._blocked(normalized_technique, source_artifact_id, "canonical_source_unreadable")
            return convert_mettler_isothermal_text(
                text,
                source_artifact_id=source_artifact_id,
                template_id="thermal_program.v1",
            )
        if (
            normalized_technique in _GENERIC_TECHNIQUES
            and source.is_file()
            and source.suffix.casefold() in _GENERIC_TABLE_EXTENSIONS
        ):
            return convert_one_dimensional_table(
                source,
                technique=normalized_technique,
                source_artifact_id=source_artifact_id,
            )
        template_id = _STATIC_TEMPLATE_IDS.get(normalized_technique)
        if template_id is None:
            return self._blocked(normalized_technique, source_artifact_id, "canonical_converter_unregistered")
        try:
            source_sha256 = self._source_sha256(source)
        except OSError:
            return self._blocked(normalized_technique, source_artifact_id, "canonical_source_unreadable")
        record = ConversionRecord.create(
            conversion_id=f"raw-file-envelope.{normalized_technique}.v1",
            source_artifact_id=source_artifact_id,
            observed_columns=("source_bytes",),
            extracted_segments=({"role": "provider_input", "sha256": source_sha256},),
        )
        template = CanonicalExperiment.create(
            template_id=template_id,
            source_artifact_id=source_artifact_id,
            payload={
                "source_sha256": source_sha256,
                "format": "directory" if source.is_dir() else source.suffix.lower().lstrip("."),
            },
            conversion_record=record,
        )
        return ConversionOutcome(status="ready", record=record, template=template)

    def replay_path(
        self,
        path: str | Path,
        *,
        technique: str,
        source_artifact_id: str,
    ) -> ConversionOutcome:
        """Recreate a template from a source already bound by a recipe."""
        return self.convert_path(path, technique=technique, source_artifact_id=source_artifact_id)

    @staticmethod
    def execute_capabilities(template: CanonicalExperiment):
        """Execute the finite generic capabilities for a ready template."""

        return CapabilityExecutor().execute(template)

    @staticmethod
    def _blocked(technique: str, source_artifact_id: str, reason: str) -> ConversionOutcome:
        record = ConversionRecord.create(
            conversion_id=f"unregistered.{technique or 'unknown'}.v1",
            source_artifact_id=source_artifact_id,
            reason_codes=(reason,),
        )
        return ConversionOutcome(status="blocked", record=record, reason_codes=(reason,))

    @staticmethod
    def _source_sha256(source: Path) -> str:
        if source.is_file():
            return hashlib.sha256(source.read_bytes()).hexdigest()
        if not source.is_dir():
            raise OSError("source does not exist")
        entries: list[dict[str, str]] = []
        for candidate in sorted(source.rglob("*"), key=lambda value: value.relative_to(source).as_posix()):
            if candidate.is_symlink() or not candidate.is_file():
                raise OSError("directory contains unsupported entry")
            entries.append({
                "path": candidate.relative_to(source).as_posix(),
                "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
            })
        if not entries:
            raise OSError("directory contains no files")
        return hashlib.sha256(
            json.dumps(
                {"kind": "directory_manifest", "entries": entries},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()


_DEFAULT_REGISTRY = CanonicalConverterRegistry()


def default_converter_registry() -> CanonicalConverterRegistry:
    """Return the immutable process-wide registry of supported conversions."""
    return _DEFAULT_REGISTRY


__all__ = ["CanonicalConverterRegistry", "default_converter_registry"]
