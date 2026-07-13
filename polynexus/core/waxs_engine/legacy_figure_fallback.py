"""Compatibility fallback for WAXS runs without publication definitions."""

from __future__ import annotations

from typing import Any

from .waxs_output import generate_all_figures, generate_strain_figures
from .waxs_temperature import generate_temperature_figures


def generate_legacy_waxs_figures(engine: Any, output_dir: str) -> dict[str, str]:
    """Use the historical WAXS writers only when the new provider is empty."""

    submodule = str(getattr(engine, "active_submodule", "") or "")
    if submodule == "waxs.temperature" and getattr(engine, "_temperature_result", None) is not None:
        return generate_temperature_figures(
            engine._temperature_result,
            engine._dataset.scans if getattr(engine, "_dataset", None) else None,
            output_dir,
            config=engine._waxs_config,
        )
    if submodule == "waxs.strain" and getattr(engine, "_strain_result", None) is not None:
        return generate_strain_figures(
            engine._strain_result,
            engine._dataset.scans if getattr(engine, "_dataset", None) else None,
            output_dir,
            config=engine._waxs_config,
        )
    return generate_all_figures(engine._results, output_dir, config=engine._waxs_config)


__all__ = ["generate_legacy_waxs_figures"]
