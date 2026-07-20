"""Regression tests for actionable figure-document load diagnostics."""

import json

from polynexus.core.figure_document import (
    load_figure_document,
    load_figure_document_report,
)


def test_load_report_classifies_missing_document_without_creating_file(tmp_path):
    figure_path = tmp_path / "missing.png"

    report = load_figure_document_report(str(figure_path))

    assert report.status == "missing"
    assert report.path == figure_path.with_suffix(".pnfig.json").resolve()
    assert report.document == {}
    assert report.message
    assert not report.path.exists()


def test_load_report_classifies_malformed_json_without_rewriting_source(tmp_path):
    document_path = tmp_path / "broken.pnfig.json"
    original = "{\"version\": 1,\n"
    document_path.write_text(original, encoding="utf-8")

    report = load_figure_document_report(str(document_path))

    assert report.status == "corrupt"
    assert report.path == document_path.resolve()
    assert report.error_type == "json"
    assert report.document == {}
    assert report.message
    assert document_path.read_text(encoding="utf-8") == original
    assert load_figure_document(str(document_path)) == {}


def test_load_report_classifies_non_mapping_json_as_corrupt(tmp_path):
    document_path = tmp_path / "array.pnfig.json"
    document_path.write_text(json.dumps(["not", "a", "document"]), encoding="utf-8")

    report = load_figure_document_report(str(document_path))

    assert report.status == "corrupt"
    assert report.error_type == "schema"
    assert report.document == {}
    assert report.message


def test_load_report_classifies_future_document_version_as_unsupported(tmp_path):
    document_path = tmp_path / "future.pnfig.json"
    document_path.write_text(
        json.dumps({"version": 99, "figure_id": "future"}),
        encoding="utf-8",
    )

    report = load_figure_document_report(str(document_path))

    assert report.status == "unsupported"
    assert report.error_type == "version"
    assert report.document["version"] == 99
    assert report.message
