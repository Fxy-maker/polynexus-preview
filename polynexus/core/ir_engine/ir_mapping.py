"""Typed IR mapping/ROI handoff and shared figure definitions.

This module deliberately consumes an already-interpreted mapping payload.  It
does not infer an instrument format, choose a spectral band, or assign a
physical meaning to a pixel value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)
from polynexus.core.scientific_review import (
    review_decision_snapshot,
    review_record_from_payload,
)


def official_thermo_omnic_picta_semantics() -> dict[str, Any]:
    """Return the documented Thermo/OMNIC Picta mapping semantics.

    This is a semantic reference profile, not a vendor-file parser.  It keeps
    sample-specific bounds, detector settings, and flattened scan order
    explicitly unverified until a native map or coordinate export is supplied.
    """

    return {
        "profile_id": "thermo_omnic_picta_official",
        "source": {
            "publisher": "Thermo Fisher Scientific",
            "document": "OMNIC Picta User Guide",
            "revision": "269-257900 Rev A",
            "url": "https://knowledge1.thermofisher.com/Molecular_Spectroscopy/Molecular_Spectroscopy_Software/OMNIC_Family/OMNIC_Picta_Software/OMNIC_Picta__Suite_Operator_Manuals/269-257900_-_REV_A_-_OMNIC_Picta_User_Guide",
        },
        "spatial_axes": {
            "x": {
                "coordinate_role": "column",
                "physical_axis": "microscope_stage_x",
                "unit": "um",
            },
            "y": {
                "coordinate_role": "row",
                "physical_axis": "microscope_stage_y",
                "unit": "um",
            },
        },
        "origin": {
            "kind": "stage_home",
            "x": 0.0,
            "y": 0.0,
        },
        "roi": {
            "kind": "area_map_boundary_or_explicit_roi",
            "coordinate_system": "stage_xy",
            "step_size_policy": "vendor_adjusted_grid",
            "sample_bounds": "unverified_without_vendor_map",
        },
        "serialization": {
            "order": "unknown_without_vendor_map",
            "reason": "official guide defines X/Y roles but not flattened array order",
        },
        "status": "official_rule_sample_metadata_unverified",
    }


@dataclass
class IRMappingROISpectrum:
    """One explicitly selected ROI spectrum and its upstream provenance."""

    roi_id: str
    label: str
    wavenumber: np.ndarray
    absorbance: np.ndarray
    valid_pixel_count: int = 0
    assignments: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class IRMappingResult:
    """Validated handoff from an IR mapping/ROI analysis adapter."""

    label: str
    map_values: np.ndarray
    row_coordinates: np.ndarray
    column_coordinates: np.ndarray
    invalid_pixel_mask: np.ndarray
    map_metric: str
    roi_spectra: tuple[IRMappingROISpectrum, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)

    @property
    def map_shape(self) -> tuple[int, int]:
        values = np.asarray(self.map_values)
        return (int(values.shape[0]), int(values.shape[1])) if values.ndim == 2 else (0, 0)

    @property
    def invalid_pixel_count(self) -> int:
        return int(np.asarray(self.invalid_pixel_mask, dtype=bool).sum())

    @property
    def valid_pixel_ratio(self) -> float:
        rows, columns = self.map_shape
        total = rows * columns
        return float(1.0 - self.invalid_pixel_count / total) if total else 0.0

    def to_evidence(self) -> dict[str, Any]:
        """Return structural evidence; no band or composition inference is made."""

        validate_ir_mapping_result(self)
        scientific_review = _mapping_scientific_review_decision(self.provenance)
        mapping_semantics = official_thermo_omnic_picta_semantics()
        return {
            "submodule_id": "ir.mapping",
            "feature_evidence": {
                "mapping_evidence": {
                    "map_shape": list(self.map_shape),
                    "map_metric": self.map_metric,
                    "invalid_pixel_count": self.invalid_pixel_count,
                    "invalid_pixel_ratio": float(1.0 - self.valid_pixel_ratio),
                    "valid_pixel_ratio": self.valid_pixel_ratio,
                    "roi_count": len(self.roi_spectra),
                    "assignment_roi_count": sum(bool(item.assignments) for item in self.roi_spectra),
                    "source_id": str(self.provenance["source_id"]),
                    "status": "review_required" if self.invalid_pixel_count else "ready_for_review",
                    "mapping_semantics": mapping_semantics,
                    "scientific_review": scientific_review,
                }
            },
        }


def validate_ir_mapping_result(result: IRMappingResult) -> None:
    """Validate only structural and provenance invariants of a mapping payload."""

    if not isinstance(result, IRMappingResult):
        raise TypeError("IR mapping result must be an IRMappingResult")
    values = np.asarray(result.map_values, dtype=float)
    if values.ndim != 2 or not values.size:
        raise ValueError("map_values must be a non-empty 2D array")
    if np.isinf(values).any():
        raise ValueError("map_values must not contain infinite values")

    rows, columns = values.shape
    row_coordinates = np.asarray(result.row_coordinates, dtype=float)
    column_coordinates = np.asarray(result.column_coordinates, dtype=float)
    if row_coordinates.ndim != 1 or len(row_coordinates) != rows:
        raise ValueError("row_coordinates must match map_values rows")
    if column_coordinates.ndim != 1 or len(column_coordinates) != columns:
        raise ValueError("column_coordinates must match map_values columns")
    if not np.isfinite(row_coordinates).all() or not np.isfinite(column_coordinates).all():
        raise ValueError("mapping coordinates must be finite")

    mask = np.asarray(result.invalid_pixel_mask)
    if mask.dtype != np.bool_ or mask.shape != values.shape:
        raise ValueError("invalid_pixel_mask must be boolean and match map_values")
    nonfinite = ~np.isfinite(values)
    if np.any(nonfinite & ~mask):
        raise ValueError("non-finite map_values must be marked in invalid_pixel_mask")
    if not str(result.map_metric).strip():
        raise ValueError("map_metric must be non-empty")
    source_id = result.provenance.get("source_id") if isinstance(result.provenance, Mapping) else None
    if not str(source_id or "").strip():
        raise ValueError("provenance.source_id must be non-empty")

    seen_ids: set[str] = set()
    for spectrum in result.roi_spectra:
        if not str(spectrum.roi_id).strip() or spectrum.roi_id in seen_ids:
            raise ValueError("ROI ids must be non-empty and unique")
        seen_ids.add(spectrum.roi_id)
        wavenumber = np.asarray(spectrum.wavenumber, dtype=float)
        absorbance = np.asarray(spectrum.absorbance, dtype=float)
        if wavenumber.ndim != 1 or absorbance.ndim != 1 or not len(wavenumber):
            raise ValueError(f"ROI spectrum {spectrum.roi_id} must be non-empty 1D arrays")
        if len(wavenumber) != len(absorbance):
            raise ValueError(f"ROI spectrum {spectrum.roi_id} wavenumber/absorbance lengths differ")
        if not np.isfinite(wavenumber).all() or not np.isfinite(absorbance).all():
            raise ValueError(f"ROI spectrum {spectrum.roi_id} must be finite")
        if int(spectrum.valid_pixel_count) < 0:
            raise ValueError(f"ROI spectrum {spectrum.roi_id} valid_pixel_count must be non-negative")


def build_ir_mapping_figure_definitions(
    result: IRMappingResult,
) -> tuple[FigureDefinition, ...]:
    """Build Main, SI, and diagnostic definitions for a validated map payload."""

    validate_ir_mapping_result(result)
    values = np.asarray(result.map_values, dtype=float)
    rows, columns = values.shape
    row_coordinates = np.asarray(result.row_coordinates, dtype=float)
    column_coordinates = np.asarray(result.column_coordinates, dtype=float)
    mapping_semantics = official_thermo_omnic_picta_semantics()
    provenance = {
        "source_kind": str(result.provenance.get("source_kind", "explicit_mapping_payload")),
        "source_id": str(result.provenance["source_id"]),
    }
    scientific_review = _mapping_scientific_review_decision(result.provenance)
    promoted = bool(scientific_review["allowed"])

    map_source = FigureDataSourceDefinition(
        source_id="ir-mapping-map",
        columns=(
            DataColumnDefinition("column_coordinate", "um"),
            DataColumnDefinition("row_coordinate", "um"),
            DataColumnDefinition("value", "a.u."),
        ),
        values={
            "column_coordinate": tuple(float(item) for item in np.tile(column_coordinates, rows)),
            "row_coordinate": tuple(float(item) for item in np.repeat(row_coordinates, columns)),
            "value": tuple(float(item) for item in values.reshape(-1)),
        },
    )
    recipe_base = {
        "module": "polynexus.core.ir_engine.ir_mapping",
        "function": "build_ir_mapping_figure_definitions",
        "inputs": {"label": result.label, "map_shape": [rows, columns]},
        "provenance": provenance,
        "map_metric": result.map_metric,
        "valid_pixel_ratio": result.valid_pixel_ratio,
        "invalid_pixel_count": result.invalid_pixel_count,
        "mapping_semantics": mapping_semantics,
        "scientific_review": scientific_review,
        "v2_adapter": "ir",
    }
    definitions: list[FigureDefinition] = [
        FigureDefinition(
            figure_id="ir.mapping.roi",
            technique="ir",
            scope="series",
            category="series_overview",
            publication_role="main" if promoted else "diagnostic",
            title=f"IR Mapping — {result.map_metric}",
            layout=_mapping_layout("X position (um)", "Y position (um)"),
            data_sources=(map_source,),
            objects=(
                {
                    "id": "mapping-map",
                    "type": "heatmap",
                    "panel_id": "main",
                    "data_ref": map_source.source_id,
                    "x_column": "column_coordinate",
                    "y_column": "row_coordinate",
                    "z_column": "value",
                    "style": {"cmap": "viridis", "colorbar_label": result.map_metric},
                },
            ),
            recipe={**recipe_base, "figure_kind": "map"},
            style_profile="sci_default",
            display_order=10,
        )
    ]

    if result.roi_spectra:
        definitions.append(
            _roi_spectra_definition(
                result,
                provenance,
                recipe_base,
                publication_role="si" if promoted else "diagnostic",
            )
        )

    invalid_source = FigureDataSourceDefinition(
        source_id="ir-mapping-invalid-pixels",
        columns=(
            DataColumnDefinition("column_coordinate", "um"),
            DataColumnDefinition("row_coordinate", "um"),
            DataColumnDefinition("invalid", "", dtype="int64"),
        ),
        values={
            "column_coordinate": tuple(float(item) for item in np.tile(column_coordinates, rows)),
            "row_coordinate": tuple(float(item) for item in np.repeat(row_coordinates, columns)),
            "invalid": tuple(int(item) for item in np.asarray(result.invalid_pixel_mask).reshape(-1)),
        },
        role="diagnostic_data",
    )
    definitions.append(
        FigureDefinition(
            figure_id="ir.mapping.invalid-pixels",
            technique="ir",
            scope="series",
            category="diagnostic",
            publication_role="diagnostic",
            title="IR Mapping Invalid-Pixel Diagnostics",
            layout=_mapping_layout("X position (um)", "Y position (um)"),
            data_sources=(invalid_source,),
            objects=(
                {
                    "id": "invalid-pixel-map",
                    "type": "heatmap",
                    "panel_id": "main",
                    "data_ref": invalid_source.source_id,
                    "x_column": "column_coordinate",
                    "y_column": "row_coordinate",
                    "z_column": "invalid",
                    "style": {"cmap": "Greys", "colorbar_label": "Invalid pixel"},
                },
            ),
            recipe={**recipe_base, "figure_kind": "invalid_pixels"},
            style_profile="sci_default",
            display_order=30,
        )
    )
    return tuple(definitions)


def _mapping_scientific_review_decision(
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the fail-closed mapping promotion decision as JSON-safe data."""

    source_ref = str(provenance.get("source_id", ""))
    review = _restore_mapping_review(provenance.get("scientific_review"))
    return review_decision_snapshot(
        review,
        expected_scope="ir.mapping",
        source_ref=source_ref,
    )


