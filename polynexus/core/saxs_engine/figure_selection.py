"""Small, deterministic dispatch contracts for SAXS figure production."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SAXSFigureModeDecision:
    mode: str
    reason: str


def _declared_mode(engine: Any) -> str:
    condition_mode = str(getattr(engine, "_condition_type", "") or "").strip().lower()
    config_mode = str(
        getattr(getattr(engine, "cfg", None), "experiment_type", "") or ""
    ).strip().lower()
    if condition_mode in {"temperature", "strain"}:
        return condition_mode
    if config_mode in {"temperature", "strain"}:
        return config_mode
    if condition_mode == "static" or config_mode == "static":
        return "static"
    return "static"


def resolve_saxs_figure_mode(engine: Any) -> SAXSFigureModeDecision:
    """Resolve completed analysis state before consulting configuration hints."""

    temperature_result = getattr(engine, "_temperature_result", None)
    strain_result = getattr(engine, "_strain_result", None)
    if temperature_result is not None and strain_result is not None:
        return SAXSFigureModeDecision("unsupported", "mixed_completed_series")
    if temperature_result is not None:
        return SAXSFigureModeDecision("temperature", "completed_temperature_result")
    if strain_result is not None:
        return SAXSFigureModeDecision("strain", "completed_strain_result")

    declared = _declared_mode(engine)
    if declared == "temperature":
        return SAXSFigureModeDecision("incomplete", "temperature_result_missing")
    if declared == "strain":
        return SAXSFigureModeDecision("incomplete", "strain_result_missing")
    return SAXSFigureModeDecision("static", "static_analysis_state")


__all__ = ["SAXSFigureModeDecision", "resolve_saxs_figure_mode"]
