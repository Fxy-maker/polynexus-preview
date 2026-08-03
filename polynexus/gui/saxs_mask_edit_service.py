"""Public GUI boundary for static SAXS mask editing eligibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SAXSMaskEditContext:
    """Detached image/base-mask data supplied to the editor widget."""

    image: np.ndarray
    base_mask: np.ndarray
    source_path: str


def build_saxs_mask_edit_context(
    result: Any,
    *,
    technique: str,
    submodule_id: str,
    input_mode: str,
    source_path: str,
) -> SAXSMaskEditContext | None:
    """Return an eligible static 2D editor context or fail closed."""

    if str(technique or "").strip().lower() != "saxs":
        return None
    if str(submodule_id or "").strip().lower() != "saxs.static":
        return None
    if str(input_mode or "").strip().lower() != "single":
        return None

    raw_data = getattr(result, "raw_data", None)
    if not isinstance(raw_data, dict):
        return None
    try:
        image = np.asarray(raw_data.get("img"), dtype=float)
        base_mask = np.asarray(raw_data.get("mask_edit_base_mask"), dtype=bool)
    except (TypeError, ValueError):
        return None
    if image.ndim != 2 or base_mask.ndim != 2 or image.shape != base_mask.shape:
        return None
    if image.size == 0:
        return None

    image_copy = np.ascontiguousarray(image, dtype=float).copy()
    base_copy = np.ascontiguousarray(base_mask, dtype=bool).copy()
    image_copy.setflags(write=False)
    base_copy.setflags(write=False)
    return SAXSMaskEditContext(
        image=image_copy,
        base_mask=base_copy,
        source_path=str(source_path or ""),
    )


__all__ = ["SAXSMaskEditContext", "build_saxs_mask_edit_context"]
