import struct
import zlib
from pathlib import Path

from polynexus.core.figure_assets import (
    discover_figure_asset,
    figure_id_from_path,
    read_figure_asset_dimensions,
    sidecar_key_for_path,
)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def _write_png(path: Path, width: int, height: int) -> None:
    raw_rows = b"".join(b"\x00" + (b"\xff\xff\xff" * width) for _ in range(height))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw_rows))
        + _png_chunk(b"IEND", b"")
    )


def test_figure_asset_spec_prefers_svg_master_and_png_preview(tmp_path):
    root = tmp_path / "output"
    fig_dir = root / "figures"
    fig_dir.mkdir(parents=True)
    svg = fig_dir / "Fig-W1_profile.svg"
    png = fig_dir / "Fig-W1_profile.png"
    pdf = fig_dir / "Fig-W1_profile.pdf"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"></svg>',
        encoding="utf-8",
    )
    png.write_bytes(b"not a real png")
    pdf.write_bytes(b"%PDF-1.4\n")

    spec = discover_figure_asset(str(png), output_root=str(root))

    assert spec.figure_id == "Fig-W1_profile"
    assert spec.preferred_master_format == "svg"
    assert Path(spec.master_path) == svg
    assert Path(spec.preview_path) == png
    assert spec.publication_paths["pdf"] == str(pdf.resolve())
    assert spec.available_formats == ["pdf", "png", "svg"]
    assert spec.sidecar_key == "figures/Fig-W1_profile.png"
    assert spec.width_px == 600
    assert spec.height_px == 400


def test_figure_asset_helpers_use_stable_relative_keys(tmp_path):
    root = tmp_path / "output"
    path = root / "summary" / "Fig-S1_overview.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"%PDF-1.4\n")

    assert figure_id_from_path(str(path)) == "Fig-S1_overview"
    assert sidecar_key_for_path(str(path), output_root=str(root)) == (
        "summary/Fig-S1_overview.pdf"
    )


def test_figure_asset_spec_reads_png_dimensions(tmp_path):
    figure_path = tmp_path / "figures" / "Fig-D1_profile.png"
    figure_path.parent.mkdir()
    _write_png(figure_path, 80, 40)

    spec = discover_figure_asset(str(figure_path))

    assert spec.width_px == 80
    assert spec.height_px == 40


def test_figure_asset_spec_reads_svg_dimensions(tmp_path):
    figure_path = tmp_path / "figures" / "Fig-D2_profile.svg"
    figure_path.parent.mkdir()
    figure_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"></svg>',
        encoding="utf-8",
    )

    spec = discover_figure_asset(str(figure_path))

    assert spec.width_px == 600
    assert spec.height_px == 400


def test_figure_asset_spec_reads_pdf_media_box_dimensions(tmp_path):
    figure_path = tmp_path / "figures" / "Fig-D3_profile.pdf"
    figure_path.parent.mkdir()
    figure_path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Page /MediaBox [0 0 612 792] >> endobj\n"
        b"%%EOF\n"
    )

    spec = discover_figure_asset(str(figure_path))

    assert spec.width_px == 612
    assert spec.height_px == 792
    assert spec.dpi == 72
    assert spec.figsize_in == (8.5, 11.0)


def test_figure_asset_spec_reads_jpeg_dimensions(tmp_path):
    figure_path = tmp_path / "figures" / "Fig-D4_profile.jpg"
    figure_path.parent.mkdir()
    figure_path.write_bytes(
        b"\xff\xd8"
        + b"\xff\xe0"
        + struct.pack(">H", 16)
        + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        + b"\xff\xc0"
        + struct.pack(">H", 17)
        + b"\x08"
        + struct.pack(">HH", 40, 80)
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
        + b"\xff\xd9"
    )

    spec = discover_figure_asset(str(figure_path))

    assert spec.width_px == 80
    assert spec.height_px == 40


def test_public_dimension_reader_reports_png_svg_and_pdf(three_format_paths):
    assert read_figure_asset_dimensions(three_format_paths["png"])[0:2] == (
        1200,
        600,
    )
    assert read_figure_asset_dimensions(three_format_paths["svg"])[0:2] == (
        192,
        96,
    )
    assert read_figure_asset_dimensions(three_format_paths["pdf"])[0:2] == (
        144,
        72,
    )
