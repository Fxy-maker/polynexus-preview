from __future__ import annotations

import importlib
import json

import pytest

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _recovery_module():
    return importlib.import_module("polynexus.core.figures.legacy_recovery")


def test_legacy_discovery_classifies_rebuildable_partial_and_static(tmp_path):
    recovery = _recovery_module()
    rebuildable = tmp_path / "rebuildable"
    rebuildable.mkdir()
    (rebuildable / "figure.png").write_bytes(b"legacy-png")
    (rebuildable / "source.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    _write_json(
        rebuildable / "recovery_context.json",
        {
            "technique": "ir",
            "title": "Rebuildable IR",
            "recipe": {
                "module": "polynexus.core.ir_engine.figure_provider",
                "function": "build_ir_figure_definitions",
            },
            "source_paths": ["source.csv"],
        },
    )

    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "preview.png").write_bytes(b"preview")
    (partial / "data.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    _write_json(
        partial / "figure.pnfig.json",
        {
            "version": 2,
            "figure_id": "ir.frame.partial.spectrum",
            "title": "Partial IR",
            "technique": "ir",
            "mode": "object",
            "recipe": {
                "module": "polynexus.core.ir_engine.figure_provider",
                "function": "build_ir_figure_definitions",
            },
            "data_sources": [
                {
                    "id": "plot-data",
                    "kind": "csv",
                    "path_kind": "run_relative",
                    "path": "data.csv",
                }
            ],
        },
    )

    static = tmp_path / "static"
    static.mkdir()
    (static / "figure.pdf").write_bytes(b"%PDF-legacy")

    candidates = recovery.LegacyFigureRecoveryService(tmp_path).discover()

    assert {item.candidate_id: item.kind for item in candidates} == {
        "partial": recovery.LegacyRecoveryKind.PARTIALLY_REPAIRABLE,
        "rebuildable": recovery.LegacyRecoveryKind.REBUILDABLE,
        "static": recovery.LegacyRecoveryKind.STATIC_ONLY,
    }
    by_id = {item.candidate_id: item for item in candidates}
    assert by_id["rebuildable"].data_paths == (
        (rebuildable / "source.csv").resolve(),
    )
    assert by_id["partial"].document_path == (
        partial / "figure.pnfig.json"
    ).resolve()
    assert by_id["static"].reason_code == "rendered_asset_only"


def test_legacy_discovery_never_changes_active_manifest_or_gallery(
    ir_definition,
    tmp_path,
):
    recovery = _recovery_module()
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="active-run",
        technique="ir",
        definitions=(ir_definition,),
    )
    active_manifest_path = tmp_path / "runs" / "active-run" / "figure_manifest.json"
    manifest_before = active_manifest_path.read_bytes()
    gallery_before = build_active_manifest_gallery_entries(tmp_path)
    legacy = tmp_path / "historical" / "old-export"
    legacy.mkdir(parents=True)
    (legacy / "figure.svg").write_text("<svg/>", encoding="utf-8")

    candidates = recovery.LegacyFigureRecoveryService(tmp_path).discover()

    assert [item.candidate_id for item in candidates] == ["historical.old-export"]
    assert active_manifest_path.read_bytes() == manifest_before
    assert build_active_manifest_gallery_entries(tmp_path) == gallery_before
    assert [entry.figure_id for entry in gallery_before] == [
        manifest.figures[0].figure_id
    ]


def test_legacy_discovery_skips_staging_and_existing_recovery_packages(tmp_path):
    recovery = _recovery_module()
    for directory in (
        tmp_path / "runs" / "run-1" / "figures" / "ignored",
        tmp_path / "runs" / ".run-2.staging" / "figures" / "ignored",
        tmp_path / "legacy_recovery" / "already-imported",
    ):
        directory.mkdir(parents=True)
        (directory / "figure.png").write_bytes(b"ignored")
    visible = tmp_path / "old"
    visible.mkdir()
    (visible / "plot.png").write_bytes(b"visible")

    candidates = recovery.LegacyFigureRecoveryService(tmp_path).discover()

    assert [item.candidate_id for item in candidates] == ["old"]


def test_static_import_creates_portable_recovery_package_without_activation(
    ir_definition,
    tmp_path,
):
    recovery = _recovery_module()
    legacy_root = tmp_path / "historical"
    static_root = legacy_root / "asset-only"
    static_root.mkdir(parents=True)
    source_asset = static_root / "figure.png"
    source_asset.write_bytes(b"legacy-rendered-asset")
    output_root = tmp_path / "output"
    FigurePipeline().run(
        output_root=output_root,
        run_id="current-run",
        technique="ir",
        definitions=(ir_definition,),
    )
    active_pointer = output_root / "active_run.json"
    pointer_before = active_pointer.read_bytes()
    source_before = source_asset.read_bytes()
    service = recovery.LegacyFigureRecoveryService(legacy_root)
    candidate = service.discover()[0]

    package_root = service.import_static(candidate, output_root=output_root)

    document = json.loads((package_root / "figure.pnfig.json").read_text("utf-8"))
    record = json.loads((package_root / "recovery_record.json").read_text("utf-8"))
    background = document["objects"][0]
    assert package_root == (
        output_root / "legacy_recovery" / candidate.candidate_id
    ).resolve()
    assert document["mode"] == "static_background"
    assert document["category"] == "legacy"
    assert document["vector_fidelity"] == "raster_embedded"
    assert background["path_kind"] == "package_relative"
    assert background["source_path"] == "background/figure.png"
    assert record["classification"] == "static_only"
    assert source_asset.read_bytes() == source_before
    assert active_pointer.read_bytes() == pointer_before


def test_rebuildable_recovery_requires_definition_factory_and_creates_new_run(
    ir_definition,
    tmp_path,
):
    recovery = _recovery_module()
    legacy_root = tmp_path / "historical"
    candidate_root = legacy_root / "rebuildable"
    candidate_root.mkdir(parents=True)
    (candidate_root / "source.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    (candidate_root / "figure.svg").write_text("<svg/>", encoding="utf-8")
    _write_json(
        candidate_root / "recovery_context.json",
        {
            "technique": "ir",
            "recipe": {
                "module": "polynexus.core.ir_engine.figure_provider",
                "function": "build_ir_figure_definitions",
            },
            "source_paths": ["source.csv"],
        },
    )
    service = recovery.LegacyFigureRecoveryService(legacy_root)
    candidate = service.discover()[0]
    output_root = tmp_path / "output"

    with pytest.raises(ValueError, match="definition factory"):
        service.rebuild(
            candidate,
            output_root=output_root,
            run_id="recovered-ir",
        )

    manifest = service.rebuild(
        candidate,
        output_root=output_root,
        run_id="recovered-ir",
        definition_factory=lambda selected: (ir_definition,),
    )

    assert manifest.run_id == "recovered-ir"
    assert manifest.figures[0].status == "ready"
    assert json.loads((output_root / "active_run.json").read_text("utf-8")) == {
        "run_id": "recovered-ir"
    }
