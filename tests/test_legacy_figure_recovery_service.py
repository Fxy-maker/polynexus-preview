from __future__ import annotations

import importlib
import json

from polynexus.gui.plot_gallery_service import (
    FIGURE_STATE_OBJECT,
    FIGURE_STATE_STATIC,
    FIGURE_STATE_UNLINKED_EXPORT,
)


def test_legacy_recovery_gallery_entries_show_honest_classification(tmp_path):
    module = importlib.import_module("polynexus.gui.legacy_figure_recovery_service")
    rebuildable = tmp_path / "rebuildable"
    rebuildable.mkdir()
    (rebuildable / "source.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    (rebuildable / "figure.svg").write_text("<svg/>", encoding="utf-8")
    (rebuildable / "recovery_context.json").write_text(
        json.dumps(
            {
                "technique": "ir",
                "title": "Rebuildable",
                "recipe": {"module": "provider", "function": "build"},
                "source_paths": ["source.csv"],
            }
        ),
        encoding="utf-8",
    )
    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "preview.png").write_bytes(b"preview")
    (partial / "data.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    (partial / "figure.pnfig.json").write_text(
        json.dumps(
            {
                "version": 2,
                "figure_id": "ir.frame.partial",
                "title": "Partial",
                "technique": "ir",
                "mode": "object",
                "data_sources": [
                    {"kind": "csv", "path_kind": "run_relative", "path": "data.csv"}
                ],
                "recipe": {"module": "provider", "function": "build"},
            }
        ),
        encoding="utf-8",
    )
    static = tmp_path / "static"
    static.mkdir()
    (static / "figure.pdf").write_bytes(b"%PDF")

    entries = module.build_legacy_recovery_gallery_entries(tmp_path)

    assert [entry.figure_id for entry in entries] == [
        "partial",
        "rebuildable",
        "static",
    ]
    by_id = {entry.figure_id: entry for entry in entries}
    assert by_id["partial"].state == FIGURE_STATE_OBJECT
    assert by_id["rebuildable"].state == FIGURE_STATE_UNLINKED_EXPORT
    assert by_id["static"].state == FIGURE_STATE_STATIC
    assert all(entry.category == "legacy" for entry in entries)
    assert all(entry.run_id == "" for entry in entries)
    assert all(entry.working_revision == 0 for entry in entries)
    assert all(entry.published_revision == 0 for entry in entries)
    assert all(entry.capability_report is None for entry in entries)
    assert by_id["partial"].document_path.endswith("figure.pnfig.json")
    assert by_id["static"].document_path == ""
    assert by_id["static"].status == "legacy:static_only"
    assert by_id["static"].error == "rendered_asset_only"
