from __future__ import annotations

import json
import zipfile

import pytest

from polynexus.core.figure_project_bundle import (
    FigureProjectBundleError,
    export_figure_project_bundle,
)


def test_export_figure_project_bundle_is_self_contained_and_relocatable(tmp_path):
    run_root = tmp_path / "run"
    source = run_root / "figures" / "fig-a" / "data" / "source-a.csv"
    source.parent.mkdir(parents=True)
    source.write_text("x,y\n1,2\n", encoding="utf-8")
    figure = run_root / "figures" / "fig-a" / "figure.png"
    figure.write_bytes(b"png")
    figure.with_suffix(".svg").write_bytes(b"svg")
    output = tmp_path / "project.pnproject.zip"
    document = {
        "figure_id": "fig-a",
        "data_sources": [
            {
                "id": "source-a",
                "path": "figures/fig-a/data/source-a.csv",
                "path_kind": "run_relative",
            }
        ],
        "objects": [],
    }

    result = export_figure_project_bundle(
        document=document,
        figure_path=figure,
        output_path=output,
        source_root=run_root,
    )

    assert result.output_path == output.resolve()
    assert output.is_file()
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert {
            "figure_document.json",
            "manifest.json",
            "assets/figure.png",
            "assets/figure.svg",
            "sources/source-a.csv",
        } <= names
        bundled_document = json.loads(archive.read("figure_document.json"))
        assert bundled_document["data_sources"][0]["path"] == "sources/source-a.csv"
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["files"]["sources/source-a.csv"]["sha256"]


def test_export_figure_project_bundle_serializes_inline_sources(tmp_path):
    output = tmp_path / "inline.pnproject.zip"

    export_figure_project_bundle(
        document={
            "data_sources": [
                {
                    "id": "inline",
                    "columns": [{"name": "x"}, {"name": "y"}],
                    "values": {"x": [1, 2], "y": [3, 4]},
                }
            ]
        },
        output_path=output,
    )

    with zipfile.ZipFile(output) as archive:
        assert archive.read("sources/inline.csv").decode("utf-8").splitlines() == [
            "x,y",
            "1,3",
            "2,4",
        ]


def test_export_figure_project_bundle_rejects_existing_output(tmp_path):
    output = tmp_path / "existing.zip"
    output.write_bytes(b"keep")

    with pytest.raises(FigureProjectBundleError, match="already exists"):
        export_figure_project_bundle(document={}, output_path=output)

    assert output.read_bytes() == b"keep"


def test_export_figure_project_bundle_cleans_up_after_missing_source(tmp_path):
    output = tmp_path / "missing.zip"

    with pytest.raises(FigureProjectBundleError, match="does not exist"):
        export_figure_project_bundle(
            document={
                "data_sources": [
                    {"id": "missing", "path": "missing.csv"}
                ]
            },
            output_path=output,
        )

    assert not output.exists()
    assert not list(tmp_path.glob(".missing.zip.*"))


def test_export_figure_project_bundle_rejects_run_relative_escape(tmp_path):
    run_root = tmp_path / "run"
    outside = tmp_path / "outside.csv"
    run_root.mkdir()
    outside.write_text("x\n1\n", encoding="utf-8")

    with pytest.raises(FigureProjectBundleError, match="escapes source root"):
        export_figure_project_bundle(
            document={
                "data_sources": [
                    {
                        "id": "escape",
                        "path": "../outside.csv",
                        "path_kind": "run_relative",
                    }
                ]
            },
            output_path=tmp_path / "escape.zip",
            source_root=run_root,
        )
