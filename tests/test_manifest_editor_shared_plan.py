import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries
from polynexus.gui.widgets.chart_editor import ChartEditor


def test_manifest_editor_builds_first_screen_from_shared_render_plan(
    ir_definition,
    tmp_path,
):
    QApplication.instance() or QApplication([])
    FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    entry = build_active_manifest_gallery_entries(tmp_path)[0]
    editor = ChartEditor()

    editor.set_source_figure_entry(entry)

    assert editor._generated_document_mode is True
    assert editor._btn_publish.isEnabled() is True
    assert editor._shared_render_plan.figure_id == entry.figure_id
    assert editor._figure_document["figure_id"] == entry.figure_id
    assert editor._figure.axes[0].xaxis_inverted()

    editor.deleteLater()
    QApplication.instance().processEvents()


def test_manifest_editor_save_then_publish_refreshes_lifecycle_context(
    ir_definition,
    tmp_path,
):
    app = QApplication.instance() or QApplication([])
    initial = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    entry = build_active_manifest_gallery_entries(tmp_path)[0]
    run_root = tmp_path / "runs" / "run-1"
    formal_before = {
        role: (run_root / initial.figures[0].assets[role]).read_bytes()
        for role in ("svg", "png", "pdf")
    }
    editor = ChartEditor()
    saved_paths = []
    editor.figure_saved.connect(saved_paths.append)
    editor.set_source_figure_entry(entry)
    editor._figure_document["objects"][0]["style"]["line_width"] = 2.1

    editor.save_to_target()

    working = editor._source_entry_context
    assert working.working_revision == 2
    assert working.published_revision == 1
    assert working.publication_status == "unpublished_changes"
    assert editor._source_path == working.preview_path
    assert all(
        (run_root / initial.figures[0].assets[role]).read_bytes()
        == formal_before[role]
        for role in formal_before
    )

    editor.publish_complete_assets()

    published = editor._source_entry_context
    assert published.working_revision == published.published_revision == 2
    assert published.publication_status == "complete"
    assert all(
        "publications/r0002/assets/" in asset.path.replace("\\", "/")
        for asset in published.assets
    )
    assert editor._figure_document["export"]["published_revision"] == 2
    assert saved_paths == [working.preview_path, published.preview_path]

    editor.deleteLater()
    app.processEvents()
