"""Immutable views over existing SAXS frame outputs for figure recipes."""

from __future__ import annotations

import copy
from collections.abc import Sequence as SequenceABC, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np

from polynexus.plotting.sci_style import AXIS_LABELS, WONG_COLORS

from ..figures.contracts import FigureDefinition


@dataclass(frozen=True)
class SAXSFrameView:
    """Provider-safe frame evidence assembled from already-emitted values.

    Arrays and parameters are copied into immutable containers. ``analysis``
    remains the original evidence reference and is never mutated or serialized.
    """

    index: int
    label: str
    condition: Any
    q: np.ndarray
    intensity: np.ndarray
    analysis: Any
    parameters: Mapping[str, Any]
    source_path: str = ""

    def __post_init__(self) -> None:
        q = np.array(self.q, copy=True)
        intensity = np.array(self.intensity, copy=True)
        q.setflags(write=False)
        intensity.setflags(write=False)
        object.__setattr__(self, "q", q)
        object.__setattr__(self, "intensity", intensity)
        object.__setattr__(
            self,
            "parameters",
            _freeze_value(self.parameters),
        )

    def to_payload(self) -> dict[str, Any]:
        """Return a persistence-safe payload without the analysis object."""

        return {
            "index": self.index,
            "label": self.label,
            "condition": _payload_value(self.condition),
            "q": _payload_value(self.q),
            "intensity": _payload_value(self.intensity),
            "parameters": _payload_value(self.parameters),
            "source_path": self.source_path,
        }


def _sci_axis_label(label: str, *, y_axis: bool = False) -> str:
    text = str(label or "").lower()
    if "temperature" in text:
        return AXIS_LABELS["T"]
    if "strain" in text:
        return AXIS_LABELS["strain"]
    if "time" in text:
        return AXIS_LABELS["time"]
    if "sample" in text:
        return AXIS_LABELS["sample"]
    if "crystall" in text:
        return AXIS_LABELS["phi_c_saxs"]
    if "invariant" in text or "q_star" in text:
        return AXIS_LABELS["Q_star"]
    if "thickness" in text or "length" in text or text in {"l", "l_nm"}:
        return AXIS_LABELS["L"]
    if "correlation" in text or "gamma" in text:
        return AXIS_LABELS["gamma"] if y_axis else AXIS_LABELS["r"]
    if "distance" in text or text in {"r", "r_nm"}:
        return AXIS_LABELS["r"]
    if "intensity" in text or text in {"i", "i(q)"}:
        return AXIS_LABELS["I_saxs"]
    if "scattering" in text or text.startswith("q"):
        return AXIS_LABELS["q"]
    return AXIS_LABELS["I_saxs"] if y_axis else AXIS_LABELS["q"]


def polish_saxs_publication_definitions(
    definitions: Sequence[FigureDefinition],
) -> tuple[FigureDefinition, ...]:
    """Apply shared SCI panel labels, axis vocabulary, and Wong colors."""

    polished: list[FigureDefinition] = []
    for definition in definitions:
        panels = tuple(
            replace(
                panel,
                title="",
                panel_label=panel.panel_label or f"({chr(ord('a') + index)})",
                x_axis=replace(panel.x_axis, label=_sci_axis_label(panel.x_axis.label), unit=""),
                y_axis=replace(panel.y_axis, label=_sci_axis_label(panel.y_axis.label, y_axis=True), unit=""),
            )
            for index, panel in enumerate(definition.layout.panels)
        )
        objects: list[dict[str, object]] = []
        for index, obj in enumerate(definition.objects):
            item = dict(obj)
            style = dict(item.get("style", {}))
            if "color" in style:
                style["color"] = WONG_COLORS[index % len(WONG_COLORS)]
            item["style"] = style
            objects.append(item)
        polished.append(
            replace(
                definition,
                layout=replace(definition.layout, panels=panels),
                objects=tuple(objects),
            )
        )
    return tuple(polished)


def _freeze_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        frozen_array = np.array(value, copy=True)
        frozen_array.setflags(write=False)
        return frozen_array
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    if isinstance(value, SequenceABC) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return tuple(_freeze_value(item) for item in value)
    return copy.deepcopy(value)


