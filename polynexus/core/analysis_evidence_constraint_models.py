from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceConstraint:
    name: str
    kind: str
    source: str
    severity: str
    description: str
    field: str | None = None
    rationale: str | None = None
    triggered: bool = False
    observed: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _inventory(*constraints: EvidenceConstraint) -> list[EvidenceConstraint]:
    return list(constraints)

