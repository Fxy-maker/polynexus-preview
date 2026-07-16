import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from polynexus.plot_runtime.matplotlib_renderer import (
    MatplotlibPublicationRenderer,
    PublicationProfile,
)
from polynexus.plot_runtime.qt_renderer import QtSceneRenderer
from polynexus.plot_runtime.scene import (
    PanelScene,
    Point,
    Rect,
    RenderScene,
    SceneNode,
    Segment,
    TickMark,
)


def _scene() -> RenderScene:
    panel = PanelScene(
        panel_id="panel-1",
        axis_rect=Rect(50.0, 30.0, 240.0, 160.0),
        x_ticks=(TickMark(0.0, "0", 50.0), TickMark(1.0, "1", 290.0)),
        y_ticks=(TickMark(0.0, "0", 190.0), TickMark(1.0, "1", 30.0)),
        x_label="q",
        y_label="I",
        title="Temperature slice",
    )
    return RenderScene(
        revision_id="worksheet-r2",
        width_px=360,
        height_px=240,
        dpi=100,
        background="#FFFFFF",
        panels=(panel,),
        nodes=(
            SceneNode(
                node_id="curve",
                node_type="plot_series",
                panel_id="panel-1",
                points=(Point(50.0, 190.0), Point(170.0, 100.0), Point(290.0, 50.0)),
                segments=(Segment(Point(170.0, 90.0), Point(170.0, 110.0)),),
                style={"color": "#1f77b4", "line_width": 2.0},
            ),
            SceneNode(
                node_id="legend",
                node_type="legend",
                panel_id="panel-1",
                bounds=Rect(180.0, 40.0, 100.0, 24.0),
                text_anchor=Point(190.0, 58.0),
                text="curve",
            ),
        ),
    )


def test_publication_renderer_exports_all_required_formats_with_provenance(tmp_path):
    renderer = MatplotlibPublicationRenderer()
    profile = PublicationProfile(dpi=100)
    provenance = {"graph_revision_id": "graph-r7", "data_revision_id": "worksheet-r2"}

    result = renderer.export(_scene(), tmp_path / "figure", profile=profile, provenance=provenance)

    assert result.ok
    assert result.audit is not None and result.audit.passed
    assert result.scene_revision_id == "worksheet-r2"
    assert result.provenance["graph_revision_id"] == "graph-r7"
    assert {path.suffix for path in result.paths} == {".svg", ".pdf", ".png", ".tiff"}
    assert all(path.exists() and path.stat().st_size > 0 for path in result.paths)


def test_publication_renderer_rejects_unsupported_scene_node_without_export(tmp_path):
    bad_scene = replace(
        _scene(),
        nodes=(SceneNode("bad", "unknown", "panel-1"),),
    )

    result = MatplotlibPublicationRenderer().export(
        bad_scene,
        tmp_path / "bad-figure",
        profile=PublicationProfile(dpi=100),
    )

    assert not result.ok
    assert result.paths == ()
    assert result.diagnostics[0].reason_code == "unsupported_object_type"


def test_publication_renderer_rejects_unsupported_format_without_export(tmp_path):
    result = MatplotlibPublicationRenderer().export(
        _scene(),
        tmp_path / "bad-format",
        profile=PublicationProfile(dpi=100, formats=("svg", "bmp")),
    )

    assert not result.ok
    assert result.paths == ()
    assert result.diagnostics[0].reason_code == "unsupported_format"


def test_qt_and_publication_renderers_share_scene_geometry_trace():
    app = QApplication.instance() or QApplication([])
    scene = _scene()

    qt_trace = QtSceneRenderer().trace(scene)
    publication_trace = MatplotlibPublicationRenderer().trace(scene)
    comparison = qt_trace.compare_geometry(publication_trace)

    assert comparison.passed
    assert comparison.messages == ()
    assert app is not None
