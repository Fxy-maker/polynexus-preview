"""WAXS publication recipe dispatcher."""

from __future__ import annotations

from typing import Any

from ..figures.contracts import FigureDefinition
from .figure_static import build_static_waxs_figure_definitions
from .figure_temperature import build_temperature_waxs_figure_definitions
from .figure_strain import build_strain_waxs_figure_definitions


def build_waxs_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    submodule = str(getattr(engine, "active_submodule", "") or "").strip().lower()
    builder = {
        "waxs.temperature": build_temperature_waxs_figure_definitions,
        "waxs.strain": build_strain_waxs_figure_definitions,
    }.get(submodule, build_static_waxs_figure_definitions)
    definitions = tuple(builder(engine))
    role_rank = {"main": 0, "si": 1, "diagnostic": 2}

    def display_order(item: FigureDefinition) -> int:
        recipe = item.recipe if isinstance(item.recipe, dict) else {}
        parameters = recipe.get("parameters", {})
        if not isinstance(parameters, dict):
            return 0
        try:
            return int(parameters.get("display_order", 0))
        except (TypeError, ValueError):
            return 0

    return tuple(
        sorted(
            definitions,
            key=lambda item: (
                role_rank.get(item.publication_role, 99),
                display_order(item),
                item.figure_id,
            ),
        )
    )


__all__ = ["build_waxs_figure_definitions"]
