from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

import pytest

from polynexus.core.engine import AnalysisResult, get_engine
from polynexus.core.joint.coordinator import JointCoordinator
from polynexus.core.joint.dataset import build_joint_hub_report, collect_joint_dataset
from polynexus.data.sample_db import SampleDB
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries


def _real_sources() -> tuple[tuple[str, str, Path], ...]:
    root = Path(__file__).resolve().parents[1] / "\u6d4b\u8bd5\u6570\u636e"
    return (
        ("dsc", "dsc.standard", next((root / "dsc").rglob("FXY-PA6.txt"), root / "missing")),
        (
            "saxs",
            "saxs.static",
            next(
                (root / "saxs").rglob("8-000-s_0_00000_with_mask.edf"),
                root / "missing",
            ),
        ),
        ("waxs", "waxs.static", next((root / "waxs").rglob("PA6.raw"), root / "missing")),
    )


def _iter_mappings(value: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(value, dict):
        return
    yield value
    for nested in value.values():
        if isinstance(nested, dict):
            yield from _iter_mappings(nested)


def _first_finite(payload: dict[str, Any], keys: tuple[str, ...]) -> float:
    for mapping in _iter_mappings(payload):
        for key in keys:
            value = mapping.get(key)
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(numeric):
                return numeric
    return math.nan


def _joint_summary(technique: str, result: AnalysisResult) -> dict[str, float]:
    if technique == "dsc":
        return {
            "Xc_pct": _first_finite(result.parameters, ("Xc_pct",)),
            "Tm_peak_C": _first_finite(result.parameters, ("Tm_peak_C",)),
        }
    if technique == "saxs":
        return {
            "L_nm": _first_finite(result.parameters, ("L_nm", "long_period_nm", "L_best")),
            "lc_nm": _first_finite(result.parameters, ("lc_nm", "crystalline_thickness_nm")),
            "phi_c": _first_finite(result.parameters, ("phi_c", "crystallinity")),
        }
    return {
        "Xc_pct": _first_finite(result.parameters, ("Xc_pct",)),
        "D_Scherrer_nm": _first_finite(result.parameters, ("D_Scherrer_nm", "D_nm")),
    }


def test_real_engine_runs_persist_into_joint_report_and_manifest(tmp_path: Path) -> None:
    sources = _real_sources()
    missing = [str(path) for _, _, path in sources if not path.exists()]
    if missing:
        pytest.skip(f"real Joint fixtures unavailable: {missing}")

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6 real Joint acceptance")
    batch_id = db.create_batch(
        sample_id,
        "real-static-cross-technique",
        instrument="fixture-real",
        condition_type="ambient",
    )
    output_root = tmp_path / "real-runs"
    source_run_ids: dict[str, str] = {}

    for technique, submodule, source in sources:
        technique_output = output_root / technique
        result = get_engine(
            technique,
            config={"fig_format": "png"},
            submodule_id=submodule,
        ).run_pipeline(str(source), str(technique_output))
        assert result.validation_passed is True
        source_run_ids[technique] = db.create_analysis_run(
            batch_id,
            technique,
            submodule=submodule,
            parameters=result.parameters,
            results_summary=_joint_summary(technique, result),
            analysis_evidence=result.analysis_evidence,
            output_dir=str(technique_output),
            confirmed=True,
        )
        db.add_data_file(
            batch_id,
            str(source),
            technique,
            submodule=submodule,
            file_type=source.suffix.lower(),
        )

    rows = collect_joint_dataset(db)
    assert len(rows) == 1
    assert rows[0].technique_count == 3
    assert {rows[0].run(technique).technique for technique in source_run_ids} == {
        "dsc",
        "saxs",
        "waxs",
    }

    report = build_joint_hub_report(rows)
    assert report["rows"]
    assert report["validations"]
    assert report["ai_context"]["scope"]

    joint_output = tmp_path / "joint-output"
    published_report = JointCoordinator().publish_hub_report(
        rows,
        joint_output,
        run_id="real-joint-run",
    )
    assert published_report["figure_publication"]["run_id"] == "real-joint-run"
    manifest = Path(published_report["figure_publication"]["manifest"])
    assert manifest.is_file()
    entries = build_active_manifest_gallery_entries(joint_output)
    assert {entry.figure_id for entry in entries} == {
        "joint.series.crystallinity",
        "joint.series.multiscale",
        "joint.series.coverage",
    }
    assert {entry.run_id for entry in entries} == {"real-joint-run"}

    validation_sources = published_report["validations"][0]["provenance"]["sources"]
    assert {validation_sources[key]["run_id"] for key in ("dsc", "saxs")} <= set(
        source_run_ids.values()
    )
