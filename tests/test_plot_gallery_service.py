import os

from polynexus.core.figure_document import save_generated_figure_document
from polynexus.gui.plot_gallery_service import (
    FIGURE_CATEGORY_OTHER_EXPORTS,
    FIGURE_CATEGORY_PER_FRAME,
    FIGURE_CATEGORY_SERIES_OVERVIEW,
    FIGURE_STATE_OBJECT,
    FIGURE_STATE_UNLINKED_EXPORT,
    build_plot_gallery_entries,
    build_active_manifest_gallery_entries,
    collect_plot_figure_paths,
    result_figure_paths,
    select_plot_gallery_entry,
    select_plot_figure_path,
)
from polynexus.core.figures.pipeline import FigurePipeline


def test_collect_plot_figure_paths_includes_figure_subdirs_and_root_files(tmp_path):
    figures_dir = tmp_path / "figures"
    summary_dir = tmp_path / "summary"
    figures_dir.mkdir()
    summary_dir.mkdir()
    (figures_dir / "a.png").write_bytes(b"fig")
    (summary_dir / "b.svg").write_bytes(b"sum")
    (tmp_path / "root.png").write_bytes(b"root")

    paths = collect_plot_figure_paths(str(tmp_path))

    assert paths == [
        str((figures_dir / "a.png").resolve()),
        str((summary_dir / "b.svg").resolve()),
        str((tmp_path / "root.png").resolve()),
    ]


def test_collect_plot_figure_paths_falls_back_to_root_files_when_no_subdirs_match(tmp_path):
    (tmp_path / "root-a.png").write_bytes(b"a")
    (tmp_path / "root-b.pdf").write_bytes(b"b")
    (tmp_path / "ignore.txt").write_text("x", encoding="utf-8")

    paths = collect_plot_figure_paths(str(tmp_path))

    assert paths == [str(tmp_path / "root-a.png"), str(tmp_path / "root-b.pdf")]


def test_collect_plot_figure_paths_merges_preferred_paths_with_discovered_gallery_entries(tmp_path):
    stale_dir = tmp_path / "figures" / "main"
    stale_dir.mkdir(parents=True)
    stale_plot = stale_dir / "saxs_SI_Guinier.pdf"
    stale_plot.write_bytes(b"stale")

    current_plot = tmp_path / "temperature_overview.pdf"
    current_plot.write_bytes(b"current")

    paths = collect_plot_figure_paths(
        str(tmp_path),
        preferred_paths=[str(current_plot)],
    )

    assert paths == [
        str(current_plot.resolve()),
        str(stale_plot.resolve()),
    ]


def test_result_figure_paths_filters_current_run_manifest_to_real_figures(tmp_path):
    current_plot = tmp_path / "temperature_overview.pdf"
    current_plot.write_bytes(b"current")
    data_csv = tmp_path / "parameters.csv"
    data_csv.write_text("x,y\n1,2\n", encoding="utf-8")

    paths = result_figure_paths(
        {
            "figures": {
                "temperature_overview": str(current_plot),
                "parameters_csv": str(data_csv),
            }
        }
    )

    assert paths == [str(current_plot.resolve())]


def test_select_plot_figure_path_prefers_newer_variant_for_same_basename(tmp_path):
    frame_dir = tmp_path / "per_frame" / "frame_001"
    frame_dir.mkdir(parents=True)

    stale_low = frame_dir / "03_IDF_LOW.pdf"
    refreshed = frame_dir / "03_IDF.pdf"
    stale_low.write_bytes(b"stale")
    refreshed.write_bytes(b"refreshed")
    os.utime(stale_low, (1_700_000_000, 1_700_000_000))
    os.utime(refreshed, (1_700_000_100, 1_700_000_100))

    selection = select_plot_figure_path(
        [str(stale_low), str(refreshed)],
        preferred_path=str(stale_low),
        preview_visible=True,
    )

    assert selection.selected_path == str(refreshed)
    assert selection.matched_preferred is True
    assert selection.emit_preview is True


