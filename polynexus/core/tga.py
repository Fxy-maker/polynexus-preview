"""Sample-neutral thermogravimetric analysis (TGA) engine.

The engine consumes a canonical temperature/time versus mass curve, preserves
the source channels, and emits deterministic descriptive and derived values.
Polymer identity remains optional metadata and is never used to name a
decomposition stage or infer a mechanism.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np

from .canonical_experiments import CanonicalExperiment, convert_one_dimensional_table
from .advanced_figures import build_advanced_figure_definitions
from .engine import BaseEngine, EngineCategory, register_technique
from .tga_processing import (
    TGAProcessingConfig,
    TGAKineticsSpec,
    analyze_tga_isoconversional_kinetics,
    analyze_tga_curve,
    analyze_tga_multirate_kinetics,
)


@register_technique("tga")
class TGAEngine(BaseEngine):
    """Deterministic descriptive TGA analysis for arbitrary sample tables."""

    name = "tga"
    label = "TGA"
    icon = "⚖️"
    category = EngineCategory.EXPERIMENTAL
    description = (
        "Thermogravimetric curves: source-preserving mass/weight summaries, "
        "normalized mass, DTG, and material-neutral event candidates"
    )

    def __init__(self, config: Any = None, log_fn=None):
        processing_config = TGAProcessingConfig.coerce(config)
        super().__init__(config=processing_config, log_fn=log_fn)
        self.processing_config = processing_config
        self._template = None
        self._measurements = ()
        self._source_path = ""
        self._metrics: Dict[str, Any] = {}

    def load(self, filepath: str) -> bool:
        source = Path(filepath)
        if not source.exists() or not source.is_file():
            self.log(f"No TGA table found at: {filepath}")
            return False
        self._source_path = str(source.resolve())
        # The engine is also usable outside ComputeRunService, so derive a
        # deterministic local binding for the canonical converter.  When a
        # ComputeRun already supplied a canonical template, this local
        # conversion still yields the same source-bound measurement contract.
        outcome = convert_one_dimensional_table(
            source,
            technique="tga",
            source_artifact_id=f"tga-source:{self._source_path}",
        )
        if outcome.status != "ready" or outcome.template is None:
            reason = ", ".join(outcome.reason_codes) or outcome.status
            self.log(f"TGA table conversion unavailable: {reason}")
            return False
        self._adopt_template(outcome.template)
        self.log(f"Loaded {len(self._measurements)} TGA curve(s)")
        return bool(self._measurements)

    def run_canonical_template(
        self,
        template: CanonicalExperiment,
        output_dir: str = "",
        *,
        skip_to: str | None = None,
    ):
        """Execute an already validated shared TGA template without reparsing.

        ``ComputeRunService`` owns validation and source binding. This adapter
        only consumes that public template, so its resulting numbers and the
        generic capability items use the same canonical measurements.
        """
        self._adopt_template(template)
        self.log(f"Loaded {len(self._measurements)} canonical TGA curve(s)")
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
            raise TypeError("TGA canonical execution requires a CanonicalExperiment")
        if template.template_id != "thermal_curve_1d.v1":
            raise ValueError("TGA canonical template id is unsupported")
        if str(template.payload.get("technique", "")).upper() != "TGA":
            raise ValueError("TGA canonical template technique mismatch")
        measurements = tuple(template.measurements)
        if not measurements or any(item.family != "thermal_1d" for item in measurements):
            raise ValueError("TGA canonical template measurements are unsupported")
        self._template = template
        self._measurements = measurements
        self._source_path = str(measurements[0].source_locator["source_path"])

    def preprocess(self) -> bool:
        if not self._measurements:
            self.log("No TGA data loaded")
            return False
        # Keep the source ordering and values intact.  Any smoothing, baseline
        # or derivative is an explicit future exploration/capability rather
        # than an implicit transformation of the canonical curve.
        return True

    def analyze(self) -> bool:
        if not self._measurements:
            self.log("No TGA data available")
            return False
        curves: list[dict[str, Any]] = []
        tga_curves: dict[str, dict[str, Any]] = {}
        total_points = 0
        warnings: list[str] = []
        units: dict[str, Any] = {}
        methods: dict[str, Any] = {}
        method_parameters: dict[str, Any] = {}
        for measurement in self._measurements:
            x = np.asarray(measurement.channels["x"], dtype=float)
            signal = np.asarray(measurement.channels["intensity"], dtype=float)
            if x.size < 2 or signal.size != x.size:
                self.log(f"Invalid TGA curve: {measurement.measurement_id}")
                return False
            mapping = measurement.mapping
            axis_kind = mapping.x_kind if mapping is not None else measurement.acquisition_metadata.get("axis_kind", "unknown")
            warnings.extend(str(item) for item in measurement.warnings)
            processed = analyze_tga_curve(
                x,
                signal,
                axis_kind=str(axis_kind),
                axis_unit=measurement.units.get("x", "unknown"),
                signal_unit=measurement.units.get("intensity", "unknown"),
                config=self.processing_config,
            )
            curve_metrics = dict(processed.metrics)
            tga_curves[measurement.measurement_id] = curve_metrics
            metric_prefix = f"tga_curves.{measurement.measurement_id}"
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
            curves.append(
                {
                    "measurement_id": measurement.measurement_id,
                    "axis_kind": str(axis_kind),
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
            derived = curve_metrics["derived"]
            normalized_mass = derived.get("normalized_mass_percent")
            if normalized_mass is not None:
                self.result.raw_data[
                    f"{measurement.measurement_id}:normalized_mass_percent"
                ] = np.asarray(normalized_mass, dtype=float)
            smoothed_mass = derived.get("smoothed_mass_percent")
            if smoothed_mass is not None:
                self.result.raw_data[
                    f"{measurement.measurement_id}:smoothed_mass_percent"
                ] = np.asarray(smoothed_mass, dtype=float)
            dtg = derived.get("dtg")
            if dtg is not None:
                self.result.raw_data[f"{measurement.measurement_id}:dtg"] = np.asarray(
                    dtg,
                    dtype=float,
                )
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
            "tga_curves": tga_curves,
        }
        kinetics_spec = (
            self._template.payload.get("tga_kinetics")
            if self._template is not None
            else None
        )
        if kinetics_spec is not None:
            try:
                spec = TGAKineticsSpec.from_mapping(kinetics_spec)
                measurements_by_id = {item.measurement_id: item for item in self._measurements}
                ordered_measurements = (
                    tuple(measurements_by_id[item] for item in spec.curve_measurement_ids)
                    if spec.curve_measurement_ids
                    else tuple(self._measurements)
                )
                if len(ordered_measurements) != len(spec.heating_rates):
                    raise ValueError("kinetics curve measurement ids do not match heating rates")
                peaks = []
                missing_peak = False
                isoconversional_curves = []
                for measurement in ordered_measurements:
                    events = tga_curves[measurement.measurement_id].get("mass_loss_events", {})
                    candidates = (
                        tuple(
                            value
                            for key, value in events.items()
                            if str(key).startswith("event_") and isinstance(value, dict)
                        )
                        if isinstance(events, dict)
                        else ()
                    )
                    peak = next(
                        (
                            item.get("peak_x")
                            for item in candidates
                            if item.get("peak_x") is not None
                        ),
                        None,
                    )
                    if peak is None:
                        missing_peak = True
                    unit = str(measurement.units.get("x", ""))
                    temperature_values = tuple(float(value) for value in measurement.channels["x"])
                    temperatures_K = tuple(value + 273.15 for value in temperature_values) if "c" in unit.casefold() else temperature_values
                    if peak is not None:
                        peak_value = float(peak)
                        peaks.append(peak_value + 273.15 if "c" in unit.casefold() else peak_value)
                    normalized = tga_curves[measurement.measurement_id].get("derived", {}).get("normalized_mass_percent")
                    mass_values = tuple(float(value) for value in (normalized if normalized is not None else measurement.channels["intensity"]))
                    isoconversional_curves.append({"measurement_id": measurement.measurement_id, "temperature_K": temperatures_K, "mass": mass_values})
                kinetics = analyze_tga_multirate_kinetics(() if missing_peak else peaks, spec)
                kinetics["source_measurement_ids"] = [item.measurement_id for item in ordered_measurements]
                kinetics["kissinger"] = dict(kinetics)
                kinetics["isoconversional_ofw"] = analyze_tga_isoconversional_kinetics(isoconversional_curves, spec)
                if kinetics["isoconversional_ofw"].get("status") in {"computed", "computed_with_warning"}:
                    kinetics["status"] = "computed_with_warning"
                    kinetics.pop("unavailable_reason", None)
                self._metrics["kinetics"] = kinetics
                if kinetics.get("activation_energy_J_mol") is not None:
                    units["kinetics.activation_energy_J_mol"] = "J/mol"
                    methods["kinetics.activation_energy_J_mol"] = "kissinger_linear_fit"
                    method_parameters["kinetics.activation_energy_J_mol"] = spec.to_dict()
                methods["kinetics.isoconversional_ofw"] = "ozawa_flynn_wall_isoconversional"
                method_parameters["kinetics.isoconversional_ofw"] = spec.to_dict()
            except (KeyError, TypeError, ValueError):
                self._metrics["kinetics"] = {"status": "unavailable", "unavailable_reason": "kinetics_spec_invalid"}
        self.result.parameters = dict(self._metrics)
        self.result.validation_warnings = sorted(set(warnings))
        self.result.metadata.update(
            {
                "source_path": self._source_path,
                "canonical_template_id": self._template.template_id if self._template is not None else "",
                "analysis_scope": "descriptive_curve_and_material_neutral_event_candidates",
                "tga_processing_contract": "tga.processing.v1",
                "tga_processing_config": self.processing_config.to_dict(),
                "tga_kinetics_spec": (
                    self._template.payload.get("tga_kinetics", {})
                    if self._template is not None
                    else {}
                ),
                "units": units,
                "methods": methods,
                "parameters": method_parameters,
            }
        )
        return True

    def build_figure_definitions(self):
        return build_advanced_figure_definitions(self)

    def plot(self, output_dir: str = "") -> Dict[str, str]:
        if not self._measurements:
            return {}
        if not output_dir:
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
        axes.set_xlabel("Temperature / time")
        axes.set_ylabel("Mass / weight")
        if len(self._measurements) > 1:
            axes.legend()
        axes.grid(alpha=0.2)
        path = destination / "tga_curve.png"
        figure.savefig(path, dpi=150)
        plt.close(figure)
        return {"curve": str(path)}

    def get_parameters(self) -> Dict[str, Any]:
        return dict(self._metrics)


__all__ = ["TGAEngine", "TGAProcessingConfig"]
