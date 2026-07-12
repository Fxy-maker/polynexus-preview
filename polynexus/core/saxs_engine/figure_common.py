"""Immutable views over existing SAXS frame outputs for figure providers."""

from __future__ import annotations

import copy
from collections.abc import Sequence as SequenceABC
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True)
class SAXSFrameView:
    """Provider-safe view that never re-runs analysis or mutates engine state."""

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
        object.__setattr__(self, "parameters", _freeze_value(self.parameters))

    def to_payload(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "label": self.label,
            "condition": _payload_value(self.condition),
            "q": _payload_value(self.q),
            "intensity": _payload_value(self.intensity),
            "parameters": _payload_value(self.parameters),
            "source_path": self.source_path,
        }


def _freeze_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        frozen = np.array(value, copy=True)
        frozen.setflags(write=False)
        return frozen
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_value(item) for item in value)
    if isinstance(value, SequenceABC) and not isinstance(value, (str, bytes, bytearray)):
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
        return [_payload_value(item) for item in sorted(value, key=repr)]
    if isinstance(value, (list, tuple)):
        return [_payload_value(item) for item in value]
    return value


def _frame_label(analysis: Any, parameters: Mapping[str, Any], source_path: str, index: int) -> str:
    label = str(getattr(analysis, "label", "") or "").strip()
    if label:
        return label
    label = str(parameters.get("label") or parameters.get("file") or "").strip()
    if label:
        return Path(label).stem
    return Path(source_path).stem if source_path else f"frame_{index}"


def frame_views_from_engine(engine: Any) -> tuple[SAXSFrameView, ...]:
    """Freeze the engine's emitted frame arrays and parameter dictionaries."""

    batch_results = tuple(getattr(engine, "_batch_results", ()) or ())
    batch_params = tuple(getattr(engine, "_batch_params", ()) or ())
    q_list = tuple(getattr(engine, "_q_list", ()) or ())
    intensity_list = tuple(getattr(engine, "_I_list", ()) or ())
    conditions = tuple(getattr(engine, "_conditions", ()) or ())
    file_list = tuple(getattr(engine, "_file_list", ()) or ())
    batch_count = max(
        len(batch_results), len(batch_params), len(q_list), len(intensity_list),
        len(conditions), len(file_list),
    )
    if batch_count > 0:
        views: list[SAXSFrameView] = []
        for index in range(batch_count):
            analysis = batch_results[index] if index < len(batch_results) else None
            raw_parameters = batch_params[index] if index < len(batch_params) else None
            if not isinstance(raw_parameters, Mapping):
                raw_parameters = getattr(analysis, "final_parameters", {})
            parameters = raw_parameters if isinstance(raw_parameters, Mapping) else {}
            q = q_list[index] if index < len(q_list) else getattr(analysis, "q", ())
            intensity = (
                intensity_list[index]
                if index < len(intensity_list)
                else getattr(analysis, "I", ())
            )
            condition = conditions[index] if index < len(conditions) else getattr(
                analysis, "condition_value", np.nan
            )
            source_path = str(file_list[index]) if index < len(file_list) else ""
            views.append(
                SAXSFrameView(
                    index=index,
                    label=_frame_label(analysis, parameters, source_path, index),
                    condition=condition,
                    q=q,
                    intensity=intensity,
                    analysis=analysis,
                    parameters=parameters,
                    source_path=source_path,
                )
            )
        return tuple(views)

    analysis = getattr(engine, "_analysis", None)
    if analysis is None:
        return ()
    q = getattr(engine, "_q", None)
    intensity = getattr(engine, "_I", None)
    parameters = getattr(analysis, "final_parameters", {})
    if not isinstance(parameters, Mapping):
        parameters = {}
    source_path = str(file_list[0]) if file_list else ""
    condition = getattr(analysis, "condition_value", np.nan)
    return (
        SAXSFrameView(
            index=0,
            label=_frame_label(analysis, parameters, source_path, 0),
            condition=condition,
            q=() if q is None else q,
            intensity=() if intensity is None else intensity,
            analysis=analysis,
            parameters=parameters,
            source_path=source_path,
        ),
    )


__all__ = ["SAXSFrameView", "frame_views_from_engine"]
