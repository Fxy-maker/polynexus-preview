"""Figure asset discovery and format selection helpers."""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


MASTER_FORMAT_PRIORITY = ("svg", "pdf", "png", "jpg", "jpeg")
PREVIEW_FORMAT_PRIORITY = ("png", "jpg", "jpeg", "svg", "pdf")
PUBLICATION_FORMAT_PRIORITY = ("pdf", "svg", "png")
KNOWN_FIGURE_FORMATS = tuple(dict.fromkeys(MASTER_FORMAT_PRIORITY + PREVIEW_FORMAT_PRIORITY))


@dataclass
class FigureAssetSpec:
    figure_id: str
    sidecar_key: str
    master_path: str
    preview_path: str
    publication_paths: Dict[str, str] = field(default_factory=dict)
    available_formats: List[str] = field(default_factory=list)
    preferred_master_format: str = ""
    width_px: int = 0
    height_px: int = 0
    dpi: int = 0
    figsize_in: Tuple[float, float] = (0.0, 0.0)
    background: str = "#FFFFFF"

    def to_dict(self) -> dict:
        return {
            "figure_id": self.figure_id,
            "sidecar_key": self.sidecar_key,
            "master_path": self.master_path,
            "preview_path": self.preview_path,
            "publication_paths": dict(self.publication_paths),
            "available_formats": list(self.available_formats),
            "preferred_master_format": self.preferred_master_format,
            "width_px": self.width_px,
            "height_px": self.height_px,
            "dpi": self.dpi,
            "figsize_in": [float(self.figsize_in[0]), float(self.figsize_in[1])],
            "background": self.background,
        }


def figure_id_from_path(path: str) -> str:
    return Path(path).stem


def sidecar_key_for_path(path: str, output_root: Optional[str] = None) -> str:
    resolved = Path(path).resolve()
    if output_root:
        try:
            return resolved.relative_to(Path(output_root).resolve()).as_posix()
        except ValueError:
            pass
    return resolved.name


def discover_figure_asset(path: str, output_root: Optional[str] = None) -> FigureAssetSpec:
    source = Path(path).resolve()
    figure_id = figure_id_from_path(str(source))
    siblings = _discover_sibling_formats(source)
    if source.suffix.lower().lstrip(".") not in siblings and source.exists():
        siblings[source.suffix.lower().lstrip(".")] = source

    master_format, master_path = _pick_format(siblings, MASTER_FORMAT_PRIORITY, source)
    _preview_format, preview_path = _pick_format(siblings, PREVIEW_FORMAT_PRIORITY, source)
    publication_paths = {
        fmt: str(siblings[fmt].resolve())
        for fmt in PUBLICATION_FORMAT_PRIORITY
        if fmt in siblings
    }
    available_formats = sorted(fmt for fmt in siblings if fmt)
    width_px, height_px, dpi, figsize_in = _read_asset_dimensions(preview_path, master_path)

    return FigureAssetSpec(
        figure_id=figure_id,
        sidecar_key=sidecar_key_for_path(str(source), output_root=output_root),
        master_path=str(master_path.resolve()),
        preview_path=str(preview_path.resolve()),
        publication_paths=publication_paths,
        available_formats=available_formats,
        preferred_master_format=master_format,
        width_px=width_px,
        height_px=height_px,
        dpi=dpi,
        figsize_in=figsize_in,
        background="#FFFFFF",
    )


def _discover_sibling_formats(source: Path) -> Dict[str, Path]:
    directory = source.parent
    figure_id = source.stem
    siblings: Dict[str, Path] = {}
    for fmt in KNOWN_FIGURE_FORMATS:
        candidate = directory / f"{figure_id}.{fmt}"
        if candidate.exists():
            siblings[fmt] = candidate.resolve()
    return siblings


def _pick_format(
    siblings: Dict[str, Path],
    priority: Tuple[str, ...],
    fallback: Path,
) -> Tuple[str, Path]:
    for fmt in priority:
        if fmt in siblings:
            return fmt, siblings[fmt]
    fallback_format = fallback.suffix.lower().lstrip(".")
    return fallback_format, fallback


def _read_asset_dimensions(*paths: Path) -> Tuple[int, int, int, Tuple[float, float]]:
    seen = set()
    for path in paths:
        resolved = Path(path).resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        width, height, dpi = _read_dimensions_for_path(resolved)
        if width > 0 and height > 0:
            figsize_in = (0.0, 0.0)
            if dpi > 0:
                figsize_in = (round(width / dpi, 3), round(height / dpi, 3))
            return width, height, dpi, figsize_in
    return 0, 0, 0, (0.0, 0.0)