def test_select_plot_figure_path_uses_first_available_for_initial_selection(tmp_path):
    first = tmp_path / "figures" / "initial.png"
    second = tmp_path / "figures" / "next.png"
    first.parent.mkdir()
    first.write_bytes(b"1")
    second.write_bytes(b"2")

    selection = select_plot_figure_path(
        [str(first), str(second)],
        preferred_path="",
        preview_visible=False,
    )

    assert selection.selected_path == str(first)
    assert selection.matched_preferred is False
    assert selection.emit_preview is True


def test_build_plot_gallery_entries_groups_sibling_exports_into_one_object_entry(tmp_path):
    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()

    png_path = figure_dir / "temperature_overview.png"
    svg_path = figure_dir / "temperature_overview.svg"
    pdf_path = figure_dir / "temperature_overview.pdf"
    png_path.write_bytes(b"png")
    svg_path.write_text(
        "<svg width='400' height='200' viewBox='0 0 400 200'></svg>",
        encoding="utf-8",
    )
    pdf_path.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Page /MediaBox [0 0 400 200] >>\nendobj\n"
    )

    save_generated_figure_document(
        str(svg_path),
        figure_id="temperature_overview",
        technique="dsc",
        objects=[],
    )

    entries = build_plot_gallery_entries([str(png_path), str(svg_path), str(pdf_path)])

    assert len(entries) == 1
    assert entries[0].figure_id == "temperature_overview"
    assert entries[0].title == "temperature overview"
    assert entries[0].state == FIGURE_STATE_OBJECT
    assert entries[0].preview_path == str(png_path.resolve())
    assert entries[0].primary_path == str(svg_path.resolve())
    assert entries[0].editable_path == str(svg_path.resolve())
    assert {asset.format for asset in entries[0].assets} == {"png", "svg", "pdf"}


def test_build_plot_gallery_entries_marks_export_only_group_as_unlinked_export(tmp_path):
    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()

    png_path = figure_dir / "summary_panel.png"
    pdf_path = figure_dir / "summary_panel.pdf"
    png_path.write_bytes(b"png")
    pdf_path.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Page /MediaBox [0 0 80 40] >>\nendobj\n"
    )

    entries = build_plot_gallery_entries([str(png_path), str(pdf_path)])

    assert len(entries) == 1
    assert entries[0].state == FIGURE_STATE_UNLINKED_EXPORT
    assert entries[0].editable_path == ""
    assert entries[0].preview_path == str(png_path.resolve())


def test_build_plot_gallery_entries_classifies_summary_per_frame_and_root_exports(tmp_path):
    summary_dir = tmp_path / "summary"
    per_frame_dir = tmp_path / "per_frame" / "T170C"
    summary_dir.mkdir(parents=True)
    per_frame_dir.mkdir(parents=True)

    waterfall_svg = summary_dir / "Fig_2_waterfall.svg"
    waterfall_png = summary_dir / "Fig_2_waterfall.png"
    frame_pdf = per_frame_dir / "01_scattering.pdf"
    root_pdf = tmp_path / "temperature_overview.pdf"

    waterfall_svg.write_text("<svg width='120' height='80'></svg>", encoding="utf-8")
    waterfall_png.write_bytes(b"png")
    frame_pdf.write_bytes(b"%PDF-1.4 frame")
    root_pdf.write_bytes(b"%PDF-1.4 root")

    save_generated_figure_document(
        str(waterfall_svg),
        figure_id="Fig_2_waterfall",
        technique="saxs",
        objects=[],
    )

    entries = build_plot_gallery_entries(
        [str(waterfall_png), str(waterfall_svg), str(frame_pdf), str(root_pdf)],
        output_root=str(tmp_path),
    )

    by_id = {entry.figure_id: entry for entry in entries}

    assert by_id["Fig_2_waterfall"].category == FIGURE_CATEGORY_SERIES_OVERVIEW
    assert by_id["01_scattering"].category == FIGURE_CATEGORY_PER_FRAME
    assert by_id["temperature_overview"].category == FIGURE_CATEGORY_OTHER_EXPORTS


