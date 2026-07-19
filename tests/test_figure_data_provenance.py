from __future__ import annotations

from types import SimpleNamespace

from polynexus.gui.figure_window_service import (
    FigureDataResolution,
    resolve_figure_data,
)


def test_resolve_figure_data_uses_selected_data_ref_and_run_root(tmp_path):
    run_root = tmp_path / "run"
    source_path = run_root / "figures" / "figure-a" / "data" / "source-a.csv"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    figure_path = run_root / "figures" / "figure-a" / "preview.png"
    figure_path.touch()
    document = {
        "objects": [
            {
                "type": "plot_series",
                "data_ref": "source-a",
                "x_column": "x",
                "y_column": "y",
            }
        ],
        "data_sources": [
            {
                "id": "source-a",
                "kind": "csv",
                "path": "figures/figure-a/data/source-a.csv",
                "path_kind": "run_relative",
            }
        ],
    }
    entry = SimpleNamespace(run_root=str(run_root))

    result = resolve_figure_data(str(figure_path), document=document, entry=entry)

    assert result == FigureDataResolution(
        headers=("x", "y"),
        rows=(("1", "2"), ("3", "4")),
        source_label=str(source_path),
        error="",
    )


def test_resolve_figure_data_reports_missing_source_without_fallback(tmp_path):
    document = {
        "objects": [
            {
                "type": "plot_series",
                "data_ref": "missing",
                "x_column": "x",
                "y_column": "y",
            }
        ],
        "data_sources": [
            {
                "id": "missing",
                "kind": "csv",
                "path": "figures/missing/data/missing.csv",
                "path_kind": "run_relative",
            }
        ],
    }
    entry = SimpleNamespace(run_root=str(tmp_path))

    result = resolve_figure_data(
        str(tmp_path / "figure.png"),
        document=document,
        entry=entry,
        fallback_data={"wrong": ["data"]},
    )

    assert result.headers == ()
    assert result.rows == ()
    assert result.source_label == ""
    assert result.error == "source_missing"


def test_resolve_figure_data_supports_explicit_inline_source():
    document = {
        "objects": [
            {
                "type": "plot_series",
                "data_ref": "inline",
                "x_column": "x",
                "y_column": "y",
            }
        ],
        "data_sources": [
            {
                "id": "inline",
                "kind": "inline",
                "data": {"x": [1, 2], "y": [3, 4]},
            }
        ],
    }

    result = resolve_figure_data("figure.png", document=document)

    assert result.headers == ("x", "y")
    assert result.rows == ((1, 3), (2, 4))
    assert result.source_label == "inline"
    assert result.error == ""
