from __future__ import annotations

from .base import TechniquePreprocessAdapter
from .dsc import DSCPreprocessAdapter
from .ir import IRPreprocessAdapter
from .nmr import NMRPreprocessAdapter
from .saxs import SAXSPreprocessAdapter
from .waxs import WAXSPreprocessAdapter


_ADAPTERS: dict[str, TechniquePreprocessAdapter] = {
    "DSC": DSCPreprocessAdapter(),
    "IR": IRPreprocessAdapter(),
    "NMR": NMRPreprocessAdapter(),
    "SAXS": SAXSPreprocessAdapter(),
    "WAXS": WAXSPreprocessAdapter(),
}


def get_preprocess_adapter(technique: str) -> TechniquePreprocessAdapter:
    key = str(technique or "").strip().upper()
    try:
        return _ADAPTERS[key]
    except KeyError as exc:
        raise ValueError(f"No preprocessing adapter registered for {technique}") from exc
