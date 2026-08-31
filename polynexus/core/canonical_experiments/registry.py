"""Closed deterministic converter registry for project technique inputs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping, Sequence

from ..artifacts import directory_manifest_entries, directory_manifest_sha256
from .capabilities import CapabilityExecutor
from .detector_image import convert_detector_image
from .dsc_isothermal import convert_mettler_isothermal_text
from .ir_temperature_series import build_ir_temperature_series_template
from .models import CanonicalExperiment, ConversionOutcome, ConversionRecord, MappingProposal
from .one_dimensional import convert_one_dimensional_table
from .nd_adapters import (
    DataBlockAdapterResult,
    adapt_conversion_outcome,
    adapt_detector_image,
    adapt_ir_temperature_series,
    adapt_nmr_fid,
)


_STATIC_TEMPLATE_IDS = {
    "ir": "ir.spectrum.v1",
    "saxs": "saxs.profile.v1",
    "waxs": "waxs.profile.v1",
}
_GENERIC_TABLE_EXTENSIONS = frozenset({
    ".csv", ".tsv", ".txt", ".dat", ".asc", ".xy", ".chi",
    ".xls", ".xlsx", ".xlsm",
})
_GENERIC_TECHNIQUES = frozenset({"ir", "nmr", "saxs", "waxs"})
_FID_EXTENSIONS = frozenset({".fid", ".ser"})
_IMAGE_EXTENSIONS = frozenset({".edf", ".cbf", ".tif", ".tiff", ".h5", ".hdf5", ".nxs"})


class CanonicalConverterRegistry:
    """Resolve only registered source-to-template conversions."""

    def convert_path(
        self,
        path: str | Path,
        *,
        technique: str,
        source_artifact_id: str,
        mapping_proposal: MappingProposal | None = None,
    ) -> ConversionOutcome:
        source = Path(path)
        normalized_technique = _normalize_technique(technique)
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
        if normalized_technique == "ir" and source.is_dir():
            frame_paths = tuple(
                sorted(
                    (
                        item
                        for item in source.iterdir()
                        if item.is_file() and item.suffix.casefold() in _GENERIC_TABLE_EXTENSIONS
                    ),
                    key=lambda item: item.name.casefold(),
                )
            )
            if len(frame_paths) >= 2:
                return build_ir_temperature_series_template(
                    frame_paths,
                    source_artifact_id=source_artifact_id,
                )
        if (
            normalized_technique in {"saxs", "waxs"}
            and source.is_file()
            and source.suffix.casefold() in {".edf", ".cbf", ".tif", ".tiff", ".h5", ".hdf5", ".nxs"}
        ):
            return convert_detector_image(
                source,
                technique=normalized_technique,
                source_artifact_id=source_artifact_id,
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
                mapping_proposal=mapping_proposal,
            )
        template_id = _STATIC_TEMPLATE_IDS.get(normalized_technique)
        if normalized_technique == "nmr":
            template_id = "nmr.spectrum.v1"
        return self.compatibility_envelope(
            source,
            technique=normalized_technique,
            source_artifact_id=source_artifact_id,
            template_id=template_id,
        )

    def compatibility_envelope(
        self,
        path: str | Path,
        *,
        technique: str,
        source_artifact_id: str,
        template_id: str | None = None,
    ) -> ConversionOutcome:
        """Create a reference-only envelope for an opaque provider input.

        This is deliberately separate from strict format conversion.  A
        provider may understand a vendor file that the canonical converter
        cannot decode (for example an unreadable-by-fabio EDF); in that case a
        direct run can still retain the raw artifact and its hash without
        claiming that detector pixels or physical axes were interpreted.
        """

        source = Path(path)
        normalized_technique = _normalize_technique(technique)
        resolved_template_id = template_id or _STATIC_TEMPLATE_IDS.get(normalized_technique)
        if normalized_technique == "nmr":
            resolved_template_id = resolved_template_id or "nmr.spectrum.v1"
        if resolved_template_id is None:
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
            template_id=resolved_template_id,
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
        mapping_proposal: MappingProposal | None = None,
    ) -> ConversionOutcome:
        """Recreate a template from a source already bound by a recipe."""
        return self.convert_path(
            path,
            technique=technique,
            source_artifact_id=source_artifact_id,
            mapping_proposal=mapping_proposal,
        )

    def convert_data_blocks(
        self,
        path: str | Path,
        *,
        technique: str,
        source_artifact_id: str,
        mapping_proposal: MappingProposal | None = None,
        mask_path: str | Path | None = None,
        mask_ref: Mapping[str, object] | None = None,
        calibration_ref: Mapping[str, object] | None = None,
        nmr_dtype: str = ">i4",
        nmr_shape: Sequence[int] | None = None,
        nmr_dims: Sequence[str] | None = None,
        nmr_coords: Mapping[str, Sequence[object]] | None = None,
        nmr_coord_units: Mapping[str, str] | None = None,
        nmr_axis_provenance: Mapping[str, object] | None = None,
        nmr_nucleus: str | None = None,
        nmr_metadata: Mapping[str, object] | None = None,
    ) -> DataBlockAdapterResult:
        """Convert a source through the shared N-D ``DataBlock`` boundary.

        ``convert_path`` remains the compatibility route and continues to
        return a ``ConversionOutcome``.  This narrow method selects the
        reference-preserving adapters for temperature IR directories,
        detector images and raw NMR FIDs, and adapts ordinary one-dimensional
        measurements for all other registered routes.
        """

        source = Path(path)
        normalized_technique = _normalize_technique(technique)
        if normalized_technique == "ir" and source.is_dir():
            frame_paths = tuple(
                sorted(
                    (
                        item
                        for item in source.iterdir()
                        if item.is_file() and item.suffix.casefold() in _GENERIC_TABLE_EXTENSIONS
                    ),
                    key=lambda item: item.name.casefold(),
                )
            )
            if len(frame_paths) >= 2:
                return adapt_ir_temperature_series(
                    frame_paths,
                    source_artifact_id=source_artifact_id,
                )
        if (
            normalized_technique in {"saxs", "waxs"}
            and source.is_file()
            and source.suffix.casefold() in _IMAGE_EXTENSIONS
        ):
            return adapt_detector_image(
                source,
                technique=normalized_technique,
                source_artifact_id=source_artifact_id,
                mask_path=mask_path,
                mask_ref=mask_ref,
                calibration_ref=calibration_ref,
            )
        if normalized_technique == "nmr" and _is_nmr_fid_path(source):
            fid_source = source / "fid" if source.is_dir() else source
            return adapt_nmr_fid(
                fid_source,
                source_artifact_id=source_artifact_id,
                dtype=nmr_dtype,
                shape=nmr_shape,
                dims=nmr_dims,
                coords=nmr_coords,
                coord_units=nmr_coord_units,
                axis_provenance=nmr_axis_provenance,
                nucleus=nmr_nucleus,
                metadata=nmr_metadata,
            )
        outcome = self.convert_path(
            source,
            technique=normalized_technique,
            source_artifact_id=source_artifact_id,
            mapping_proposal=mapping_proposal,
        )
        return adapt_conversion_outcome(outcome, technique=normalized_technique)

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
        return directory_manifest_sha256(directory_manifest_entries(source))


_DEFAULT_REGISTRY = CanonicalConverterRegistry()


_TECHNIQUE_ALIASES = {
    "ftir": "ir",
    "infrared": "ir",
    "fourier_transform_infrared": "ir",
    "saxs2d": "saxs",
    "waxs2d": "waxs",
    "gpc": "sec",
    "sec/gpc": "sec",
}


def _normalize_technique(value: object) -> str:
    normalized = str(value).strip().lower()
    return _TECHNIQUE_ALIASES.get(normalized, normalized)


def _is_nmr_fid_path(path: Path) -> bool:
    # Recognize a declared FID route even before the file exists so callers
    # receive ``needs_input`` (missing acquisition) rather than an unrelated
    # generic/unsupported-converter status.
    if path.name.casefold() == "fid" or path.suffix.casefold() in _FID_EXTENSIONS:
        return True
    if path.is_dir():
        return (path / "fid").is_file()
    return False


def default_converter_registry() -> CanonicalConverterRegistry:
    """Return the immutable process-wide registry of supported conversions."""
    return _DEFAULT_REGISTRY


__all__ = ["CanonicalConverterRegistry", "default_converter_registry"]
