"""Sample-neutral dynamic mechanical analysis (DMA/DMTA) engine.

The engine preserves explicitly labelled source signals and derives only
dimensionally valid relationships. Response peaks remain candidates rather
than glass-transition assignments.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np

from .canonical_experiments import CanonicalExperiment, convert_one_dimensional_table
from .advanced_figures import build_advanced_figure_definitions
from .dma_processing import (
    DMAProcessingConfig,
    DMASignalSeries,
    DMATTSSpec,
    analyze_dma_group,
    build_dma_master_curve,
)
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
        processing_config = DMAProcessingConfig.coerce(config)
        super().__init__(config=processing_config, log_fn=log_fn)
        self.processing_config = processing_config
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
        self._adopt_template(outcome.template)
        self.log(f"Loaded {len(self._measurements)} DMA curve(s)")
        return bool(self._measurements)

    def run_canonical_template(
        self,
        template: CanonicalExperiment,
        output_dir: str = "",
        *,
        skip_to: str | None = None,
    ):
        """Execute an already validated shared DMA template without reparsing."""
        self._adopt_template(template)
        self.log(f"Loaded {len(self._measurements)} canonical DMA curve(s)")
        if skip_to != "plot":
            if not self.preprocess() or not self.analyze():
                return self.result
        if output_dir:
            figures = self.plot(output_dir)
            if figures:
                self.result.figures = figures
        self._validate_results()
        return self.result

    def _adopt_template(self, template: CanonicalExperiment) -> None:
        if not isinstance(template, CanonicalExperiment):
            raise TypeError("DMA canonical execution requires a CanonicalExperiment")
        if template.template_id != "dma_curve_1d.v1":
            raise ValueError("DMA canonical template id is unsupported")
        if str(template.payload.get("technique", "")).upper() != "DMA":
            raise ValueError("DMA canonical template technique mismatch")
        measurements = tuple(template.measurements)
        if not measurements or any(item.family != "viscoelastic_1d" for item in measurements):
            raise ValueError("DMA canonical template measurements are unsupported")
        self._template = template
        self._measurements = measurements
        self._source_path = str(measurements[0].source_locator["source_path"])

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
        grouped_signals: dict[str, list[tuple[Any, np.ndarray, np.ndarray]]] = {}
        total_points = 0
        warnings: list[str] = []
        units: dict[str, Any] = {}
        methods: dict[str, Any] = {}
        method_parameters: dict[str, Any] = {}
        for measurement in self._measurements:
            x = np.asarray(measurement.channels["x"], dtype=float)
            signal = np.asarray(measurement.channels["intensity"], dtype=float)
            if x.size < 2 or signal.size != x.size:
                self.log(f"Invalid DMA curve: {measurement.measurement_id}")
                return False
            mapping = measurement.mapping
            axis_kind = mapping.x_kind if mapping is not None else measurement.acquisition_metadata.get("axis_kind", "unknown")
            signal_kind = measurement.acquisition_metadata.get("signal_kind", "viscoelastic_signal")
            modulus_basis = measurement.acquisition_metadata.get("modulus_basis", "unspecified")
            warnings.extend(str(item) for item in measurement.warnings)
            group_id = str(
                measurement.acquisition_metadata.get(
                    "source_table_id",
                    (
                        f"sheet-{measurement.source_locator.get('sheet_index') or 0}"
                        f"-table-{measurement.source_locator.get('table_index', 0)}"
                    ),
                )
            )
            grouped_signals.setdefault(group_id, []).append((measurement, x, signal))
            curves.append(
                {
                    "measurement_id": measurement.measurement_id,
                    "axis_kind": str(axis_kind),
                    "signal_kind": str(signal_kind),
                    "modulus_basis": str(modulus_basis),
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
        dma_groups: dict[str, dict[str, Any]] = {}
        for group_id, group_items in grouped_signals.items():
            first_measurement, group_x, _ = group_items[0]
            first_mapping = first_measurement.mapping
            axis_kind = (
                first_mapping.x_kind
                if first_mapping is not None
                else first_measurement.acquisition_metadata.get("axis_kind", "unknown")
            )
            signal_series = tuple(
                DMASignalSeries.create(
                    measurement_id=measurement.measurement_id,
                    signal_kind=str(
                        measurement.acquisition_metadata.get(
                            "signal_kind", "viscoelastic_signal"
                        )
                    ),
                    modulus_basis=str(
                        measurement.acquisition_metadata.get(
                            "modulus_basis", "unspecified"
                        )
                    ),
                    unit=measurement.units.get("intensity", "unknown"),
                    values=signal,
                    x_values=x,
                )
                for measurement, x, signal in group_items
            )
            processed = analyze_dma_group(
                group_x,
                axis_kind=str(axis_kind),
                axis_unit=first_measurement.units.get("x", "unknown"),
                signals=signal_series,
                config=self.processing_config,
            )
            group_metrics = dict(processed.metrics)
            dma_groups[group_id] = group_metrics
            metric_prefix = f"dma_groups.{group_id}"
            units.update(
                {f"{metric_prefix}.{path}": value for path, value in processed.units.items()}
            )
            methods.update(
                {f"{metric_prefix}.{path}": value for path, value in processed.methods.items()}
            )
            method_parameters.update(
                {
                    f"{metric_prefix}.{path}": value
                    for path, value in processed.parameters.items()
                }
            )
            for basis, record in group_metrics["derived_tan_delta"].items():
                if record.get("values") is None:
                    continue
                derived_values = np.asarray(
                    [np.nan if value is None else value for value in record["values"]],
                    dtype=float,
                )
                self.result.raw_data[
                    f"{group_id}:derived_tan_delta:{basis}"
                ] = derived_values
        first = curves[0]
        axis_kinds = {item["axis_kind"] for item in curves}
        x_units = {item["x_unit"] for item in curves}
        signal_units = {item["signal_unit"] for item in curves}
        self._metrics = {
            "n_curves": len(curves),
            "point_count": total_points,
            "axis_kind": first["axis_kind"] if len(axis_kinds) == 1 else "mixed",
            "x_unit": first["x_unit"] if len(x_units) == 1 else "mixed",
            "signal_unit": first["signal_unit"] if len(signal_units) == 1 else "mixed",
            "x_min": min(item["x_min"] for item in curves),
            "x_max": max(item["x_max"] for item in curves),
            "signal_min": min(item["signal_min"] for item in curves),
            "signal_max": max(item["signal_max"] for item in curves),
            "curves": curves,
            "dma_groups": dma_groups,
        }
        tts_payload = self._template.payload.get("dma_tts") if self._template is not None else None
        if tts_payload is not None:
            self._metrics["dma_tts"] = self._compute_tts(tts_payload)
            tts = self._metrics["dma_tts"]
            if isinstance(tts, dict) and tts.get("status") in {"computed", "computed_with_warning"}:
                units["dma_tts.reference_temperature"] = "degC"
                units["dma_tts.points.frequency"] = str(tts.get("frequency_unit", "unknown"))
                units["dma_tts.points.modulus"] = str(tts.get("modulus_unit", "unknown"))
                units["dma_tts.shift_factors"] = "1"
                for path in ("dma_tts.points", "dma_tts.shift_factors"):
                    methods[path] = str(tts.get("method", "horizontal_frequency_shift"))
                    method_parameters[path] = dict(tts.get("parameters", {}))
        self.result.parameters = dict(self._metrics)
        self.result.validation_warnings = sorted(set(warnings))
        self.result.metadata.update(
            {
                "source_path": self._source_path,
                "canonical_template_id": self._template.template_id if self._template is not None else "",
                "analysis_scope": "descriptive_curve_and_material_neutral_response_candidates",
                "dma_processing_contract": "dma.processing.v1",
                "dma_processing_config": self.processing_config.to_dict(),
                "units": units,
                "methods": methods,
                "parameters": method_parameters,
                "dma_tts_spec": tts_payload or {},
            }
        )
        return True

    def _compute_tts(self, payload: Any) -> dict[str, Any]:
        try:
            spec = DMATTSSpec.from_mapping(payload)
        except (TypeError, ValueError):
            return {"status": "unavailable", "unavailable_reason": "tts_spec_invalid"}
        by_id = {measurement.measurement_id: measurement for measurement in self._measurements}
        ids = spec.curve_measurement_ids
        if not ids:
            return {"status": "unavailable", "unavailable_reason": "tts_curve_measurement_ids_required"}
        curves = []
        for temperature, measurement_id in zip(spec.temperatures, ids, strict=True):
            measurement = by_id.get(measurement_id)
            if measurement is None:
                return {"status": "unavailable", "unavailable_reason": "tts_measurement_not_found"}
            curves.append({"temperature": temperature, "frequency": tuple(float(value) for value in measurement.channels["x"]), "modulus": tuple(float(value) for value in measurement.channels["intensity"]), "modulus_unit": measurement.units.get("intensity", "unknown"), "measurement_id": measurement_id})
        result = build_dma_master_curve(curves, spec)
        result["source_measurement_ids"] = list(ids)
        return result

    def build_figure_definitions(self):
        return build_advanced_figure_definitions(self)

    def plot(self, output_dir: str = "") -> Dict[str, str]:
        if not self._measurements or not output_dir:
            return {}
        definitions = tuple(self.build_figure_definitions())
        if definitions:
            return self.publish_figure_definitions(output_dir, definitions)
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


__all__ = ["DMAEngine", "DMAProcessingConfig"]
