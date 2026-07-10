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
    assert editor._shared_render_plan.figure_id == entry.figure_id
    assert editor._figure_document["figure_id"] == entry.figure_id
    assert editor._figure.axes[0].xaxis_inverted()
