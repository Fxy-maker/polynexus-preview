"""Sample-neutral dynamic mechanical analysis (DMA/DMTA) engine.

This foundation intentionally handles one explicitly mapped curve at a time.
Instrument exports containing several candidate signals (E', E'', tan delta,
etc.) remain ``needs_input`` in canonical conversion until the caller supplies
an explicit mapping, avoiding a silent scientific choice.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np

from .canonical_experiments import convert_one_dimensional_table
from .engine import BaseEngine, EngineCategory, register_technique


@register_technique("dma")
class DMAEngine(BaseEngine):
    """Deterministic descriptive DMA analysis for arbitrary sample tables."""

    name = "dma"
    label = "DMA/DMTA"
    icon = "〰️"
    category = EngineCategory.EXPERIMENTAL
    description = (
        "Dynamic mechanical curves: source-preserving modulus, damping, "
        "stress, or strain summaries"
    )

    def __init__(self, config: Any = None, log_fn=None):
        super().__init__(config=config, log_fn=log_fn)
        self._template = None
        self._measurements = ()
        self._source_path = ""
        self._metrics: Dict[str, Any] = {}

    def load(self, filepath: str) -> bool:
        source = Path(filepath)
        if not source.exists() or not source.is_file():
            self.log(f"No DMA table found at: {filepath}")
            return False
        self._source_path = str(source.resolve())
        outcome = convert_one_dimensional_table(
            source,
            technique="dma",
            source_artifact_id=f"dma-source:{self._source_path}",
        )
        if outcome.status != "ready" or outcome.template is None:
            reason = ", ".join(outcome.reason_codes) or outcome.status
            self.log(f"DMA table conversion unavailable: {reason}")
            return False
        self._template = outcome.template
        self._measurements = tuple(outcome.template.measurements)
        self.log(f"Loaded {len(self._measurements)} DMA curve(s)")
        return bool(self._measurements)

    def preprocess(self) -> bool:
        if not self._measurements:
            self.log("No DMA data loaded")
            return False
        return True

    def analyze(self) -> bool:
        if not self._measurements:
            self.log("No DMA data available")
            return False
        curves: list[dict[str, Any]] = []
        total_points = 0
        warnings: list[str] = []
        for measurement in self._measurements:
            x = np.asarray(measurement.channels["x"], dtype=float)
            signal = np.asarray(measurement.channels["intensity"], dtype=float)
            if x.size < 2 or signal.size != x.size:
                self.log(f"Invalid DMA curve: {measurement.measurement_id}")
                return False
            mapping = measurement.mapping
            axis_kind = mapping.x_kind if mapping is not None else measurement.acquisition_metadata.get("axis_kind", "unknown")
            signal_kind = measurement.acquisition_metadata.get("signal_kind", "viscoelastic_signal")
            warnings.extend(str(item) for item in measurement.warnings)
            curves.append(
                {
                    "measurement_id": measurement.measurement_id,
                    "axis_kind": str(axis_kind),
                    "signal_kind": str(signal_kind),
                    "x_unit": measurement.units.get("x", "unknown"),
                    "signal_unit": measurement.units.get("intensity", "unknown"),
                    "point_count": int(x.size),
                    "x_min": float(np.min(x)),
                    "x_max": float(np.max(x)),
                    "signal_min": float(np.min(signal)),
                    "signal_max": float(np.max(signal)),
                    "signal_range": float(np.max(signal) - np.min(signal)),
                }
            )
            total_points += int(x.size)
            self.result.raw_data[f"{measurement.measurement_id}:x"] = x
            self.result.raw_data[f"{measurement.measurement_id}:signal"] = signal
        first = curves[0]
        self._metrics = {
            "n_curves": len(curves),
            "point_count": total_points,
            "axis_kind": first["axis_kind"] if len(curves) == 1 else "mixed",
            "x_unit": first["x_unit"] if len(curves) == 1 else "mixed",
            "signal_unit": first["signal_unit"] if len(curves) == 1 else "mixed",
            "x_min": min(item["x_min"] for item in curves),
            "x_max": max(item["x_max"] for item in curves),
            "signal_min": min(item["signal_min"] for item in curves),
            "signal_max": max(item["signal_max"] for item in curves),
            "curves": curves,
        }
        self.result.parameters = dict(self._metrics)
        self.result.validation_warnings = sorted(set(warnings))
        self.result.metadata.update(
            {
                "source_path": self._source_path,
                "canonical_template_id": self._template.template_id if self._template is not None else "",
                "analysis_scope": "descriptive_curve_summary",
            }
        )
        return True

    def build_figure_definitions(self):
        return ()

    def plot(self, output_dir: str = "") -> Dict[str, str]:
        if not self._measurements or not output_dir:
            return {}
        import matplotlib.pyplot as plt

        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        figure, axes = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
        for measurement in self._measurements:
            axes.plot(
                measurement.channels["x"],
                measurement.channels["intensity"],
                label=measurement.measurement_id,
            )
        axes.set_xlabel("Frequency / temperature / time")
        axes.set_ylabel("DMA signal")
        if len(self._measurements) > 1:
            axes.legend()
        axes.grid(alpha=0.2)
        path = destination / "dma_curve.png"
        figure.savefig(path, dpi=150)
        plt.close(figure)
        return {"curve": str(path)}

    def get_parameters(self) -> Dict[str, Any]:
        return dict(self._metrics)


__all__ = ["DMAEngine"]
