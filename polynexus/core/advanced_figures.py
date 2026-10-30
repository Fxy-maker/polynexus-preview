"""Shared diagnostic FigureDefinitions for advanced polymer model outputs."""

from __future__ import annotations

import math
import re
from typing import Any, Iterable, Mapping, Sequence

from .figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)


_COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9")


def build_advanced_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    technique = str(getattr(engine, "name", "")).casefold()
    builders = {
        "tga": _tga_definitions,
        "dma": _dma_definitions,
        "rheology": _rheology_definitions,
        "mechanics": _mechanics_definitions,
    }
    builder = builders.get(technique)
    return () if builder is None else tuple(builder(engine))


def _tga_definitions(engine: Any) -> Iterable[FigureDefinition]:
    kinetics = _mapping(getattr(engine, "_metrics", {}).get("kinetics"))
    kissinger = _mapping(kinetics.get("kissinger", kinetics))
    temperatures = _floats(kissinger.get("peak_temperatures_K"))
    rates = _floats(kissinger.get("heating_rates"))
    if kissinger.get("status") in {"computed", "computed_with_warning"} and len(temperatures) == len(rates) >= 2:
        x = tuple(1.0 / value for value in temperatures)
        y = tuple(math.log(rate / temperature**2) for rate, temperature in zip(rates, temperatures, strict=True))
        activation = float(kissinger["activation_energy_J_mol"])
        gas = float(_mapping(kissinger.get("parameters")).get("gas_constant", 8.31446261815324))
        intercept = float(kissinger["intercept"])
        fit = tuple((-activation / gas) * value + intercept for value in x)
        source = _source(
            "tga-kissinger-data",
            (("inverse_temperature", "1/K", x), ("observed", "1", y), ("fitted", "1", fit)),
        )
        yield _definition(
            figure_id="tga.series.kissinger.001",
            technique="tga",
            title="TGA Multi-rate Kissinger Candidate",
            x=AxisDefinition("inverse_temperature", "Inverse peak temperature", "1/K"),
            y=AxisDefinition("log_rate_over_temperature_squared", "ln(β/Tp²)", "1"),
            sources=(source,),
            objects=(
                _series("kissinger-observed", source.source_id, "inverse_temperature", "observed", "Observed", _COLORS[0], "scatter"),
                _series("kissinger-fit", source.source_id, "inverse_temperature", "fitted", "Linear fit", _COLORS[1]),
            ),
            recipe_parameters={
                "model": "kissinger",
                "method": kissinger.get("method", "kissinger_linear_fit"),
                "source_measurement_ids": kinetics.get("source_measurement_ids", ()),
            },
        )
    isoconversional = _mapping(kinetics.get("isoconversional_ofw"))
    levels = _mapping(isoconversional.get("conversion_levels"))
    conversion: list[float] = []
    energy: list[float] = []
    for item in levels.values():
        record = _mapping(item)
        if record.get("status") not in {"computed", "computed_with_warning"}:
            continue
        conversion.append(float(record["conversion"]))
        energy.append(float(record["activation_energy_J_mol"]) / 1000.0)
    if conversion:
        source = _source("tga-ofw-data", (("conversion", "1", conversion), ("activation_energy", "kJ/mol", energy)))
        yield _definition(
            figure_id="tga.series.isoconversional.001",
            technique="tga",
            title="TGA Isoconversional Activation-Energy Candidates",
            x=AxisDefinition("conversion", "Conversion", "1"),
            y=AxisDefinition("activation_energy", "Activation energy", "kJ/mol"),
            sources=(source,),
            objects=(_series("ofw-energy", source.source_id, "conversion", "activation_energy", "OFW candidate", _COLORS[0], "scatter"),),
            recipe_parameters={
                "model": "ozawa_flynn_wall",
                "method": isoconversional.get(
                    "method", "ozawa_flynn_wall_isoconversional"
                ),
                "source_measurement_ids": isoconversional.get(
                    "source_measurement_ids", ()
                ),
            },
            display_order=2,
        )


def _dma_definitions(engine: Any) -> Iterable[FigureDefinition]:
    tts = _mapping(getattr(engine, "_metrics", {}).get("dma_tts"))
    if tts.get("status") not in {"computed", "computed_with_warning"}:
        return
    grouped = _group_points(tts.get("points", ()), value_key="modulus")
    sources: list[FigureDataSourceDefinition] = []
    objects: list[dict[str, Any]] = []
    for index, (temperature, points) in enumerate(grouped.items()):
        source = _source(
            f"dma-master-{index + 1:03d}",
            (
                ("frequency", str(tts.get("frequency_unit", "unknown")), [item["frequency"] for item in points]),
                ("modulus", str(tts.get("modulus_unit", "unknown")), [item["modulus"] for item in points]),
            ),
        )
        sources.append(source)
        objects.append(_series(f"dma-master-series-{index + 1:03d}", source.source_id, "frequency", "modulus", f"{temperature:g}", _COLORS[index % len(_COLORS)]))
    if sources:
        yield _definition(
            figure_id="dma.series.master-curve.001",
            technique="dma",
            title="DMA Time–Temperature Superposition Candidate",
            x=AxisDefinition("frequency", "Reduced frequency", str(tts.get("frequency_unit", "unknown")), "log"),
            y=AxisDefinition("modulus", "Modulus", str(tts.get("modulus_unit", "unknown")), "log"),
            sources=tuple(sources),
            objects=tuple(objects),
            recipe_parameters={
                "method": tts.get("method", "horizontal_frequency_shift"),
                "shift_mode": tts.get("shift_mode"),
                "shift_factors": tts.get("shift_factors"),
                "source_measurement_ids": tts.get("source_measurement_ids", ()),
            },
        )


