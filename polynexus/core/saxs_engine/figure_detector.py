"""Read-only detector-image projections for SAXS Figure providers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from ..figures.contracts import (
    DataColumnDefinition,
    FigureDataSourceDefinition,
)
from . import io as saxs_io
from .figure_common import SAXSFrameView


@dataclass(frozen=True)
class DetectorProjection:
    pixel_x: tuple[int, ...]
    pixel_y: tuple[int, ...]
    log_intensity: tuple[float, ...]
    sampled_pixel_count: int
    retained_pixel_count: int
    nonfinite_pixel_count: int


@dataclass(frozen=True)
class DetectorFrameEvidence:
    frame: SAXSFrameView
    source: FigureDataSourceDefinition
    sampled_pixel_count: int
    retained_pixel_count: int
    nonfinite_pixel_count: int

    @property
    def projection_quality(self) -> dict[str, Any]:
        return {
            "sampled_pixel_count": self.sampled_pixel_count,
            "retained_pixel_count": self.retained_pixel_count,
            "nonfinite_pixel_count": self.nonfinite_pixel_count,
            "status": (
                "partial_nonfinite"
                if self.nonfinite_pixel_count
                else "complete"
            ),
        }


def detector_capable(frames: Sequence[SAXSFrameView]) -> bool:
    """Return whether an existing frame path declares a supported 2D source."""

    return any(
        Path(str(frame.source_path or "")).suffix.lower()
        in saxs_io.SUPPORTED_2D_EXTENSIONS
        for frame in frames
    )


def _downsample_detector(image: Any) -> DetectorProjection | None:
    try:
        array = np.asarray(image, dtype=float)
    except (TypeError, ValueError):
        return None
    if array.ndim != 2 or array.size == 0:
        return None

    row_count, column_count = array.shape
    row_indices = np.linspace(0, row_count - 1, min(row_count, 256), dtype=int)
    column_indices = np.linspace(
        0,
        column_count - 1,
        min(column_count, 256),
        dtype=int,
    )
    sampled = array[np.ix_(row_indices, column_indices)]
    x_grid, y_grid = np.meshgrid(column_indices, row_indices)
    flattened = sampled.reshape(-1)
    finite = np.isfinite(flattened)
    sampled_pixel_count = int(finite.size)
    retained_pixel_count = int(np.count_nonzero(finite))
    nonfinite_pixel_count = sampled_pixel_count - retained_pixel_count
    if retained_pixel_count == 0:
        return None

    values = np.clip(flattened[finite], np.finfo(float).tiny, None)
    return DetectorProjection(
        pixel_x=tuple(int(value) for value in x_grid.reshape(-1)[finite]),
        pixel_y=tuple(int(value) for value in y_grid.reshape(-1)[finite]),
        log_intensity=tuple(float(value) for value in np.log10(values)),
        sampled_pixel_count=sampled_pixel_count,
        retained_pixel_count=retained_pixel_count,
        nonfinite_pixel_count=nonfinite_pixel_count,
    )


def build_detector_evidence(
    frames: Sequence[SAXSFrameView],
) -> tuple[tuple[DetectorFrameEvidence, ...], dict[str, str]]:
    """Project existing detector files without changing analysis inputs."""

    evidence: list[DetectorFrameEvidence] = []
    failures: dict[str, str] = {}
    for frame in frames:
        source_path = str(frame.source_path or "")
        if Path(source_path).suffix.lower() not in saxs_io.SUPPORTED_2D_EXTENSIONS:
            failures[str(frame.index)] = "source is not a supported detector image"
            continue
        try:
            image, _header = saxs_io.read_image(source_path)
        except Exception as exc:  # reader failures stay at the Figure boundary
            failures[str(frame.index)] = str(exc) or type(exc).__name__
            continue
        projection = _downsample_detector(image)
        if projection is None:
            failures[str(frame.index)] = (
                "detector image is empty, non-finite, or not two-dimensional"
            )
            continue
        source = FigureDataSourceDefinition(
            source_id=f"detector-image-{frame.index:03d}",
            columns=(
                DataColumnDefinition("pixel_x", "pixel", "int64"),
                DataColumnDefinition("pixel_y", "pixel", "int64"),
                DataColumnDefinition("log_intensity", "log10(counts)", "float64"),
            ),
            values={
                "pixel_x": projection.pixel_x,
                "pixel_y": projection.pixel_y,
                "log_intensity": projection.log_intensity,
            },
            role="detector_image",
        )
        evidence.append(
            DetectorFrameEvidence(
                frame=frame,
                source=source,
                sampled_pixel_count=projection.sampled_pixel_count,
                retained_pixel_count=projection.retained_pixel_count,
                nonfinite_pixel_count=projection.nonfinite_pixel_count,
            )
        )
    return tuple(evidence), failures


__all__ = [
    "DetectorFrameEvidence",
    "DetectorProjection",
    "build_detector_evidence",
    "detector_capable",
]
