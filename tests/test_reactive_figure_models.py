from __future__ import annotations

import json

import pytest

from polynexus.plot_runtime.bindings import (
    ColumnReference,
    DataBinding,
    RowFilter,
    UnitMismatchError,
)
from polynexus.plot_runtime.commands import (
    CommandStack,
    EditWorksheetCells,
    PlotState,
    UpdateGraphProperties,
    UpdateGraphStyle,
)
from polynexus.plot_runtime.compat import adapt_legacy_figure_document
from polynexus.plot_runtime.models import (
    AxisModel,
    GraphDocument,
    GraphObject,
    MutableValueError,
    PanelModel,
    SourceDataset,
    Worksheet,
)


def _worksheet() -> Worksheet:
    source = SourceDataset.from_columns(
        dataset_id="saxs-source",
        revision_id="source-r1",
        columns={
            "q": [0.1, 0.2, 0.3],
            "intensity": [10.0, 7.0, 3.0],
            "sigma": [0.5, 0.4, 0.2],
        },
        units={"q": "nm^-1", "intensity": "a.u.", "sigma": "a.u."},
    )
    return Worksheet.from_source(source)


def _document() -> GraphDocument:
    return GraphDocument(
        graph_id="saxs-curve",
        revision_id="graph-r1",
        canvas_width_px=640,
        canvas_height_px=480,
        panels=(
            PanelModel(
                panel_id="main",
                row=0,
                column=0,
                x_axis=AxisModel(label="q", unit="nm^-1"),
                y_axis=AxisModel(label="I(q)", unit="a.u."),
            ),
        ),
        objects=(
            GraphObject(
                object_id="curve",
                object_type="plot_series",
                panel_id="main",
                binding_id="curve-binding",
                style={"color": "#0072B2", "line_width": 1.5},
            ),
        ),
        bindings=(
            DataBinding(
                binding_id="curve-binding",
                object_id="curve",
                kind="line",
                columns=(
                    ColumnReference(role="x", column_id="q", expected_unit="nm^-1"),
                    ColumnReference(role="y", column_id="intensity", expected_unit="a.u."),
                ),
            ),
        ),
    )


def test_worksheet_edits_create_new_revision_without_mutating_source_values():
    worksheet = _worksheet()

    edited_revision = worksheet.edit_cells({"intensity": {1: 8.0}})
    edited = worksheet.checkout(edited_revision)

    assert worksheet.source.values_for("intensity") == (10.0, 7.0, 3.0)
    assert worksheet.current.values_for("intensity") == (10.0, 7.0, 3.0)
    assert edited.current.values_for("intensity") == (10.0, 8.0, 3.0)
    assert edited_revision.parent_revision_id == "source-r1"
    assert edited_revision.changed_columns == ("intensity",)
    assert edited_revision.source_dataset_id == "saxs-source"


def test_worksheet_json_round_trip_preserves_source_and_current_revision():
    worksheet = _worksheet()
    edited = worksheet.checkout(worksheet.edit_cells({"intensity": {1: 8.0}}))

    restored = Worksheet.from_payload(json.loads(json.dumps(edited.to_payload())))

    assert restored.source == worksheet.source
    assert restored.current == edited.current
    assert restored.current.changed_columns == ("intensity",)


def test_nested_mutable_data_values_are_rejected_and_numpy_scalars_are_normalized():
    with pytest.raises(MutableValueError):
        SourceDataset.from_columns(
            dataset_id="bad",
            revision_id="r1",
            columns={"q": [[0.1], [0.2]]},
        )

    source = SourceDataset.from_columns(
        dataset_id="scalar",
        revision_id="r1",
        columns={"q": [1]},
    )
    assert source.values_for("q") == (1,)