def _rheology_definitions(engine: Any) -> Iterable[FigureDefinition]:
    metrics = _mapping(getattr(engine, "_metrics", {}).get("rheology_advanced"))
    cox = _mapping(metrics.get("cox_merz"))
    if cox.get("status") in {"computed", "computed_with_warning"}:
        frequency = _floats(cox.get("frequency"))
        shear_rate = _floats(cox.get("shear_rate"))
        complex_viscosity = _floats(cox.get("complex_viscosity_Pa_s"))
        steady_viscosity = _floats(cox.get("steady_viscosity_Pa_s"))
        if len(frequency) == len(shear_rate) == len(complex_viscosity) == len(steady_viscosity) and frequency:
            source = _source("rheology-cox-merz-data", (("frequency", "rad/s", frequency), ("complex_viscosity", "Pa*s", complex_viscosity), ("shear_rate", "1/s", shear_rate), ("steady_viscosity", "Pa*s", steady_viscosity)))
            yield _definition(
                figure_id="rheology.series.cox-merz.001",
                technique="rheology",
                title="Rheology Cox–Merz Diagnostic Comparison",
                x=AxisDefinition("rate", "Angular frequency / shear rate", "1/s", "log"),
                y=AxisDefinition("viscosity", "Viscosity", "Pa*s", "log"),
                sources=(source,),
                objects=(
                    _series("cox-merz-complex", source.source_id, "frequency", "complex_viscosity", "Complex viscosity", _COLORS[0]),
                    _series("cox-merz-steady", source.source_id, "shear_rate", "steady_viscosity", "Steady viscosity", _COLORS[1]),
                ),
                recipe_parameters={
                    "method": cox.get(
                        "method", "cox_merz_pointwise_comparison"
                    ),
                    "source_measurement_ids": cox.get(
                        "source_measurement_ids", ()
                    ),
                },
            )
    tts = _mapping(metrics.get("tts"))
    if tts.get("status") in {"computed", "computed_with_warning"}:
        grouped = _group_points(tts.get("points", ()), value_key="value")
        sources = []
        objects = []
        for index, (temperature, points) in enumerate(grouped.items()):
            source = _source(f"rheology-master-{index + 1:03d}", (("frequency", "unknown", [item["frequency"] for item in points]), ("value", "unknown", [item["value"] for item in points])))
            sources.append(source)
            objects.append(_series(f"rheology-master-series-{index + 1:03d}", source.source_id, "frequency", "value", f"{temperature:g}", _COLORS[index % len(_COLORS)]))
        if sources:
            yield _definition("rheology.series.master-curve.001", "rheology", "Rheology TTS Candidate", AxisDefinition("frequency", "Reduced frequency", "unknown", "log"), AxisDefinition("response", "Rheological response", "unknown", "log"), tuple(sources), tuple(objects), {"method": tts.get("method", "horizontal_frequency_shift"), "source_measurement_ids": tts.get("source_measurement_ids", ()), "shift_factors": _mapping(tts.get("parameters")).get("shift_factors", ())}, display_order=2)
    yield from _bound_measurement_figures(engine, metrics, technique="rheology", names=("thixotropy", "creep", "relaxation"), start_order=3)


def _mechanics_definitions(engine: Any) -> Iterable[FigureDefinition]:
    metrics = _mapping(getattr(engine, "_metrics", {}).get("mechanics_advanced"))
    cycles = _mapping(metrics.get("cycles"))
    if cycles.get("status") in {"computed", "computed_with_warning"}:
        cycle_ids = _floats(cycles.get("cycle_ids"))
        peak = _floats(cycles.get("peak_response"))
        if len(cycle_ids) == len(peak) and cycle_ids:
            source = _source("mechanics-cycle-envelope", (("cycle", "cycle", cycle_ids), ("peak_response", "unknown", peak)))
            yield _definition("mechanics.series.cycle-envelope.001", "mechanics", "Mechanical Cycle Peak Envelope", AxisDefinition("cycle", "Cycle", "cycle"), AxisDefinition("peak_response", "Peak response", "unknown"), (source,), (_series("cycle-envelope", source.source_id, "cycle", "peak_response", "Peak envelope", _COLORS[0]),), {"method": cycles.get("method", "cycle_peak_envelope"), "source_measurement_ids": cycles.get("source_measurement_ids", ())})
    fatigue = _mapping(metrics.get("fatigue"))
    if fatigue.get("status") in {"computed", "computed_with_warning"}:
        count = _floats(fatigue.get("cycle_count"))
        response = _floats(fatigue.get("response"))
        if len(count) == len(response) and count:
            source = _source("mechanics-fatigue-history", (("cycle_count", "cycle", count), ("response", "unknown", response)))
            yield _definition("mechanics.series.fatigue.001", "mechanics", "Mechanical Fatigue Response History", AxisDefinition("cycle_count", "Cycle count", "cycle", "log"), AxisDefinition("response", "Recorded response", "unknown"), (source,), (_series("fatigue-history", source.source_id, "cycle_count", "response", "Fatigue history", _COLORS[0]),), {"method": fatigue.get("method", "fatigue_response_history"), "source_measurement_ids": fatigue.get("source_measurement_ids", ())}, display_order=2)
    yield from _bound_measurement_figures(engine, metrics, technique="mechanics", names=("creep", "fracture"), start_order=3)


