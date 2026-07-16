from __future__ import annotations

import importlib
import importlib.util


def test_generic_v2_adapter_has_technique_neutral_public_home() -> None:
    module_name = "polynexus.core.figures.v2_adapter"

    assert importlib.util.find_spec(module_name) is not None
    public_adapter = importlib.import_module(module_name)
    legacy_adapter = importlib.import_module(
        "polynexus.core.saxs_engine.figure_v2_adapter"
    )

    assert (
        public_adapter.adapt_figure_definition
        is legacy_adapter.adapt_figure_definition
    )
    assert (
        public_adapter.adapt_temperature_figure_definition
        is legacy_adapter.adapt_temperature_figure_definition
    )