def test_data_binding_resolves_columns_filters_rows_and_reports_unit_errors():
    worksheet = _worksheet()
    binding = DataBinding(
        binding_id="curve-binding",
        object_id="curve",
        kind="line",
        columns=(
            ColumnReference(role="x", column_id="q", expected_unit="nm^-1"),
            ColumnReference(role="y", column_id="intensity", expected_unit="a.u."),
        ),
        filters=(RowFilter(column_id="q", operator=">=", value=0.2),),
    )

    resolved = binding.resolve(worksheet.current)

    assert resolved.ok
    assert resolved.columns["x"] == (0.2, 0.3)
    assert resolved.columns["y"] == (7.0, 3.0)
    assert resolved.provenance.source_dataset_id == "saxs-source"

    bad_binding = DataBinding(
        binding_id="bad-binding",
        object_id="curve",
        kind="line",
        columns=(
            ColumnReference(role="x", column_id="q", expected_unit="angstrom^-1"),
        ),
    )
    bad_result = bad_binding.resolve(worksheet.current)
    assert not bad_result.ok
    assert bad_result.diagnostics[0].reason_code == "unit_mismatch"
    assert isinstance(bad_result.diagnostics[0].error, UnitMismatchError)


def test_graph_document_json_round_trip_contains_only_renderer_neutral_state():
    document = _document()

    payload = document.to_payload()
    restored = GraphDocument.from_payload(json.loads(json.dumps(payload)))

    assert restored == document
    assert "renderer" not in payload
    assert "data" not in payload["objects"][0]


def test_legacy_adapter_maps_object_document_and_explains_static_fallback():
    result = adapt_legacy_figure_document(
        {
            "mode": "object",
            "figure_id": "legacy-curve",
            "layout": {
                "canvas": {"width": 3.5, "height": 2.5},
                "panels": [
                    {
                        "panel_id": "main",
                        "grid_position": {"row": 0, "column": 0},
                        "x_axis": {"label": "q", "unit": "nm^-1"},
                        "y_axis": {"label": "I(q)", "unit": "a.u."},
                    }
                ],
            },
            "data_sources": [],
            "objects": [
                {
                    "id": "line",
                    "type": "line",
                    "panel_id": "main",
                    "x": 0.2,
                    "style": {"color": "#D55E00"},
                }
            ],
        }
    )

    assert result.document is not None
    assert result.document.graph_id == "legacy-curve"
    assert result.document.objects[0].object_type == "line"

    static_result = adapt_legacy_figure_document({"mode": "static_background"})
    assert static_result.document is None
    assert static_result.diagnostic is not None
    assert static_result.diagnostic.reason_code == "static_document"
    assert static_result.diagnostic.static_fallback


def test_legacy_adapter_does_not_claim_v2_support_for_image_grid_or_highlight():
    result = adapt_legacy_figure_document(
        {
            "mode": "object",
            "figure_id": "legacy-image-grid",
            "objects": [{"id": "grid", "type": "image_grid", "panel_id": "main"}],
        }
    )

    assert result.document is None
    assert result.diagnostic is not None
    assert result.diagnostic.reason_code == "unsupported_object_type"
    assert result.diagnostic.static_fallback


def test_command_stack_tracks_affected_ids_and_supports_undo_redo():
    state = PlotState(worksheet=_worksheet(), document=_document())
    stack = CommandStack(state)

    worksheet_result = stack.execute(
        EditWorksheetCells(changes={"intensity": {1: 8.0}})
    )
    assert worksheet_result.affected_data_ids == ("intensity",)
    assert worksheet_result.affected_object_ids == ("curve",)
    assert stack.current.worksheet.current.values_for("intensity") == (10.0, 8.0, 3.0)

    style_result = stack.execute(
        UpdateGraphStyle(object_id="curve", updates={"line_width": 2.0})
    )
    assert style_result.affected_object_ids == ("curve",)
    assert stack.current.document.object_by_id("curve").style_map["line_width"] == 2.0

    stack.undo()
    assert stack.current.document.object_by_id("curve").style_map["line_width"] == 1.5
    stack.undo()
    assert stack.current.worksheet.current.values_for("intensity") == (10.0, 7.0, 3.0)
    stack.redo()
    assert stack.current.worksheet.current.values_for("intensity") == (10.0, 8.0, 3.0)


def test_command_stack_updates_object_properties_for_interaction_commands():
    state = PlotState(worksheet=_worksheet(), document=_document())
    stack = CommandStack(state)

    result = stack.execute(UpdateGraphProperties("curve", {"x": 0.25, "y": 0.75}))

    assert result.affected_data_ids == ()
    assert result.affected_object_ids == ("curve",)
    assert stack.current.document.object_by_id("curve").property_map == {"x": 0.25, "y": 0.75}
    stack.undo()
    assert stack.current.document.object_by_id("curve").property_map == {}