def _restore_mapping_review(value: Any):
    return review_record_from_payload(value)


def _roi_spectra_definition(
    result: IRMappingResult,
    provenance: Mapping[str, str],
    recipe_base: Mapping[str, Any],
    *,
    publication_role: str,
) -> FigureDefinition:
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for index, spectrum in enumerate(result.roi_spectra, start=1):
        source_id = f"ir-mapping-roi-{index:03d}"
        source = FigureDataSourceDefinition(
            source_id=source_id,
            columns=(
                DataColumnDefinition("wavenumber_cm1", "cm^-1"),
                DataColumnDefinition("absorbance", "a.u."),
            ),
            values={
                "wavenumber_cm1": tuple(float(item) for item in spectrum.wavenumber),
                "absorbance": tuple(float(item) for item in spectrum.absorbance),
            },
        )
        sources.append(source)
        objects.append(
            {
                "id": f"roi-spectrum-{index:03d}",
                "type": "plot_series",
                "panel_id": "main",
                "name": spectrum.label or spectrum.roi_id,
                "data_ref": source_id,
                "x_column": "wavenumber_cm1",
                "y_column": "absorbance",
                "style": {"line_width": 0.9},
            }
        )
    assignments = {
        spectrum.roi_id: list(spectrum.assignments)
        for spectrum in result.roi_spectra
        if spectrum.assignments
    }
    return FigureDefinition(
        figure_id="ir.mapping.spectra",
        technique="ir",
        scope="series",
        category="supplementary",
        publication_role=publication_role,
        title="IR Mapping ROI Spectra",
        layout=_mapping_layout("Wavenumber", "Absorbance", x_reversed=True),
        data_sources=tuple(sources),
        objects=tuple(objects),
        recipe={
            **dict(recipe_base),
            "figure_kind": "roi_spectra",
            "roi_ids": [spectrum.roi_id for spectrum in result.roi_spectra],
            "assignments": assignments,
            "provenance": dict(provenance),
        },
        style_profile="sci_default",
        display_order=20,
    )


def _mapping_layout(x_label: str, y_label: str, *, x_reversed: bool = False) -> FigureLayoutDefinition:
    return FigureLayoutDefinition(
        width_in=7.0,
        height_in=4.6,
        rows=1,
        columns=1,
        panels=(
            PanelDefinition(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisDefinition(axis_id="x", label=x_label, reversed=x_reversed),
                y_axis=AxisDefinition(axis_id="y", label=y_label),
                show_legend=True,
            ),
        ),
    )


__all__ = [
    "IRMappingROISpectrum",
    "IRMappingResult",
    "build_ir_mapping_figure_definitions",
    "official_thermo_omnic_picta_semantics",
    "validate_ir_mapping_result",
]
