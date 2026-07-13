from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.waxs_engine.figure_temperature import build_temperature_waxs_figure_definitions


def _frame(index: int, *, r_squared: float = 0.95) -> SimpleNamespace:
    return SimpleNamespace(
        label=f"T={20 + index * 10} C",
        two_theta=np.arange(5.0),
        I=np.asarray([1.0, 2.0, 4.0 + index, 2.0, 1.0]),
        I_fit=np.asarray([1.0, 2.0, 4.0 + index, 2.0, 1.0]),
        I_instrument_background=np.zeros(5),
        peaks=[{"two_theta": 2.0 + index * 0.1}],
        parameters={"Xc_pct": 20.0 + index * 2.0, "D_Scherrer_nm": 10.0 + index},
        r_squared=r_squared,
        size_reliability_status="reliable",
        sector_used="full",
        quality_flags=[],
    )


def _temperature_engine(*, valid_frames: int = 4, axis_ready: bool = True) -> SimpleNamespace:
    results = [_frame(index) for index in range(valid_frames)]
    temperature_result = SimpleNamespace(
        temperatures=[20.0 + index * 10.0 for index in range(valid_frames)],
        results=results,
        Xc_vs_T=[20.0 + index * 2.0 for index in range(valid_frames)],
        D_Scherrer_vs_T=[10.0 + index for index in range(valid_frames)],
        peak_family_tracks=[],
        transitions=[],
        parameters={"temperature_axis_ready": axis_ready, "frame_evidence": []},
    )
    return SimpleNamespace(_temperature_result=temperature_result, _results=results)


def _definition(definitions, figure_id: str):
    return next(item for item in definitions if item.figure_id == figure_id)


def test_reliable_temperature_sequence_creates_evolution_main() -> None:
    definitions = build_temperature_waxs_figure_definitions(_temperature_engine(valid_frames=4))
    assert _definition(definitions, "waxs.temperature.evolution").publication_role == "main"


def test_trend_requires_three_reliable_frames() -> None:
    definitions = build_temperature_waxs_figure_definitions(_temperature_engine(valid_frames=2))
    assert "waxs.temperature.trend" not in {item.figure_id for item in definitions if item.publication_role == "main"}


def test_axis_ambiguity_is_diagnostic() -> None:
    definitions = build_temperature_waxs_figure_definitions(_temperature_engine(valid_frames=4, axis_ready=False))
    assert all(item.publication_role != "main" for item in definitions)
    assert any(item.figure_id == "waxs.temperature.sequence.diagnostic" for item in definitions)
