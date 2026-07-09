from __future__ import annotations

from typing import Any

from .analysis_evidence_common import _clean_float
from .analysis_evidence_ir_temperature_2d_feature import _safe_int


def _ir_temperature_2d_matrix_constraint_rows(ir_2d_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    matrix_shapes_consistent = bool(ir_2d_metrics.get("matrix_shapes_consistent"))
    neg_fraction = _clean_float(ir_2d_metrics.get("neg_fraction"))
    nan_fraction = _clean_float(ir_2d_metrics.get("nan_fraction"))
    dynamic_rms = _clean_float(ir_2d_metrics.get("dynamic_rms"))
    dynamic_signal_rms = _clean_float(ir_2d_metrics.get("dynamic_signal_rms", dynamic_rms))
    frame_intensity_scale_spread = _clean_float(ir_2d_metrics.get("frame_intensity_scale_spread"))
    wavenumber_grid_consistent = bool(ir_2d_metrics.get("wavenumber_grid_consistent", True))
    sync_cross_peak_count = _safe_int(ir_2d_metrics.get("sync_cross_peak_count"), 0)
    async_cross_peak_count = _safe_int(ir_2d_metrics.get("async_cross_peak_count"), 0)

    return [
        {
            "name": "matrix_shape_inconsistent",
            "kind": "hard_fail",
            "source": "IR_temperature_2d",
            "severity": "ERROR",
            "description": "The 2D IR matrix and correlation shapes are inconsistent.",
            "field": "matrix_shape",
            "rationale": "The dynamic matrix and sync/async maps must agree before interpretation.",
            "triggered": not matrix_shapes_consistent,
            "observed": {
                "matrix_shape": ir_2d_metrics.get("matrix_shape"),
                "dynamic_shape": ir_2d_metrics.get("dynamic_shape"),
                "sync_shape": ir_2d_metrics.get("sync_shape"),
                "async_shape": ir_2d_metrics.get("async_shape"),
            },
        },
        {
            "name": "negative_matrix_fraction_high",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "The absorbance matrix contains a high fraction of non-positive values.",
            "field": "neg_fraction",
            "rationale": "High negativity often means baseline over-subtraction or clipping.",
            "triggered": neg_fraction is not None and neg_fraction > 0.30,
            "observed": {
                "neg_fraction": neg_fraction,
                "nan_fraction": nan_fraction,
                "dynamic_rms": dynamic_rms,
            },
        },
        {
            "name": "matrix_nan_fraction_high",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "The absorbance matrix still contains too many NaN values.",
            "field": "nan_fraction",
            "rationale": "Matrix holes make 2D-COS peaks unstable and harder to trust.",
            "triggered": nan_fraction is not None and nan_fraction > 0.01,
            "observed": {
                "nan_fraction": nan_fraction,
                "wavenumber_grid_consistent": wavenumber_grid_consistent,
            },
        },
        {
            "name": "wavenumber_grid_inconsistent",
            "kind": "hard_fail",
            "source": "IR_temperature_2d",
            "severity": "ERROR",
            "description": "The per-frame wavenumber grids are not aligned to a shared matrix axis.",
            "field": "wavenumber_grid_consistent",
            "rationale": "Cross-peaks cannot be trusted when frame grids do not align.",
            "triggered": not wavenumber_grid_consistent,
            "observed": {
                "wavenumber_grid_consistent": wavenumber_grid_consistent,
                "matrix_shape": ir_2d_metrics.get("matrix_shape"),
            },
        },
        {
            "name": "frame_intensity_scale_unstable",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "Frame-to-frame intensity scaling is drifting too much.",
            "field": "frame_intensity_scale_spread",
            "rationale": "Large frame-scale drift often means baseline or normalization artifacts dominate the trend.",
            "triggered": frame_intensity_scale_spread is not None and frame_intensity_scale_spread > 0.85,
            "observed": {
                "frame_intensity_scale_spread": frame_intensity_scale_spread,
                "dynamic_rms": dynamic_signal_rms,
            },
        },
        {
            "name": "dynamic_signal_too_weak",
            "kind": "soft_warn",
            "source": "IR_temperature_2d",
            "severity": "WARN",
            "description": "The dynamic signal is too weak to support a robust 2D-COS interpretation.",
            "field": "dynamic_signal_rms",
            "rationale": "When the dynamic signal is tiny, cross-peaks may mainly reflect amplified noise.",
            "triggered": dynamic_signal_rms is not None and dynamic_signal_rms < 0.005,
            "observed": {
                "dynamic_signal_rms": dynamic_signal_rms,
                "sync_cross_peak_count": sync_cross_peak_count,
                "async_cross_peak_count": async_cross_peak_count,
            },
        },
    ]


__all__ = ["_ir_temperature_2d_matrix_constraint_rows"]
