"""DSC publication recipe dispatcher."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..figures.contracts import FigureDefinition
from .figure_isothermal import build_isothermal_dsc_figure_definitions
from .legacy_figure_provider import build_dsc_figure_definitions as build_legacy_dsc_figure_definitions
from .figure_nonisothermal import build_nonisothermal_dsc_figure_definitions
from .figure_standard import build_standard_dsc_figure_definitions


def build_dsc_figure_definitions(engine: Any) -> tuple[FigureDefinition, ...]:
    """Select exactly one DSC experiment-mode provider and order its roles."""

    if isinstance(engine, Sequence) and not isinstance(engine, (str, bytes)):
        return build_legacy_dsc_figure_definitions(engine)

    submodule = str(getattr(engine, "active_submodule", "") or "").strip().lower()
    if submodule == "dsc.isothermal":
        definitions = build_isothermal_dsc_figure_definitions(engine)
    elif submodule == "dsc.nonisothermal":
        definitions = build_nonisothermal_dsc_figure_definitions(engine)
    else:
        definitions = build_standard_dsc_figure_definitions(engine)
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

    return tuple(sorted(definitions, key=lambda item: (role_rank.get(item.publication_role, 99), display_order(item), item.figure_id)))


__all__ = ["build_dsc_figure_definitions"]
