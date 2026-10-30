"""Bounded readers for the observed NETZSCH Proteus ``.ngb`` layouts.

This is deliberately a reader for the layouts exercised by the public
validation pack, not a claim of support for every Proteus release.  The
files are a ZIP/``CDbTable`` DSC container and a raw ``CDbTable`` TA file.
Unknown blocks are retained as provenance and never silently re-labelled.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
from pathlib import Path
import struct
import zipfile


MAX_SOURCE_BYTES = 512 * 1024 * 1024
READER_VERSION = "netzsch.ngb.observed.v1"
_BLOCK_FLOAT32 = bytes.fromhex("04a001")
_BLOCK_FLOAT64 = bytes.fromhex("05a001")


@dataclass(frozen=True)
class NetzschBlock:
    kind: str
    offset: int
    count: int
    values: tuple[float, ...]

    @property
    def end_offset(self) -> int:
        return self.offset + 7 + self.count * (4 if self.kind == "float32" else 8)


@dataclass(frozen=True)
class NetzschDSCSegment:
    index: int
    time_min: tuple[float, ...]
    temperature_c: tuple[float, ...]
    dsc_mw_per_mg: tuple[float, ...]
    extra_channels: tuple[tuple[float, ...], ...]
    source_offsets: tuple[int, ...]


@dataclass(frozen=True)
class NetzschDSCExport:
    segments: tuple[NetzschDSCSegment, ...]
    labels: tuple[str, ...]
    source_stream: str
    all_blocks: tuple[NetzschBlock, ...]


@dataclass(frozen=True)
class NetzschTGASegment:
    index: int
    temperature_c: tuple[float, ...]
    tg_mg: tuple[float, ...]
    time_min: tuple[float, ...]
    extra_channels: tuple[tuple[float, ...], ...]
    source_offsets: tuple[int, ...]

    @property
    def mass_mg(self) -> tuple[float, ...]:
        """Compatibility alias for the explicitly labelled ``TG /mg`` signal."""

        return self.tg_mg


@dataclass(frozen=True)
class NetzschTGAExport:
    segments: tuple[NetzschTGASegment, ...]
    labels: tuple[str, ...]
    all_blocks: tuple[NetzschBlock, ...]


def looks_like_netzsch_dsc(path: str | Path) -> bool:
    source = Path(path)
    if source.suffix.casefold() != ".ngb-sd7":
        return False
    try:
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
            return "Streams/stream_2.table" in names and "Streams/stream_6.table" in names
    except (OSError, zipfile.BadZipFile):
        return False


def looks_like_netzsch_tga(path: str | Path) -> bool:
    source = Path(path)
    if source.suffix.casefold() != ".ngb-ds1":
        return False
    try:
        with source.open("rb") as handle:
            prefix = handle.read(1024)
        return (
            prefix.startswith(b"\x00\x00Netzsch TA file")
            and b"CDbTable" in prefix
            and source.stat().st_size >= 1024
        )
    except OSError:
        return False


def read_netzsch_dsc(path: str | Path) -> NetzschDSCExport:
    source = Path(path)
    _check_size(source)
    try:
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
            required = {"Streams/stream_2.table", "Streams/stream_6.table"}
            if not required.issubset(names):
                raise ValueError("NETZSCH DSC stream tables are incomplete")
            data = archive.read("Streams/stream_2.table")
            labels = _extract_labels(archive.read("Streams/stream_6.table"))
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        raise ValueError("NETZSCH DSC container is unreadable") from exc
    blocks = _read_blocks(data)
    time_blocks = [block for block in blocks if block.kind == "float64"]
    signal_blocks = [block for block in blocks if block.kind == "float32"]
    if len(time_blocks) != 3 or len(signal_blocks) != 12:
        raise ValueError("NETZSCH DSC observed block layout is incomplete")
    lengths = tuple(block.count for block in time_blocks)
    if tuple(block.count for block in signal_blocks[:3]) != lengths:
        raise ValueError("NETZSCH DSC temperature channel layout is invalid")
    # The observed stream stores each float32 channel contiguously by channel,
    # with three segments per channel: temperature, DSC, and two controls.
    if any(signal_blocks[channel * 3 + segment].count != lengths[segment]
           for channel in range(4) for segment in range(3)):
        raise ValueError("NETZSCH DSC channel/segment lengths are inconsistent")
    segments = tuple(
        NetzschDSCSegment(
            index=segment,
            time_min=time_blocks[segment].values,
            temperature_c=signal_blocks[segment].values,
            dsc_mw_per_mg=signal_blocks[3 + segment].values,
            extra_channels=(signal_blocks[6 + segment].values, signal_blocks[9 + segment].values),
            source_offsets=(time_blocks[segment].offset, signal_blocks[segment].offset,
                            signal_blocks[3 + segment].offset, signal_blocks[6 + segment].offset,
                            signal_blocks[9 + segment].offset),
        )
        for segment in range(3)
    )
    return NetzschDSCExport(segments, labels, "Streams/stream_2.table", tuple(blocks))


def read_netzsch_tga(path: str | Path) -> NetzschTGAExport:
    source = Path(path)
    _check_size(source)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise ValueError("NETZSCH TGA source is unreadable") from exc
    if not looks_like_netzsch_tga(source):
        raise ValueError("source is not a recognized NETZSCH TGA file")
    blocks = _read_blocks(data)
    labels = _extract_labels(data)
    if not _has_label(labels, "tg /mg"):
        raise ValueError("NETZSCH TGA source does not declare a TG /mg channel")
    float32 = [block for block in blocks if block.kind == "float32" and block.count >= 100]
    float64 = [block for block in blocks if block.kind == "float64" and block.count >= 100]
    # The public Proteus layout contains two complete acquisition groups.  A
    # group is identified by a monotone time axis and a temperature axis.
    groups: list[NetzschTGASegment] = []
    used: set[int] = set()
    for time_block in float32:
        if time_block.offset in used or not _is_time_axis(time_block.values):
            continue
        candidates = [block for block in float32 if block.count == time_block.count and block is not time_block]
        temperature = next(
            (
                block
                for block in candidates
                if block.offset > time_block.offset and _is_temperature_axis(block.values)
            ),
            None,
        )
        if temperature is None:
            continue
        # In the observed Proteus TA layout the time/temperature/auxiliary
        # channels are float32, while TG is stored as a float64 block with the
        # same point count immediately after that group.
        mass = next(
            (block for block in float64 if block.count == time_block.count and block.offset > temperature.offset),
            None,
        )
        if mass is None:
            continue
        extras = tuple(
            block.values
            for block in candidates
            if temperature.offset < block.offset < mass.offset
        )
        used.add(time_block.offset)
        groups.append(
            NetzschTGASegment(
                index=len(groups),
                temperature_c=temperature.values,
                tg_mg=mass.values,
                time_min=time_block.values,
                extra_channels=extras,
                source_offsets=(time_block.offset, temperature.offset, mass.offset),
            )
        )
    if not groups:
        raise ValueError("NETZSCH TGA observed time/temperature/mass layout is unavailable")
    return NetzschTGAExport(tuple(groups), labels, tuple(blocks))


def _check_size(path: Path) -> None:
    try:
        if path.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("NETZSCH source exceeds the bounded reader size")
    except OSError as exc:
        raise ValueError("NETZSCH source is unreadable") from exc


def _read_blocks(data: bytes) -> tuple[NetzschBlock, ...]:
    blocks: list[NetzschBlock] = []
    for marker, kind, fmt, item_size in (
        (_BLOCK_FLOAT32, "float32", "<f", 4),
        (_BLOCK_FLOAT64, "float64", "<d", 8),
    ):
        start = 0
        while (offset := data.find(marker, start)) >= 0:
            if offset + 7 > len(data):
                raise ValueError("NETZSCH data block header is truncated")
            count = struct.unpack_from("<I", data, offset + 3)[0]
            end = offset + 7 + count * item_size
            if count < 2 or end > len(data):
                start = offset + 1
                continue
            values = struct.unpack_from(f"<{count}{'f' if kind == 'float32' else 'd'}", data, offset + 7)
            if not all(math.isfinite(value) for value in values):
                start = offset + 1
                continue
            blocks.append(NetzschBlock(kind, offset, count, tuple(float(value) for value in values)))
            start = end
    return tuple(sorted(blocks, key=lambda item: item.offset))


def _extract_labels(data: bytes) -> tuple[str, ...]:
    labels: list[str] = []
    marker = b"\x00"
    for raw in data.split(marker):
        if len(raw) < 4 or not all(32 <= value < 127 or value >= 128 for value in raw):
            continue
        text = raw.decode("latin1", errors="ignore").strip()
        if any(token in text.casefold() for token in ("time /", "temperature /", "dsc /", "tg /", "gas /", "gram")):
            if text not in labels:
                labels.append(text)
    # Labels in the uncompressed TA tables are UTF-16LE strings embedded in
    # binary records.  Scan for printable runs rather than decoding the whole
    # file, which would turn the numeric payload into misleading text.
    import re
    for match in re.finditer(rb"(?:[\x20-\x7e]\x00){3,}", data):
        text = match.group().decode("utf-16le", errors="ignore").strip("\x00 ")
        if any(token in text.casefold() for token in ("time /", "temperature /", "dsc /", "tg /", "gas /", "gram")):
            if text not in labels:
                labels.append(text)
    return tuple(labels)


def _has_label(labels: Sequence[str], expected: str) -> bool:
    expected_key = expected.casefold().replace(" ", "")
    return any(expected_key in label.casefold().replace(" ", "") for label in labels)


def _is_time_axis(values: Sequence[float]) -> bool:
    if len(values) < 100 or values[0] < -1.0 or values[-1] <= values[0] + 10.0:
        return False
    deltas = [right - left for left, right in zip(values, values[1:])]
    positive = [delta for delta in deltas if delta > 0.0]
    if len(positive) < int(0.995 * len(deltas)):
        return False
    median_step = sorted(positive)[len(positive) // 2]
    if median_step <= 0.0:
        return False
    return max(abs(delta - median_step) for delta in positive) <= median_step * 0.05


def _is_temperature_axis(values: Sequence[float]) -> bool:
    if len(values) < 100 or min(values) <= -273.15 or max(values) <= min(values) + 10.0:
        return False
    # Instrument temperature records contain small quantisation/reversal
    # noise, so require a dominant positive trend rather than strict pointwise
    # monotonicity.
    deltas = [right - left for left, right in zip(values, values[1:])]
    return sum(delta >= -0.2 for delta in deltas) >= int(0.98 * len(deltas))


def _is_mass_channel(values: Sequence[float]) -> bool:
    if not values or max(values) - min(values) <= 1e-8:
        return False
    return max(abs(value) for value in values) < 1e5


def _monotone(values: Sequence[float]) -> bool:
    return all(right >= left - 1e-6 for left, right in zip(values, values[1:]))


__all__ = [
    "MAX_SOURCE_BYTES", "READER_VERSION", "NetzschBlock", "NetzschDSCExport",
    "NetzschDSCSegment", "NetzschTGAExport", "NetzschTGASegment",
    "looks_like_netzsch_dsc", "looks_like_netzsch_tga", "read_netzsch_dsc", "read_netzsch_tga",
]
