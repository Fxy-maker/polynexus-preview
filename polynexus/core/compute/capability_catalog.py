"""Technique-neutral capability inventory exposed by :class:`ComputeRun`.

Historically this module contained a small, hand-written table of provider
metric names.  The AI platform now owns the versioned descriptor registry, but
the compute catalog remains a compatibility-facing view used by GUI/CLI
consumers.  This module projects descriptors into that view without creating a
second scientific result or inventing values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


def _public(value: Any) -> Any:
    """Return a JSON-compatible copy of frozen descriptor payloads."""

    if isinstance(value, Mapping):
        return {str(key): _public(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_public(item) for item in value]
    return value


@dataclass(frozen=True)
class CapabilityCoverage:
    """One catalog row, optionally backed by a versioned descriptor.

    ``status`` and ``shared_projection`` retain the legacy provider-result
    contract.  Descriptor-backed rows additionally expose immutable
    descriptor fields directly so callers do not need to import the AI
    platform package merely to inspect input/output contracts.
    """

    technique: str
    capability_id: str
    status: str = "provider_result"
    shared_projection: str = "result.metric_manifest"
    descriptor_version: str | None = None
    descriptor_hash: str | None = None
    input_contract: Mapping[str, Any] = field(default_factory=dict)
    output_schema: Mapping[str, Any] = field(default_factory=dict)
    preconditions: tuple[Mapping[str, Any], ...] = ()
    dependencies: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    uncertainty_policy: Mapping[str, Any] = field(default_factory=dict)
    executor_key: str | None = None
    missing_input_actions: tuple[Mapping[str, Any] | str, ...] = ()
    evidence_policy: Mapping[str, Any] = field(default_factory=dict)
    cost: Mapping[str, Any] = field(default_factory=dict)
    failure_reason_codes: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    descriptor_status: str | None = None
    descriptor_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "technique", _normalize_technique(self.technique))
        capability_id = str(self.capability_id).strip()
        if not capability_id:
            raise ValueError("Capability coverage capability_id must not be empty")
        object.__setattr__(self, "capability_id", capability_id)
        object.__setattr__(self, "status", str(self.status).strip())
        object.__setattr__(self, "shared_projection", str(self.shared_projection).strip())

    @classmethod
    def from_descriptor(
        cls,
        descriptor: Any,
        *,
        technique: str | None = None,
        status: str | None = None,
        capability_id: str | None = None,
    ) -> "CapabilityCoverage":
        """Project one ``CapabilityDescriptor`` without retaining a live ref."""

        techniques = tuple(getattr(descriptor, "techniques", ()))
        selected_technique = _normalize_technique(
            technique or (techniques[0] if techniques else "")
        )
        descriptor_status = str(getattr(descriptor, "status", "available"))
        descriptor_id = str(getattr(descriptor, "capability_id"))
        return cls(
            technique=selected_technique,
            capability_id=descriptor_id if capability_id is None else str(capability_id),
            descriptor_id=descriptor_id,
            status=descriptor_status if status is None else str(status),
            shared_projection="result.metric_manifest",
            descriptor_version=str(getattr(descriptor, "version", "1")),
            descriptor_hash=getattr(descriptor, "content_hash", None),
            input_contract=_public(getattr(descriptor, "input_contract", {})),
            output_schema=_public(getattr(descriptor, "output_schema", {})),
            preconditions=tuple(
                _public(value) for value in getattr(descriptor, "preconditions", ())
            ),
            dependencies=tuple(getattr(descriptor, "dependencies", ())),
            alternatives=tuple(getattr(descriptor, "alternatives", ())),
            uncertainty_policy=_public(getattr(descriptor, "uncertainty_policy", {})),
            executor_key=getattr(descriptor, "executor_key", None),
            missing_input_actions=tuple(
                _public(value)
                for value in getattr(descriptor, "missing_input_actions", ())
            ),
            evidence_policy=_public(getattr(descriptor, "evidence_policy", {})),
            cost=_public(getattr(descriptor, "cost", {})),
            failure_reason_codes=tuple(getattr(descriptor, "failure_reason_codes", ())),
            aliases=tuple(getattr(descriptor, "aliases", ())),
            descriptor_status=descriptor_status,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "technique": self.technique,
            "capability_id": self.capability_id,
            "status": self.status,
            "shared_projection": self.shared_projection,
        }
        # Keep the old four-field shape for rows that have no descriptor.  A
        # descriptor-backed row gets the full contract as additive fields.
        if self.descriptor_version is not None:
            payload.update(
                {
                    "descriptor_id": self.descriptor_id,
                    "descriptor_version": self.descriptor_version,
                    "descriptor_hash": self.descriptor_hash,
                    "descriptor_status": self.descriptor_status,
                    "input_contract": _public(self.input_contract),
                    "output_schema": _public(self.output_schema),
                    "preconditions": _public(self.preconditions),
                    "dependencies": list(self.dependencies),
                    "alternatives": list(self.alternatives),
                    "uncertainty_policy": _public(self.uncertainty_policy),
                    "executor_key": self.executor_key,
                    "missing_input_actions": _public(self.missing_input_actions),
                    "evidence_policy": _public(self.evidence_policy),
                    "cost": _public(self.cost),
                    "failure_reason_codes": list(self.failure_reason_codes),
                    "aliases": list(self.aliases),
                }
            )
        return payload


class CapabilityCatalog:
    """Immutable lookup over legacy and descriptor-backed capability rows."""

    def __init__(
        self,
        entries: tuple[CapabilityCoverage, ...] | list[CapabilityCoverage] = (),
    ) -> None:
        selected = tuple(entries)
        if not all(isinstance(item, CapabilityCoverage) for item in selected):
            raise TypeError("Capability catalog entries must be CapabilityCoverage values")
        self._entries = selected

    @property
    def entries(self) -> tuple[CapabilityCoverage, ...]:
        return self._entries

    def for_technique(self, technique: str) -> tuple[CapabilityCoverage, ...]:
        normalized = _normalize_technique(technique)
        return tuple(item for item in self._entries if item.technique == normalized)

    def to_dict(self) -> dict[str, Any]:
        canonical = {
            technique: [item.to_dict() for item in self.for_technique(technique)]
            for technique in sorted({item.technique for item in self._entries})
        }
        # The descriptor namespace is ``ir`` while older callers commonly use
        # ``ftir``.  Emit both keys with the exact same row objects so JSON
        # consumers cannot observe a different inventory merely by crossing an
        # entry-point alias.
        aliases = {"ftir": "ir", "infrared": "ir", "gpc": "sec", "sec/gpc": "sec"}
        for alias, target in aliases.items():
            if target in canonical:
                canonical.setdefault(alias, canonical[target])
        return {"techniques": canonical}


_CAPABILITY_NAMES = {
    "dsc": ("Tg", "Tm", "Tc", "enthalpy", "multi_peak", "Avrami", "nonisothermal_kinetics"),
    "ftir": ("peak_position", "peak_height", "peak_area", "FWHM", "peak_ratio", "temperature_tracking"),
    "saxs": ("long_period", "crystalline_layer", "amorphous_layer", "Porod", "Kratky", "Guinier", "Invariant", "temperature_strain"),
    "waxs": ("peak_decomposition", "crystallinity", "crystallite_size", "lattice_parameters", "williamson_hall"),
    "nmr": ("peak_position", "area", "FWHM", "SNR", "region_integral", "relaxation", "solid_13C_phase"),
}


def _normalize_technique(technique: object) -> str:
    """Keep catalog lookups aligned with the shared descriptor namespace."""

    normalized = str(technique).strip().lower()
    return {
        "ir": "ir",
        "ftir": "ir",
        "infrared": "ir",
        "fourier_transform_infrared": "ir",
        "saxs2d": "saxs",
        "waxs2d": "waxs",
        "gpc": "sec",
        "sec/gpc": "sec",
    }.get(normalized, normalized)


def _descriptor_for_legacy_name(
    descriptors: tuple[Any, ...], technique: str, name: str
) -> Any | None:
    normalized = _normalize_technique(technique)
    wanted = str(name).casefold()
    for descriptor in descriptors:
        if normalized not in tuple(getattr(descriptor, "techniques", ())):
            continue
        capability_id = str(getattr(descriptor, "capability_id", ""))
        short_id = (
            capability_id.rsplit(".", 2)[-2]
            if capability_id.endswith(".v1")
            else capability_id.rsplit(".", 1)[-1]
        )
        aliases = tuple(str(value) for value in getattr(descriptor, "aliases", ()))
        if (
            short_id.casefold() == wanted
            or capability_id.casefold() == wanted
            or any(alias.casefold() == wanted for alias in aliases)
        ):
            return descriptor
    return None


def _build_default_catalog() -> CapabilityCatalog:
    # Keep imports lazy: compute.models imports this module during package
    # initialization, while descriptor construction imports legacy registries.
    try:
        from ..ai_platform.capabilities import default_descriptor_registry

        descriptors = tuple(default_descriptor_registry().descriptors)
    except Exception:  # noqa: BLE001 - preserve the legacy view if a plugin is unavailable
        descriptors = ()

    entries: list[CapabilityCoverage] = []
    represented_descriptor_ids: set[str] = set()
    for technique, names in _CAPABILITY_NAMES.items():
        canonical_technique = _normalize_technique(technique)
        for name in names:
            descriptor = _descriptor_for_legacy_name(descriptors, canonical_technique, name)
            if descriptor is None:
                entries.append(CapabilityCoverage(canonical_technique, name))
                continue
            # Preserve the historical provider-result status for these rows;
            # descriptor_status carries the actual descriptor state.
            entries.append(
                CapabilityCoverage.from_descriptor(
                    descriptor,
                    technique=canonical_technique,
                    status="provider_result",
                    capability_id=name,
                )
            )
            represented_descriptor_ids.add(str(descriptor.capability_id))

    # Add namespaced generic, N-D, and unsupported descriptors.  A
    # multi-technique descriptor gets one row per namespace so for_technique()
    # remains complete and deterministic.
    seen_pairs = {(item.technique, item.capability_id) for item in entries}
    for descriptor in descriptors:
        capability_id = str(descriptor.capability_id)
        if capability_id in represented_descriptor_ids:
            continue
        for technique in tuple(getattr(descriptor, "techniques", ())):
            canonical_technique = _normalize_technique(technique)
            pair = (canonical_technique, capability_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            entries.append(
                CapabilityCoverage.from_descriptor(
                    descriptor,
                    technique=canonical_technique,
                )
            )
    return CapabilityCatalog(tuple(entries))


_DEFAULT_CATALOG: CapabilityCatalog | None = None


def default_capability_catalog() -> CapabilityCatalog:
    """Return the process-wide descriptor-projected capability catalog."""

    global _DEFAULT_CATALOG
    if _DEFAULT_CATALOG is None:
        _DEFAULT_CATALOG = _build_default_catalog()
    return _DEFAULT_CATALOG


__all__ = ["CapabilityCatalog", "CapabilityCoverage", "default_capability_catalog"]
