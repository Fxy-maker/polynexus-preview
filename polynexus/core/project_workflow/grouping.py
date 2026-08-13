"""Conservative filename-derived experiment candidate grouping."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .models import ProjectArtifact


_TEMPERATURE = re.compile(r"^(?P<prefix>.+?)-(?P<value>\d+(?:\.\d+)?)$", re.IGNORECASE)
_TIME = re.compile(r"^(?P<prefix>.+?)-for\s+(?P<value>\d+(?:\.\d+)?)\s*min$", re.IGNORECASE)


@dataclass(frozen=True)
class CandidateExperimentGroup:
    """A filename-derived selection option, never a verified lab fact."""

    group_id: str
    label: str
    technique: str
    condition_kind: str
    condition_values: tuple[float, ...]
    artifact_paths: tuple[str, ...]
    status: str = "inferred_from_filename"

    def to_dict(self) -> dict[str, object]:
        return {
            "group_id": self.group_id,
            "label": self.label,
            "technique": self.technique,
            "condition_kind": self.condition_kind,
            "condition_values": list(self.condition_values),
            "artifact_paths": list(self.artifact_paths),
            "status": self.status,
        }


def candidate_groups(artifacts: Iterable[ProjectArtifact]) -> tuple[CandidateExperimentGroup, ...]:
    """Return stable candidates from compatible same-technique file names."""
    grouped: dict[tuple[str, str, str], list[tuple[float, str]]] = {}
    for artifact in artifacts:
        if artifact.technique == "unknown" or artifact.inspection_status == "blocked":
            continue
        stem = artifact.relative_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        time_match = _TIME.match(stem)
        temperature_match = _TEMPERATURE.match(stem)
        if time_match:
            prefix, value, kind = time_match.group("prefix"), float(time_match.group("value")), "time_min"
        elif temperature_match:
            prefix, value, kind = temperature_match.group("prefix"), float(temperature_match.group("value")), "temperature_C"
        else:
            continue
        key = (artifact.technique, prefix, kind)
        grouped.setdefault(key, []).append((value, artifact.relative_path))
    candidates: list[CandidateExperimentGroup] = []
    for (technique, prefix, kind), values in sorted(
        grouped.items(), key=lambda item: (item[0][2] == "time_min", item[0])
    ):
        ordered = sorted(values)
        display_prefix = prefix.replace("-", " ").strip()
        if kind == "time_min":
            label = f"{display_prefix} C time series"
        else:
            label = f"{display_prefix} temperature series"
        candidates.append(CandidateExperimentGroup(
            group_id=f"{technique}:{prefix.lower()}:{kind}",
            label=label,
            technique=technique,
            condition_kind=kind,
            condition_values=tuple(value for value, _ in ordered),
            artifact_paths=tuple(path for _, path in ordered),
        ))
    return tuple(candidates)


__all__ = ["CandidateExperimentGroup", "candidate_groups"]
