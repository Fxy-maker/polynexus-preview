from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from polynexus.core.waxs import WAXSEngine
from polynexus.core.waxs_engine.core import WAXSResult
from polynexus.core.waxs_engine.figure_provider import build_waxs_figure_definitions


def _result() -> WAXSResult:
    return WAXSResult(
        label="static",
        two_theta=np.arange(5.0),
        I=np.asarray([1.0, 2.0, 4.0, 2.0, 1.0]),
        peaks=[{"two_theta": 2.0}],
        Xc_pct=30.0,
        D_Scherrer_nm=12.0,
        r_squared=0.95,
        size_reliability_status="reliable",
    )


def test_waxs_engine_publishes_manifest_backed_assets(tmp_path: Path) -> None:
    engine = WAXSEngine()
    engine.active_submodule = "waxs.static"
    engine._results = [_result()]
    assets = engine.plot(str(tmp_path))
    manifest = Path(engine.result.metadata["figure_manifest"])
    assert manifest.is_file()
    assert assets == engine.result.figures
    assert any(path.endswith(".svg") for path in assets.values())


def test_dispatcher_uses_only_active_mode() -> None:
    temperature_result = SimpleNamespace(
        temperatures=[20.0],
        results=[_result()],
        Xc_vs_T=[30.0],
        D_Scherrer_vs_T=[12.0],
        parameters={"temperature_axis_ready": True},
        transitions=[],
    )
    engine = SimpleNamespace(active_submodule="waxs.temperature", _temperature_result=temperature_result, _results=[_result()])
    definitions = build_waxs_figure_definitions(engine)
    assert any(item.figure_id == "waxs.temperature.evolution" for item in definitions)
    assert not any(item.figure_id.startswith("waxs.strain") for item in definitions)