def _bound_measurement_figures(engine: Any, metrics: Mapping[str, Any], *, technique: str, names: Sequence[str], start_order: int) -> Iterable[FigureDefinition]:
    measurements = {item.measurement_id: item for item in tuple(getattr(engine, "_measurements", ()) or ())}
    for offset, name in enumerate(names):
        record = _mapping(metrics.get(name))
        if record.get("status") not in {"computed", "computed_with_warning"}:
            continue
        source_ids = tuple(str(value) for value in record.get("source_measurement_ids", ()))
        if not source_ids or source_ids[0] not in measurements:
            continue
        measurement = measurements[source_ids[0]]
        x_unit = str(measurement.units.get("x", "unknown"))
        y_unit = str(measurement.units.get("intensity", "unknown"))
        source = _source(f"{technique}-{name}-data", (("coordinate", x_unit, measurement.channels["x"]), ("response", y_unit, measurement.channels["intensity"])))
        yield _definition(
            f"{technique}.series.{name}.001",
            technique,
            f"{technique.upper()} {name.title()} Diagnostic Candidate",
            AxisDefinition("coordinate", "Recorded coordinate", x_unit),
            AxisDefinition("response", "Recorded response", y_unit),
            (source,),
            (_series(f"{technique}-{name}", source.source_id, "coordinate", "response", name.title(), _COLORS[offset % len(_COLORS)]),),
            {"source_measurement_ids": source_ids, "method": record.get("method")},
            display_order=start_order + offset,
        )


def _definition(
    figure_id: str,
    technique: str,
    title: str,
    x: AxisDefinition,
    y: AxisDefinition,
    sources: tuple[FigureDataSourceDefinition, ...],
    objects: tuple[dict[str, Any], ...],
    recipe_parameters: Mapping[str, Any],
    *,
    display_order: int = 1,
) -> FigureDefinition:
    return FigureDefinition(
        figure_id=figure_id,
        technique=technique,
        scope="series",
        category="diagnostic",
        title=title,
        layout=FigureLayoutDefinition(7.0, 4.5, 1, 1, (PanelDefinition("main", 0, 0, x, y, title=title, show_legend=len(objects) > 1),)),
        data_sources=sources,
        objects=objects,
        recipe={
            "module": "polynexus.core.advanced_figures",
            "function": "build_advanced_figure_definitions",
            "parameters": {
                **dict(recipe_parameters),
                "display_order": int(display_order),
            },
            "v2_adapter": technique,
        },
        style_profile="sci_default",
        publication_role="diagnostic",
        display_order=display_order,
    )


def _source(source_id: str, columns: Sequence[tuple[str, str, Sequence[Any]]]) -> FigureDataSourceDefinition:
    return FigureDataSourceDefinition(
        source_id=_slug(source_id),
        columns=tuple(DataColumnDefinition(name, unit) for name, unit, _ in columns),
        values={name: tuple(values) for name, _, values in columns},
    )


def _series(object_id: str, source_id: str, x: str, y: str, name: str, color: str, chart_kind: str = "line") -> dict[str, Any]:
    return {"id": _slug(object_id), "type": "plot_series", "chart_kind": chart_kind, "panel_id": "main", "name": name, "data_ref": source_id, "x_column": x, "y_column": y, "style": {"color": color, "line_width": 1.0}}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _floats(values: Any) -> tuple[float, ...]:
    if isinstance(values, (str, bytes, bytearray)) or values is None:
        return ()
    try:
        return tuple(float(value) for value in values)
    except (TypeError, ValueError):
        return ()


def _group_points(values: Any, *, value_key: str) -> dict[float, list[dict[str, float]]]:
    grouped: dict[float, list[dict[str, float]]] = {}
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        return grouped
    for value in values:
        item = _mapping(value)
        try:
            temperature = float(item["temperature"])
            point = {"frequency": float(item["frequency"]), value_key: float(item[value_key])}
        except (KeyError, TypeError, ValueError):
            continue
        grouped.setdefault(temperature, []).append(point)
    return grouped


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", str(value).casefold()).strip("-") or "item"


__all__ = ["build_advanced_figure_definitions"]
