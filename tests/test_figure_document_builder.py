from dataclasses import replace

from polynexus.core.figures.data_writer import FigureDataSnapshotWriter
from polynexus.core.figures.document_builder import FigureDocumentBuilder


def test_document_builder_writes_layout_revision_and_relative_sources(
    ir_definition,
    tmp_path,
):
    ir_definition = replace(ir_definition, publication_role="main")
    run_root = tmp_path / "runs" / "run-1"
    figure_dir = run_root / "figures" / ir_definition.figure_id
    records = FigureDataSnapshotWriter(run_root).write(ir_definition, figure_dir)

    document_path, document = FigureDocumentBuilder().write(
        definition=ir_definition,
        run_id="run-1",
        revision=1,
        figure_dir=figure_dir,
        data_sources=records,
    )

    assert document_path.name == "figure.pnfig.json"
    assert document["run_id"] == "run-1"
    assert document["revision"] == 1
    assert document["publication_role"] == "main"
    assert document["layout"]["panels"][0]["panel_id"] == "main"
    assert document["data_sources"][0]["path_kind"] == "run_relative"
    assert document["objects"][0]["panel_id"] == "main"