def _read_dimensions_for_path(path: Path) -> Tuple[int, int, int]:
    suffix = path.suffix.lower().lstrip(".")
    try:
        if suffix == "png":
            return _read_png_dimensions(path)
        if suffix == "svg":
            return _read_svg_dimensions(path)
        if suffix == "pdf":
            return _read_pdf_dimensions(path)
        if suffix in {"jpg", "jpeg"}:
            return _read_jpeg_dimensions(path)
    except OSError:
        return 0, 0, 0
    return 0, 0, 0


def _read_png_dimensions(path: Path) -> Tuple[int, int, int]:
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            return 0, 0, 0
        width = 0
        height = 0
        dpi = 0
        while True:
            length_data = handle.read(4)
            if len(length_data) != 4:
                break
            length = struct.unpack(">I", length_data)[0]
            chunk_type = handle.read(4)
            chunk_data = handle.read(length)
            handle.read(4)
            if len(chunk_type) != 4 or len(chunk_data) != length:
                break
            if chunk_type == b"IHDR" and length >= 8:
                width, height = struct.unpack(">II", chunk_data[:8])
            elif chunk_type == b"pHYs" and length >= 9:
                x_ppu, y_ppu, unit = struct.unpack(">IIB", chunk_data[:9])
                if unit == 1 and x_ppu > 0 and y_ppu > 0:
                    dpi = int(round(((x_ppu + y_ppu) / 2.0) * 0.0254))
            elif chunk_type == b"IEND":
                break
        return int(width), int(height), dpi


def _read_svg_dimensions(path: Path) -> Tuple[int, int, int]:
    text = path.read_text(encoding="utf-8", errors="ignore")[:8192]
    width = _svg_length_to_px(_svg_attr(text, "width"))
    height = _svg_length_to_px(_svg_attr(text, "height"))
    if width <= 0 or height <= 0:
        view_box = _svg_attr(text, "viewBox")
        if view_box:
            numbers = [
                float(value)
                for value in re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", view_box)
            ]
            if len(numbers) >= 4:
                width = width or int(round(numbers[2]))
                height = height or int(round(numbers[3]))
    dpi = 96 if width > 0 and height > 0 else 0
    return int(width), int(height), dpi


def _read_pdf_dimensions(path: Path) -> Tuple[int, int, int]:
    data = path.read_bytes()[:65536].decode("latin-1", errors="ignore")
    match = re.search(
        r"/MediaBox\s*\[\s*"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s+"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s+"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s+"
        r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*\]",
        data,
        re.IGNORECASE,
    )
    if not match:
        return 0, 0, 0
    x0, y0, x1, y1 = (float(match.group(index)) for index in range(1, 5))
    width = int(round(abs(x1 - x0)))
    height = int(round(abs(y1 - y0)))
    return width, height, 72 if width > 0 and height > 0 else 0


def _read_jpeg_dimensions(path: Path) -> Tuple[int, int, int]:
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            return 0, 0, 0
        while True:
            marker_prefix = handle.read(1)
            if not marker_prefix:
                return 0, 0, 0
            if marker_prefix != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if not marker or marker in {b"\xd9", b"\xda"}:
                return 0, 0, 0
            length_data = handle.read(2)
            if len(length_data) != 2:
                return 0, 0, 0
            segment_length = struct.unpack(">H", length_data)[0]
            if segment_length < 2:
                return 0, 0, 0
            payload_length = segment_length - 2
            marker_value = marker[0]
            if marker_value in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            }:
                data = handle.read(payload_length)
                if len(data) < 5:
                    return 0, 0, 0
                height, width = struct.unpack(">HH", data[1:5])
                return int(width), int(height), 0
            handle.seek(payload_length, 1)


def _svg_attr(text: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*=\s*['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _svg_length_to_px(value: str) -> int:
    if not value:
        return 0
    match = re.match(r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*([a-z%]*)\s*$", value, re.IGNORECASE)
    if not match:
        return 0
    number = float(match.group(1))
    unit = match.group(2).lower()
    if unit in {"", "px"}:
        return int(round(number))
    if unit == "in":
        return int(round(number * 96))
    if unit == "cm":
        return int(round(number * 96 / 2.54))
    if unit == "mm":
        return int(round(number * 96 / 25.4))
    if unit == "pt":
        return int(round(number * 96 / 72.0))
    return 0
