"""Bounded reader for TA Instruments DMA Q800 binary exports.

The Q800 exports used by the public validation pack contain a UTF-16LE header
followed by a fixed-width float32 signal record.  This reader only accepts the
observed ``CLOSED`` + ``Instrument DMA`` + ``Nsig`` signature and keeps every
declared signal as a source channel.  It does not interpret geometry or fit
material models.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
import re
import struct
from pathlib import Path


MAX_SOURCE_BYTES = 512 * 1024 * 1024
_HEADER_LIMIT = 256 * 1024
_SIGNAL_RE = re.compile(r"^\s*Sig(\d+)\s+(.+?)\s*$", re.IGNORECASE)
_NSIG_RE = re.compile(r"^\s*Nsig\s+(\d+)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class TADMAExport:
    """Decoded TA DMA channels with source-bound header provenance."""

    headers: tuple[str, ...]
    rows: tuple[tuple[float, ...], ...]
    metadata: Mapping[str, str]
    header_text: str
    data_offset: int


def looks_like_ta_dma(source: bytes) -> bool:
    """Return whether a bounded prefix has the verified TA DMA signature."""

    text = _decode_header(source)
    return (
        "closed" in text.casefold()
        and re.search(r"\binstrument\s+dma\b", text, re.IGNORECASE) is not None
        and _extract_nsig(text) is not None
        and bool(_extract_signal_headers(text))
    )


def read_ta_dma(path: str | Path) -> TADMAExport:
    """Read a TA DMA export without writing or executing external code."""

    source = Path(path)
    with source.open("rb") as handle:
        raw = handle.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("TA DMA source exceeds the bounded reader size")
    marker = raw[:_HEADER_LIMIT].find(b"\x0c\x00")
    if marker < 0:
        raise ValueError("TA DMA header terminator is missing")
    header_bytes = raw[: marker + 2]
    header_text = _decode_header(header_bytes)
    if "closed" not in header_text.casefold() or re.search(
        r"\binstrument\s+dma\b", header_text, re.IGNORECASE
    ) is None:
        raise ValueError("source is not a recognized TA DMA export")
    n_signals = _extract_nsig(header_text)
    headers = _extract_signal_headers(header_text)
    if n_signals is None or len(headers) != n_signals:
        raise ValueError("TA DMA signal header is incomplete")

    data_offset = marker + 2
    if data_offset + 1 >= len(raw):
        raise ValueError("TA DMA signal payload is missing")
    # The observed format stores Nsig as one byte immediately after the UTF-16
    # form-feed marker, followed by float32 records.  Keep a small bounded
    # fallback search for exports with one alignment byte inserted.
    if raw[data_offset] == n_signals:
        data_offset += 1
    else:
        data_offset = _find_data_offset(raw, data_offset, n_signals)
    rows = _read_rows(raw, data_offset, n_signals)
    if len(rows) < 2:
        raise ValueError("TA DMA export contains fewer than two valid records")
    metadata = _header_metadata(header_text)
    return TADMAExport(
        headers=headers,
        rows=tuple(rows),
        metadata=metadata,
        header_text=header_text,
        data_offset=data_offset,
    )


def _decode_header(source: bytes) -> str:
    if source.startswith((b"\xff\xfe", b"\xfe\xff")):
        return source.decode("utf-16", errors="replace")
    return source.decode("utf-16-le", errors="replace")


def _extract_nsig(text: str) -> int | None:
    for line in text.splitlines():
        match = _NSIG_RE.match(line)
        if match:
            value = int(match.group(1))
            return value if 1 <= value <= 256 else None
    return None


def _extract_signal_headers(text: str) -> tuple[str, ...]:
    found: dict[int, str] = {}
    for line in text.splitlines():
        match = _SIGNAL_RE.match(line)
        if match:
            index = int(match.group(1))
            label = match.group(2).strip()
            if index > 0 and label:
                found[index] = label
    if not found or tuple(found) != tuple(range(1, max(found) + 1)):
        return ()
    return tuple(found[index] for index in range(1, max(found) + 1))


def _header_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.casefold().startswith("sig"):
            continue
        key, separator, value = stripped.partition(" ")
        if separator and key and value.strip() and len(key) <= 64:
            metadata.setdefault(key, value.strip())
    return metadata


def _find_data_offset(raw: bytes, start: int, n_signals: int) -> int:
    best: tuple[int, int] | None = None
    for candidate in range(start, min(start + 32, len(raw) - n_signals * 4), 1):
        rows = _read_rows(raw, candidate, n_signals, limit=6)
        score = len(rows)
        if rows and _row_is_plausible(rows[0]):
            score += 100
        if best is None or score > best[0]:
            best = (score, candidate)
    if best is None or best[0] < 100:
        raise ValueError("TA DMA signal payload alignment is invalid")
    return best[1]


def _read_rows(
    raw: bytes,
    offset: int,
    n_signals: int,
    *,
    limit: int | None = None,
) -> list[tuple[float, ...]]:
    width = n_signals * 4
    rows: list[tuple[float, ...]] = []
    available = (len(raw) - offset) // width
    if limit is not None:
        available = min(available, limit)
    for index in range(max(0, available)):
        begin = offset + index * width
        values = struct.unpack_from(f"<{n_signals}f", raw, begin)
        if not _row_is_plausible(values):
            break
        rows.append(tuple(float(value) for value in values))
    return rows


def _row_is_plausible(values: tuple[float, ...]) -> bool:
    if not values or not all(math.isfinite(value) and abs(value) < 1e12 for value in values):
        return False
    # Time is the first declared signal in the verified Q800 exports; -100 is
    # the format's end marker.  Temperature is the second signal and remains
    # within a broad instrument-safe range.
    return values[0] >= 0.0 and -1000.0 <= values[1] <= 5000.0


__all__ = ["MAX_SOURCE_BYTES", "TADMAExport", "looks_like_ta_dma", "read_ta_dma"]
