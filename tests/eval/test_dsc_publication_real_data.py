from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from polynexus.core.figure_assets import read_figure_asset_dimensions
from polynexus.core.dsc import DSCEngine
from polynexus.core.dsc_engine.figure_provider import build_dsc_figure_definitions
from polynexus.core.figures.production import FigureProductionPublisher


def _assert_ready_manifest(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["figures"]
    for figure in payload["figures"]:
        assert figure["status"] == "ready"
        assert figure["capability_report"]["object_editing"] is True
        assert {"preview", "png", "pdf", "svg", "tiff"}.issubset(figure["assets"])
        tiff = path.parent / figure["assets"]["tiff"]
        assert read_figure_asset_dimensions(tiff)[2] == 600


def test_real_dsc_standard_scan_publishes_audited_editable_assets(tmp_path: Path) -> None:
    engine = DSCEngine()
    engine.active_submodule = "dsc.standard"
    source = Path(__file__).parent / "synth_data" / "dsc_synth_heating_standard.xy"
    assert engine.load(str(source))
    assert engine.preprocess()
    assert engine.analyze()
    engine.plot(str(tmp_path))
    _assert_ready_manifest(Path(engine.result.metadata["figure_manifest"]))


def test_isothermal_and_nonisothermal_completed_evidence_publish(tmp_path: Path) -> None:
    avrami = SimpleNamespace(
        label="150 C",
        t_data=np.arange(6.0),
        Xt_data=np.array([0.02, 0.12, 0.35, 0.60, 0.82, 0.95]),
        Xt_fit=np.array([0.01, 0.13, 0.34, 0.59, 0.81, 0.94]),
        n=2.0,
        k=0.1,
        t_half_min=3.0,
        r_squared=0.97,
        quality_flags=[],
    )
    iso_engine = SimpleNamespace(active_submodule="dsc.isothermal", _results=[], _kinetics_data={"avrami": avrami, "avrami_series": [avrami]})
    iso_defs = build_dsc_figure_definitions(iso_engine)
    iso = FigureProductionPublisher().publish(output_root=tmp_path / "isothermal", technique="dsc", definitions=iso_defs, profile_id="dsc_publication")
    assert {entry.figure_id for entry in iso.manifest.figures} == {"dsc.isothermal.avrami", "dsc.isothermal.series"}
    _assert_ready_manifest(tmp_path / "isothermal" / "runs" / iso.run_id / "figure_manifest.json")

    curves = [
        SimpleNamespace(label="1 K/min", T_xt_C=np.arange(5.0), Xt=np.linspace(0.1, 0.9, 5)),
        SimpleNamespace(label="2 K/min", T_xt_C=np.arange(5.0) + 1.0, Xt=np.linspace(0.1, 0.9, 5)),
    ]
    series = SimpleNamespace(curves=curves)
    kissinger = SimpleNamespace(rates=[1.0, 2.0, 5.0], r_squared=0.96, kissinger_Ea_kJmol=120.0, quality_flags=[])
    non_engine = SimpleNamespace(active_submodule="dsc.nonisothermal", _results=[], _kinetics_data={"non_isothermal": series, "kissinger": kissinger})
    non_defs = build_dsc_figure_definitions(non_engine)
    non = FigureProductionPublisher().publish(output_root=tmp_path / "nonisothermal", technique="dsc", definitions=non_defs, profile_id="dsc_publication")
    assert {entry.figure_id for entry in non.manifest.figures} == {"dsc.nonisothermal.conversion", "dsc.nonisothermal.kissinger"}
    _assert_ready_manifest(tmp_path / "nonisothermal" / "runs" / non.run_id / "figure_manifest.json")
