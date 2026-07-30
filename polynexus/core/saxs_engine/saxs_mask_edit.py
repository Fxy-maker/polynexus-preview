"""Strict, user-owned SAXS detector mask edit candidates."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


class MaskEditValidationError(ValueError):
    """Raised when a mask candidate cannot be safely validated."""


def _normalize_mask(mask: Any, *, name: str) -> np.ndarray:
    try:
        array = np.asarray(mask, dtype=bool)
    except (TypeError, ValueError) as exc:
        raise MaskEditValidationError(f"{name} must be a boolean 2D mask") from exc
    if array.ndim != 2:
        raise MaskEditValidationError(f"{name} must be a boolean 2D mask")
    return np.ascontiguousarray(array, dtype=bool)


def mask_digest(mask: Any) -> str:
    """Return a shape-bound digest without retaining the mask payload."""

    array = _normalize_mask(mask, name="mask")
    shape = ",".join(str(int(value)) for value in array.shape).encode("ascii")
    return hashlib.sha256(shape + b":" + array.tobytes(order="C")).hexdigest()


def build_mask_edit_candidate(
    base_mask: Any,
    edited_mask: Any,
    *,
    source_path: str = "",
    frame_index: int | None = None,
) -> dict[str, Any]:
    """Build a detached candidate from two same-shaped boolean masks."""

    base = _normalize_mask(base_mask, name="base_mask")
    edited = _normalize_mask(edited_mask, name="edited_mask")
    if base.shape != edited.shape:
        raise MaskEditValidationError("base_mask and edited_mask shapes differ")

    operations = [
        [int(row), int(column), bool(edited[row, column])]
        for row, column in np.argwhere(base != edited)
    ]
    return {
        "schema_version": 1,
        "source_path": str(source_path or ""),
        "frame_index": int(frame_index) if frame_index is not None else None,
        "shape": [int(value) for value in base.shape],
        "base_mask_digest": mask_digest(base),
        "edited_mask_digest": mask_digest(edited),
        "changed_pixel_count": len(operations),
        "operations": operations,
        "confirmed": False,
    }


def _candidate_shape(candidate: Mapping[str, Any]) -> tuple[int, int]:
    raw_shape = candidate.get("shape")
    if (
        not isinstance(raw_shape, Sequence)
        or isinstance(raw_shape, (str, bytes))
        or len(raw_shape) != 2
    ):
        raise MaskEditValidationError("candidate shape is invalid")
    try:
        shape = (int(raw_shape[0]), int(raw_shape[1]))
    except (TypeError, ValueError, OverflowError) as exc:
        raise MaskEditValidationError("candidate shape is invalid") from exc
    if any(value <= 0 for value in shape) or any(
        isinstance(value, bool) for value in raw_shape
    ):
        raise MaskEditValidationError("candidate shape is invalid")
    return shape


def validate_mask_edit_candidate(candidate: Any, base_mask: Any) -> np.ndarray:
    """Validate and materialize a candidate's edited mask without applying it."""

    if not isinstance(candidate, Mapping):
        raise MaskEditValidationError("mask candidate must be a mapping")
    if candidate.get("schema_version") != 1:
        raise MaskEditValidationError("unsupported mask candidate schema")

    base = _normalize_mask(base_mask, name="base_mask")
    if _candidate_shape(candidate) != base.shape:
        raise MaskEditValidationError("candidate shape does not match base_mask")
    if candidate.get("base_mask_digest") != mask_digest(base):
        raise MaskEditValidationError("base mask digest does not match candidate")

    operations = candidate.get("operations")
    if not isinstance(operations, Sequence) or isinstance(operations, (str, bytes)):
        raise MaskEditValidationError("candidate operations are invalid")

    edited = base.copy()
    seen: set[tuple[int, int]] = set()
    for operation in operations:
        if (
            not isinstance(operation, Sequence)
            or isinstance(operation, (str, bytes))
            or len(operation) != 3
            or not isinstance(operation[2], (bool, np.bool_))
        ):
            raise MaskEditValidationError("candidate operation is invalid")
        row, column = operation[0], operation[1]
        if isinstance(row, bool) or isinstance(column, bool):
            raise MaskEditValidationError("candidate coordinate is invalid")
        try:
            row, column = int(row), int(column)
        except (TypeError, ValueError, OverflowError) as exc:
            raise MaskEditValidationError("candidate coordinate is invalid") from exc
        if not (0 <= row < base.shape[0] and 0 <= column < base.shape[1]):
            raise MaskEditValidationError("candidate coordinate is out of bounds")
        coordinate = (row, column)
        if coordinate in seen or bool(base[coordinate]) == bool(operation[2]):
            raise MaskEditValidationError("candidate operation is not a change")
        seen.add(coordinate)
        edited[coordinate] = bool(operation[2])

    try:
        changed_count = int(candidate.get("changed_pixel_count"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise MaskEditValidationError("candidate changed_pixel_count is invalid") from exc
    if changed_count != len(operations):
        raise MaskEditValidationError("candidate changed_pixel_count is inconsistent")
    if candidate.get("edited_mask_digest") != mask_digest(edited):
        raise MaskEditValidationError("edited mask digest does not match candidate")
    return edited


def confirm_mask_edit_candidate(candidate: Any, base_mask: Any) -> dict[str, Any]:
    """Validate a candidate and return a detached confirmed record."""

    if not isinstance(candidate, Mapping):
        raise MaskEditValidationError("mask candidate must be a mapping")
    validate_mask_edit_candidate(candidate, base_mask)
    confirmed = dict(candidate)
    confirmed["operations"] = [list(operation) for operation in candidate["operations"]]
    confirmed["confirmed"] = True
    return confirmed


def apply_confirmed_mask_edit(candidate_base_mask: Any, candidate: Any) -> np.ndarray:
    """Apply only a validated confirmed candidate to a new mask array."""

    if not isinstance(candidate, Mapping) or candidate.get("confirmed") is not True:
        raise MaskEditValidationError("mask candidate is not confirmed")
    return validate_mask_edit_candidate(candidate, candidate_base_mask)


__all__ = [
    "MaskEditValidationError",
    "apply_confirmed_mask_edit",
    "build_mask_edit_candidate",
    "confirm_mask_edit_candidate",
    "mask_digest",
    "validate_mask_edit_candidate",
]
