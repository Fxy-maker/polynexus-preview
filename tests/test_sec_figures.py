from __future__ import annotations

import json
from pathlib import Path

import pytest

from polynexus.core.compute import ComputeRunService
from polynexus.core.compute.models import ComputeResult
from polynexus.core.figures.validation import validate_figure_definition
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.core.sec import SECEngine


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _uncalibrated_engine(source: Path) -> SECEngine:
    engine = SECEngine()
    assert engine.load(str(source))
    assert engine.preprocess()
    assert engine.analyze()
    return engine


def _calibrated_engine(source: Path) -> SECEngine:
    run = ComputeRunService().run_direct(
        technique="sec",
        path=source,
        output_dir="",
        pipeline_options={
            "sec_analysis": {
                "response_measurement_id": "sheet-0-table-0",
                "calibration_coordinates": [1.0, 2.0, 3.0],
                "calibration_molar_masses": [1000.0, 100.0, 10.0],
                "calibration_id": "polystyrene-kit-v1",
                "standard_source": "lab-record://sec-standards/2026-09",
                "standard_ids": ["PS-1000", "PS-100", "PS-10"],
                "distribution_mode": "mass",
                "coordinate_kind": "elution_volume",
                "calibration_unit": "mL",
            }
        },
    )
    assert run.status == "completed"
    assert run.canonical_template is not None
    engine = SECEngine()
    result = engine.run_canonical_template(run.canonical_template)
    assert result.parameters["sec_groups"]["sheet-0-table-0"][
        "molecular_weight_summary"
    ]["status"] == "computed"
    return engine


def test_uncalibrated_sec_emits_only_shared_chromatogram_definition(
    tmp_path: Path,
) -> None:
    engine = _uncalibrated_engine(
        _write(
            tmp_path / "uncalibrated.csv",
            "Elution Volume (mL),RI (mV),UV (mAU)\n"
            "1,0,1\n2,2,3\n3,1,2\n",
        )
    )

    definitions = tuple(engine.build_figure_definitions())

    assert [item.figure_id for item in definitions] == [
        "sec.frame.chromatogram.001"
    ]
    chromatogram = definitions[0]
    validate_figure_definition(chromatogram)
    assert chromatogram.publication_role == "diagnostic"
    assert chromatogram.recipe["parameters"]["figure_kind"] == "chromatogram"
    assert len(chromatogram.data_sources) == 2
    assert all(source.source_id.endswith("-data") for source in chromatogram.data_sources)
    assert build_v2_definition_artifact(chromatogram).capability["v2_runtime"] == "ready"


def test_calibrated_sec_emits_mwd_calibration_and_metric_summary_exports(
    tmp_path: Path,
) -> None:
    engine = _calibrated_engine(
        _write(
            tmp_path / "calibrated.csv",
            "Elution Volume (mL),RI (mV)\n1,1\n2,2\n3,1\n",
        )
    )

    definitions = tuple(engine.build_figure_definitions())

    assert [item.figure_id for item in definitions] == [
        "sec.frame.chromatogram.001",
        "sec.frame.molecular-weight-distribution.001",
        "sec.frame.calibration.001",
    ]
    for definition in definitions:
        validate_figure_definition(definition)
        assert build_v2_definition_artifact(definition).capability["v2_runtime"] == "ready"

    distribution = definitions[1]
    assert distribution.layout.panels[0].x_axis.scale == "log"
    assert distribution.recipe["parameters"]["distribution_mode"] == "mass"
    assert distribution.recipe["parameters"]["calibration_id"] == "polystyrene-kit-v1"
    distribution_data = next(
        item
        for item in distribution.data_sources
        if item.source_id == "molecular-weight-distribution-data"
    )
    assert distribution_data.values["molar_mass"] == pytest.approx((1000.0, 100.0, 10.0))
    summary = next(
        item
        for item in distribution.data_sources
        if item.source_id == "molecular-weight-summary"
    )
    assert summary.role == "metric_summary"
    assert tuple(summary.values["metric"]) == ("Mn", "Mw", "Mz", "dispersity")
    group_id = "sheet-0-table-0"
    expected_paths = tuple(
        f"sec_groups.{group_id}.molecular_weight_summary.{name}"
        for name in ("Mn", "Mw", "Mz", "dispersity")
    )
    assert tuple(summary.values["metric_path"]) == expected_paths
    assert tuple(summary.values["unit"]) == ("g/mol", "g/mol", "g/mol", "1")
    assert tuple(summary.values["method"]) == (
        "calibrated_log_molar_mass_weighted_moment",
        "calibrated_log_molar_mass_weighted_moment",
        "calibrated_log_molar_mass_weighted_moment",
        "molecular_weight_ratio_Mw_over_Mn",
    )
    manifest = {
        row["path"]: row
        for row in ComputeResult.from_legacy_result(engine.result).metric_manifest()
    }
    assert tuple(summary.values["value"]) == pytest.approx(
        tuple(manifest[path]["value"] for path in expected_paths)
    )
    assert distribution.recipe["group_id"] == group_id
    assert tuple(distribution.recipe["metric_manifest_paths"]) == expected_paths
    assert distribution.recipe["metric_manifest_binding"] == {
        path: {
            "unit": manifest[path]["unit"],
            "method": manifest[path]["method"],
            "parameters": manifest[path]["parameters"],
        }
        for path in expected_paths
    }

    calibration = definitions[2]
    standards = next(
        item for item in calibration.data_sources if item.source_id == "calibration-standards"
    )
    assert tuple(standards.values["standard_id"]) == ("PS-1000", "PS-100", "PS-10")
    assert calibration.recipe["provenance"]["standard_source"] == (
        "lab-record://sec-standards/2026-09"
    )

    output_root = tmp_path / "published"
    figures = engine.publish_figure_definitions(output_root, run_id="sec-figures")
    assert set(figures) == {item.figure_id for item in definitions}
    distribution_root = (
        output_root
        / "runs"
        / "sec-figures"
        / "figures"
        / "sec.frame.molecular-weight-distribution.001"
    )
    assert (distribution_root / "data" / "molecular-weight-summary.csv").is_file()
    assert (distribution_root / "assets" / "figure.svg").is_file()
    assert (distribution_root / "assets" / "figure.png").is_file()
    assert (distribution_root / "assets" / "figure.pdf").is_file()
    sidecar = json.loads(
        (distribution_root / "reactive_figure_v2.json").read_text(encoding="utf-8")
    )
    assert sidecar["runtime"] == "reactive_figure_v2"
    assert sidecar["graph_document"]["bindings"]
