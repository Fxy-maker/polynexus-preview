from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)
from polynexus.core.figures.v2_adapter import adapt_figure_definition
from polynexus.core.figures.v2_capabilities import build_v2_definition_artifact
from polynexus.plot_runtime.layout import LayoutResolver
from polynexus.plot_runtime.compat import adapt_legacy_figure_document
from polynexus.plot_runtime.models import thaw_json
from polynexus.plot_runtime.matplotlib_renderer import MatplotlibPublicationRenderer, PublicationProfile


def _image_grid_definition() -> FigureDefinition:
    source = FigureDataSourceDefinition(
        source_id="grid-source",
        columns=(
            DataColumnDefinition("grid_column", "", "int64"),
            DataColumnDefinition("grid_row", "", "int64"),
            DataColumnDefinition("pixel_x", "px"),
            DataColumnDefinition("pixel_y", "px"),
            DataColumnDefinition("intensity", "a.u."),
        ),
        values={
            "grid_column": (0, 0, 0, 0, 1, 1, 1, 1),
            "grid_row": (0, 0, 1, 1, 0, 0, 1, 1),
            "pixel_x": (0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0),
            "pixel_y": (0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0),
            "intensity": (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0),
        },
        role="image_data",
    )
    panel = PanelDefinition(
        "patterns",
        0,
        0,
        AxisDefinition("x", "Detector x", "px"),
        AxisDefinition("y", "Detector y", "px"),
    )
    return FigureDefinition(
        figure_id="waxs.strain.evolution",
        technique="waxs",
        scope="series",
        category="series_overview",
        title="WAXS patterns",
        layout=FigureLayoutDefinition(7.0, 3.8, 1, 1, (panel,)),
        data_sources=(source,),
        objects=(
            {
                "id": "pattern-grid",
                "type": "image_grid",
                "panel_id": "patterns",
                "data_ref": "grid-source",
                "grid_column": "grid_column",
                "grid_row": "grid_row",
                "x_column": "pixel_x",
                "y_column": "pixel_y",
                "z_column": "intensity",
                "style": {"cmap": "viridis", "origin": "upper"},
            },
        ),
        recipe={"v2_adapter": "waxs"},
        style_profile="sci_default",
        publication_role="main",
    )


def test_v2_adapter_preserves_native_image_grid_as_editable_graph_object():
    result = adapt_figure_definition(_image_grid_definition())

    assert result.ok, result.diagnostics
    assert result.document is not None
    image_grid = result.document.object_by_id("pattern-grid")
    assert image_grid.object_type == "image_grid"
    assert image_grid.binding_id == "pattern-grid::binding"
    binding = next(item for item in result.document.bindings if item.object_id == "pattern-grid")
    assert binding.kind == "image_grid"
    assert {item.role for item in binding.columns} == {
        "x",
        "y",
        "z",
        "grid_column",
        "grid_row",
    }


def test_v2_image_grid_style_edit_preserves_native_object_and_binding():
    result = adapt_figure_definition(_image_grid_definition())
    assert result.ok and result.document is not None
    original = result.document.object_by_id("pattern-grid")

    edited = result.document.replace_object(
        original.with_style({"cmap": "magma", "origin": "lower"})
    )
    updated = edited.object_by_id("pattern-grid")

    assert updated.object_type == "image_grid"
    assert updated.style_map["cmap"] == "magma"
    assert updated.binding_id == original.binding_id
    assert edited.object_ids_for_columns({"grid-source::intensity"}) == ("pattern-grid",)


def test_v2_layout_keeps_image_grid_frames_tiled_and_non_overlapping():
    result = adapt_figure_definition(_image_grid_definition())
    assert result.ok and result.document is not None and result.worksheet is not None

    layout = LayoutResolver().resolve(result.document, result.worksheet.current)

    assert layout.ok, layout.diagnostics
    node = layout.scene.node_by_id("pattern-grid")
    assert node.node_type == "image_grid"
    assert len(node.rectangles) == 8
    assert thaw_json(node.metadata)["grid_shape"] == [2, 2]
    # Cells belonging to different frames occupy disjoint tile rectangles.
    frame_rects = {}
    for cell in node.rectangles:
        frame_rects.setdefault((cell.grid_column, cell.grid_row), []).append(cell.rect)
    assert len(frame_rects) == 4
    for index, left_frame in enumerate(frame_rects.values()):
        for right_frame in list(frame_rects.values())[index + 1 :]:
            assert all(
                left.right <= right.left
                or right.right <= left.left
                or left.bottom <= right.top
                or right.bottom <= left.top
                for left in left_frame
                for right in right_frame
            )


def test_v2_layout_rejects_incomplete_image_grid_frame_without_fallback():
    definition = _image_grid_definition()
    source = definition.data_sources[0]
    truncated = {name: tuple(values[:-1]) for name, values in source.values.items()}
    broken_source = type(source)(source.source_id, source.columns, truncated, role=source.role)
    broken = type(definition)(
        figure_id=definition.figure_id,
        technique=definition.technique,
        scope=definition.scope,
        category=definition.category,
        title=definition.title,
        layout=definition.layout,
        data_sources=(broken_source,),
        objects=definition.objects,
        recipe=definition.recipe,
        style_profile=definition.style_profile,
        publication_role=definition.publication_role,
    )
    result = adapt_figure_definition(broken)
    assert result.ok and result.document is not None and result.worksheet is not None
    layout = LayoutResolver().resolve(result.document, result.worksheet.current)

    assert not layout.ok
    assert layout.diagnostics[0].reason_code == "invalid_image_grid"


def test_legacy_compatibility_keeps_native_image_grid_object_editable():
    result = adapt_legacy_figure_document(
        {
            "mode": "object",
            "figure_id": "legacy-image-grid",
            "objects": [{"id": "grid", "type": "image_grid", "panel_id": "main"}],
        }
    )

    assert result.document is not None
    assert result.document.object_by_id("grid").object_type == "image_grid"


def test_publication_renderer_renders_native_image_grid_without_static_fallback(tmp_path):
    result = adapt_figure_definition(_image_grid_definition())
    assert result.ok and result.document is not None and result.worksheet is not None
    layout = LayoutResolver().resolve(result.document, result.worksheet.current)
    assert layout.ok and layout.scene is not None

    publication = MatplotlibPublicationRenderer().export(
        layout.scene,
        tmp_path / "image-grid",
        profile=PublicationProfile(dpi=100, formats=("png",)),
        provenance={"scene_revision_id": layout.scene.revision_id},
    )

    assert publication.ok, publication.diagnostics
    assert publication.paths and publication.paths[0].suffix == ".png"


def test_qt_renderer_materializes_native_image_grid_as_one_editable_item():
    from PySide6.QtWidgets import QApplication
    from polynexus.plot_runtime.qt_renderer import QtSceneRenderer

    app = QApplication.instance() or QApplication([])
    result = adapt_figure_definition(_image_grid_definition())
    assert result.ok and result.document is not None and result.worksheet is not None
    layout = LayoutResolver().resolve(result.document, result.worksheet.current)
    assert layout.ok and layout.scene is not None

    renderer = QtSceneRenderer()
    renderer.render(layout.scene)

    assert renderer.item_for_id("pattern-grid") is not None
    assert app is not None


def test_v2_capability_accepts_native_image_grid_without_static_fallback():
    artifact = build_v2_definition_artifact(_image_grid_definition())

    assert artifact.capability["v2_runtime"] == "ready"
    assert artifact.sidecar is not None
    assert artifact.sidecar["graph_document"]["objects"][0]["type"] == "image_grid"
