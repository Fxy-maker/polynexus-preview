"""Pure value-mapping helpers used by the chart editor."""

from __future__ import annotations

from typing import Any, Mapping


def annotation_line_style_value(current_text: Any, options: Mapping[str, str]) -> str:
    return options.get(str(current_text or "Solid"), "-")


def annotation_marker_value(current_text: Any, options: Mapping[str, str]) -> str:
    return options.get(str(current_text or "None"), "")


def line_style_label_for_value(value: Any, options: Mapping[str, str]) -> str:
    value = str(value or "-")
    for label, token in options.items():
        if token == value:
            return label
    return "Solid"


def marker_label_for_value(value: Any, options: Mapping[str, str]) -> str:
    value = str(value or "")
    for label, token in options.items():
        if token == value:
            return label
    return "None"


def generated_plot_series_marker_value(figure_object: Any) -> str:
    if not isinstance(figure_object, dict):
        return ""
    style = figure_object.get("style", {}) if isinstance(figure_object.get("style"), dict) else {}
    marker = str(style.get("marker", "") or "")
    if marker:
        return marker
    if str(figure_object.get("chart_kind", "") or "") == "scatter":
        return "o"
    return ""


def format_generated_grid_label(value: Any) -> str:
    try:
        number = float(value)
    except Exception:
        return str(value or "").strip()
    if number.is_integer():
        return str(int(number))
    return str(number)


def coerce_plot_value(value: Any) -> Any:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return value


def optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None
