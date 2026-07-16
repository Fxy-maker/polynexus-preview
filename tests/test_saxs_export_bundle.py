from __future__ import annotations

import csv
import json
from types import SimpleNamespace

import numpy as np

from polynexus.core.engine import AnalysisResult
from polynexus.core.saxs_engine.config import SAXSConfig
import polynexus.core.saxs_export_bundle as export_module
from polynexus.core.saxs_export_bundle import export_saxs_bundle


def _engine() -> SimpleNamespace:
    result = AnalysisResult(
        technique="saxs",
        parameters={"L_nm": 12.4},
        raw_data={
            "q": np.asarray([0.1, 0.2, 0.3]),
            "I": np.asarray([10.0, 8.0, 5.0]),
            "I_smooth": np.asarray([9.5, 7.5, 4.5]),
        },
    )
    return SimpleNamespace(
        result=result,
        cfg=SAXSConfig(q_min=0.12, q_max=2.2),
        _analysis=None,
        _batch_results=[],
        _temperature_result=None,
        _strain_result=None,
        _q_list=[],
        _I_list=[],
        _processed_list=[],
        _file_list=[],
    )


def test_export_saxs_bundle_writes_reproducible_core_artifacts(tmp_path) -> None:
    bundle = export_saxs_bundle(_engine(), str(tmp_path / "bundle"))

    assert bundle.status == "ok"
    root = tmp_path / "bundle"
    assert (root / "bundle_manifest.json").exists()
    assert (root / "analysis_result.json").exists()
    assert (root / "config_snapshot.json").exists()
    assert (root / "provenance.json").exists()
    assert list((root / "data" / "profiles").glob("*.csv"))
    assert json.loads((root / "config_snapshot.json").read_text())["q_min"] == 0.12


def test_export_saxs_bundle_defends_non_mapping_parameter_rows(tmp_path, monkeypatch) -> None:
    engine = _engine()
    engine._analysis = SimpleNamespace(final_parameters={"L_nm": 12.4})
    monkeypatch.setattr(
        export_module,
        "_parameter_payload",
        lambda _engine, mode: {
            "mode": mode, "summary": {}, "rows": [None, {"L_nm": 12.4}],
            "quality_flags": {}, "validation_warnings": [],
        },
    )

    bundle = export_saxs_bundle(engine, str(tmp_path / "mixed_rows"))

    assert bundle.status == "ok"
    with (tmp_path / "mixed_rows" / "data" / "parameters.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        assert list(csv.DictReader(handle)) == [{"L_nm": ""}, {"L_nm": "12.4"}]


def test_export_saxs_bundle_returns_failed_status_if_manifest_fallback_also_fails(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(export_module, "_write_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("write failed")))

    bundle = export_saxs_bundle(_engine(), str(tmp_path / "failed"))

    assert bundle.status == "failed"
    assert any(error.startswith("export_failed:") for error in bundle.errors)
