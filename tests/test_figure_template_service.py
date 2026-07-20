from __future__ import annotations

from polynexus.core.figure_template_service import (
    apply_template,
    list_templates,
    load_template,
    save_template,
    template_from_document,
)
from polynexus.core.figure_edit_commands import ReplaceDocumentCommand
from polynexus.core.figure_edit_session import EditSession


def _document():
    return {
        "version": 1,
        "figure_id": "source",
        "mode": "object",
        "canvas": {"width_px": 800, "height_px": 500},
        "style": {"xlabel": "q", "ylabel": "I(q)"},
        "data_sources": [{"id": "source-a", "path": "data/a.csv"}],
        "objects": [
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data_ref": "source-a",
                "data": {"x": [1, 2], "y": [3, 4]},
                "bounds": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.4},
                "style": {"color": "#0072B2", "line_width": 1.5},
            }
        ],
    }


def test_template_round_trip_excludes_data_bindings(tmp_path, monkeypatch):
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "config"))

    template = template_from_document(_document(), "Publication")
    path = save_template("Publication", template)
    loaded = load_template("Publication")

    assert path.exists()
    assert list_templates() == ["Publication"]
    assert loaded["name"] == "Publication"
    assert "data_sources" not in loaded
    assert "data" not in loaded["objects"][0]
    assert "data_ref" not in loaded["objects"][0]


def test_apply_template_preserves_current_data_sources_and_updates_compatible_fields():
    template = template_from_document(_document(), "Publication")
    current = _document()
    current["data_sources"] = [{"id": "current", "path": "data/current.csv"}]
    current["objects"][0]["style"] = {"color": "#000000"}

    applied = apply_template(current, template)

    assert applied["data_sources"] == current["data_sources"]
    assert applied["objects"][0]["data_ref"] == "source-a"
    assert applied["objects"][0]["style"]["color"] == "#0072B2"
    assert applied["objects"][0]["bounds"]["width"] == 0.5


def test_template_application_can_be_committed_and_undone_as_one_document_edit():
    current = _document()
    applied = apply_template(current, template_from_document(current, "Publication"))
    applied["style"]["xlabel"] = "r (nm)"
    session = EditSession(current)

    result = session.execute(ReplaceDocumentCommand(applied))

    assert result.changed is True
    assert session.document["style"]["xlabel"] == "r (nm)"
    assert session.undo().changed is True
    assert session.document == current