def _payload_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return _payload_value(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _payload_value(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return [
            _payload_value(item)
            for item in sorted(value, key=repr)
        ]
    if isinstance(value, (list, tuple)):
        return [_payload_value(item) for item in value]
    return value


def _frame_label(
    analysis: Any,
    parameters: Mapping[str, Any],
    source_path: str,
    index: int,
) -> str:
    analysis_label = str(getattr(analysis, "label", "") or "").strip()
    if analysis_label:
        return analysis_label

    parameter_label = str(
        parameters.get("label") or parameters.get("file") or ""
    ).strip()
    if parameter_label:
        return Path(parameter_label).stem
    if source_path:
        return Path(source_path).stem
    return f"frame_{index}"


def frame_views_from_engine(engine: Any) -> tuple[SAXSFrameView, ...]:
    """Build frame views without invoking analysis or recalculating parameters."""

    batch_views: list[SAXSFrameView] = []
    batch_results = _sequence_or_empty(getattr(engine, "_batch_results", ()))
    batch_params = _sequence_or_empty(getattr(engine, "_batch_params", ()))
    q_list = _sequence_or_empty(getattr(engine, "_q_list", ()))
    intensity_list = _sequence_or_empty(getattr(engine, "_I_list", ()))
    conditions = _sequence_or_empty(getattr(engine, "_conditions", ()))
    file_list = _sequence_or_empty(getattr(engine, "_file_list", ()))

    single_analysis = getattr(engine, "_analysis", None)
    batch_count = max(
        len(batch_results),
        len(batch_params),
        len(q_list),
        len(intensity_list),
        len(conditions),
        len(file_list),
    )
    for index in range(batch_count):
        analysis = batch_results[index] if index < len(batch_results) else None
        raw_parameters = batch_params[index] if index < len(batch_params) else None
        parameters = raw_parameters if isinstance(raw_parameters, Mapping) else {}
        if not parameters and analysis is not None:
            candidate = getattr(analysis, "final_parameters", {})
            if isinstance(candidate, Mapping):
                parameters = candidate
        q = q_list[index] if index < len(q_list) else getattr(analysis, "q", ())
        intensity = (
            intensity_list[index]
            if index < len(intensity_list)
            else getattr(analysis, "I_smooth", None)
        )
        if intensity is None:
            intensity = getattr(analysis, "I", ())
        condition = (
            conditions[index]
            if index < len(conditions)
            else getattr(analysis, "condition_value", np.nan)
        )
        source_path = (
            file_list[index]
            if index < len(file_list)
            else parameters.get("file", "")
        )
        if analysis is None and not np.asarray(q).size and not np.asarray(intensity).size:
            continue
        parameter_mapping = parameters if isinstance(parameters, Mapping) else {}
        source_text = str(source_path or "")
        batch_views.append(
            SAXSFrameView(
                index=index,
                label=_frame_label(
                    analysis,
                    parameter_mapping,
                    source_text,
                    index,
                ),
                condition=condition,
                q=q,
                intensity=intensity,
                analysis=analysis,
                parameters=parameter_mapping,
                source_path=source_text,
            )
        )
    if batch_views:
        return tuple(batch_views)

    analysis = single_analysis
    if analysis is None:
        return ()

    q = getattr(engine, "_q", None)
    if q is None:
        q = getattr(analysis, "q", None)
    intensity = getattr(engine, "_I", None)
    if intensity is None:
        intensity = getattr(analysis, "I", None)

    parameters = getattr(analysis, "final_parameters", None)
    if not isinstance(parameters, Mapping):
        parameters = batch_params[0] if batch_params and isinstance(batch_params[0], Mapping) else {}

    condition = getattr(analysis, "condition_value", np.nan)
    if conditions:
        condition = conditions[0]
    source_path = str(file_list[0] or "") if file_list else ""

    return (
        SAXSFrameView(
            index=0,
            label=_frame_label(analysis, parameters, source_path, 0),
            condition=condition,
            q=q,
            intensity=intensity,
            analysis=analysis,
            parameters=parameters,
            source_path=source_path,
        ),
    )


def _sequence_or_empty(value: Any) -> SequenceABC:
    """Normalize optional engine collections without truth-testing arrays."""

    if value is None:
        return ()
    if isinstance(value, np.ndarray):
        return tuple(value.reshape(-1).tolist())
    if isinstance(value, (str, bytes, bytearray)):
        return (value,)
    try:
        len(value)
    except TypeError:
        return (value,)
    return value
