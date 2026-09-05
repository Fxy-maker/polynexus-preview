"""Sample-neutral rheology engine for canonical table signals."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np

from .canonical_experiments import CanonicalExperiment, convert_one_dimensional_table
from .engine import BaseEngine, EngineCategory, register_technique
from .rheology_processing import RheologySignalSeries, analyze_rheology_group


RHEOLOGY_TABLE_EXTENSIONS = frozenset(
    {".csv", ".tsv", ".txt", ".dat", ".asc", ".xls", ".xlsx", ".xlsm"}
)


@register_technique("rheology")
class RheologyEngine(BaseEngine):
    """Deterministic rheology identities without material-model assumptions."""

    name = "rheology"
    label = "Rheology"
    icon = "R"
    category = EngineCategory.EXPERIMENTAL
    description = (
        "Rheometer tables: source-preserving steady-flow and oscillatory "
        "signals with dimensionally valid derived identities"
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
            self.log(f"No rheology table found at: {filepath}")
            return False
        self._source_path = str(source.resolve())
        outcome = convert_one_dimensional_table(
            source,
            technique="rheology",
            source_artifact_id=f"rheology-source:{self._source_path}",
        )
        if outcome.status != "ready" or outcome.template is None:
            reason = ", ".join(outcome.reason_codes) or outcome.status
            self.log(f"Rheology table conversion unavailable: {reason}")
            return False
        self._adopt_template(outcome.template)
        self.log(f"Loaded {len(self._measurements)} rheology signal(s)")
        return bool(self._measurements)

    def run_canonical_template(
        self,
        template: CanonicalExperiment,
        output_dir: str = "",
        *,
        skip_to: str | None = None,
    ):
        """Execute an already validated shared rheology template."""
        self._adopt_template(template)
        self.log(f"Loaded {len(self._measurements)} canonical rheology signal(s)")
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
            raise TypeError("rheology canonical execution requires a CanonicalExperiment")
        if template.template_id != "rheology_curve_1d.v1":
            raise ValueError("rheology canonical template id is unsupported")
        if str(template.payload.get("technique", "")).upper() != "RHEOLOGY":
            raise ValueError("rheology canonical template technique mismatch")
        measurements = tuple(template.measurements)
        if not measurements or any(item.family != "rheological_1d" for item in measurements):
            raise ValueError("rheology canonical template measurements are unsupported")
        self._template = template
        self._measurements = measurements
        self._source_path = str(measurements[0].source_locator["source_path"])

    def preprocess(self) -> bool:
        if not self._measurements:
            self.log("No rheology data loaded")
            return False
        return True

    def analyze(self) -> bool:
        if not self._measurements:
            self.log("No rheology data available")
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
                self.log(f"Invalid rheology signal: {measurement.measurement_id}")
                return False
            mapping = measurement.mapping
            axis_kind = (
                mapping.x_kind
                if mapping is not None
                else measurement.acquisition_metadata.get("axis_kind", "unknown")
            )
            signal_kind = measurement.acquisition_metadata.get(
                "signal_kind", "rheology_signal"
            )
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

        rheology_groups: dict[str, dict[str, Any]] = {}
        for group_id, group_items in grouped_signals.items():
            first_measurement, group_x, _ = group_items[0]
            first_mapping = first_measurement.mapping
            axis_kind = (
                first_mapping.x_kind
                if first_mapping is not None
                else first_measurement.acquisition_metadata.get("axis_kind", "unknown")
            )
            signal_series = tuple(
                RheologySignalSeries.create(
                    measurement_id=measurement.measurement_id,
                    signal_kind=str(
                        measurement.acquisition_metadata.get(
                            "signal_kind", "rheology_signal"
                        )
                    ),
                    unit=measurement.units.get("intensity", "unknown"),
                    values=signal,
                    x_values=x,
                )
                for measurement, x, signal in group_items
            )
            processed = analyze_rheology_group(
                group_x,
                axis_kind=str(axis_kind),
                axis_unit=first_measurement.units.get("x", "unknown"),
                signals=signal_series,
            )
            group_metrics = dict(processed.metrics)
            rheology_groups[group_id] = group_metrics
            metric_prefix = f"rheology_groups.{group_id}"
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
            for result_name, record in _derived_records(group_metrics):
                values = record.get("values")
                if values is None:
                    continue
                self.result.raw_data[f"{group_id}:{result_name}"] = np.asarray(
                    [np.nan if value is None else value for value in values],
                    dtype=float,
                )

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
            "rheology_groups": rheology_groups,
        }
        self.result.parameters = dict(self._metrics)
        self.result.validation_warnings = sorted(set(warnings))
        self.result.metadata.update(
            {
                "source_path": self._source_path,
                "canonical_template_id": (
                    self._template.template_id if self._template is not None else ""
                ),
                "analysis_scope": "material_neutral_rheology_identities",
                "rheology_processing_contract": "rheology.processing.v1",
                "units": units,
                "methods": methods,
                "parameters": method_parameters,
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
        axes.set_xlabel("Canonical rheology coordinate")
        axes.set_ylabel("Rheology signal")
        if len(self._measurements) > 1:
            axes.legend()
        axes.grid(alpha=0.2)
        path = destination / "rheology_curve.png"
        figure.savefig(path, dpi=150)
        plt.close(figure)
        return {"curve": str(path)}

    def get_parameters(self) -> Dict[str, Any]:
        return dict(self._metrics)


def _derived_records(metrics: dict[str, Any]):
    for name in (
        "derived_apparent_viscosity",
        "derived_shear_stress",
        "derived_shear_rate",
    ):
        record = metrics.get(name)
        if isinstance(record, dict):
            yield name, record
    oscillatory = metrics.get("oscillatory", {})
    if isinstance(oscillatory, dict):
        for name, record in oscillatory.items():
            if isinstance(record, dict):
                yield f"oscillatory:{name}", record


__all__ = ["RHEOLOGY_TABLE_EXTENSIONS", "RheologyEngine"]