def test_temperature_style_gallery_orders_series_overview_before_other_exports(tmp_path):
    summary_dir = tmp_path / "summary"
    per_frame_dir = tmp_path / "per_frame" / "T170C"
    summary_dir.mkdir(parents=True)
    per_frame_dir.mkdir(parents=True)

    fig1 = summary_dir / "Fig_1_overview.pdf"
    fig2 = summary_dir / "Fig_2_waterfall.svg"
    fig2_png = summary_dir / "Fig_2_waterfall.png"
    frame = per_frame_dir / "01_scattering.pdf"
    root = tmp_path / "temperature_overview.pdf"

    fig1.write_bytes(b"%PDF-1.4 fig1")
    fig2.write_text("<svg width='80' height='40'></svg>", encoding="utf-8")
    fig2_png.write_bytes(b"png")
    frame.write_bytes(b"%PDF-1.4 frame")
    root.write_bytes(b"%PDF-1.4 root")

    save_generated_figure_document(
        str(fig2),
        figure_id="Fig_2_waterfall",
        technique="saxs",
        objects=[],
    )

    entries = build_plot_gallery_entries(
        collect_plot_figure_paths(str(tmp_path), preferred_paths=[str(root)]),
        output_root=str(tmp_path),
    )

    assert [entry.figure_id for entry in entries] == [
        "Fig_1_overview",
        "Fig_2_waterfall",
        "01_scattering",
        "temperature_overview",
    ]


def test_select_plot_gallery_entry_prefers_entry_containing_current_asset(tmp_path):
    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()

    png_path = figure_dir / "temperature_overview.png"
    svg_path = figure_dir / "temperature_overview.svg"
    pdf_path = figure_dir / "temperature_overview.pdf"
    png_path.write_bytes(b"png")
    svg_path.write_text(
        "<svg width='400' height='200' viewBox='0 0 400 200'></svg>",
        encoding="utf-8",
    )
    pdf_path.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Page /MediaBox [0 0 400 200] >>\nendobj\n"
    )

    save_generated_figure_document(
        str(svg_path),
        figure_id="temperature_overview",
        technique="dsc",
        objects=[],
    )

    entries = build_plot_gallery_entries([str(png_path), str(svg_path), str(pdf_path)])
    selection = select_plot_gallery_entry(
        entries,
        preferred_path=str(pdf_path),
        preview_visible=True,
    )

    assert selection.selected_figure_id == "temperature_overview"
    assert selection.selected_path == str(png_path.resolve())
    assert selection.matched_preferred is True
    assert selection.emit_preview is True


def test_active_manifest_gallery_ignores_unrelated_historical_files(
    ir_definition,
    tmp_path,
):
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="run-1",
        technique="ir",
        definitions=(ir_definition,),
    )
    historical = tmp_path / "old" / "stale.png"
    historical.parent.mkdir()
    historical.write_bytes(b"stale")

    entries = build_active_manifest_gallery_entries(tmp_path)

    assert [entry.figure_id for entry in entries] == [manifest.figures[0].figure_id]
    entry = entries[0]
    run_root = tmp_path / "runs" / "run-1"
    assert entry.run_id == "run-1"
    assert entry.run_root == str(run_root.resolve())
    assert entry.document_path == str(
        (run_root / manifest.figures[0].document).resolve()
    )
    assert entry.capability_report["editing_mode"] == "object"
    assert entry.working_revision == 1
    assert entry.published_revision == 1
    assert {asset.role for asset in entry.assets} == {
        "preview",
        "svg",
        "png",
        "pdf",
    }
