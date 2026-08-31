"""Strict parsing for serialized shared :class:`ComputeRun` projections.

The GUI, Agent, CLI, evidence and Joint adapters all consume the JSON-safe
projection emitted by ``ComputeRun.to_dict``.  This module keeps those
consumers on one admission boundary:

* absence of a ``compute_run`` key is the only condition that permits a
  legacy-summary fallback;
* an explicitly supplied projection is never silently treated as legacy data;
* all state aliases are parsed through the canonical four-axis contract and
  must agree;
* a shared projection must explicitly describe a completed run with a
  computed state; lightweight projections may omit the larger execution
  context, but may not omit that state.

The parser is deliberately non-throwing for read-only consumers.  Invalid
projections are represented by ``valid=False`` and reason codes so each
consumer can fail closed without duplicating validation logic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from ..ai_platform.contracts import ComputationState


_MISSING = object()
_RUN_STATUSES = frozenset({"ready", "needs_input", "failed", "completed"})
_STATE_ALIASES = ("computation_state", "state")
_METRIC_MANIFEST_STATUSES = frozenset(
    {"computed", "unavailable", "needs_input", "failed", "blocked", "not_applicable"}
)
_METRIC_STATUS_COMPUTABILITY = {
    "computed": "computed",
    "needs_input": "needs_input",
    "failed": "failed",
    "blocked": "blocked",
    "not_applicable": "not_applicable",
}


def _snapshot_mapping(value: Mapping[str, Any]) -> dict[Any, Any]:
    """Return a plain recursive snapshot of a public projection mapping.

    The parser is also called by in-process adapters, where a user supplied
    ``dict``/``Mapping`` subclass could override ``get`` or ``__contains__``
    and present a different value on each read.  A single materialization at
    the boundary makes subsequent validation and consumer reads deterministic.
    Cycles are rejected because a serialized ComputeRun is JSON-shaped.
    """

    active: set[int] = set()

    def snapshot(current: Any) -> Any:
        # Check the canonical state DTO before the Mapping branch.  A
        # malicious multiple-inheritance object can otherwise present itself
        # as a mapping and be rehydrated as a trusted plain dictionary.
        if isinstance(current, ComputationState):
            # Keep the object visible to the alias validator, which can return
            # the precise ``compute_run_state_invalid`` reason for a subclass.
            # It is never invoked as a mapping here, so an MRO that also
            # implements Mapping cannot hide the type check below.
            return current
        if isinstance(current, Mapping):
            # A generic Mapping has no trustworthy way to enumerate its
            # backing entries: ``__iter__``/``__getitem__`` may deliberately
            # hide an explicit ``compute_run`` key or forge a status value.
            # Only built-in dictionaries (including subclasses whose C-level
            # storage can be read directly) and MappingProxyType are accepted
            # as JSON-shaped projection containers.  Everything else fails
            # closed instead of becoming a legacy-fallback sentinel.
            if not isinstance(current, dict) and type(current) is not MappingProxyType:
                raise TypeError("projection mapping must be a plain dict or MappingProxyType")
            marker = id(current)
            if marker in active:
                raise ValueError("cyclic projection mapping")
            active.add(marker)
            try:
                if isinstance(current, dict) and type(current) is not dict:
                    # Bypass overridable methods on dict subclasses.  The
                    # built-in slots expose the underlying stored entries.
                    raw = {
                        key: dict.__getitem__(current, key)
                        for key in dict.__iter__(current)
                    }
                else:
                    raw = dict(current)
                return {key: snapshot(item) for key, item in raw.items()}
            finally:
                active.discard(marker)
        if isinstance(current, list):
            marker = id(current)
            if marker in active:
                raise ValueError("cyclic projection sequence")
            active.add(marker)
            try:
                return [snapshot(item) for item in current]
            finally:
                active.discard(marker)
        if isinstance(current, tuple):
            marker = id(current)
            if marker in active:
                raise ValueError("cyclic projection sequence")
            active.add(marker)
            try:
                return tuple(snapshot(item) for item in current)
            finally:
                active.discard(marker)
        return current

    normalized = snapshot(value)
    if not isinstance(normalized, dict):  # defensive; the input is a Mapping
        raise TypeError("projection snapshot must be a mapping")
    return normalized


def _metric_value_at_path(
    metrics: Mapping[str, Any],
    path: str,
) -> tuple[bool, Any]:
    """Resolve one exact or dotted metric path without alias guessing."""

    if path in metrics:
        return True, metrics[path]
    parts = path.split(".")
    current: Any = metrics
    index = 0
    while index < len(parts):
        if not isinstance(current, Mapping):
            return False, None
        matched = False
        # Provider-owned field names may themselves contain periods.  Match
        # the longest available key at each level, as the ProviderResultInput
        # contract does, so validation does not invent a second escaping rule.
        for end in range(len(parts), index, -1):
            candidate = ".".join(parts[index:end])
            if candidate in current:
                current = current[candidate]
                index = end
                matched = True
                break
        if not matched:
            return False, None
    return True, current


def _metric_values_equal(left: Any, right: Any) -> bool:
    """Compare JSON-shaped metric values without leaking comparison errors."""

    try:
        result = left == right
    except Exception:  # noqa: BLE001 - malformed values fail closed
        return False
    return type(result) is bool and result


def _projection_state_equal(left: Any, right: Any) -> bool:
    """Compare canonical states without invoking a polymorphic override."""

    if left is None or right is None:
        return left is right
    if type(left) is not ComputationState or type(right) is not ComputationState:
        return False
    try:
        return _metric_values_equal(left.to_dict(), right.to_dict())
    except Exception:  # noqa: BLE001 - malformed manually supplied DTOs fail closed
        return False


def _projection_fields_equal(
    left: "ComputeRunProjection",
    right: "ComputeRunProjection",
) -> bool:
    """Return whether a hand-built DTO matches its payload re-parse."""

    try:
        if left.valid != right.valid or left.status != right.status:
            return False
        if not _projection_state_equal(left.state, right.state):
            return False
        if not _metric_values_equal(left.result, right.result):
            return False
        if left.descriptor_id != right.descriptor_id:
            return False
        if not _metric_values_equal(left.provenance, right.provenance):
            return False
        return _metric_values_equal(left.uncertainty, right.uncertainty)
    except Exception:  # noqa: BLE001 - malformed manually supplied DTOs fail closed
        return False


@dataclass(frozen=True)
class ComputeRunProjection:
    """Normalized read-only view of one serialized ComputeRun envelope.

    ``present`` distinguishes an absent field (legacy compatibility) from an
    explicitly supplied but malformed projection.  Consumers must use
    ``allows_legacy_fallback`` rather than checking ``payload is None``.
    """

    present: bool
    valid: bool
    status: str | None = None
    state: ComputationState | None = None
    result: Mapping[str, Any] | None = None
    descriptor_id: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    uncertainty: Mapping[str, Any] = field(default_factory=dict)
    payload: Mapping[str, Any] | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Keep manually created projection values on the parser contract.

        Parser-produced projections are the only values consumers should trust.
        The dataclass remains public for compatibility, though, so accepting a
        polymorphic ``ComputationState`` here would let a caller forge the
        ``computed`` property by overriding an axis or ``to_dict``.  Other
        shared DTOs reject state subclasses at construction for the same
        reason; keep this result DTO equally strict.
        """

        if self.state is not None:
            if type(self.state) is not ComputationState:
                raise TypeError(
                    "ComputeRunProjection state must use the exact ComputationState type"
                )
        if not isinstance(self.provenance, Mapping):
            raise TypeError("ComputeRunProjection provenance must be a mapping")
        if not isinstance(self.uncertainty, Mapping):
            raise TypeError("ComputeRunProjection uncertainty must be a mapping")
        if self.result is not None and not isinstance(self.result, Mapping):
            raise TypeError("ComputeRunProjection result must be a mapping or null")
        if self.payload is not None and not isinstance(self.payload, Mapping):
            raise TypeError("ComputeRunProjection payload must be a mapping or null")

    @property
    def allows_legacy_fallback(self) -> bool:
        """Whether the caller may read legacy summary fields instead."""

        return not self.present

    @property
    def computed(self) -> bool:
        """Whether this projection is a valid, completed computation."""

        return bool(
            self.valid
            and self.status == "completed"
            and self.state is not None
            and self.state.computability == "computed"
        )

    @property
    def computability(self) -> str | None:
        """Expose the canonical computability axis for lightweight consumers."""

        return self.state.computability if self.state is not None else None


def read_compute_run_projection(
    container: Mapping[str, Any] | Any,
    *,
    key: str = "compute_run",
) -> ComputeRunProjection:
    """Read a ComputeRun field while preserving absence versus invalidity.

    ``container`` is normally a step/result-summary mapping.  If ``key`` is
    absent, the returned projection is a valid legacy sentinel.  If the key is
    present, even with ``None`` or a non-mapping value, it is treated as an
    explicit shared projection and parsed strictly.
    """

    if not isinstance(container, Mapping):
        return _invalid(
            present=True,
            reason_codes=("compute_run_container_invalid",),
        )
    # Materialize the outer mapping before checking presence.  Public
    # projections are normally JSON dictionaries, but an in-process Mapping
    # subclass can override ``__contains__``/``__getitem__`` and hide an
    # explicit envelope behind the legacy fallback.
    try:
        container_snapshot = _snapshot_mapping(container)
    except Exception:  # noqa: BLE001 - read-only parser must fail closed
        return _invalid(
            present=True,
            reason_codes=("compute_run_container_invalid",),
        )
    if key not in container_snapshot:
        return _absent()
    return parse_compute_run_projection(container_snapshot[key])


def parse_compute_run_projection(value: Any = _MISSING) -> ComputeRunProjection:
    """Parse one serialized ComputeRun mapping without raising.

    Non-completed envelopes are intentionally invalid.  Their ``present`` bit
    remains true, so callers fail closed and cannot reinterpret their legacy
    fields as a successful result.
    """

    if value is _MISSING:
        return _absent()
    if not isinstance(value, Mapping):
        return _invalid(present=True, reason_codes=("compute_run_not_mapping",))

    # Work exclusively on a plain recursive snapshot.  This keeps the
    # non-throwing parser from invoking attacker-controlled ``get``/``items``
    # implementations repeatedly and prevents a validated Mapping subclass
    # from changing what downstream consumers read after admission.
    try:
        payload = _snapshot_mapping(value)
    except Exception:  # noqa: BLE001 - malformed read-only payloads fail closed
        return _invalid(
            present=True,
            reason_codes=("compute_run_mapping_invalid",),
        )
    reasons: list[str] = []
    status_value = payload.get("status", _MISSING)
    if not isinstance(status_value, str) or not status_value.strip():
        status: str | None = None
        reasons.append("compute_run_status_missing")
    else:
        status = status_value.strip().casefold()
        if status not in _RUN_STATUSES:
            reasons.append("compute_run_status_invalid")

    nested_result = payload.get("result", _MISSING)
    result: Mapping[str, Any] | None
    if nested_result is _MISSING or nested_result is None:
        result = None
    elif isinstance(nested_result, Mapping):
        result = nested_result
    else:
        result = None
        reasons.append("compute_run_result_invalid")
    # A lightweight shared projection may omit the larger result/execution
    # context.  Consumers that need metric leaves validate ``result`` at their
    # own boundary; this parser only owns the shared run identity and state.

    state_values: list[ComputationState] = []
    state_seen = False
    for current in (payload, result):
        if not isinstance(current, Mapping):
            continue
        for alias in _STATE_ALIASES:
            if alias not in current:
                continue
            state_seen = True
            candidate = current[alias]
            if candidate is None or (
                isinstance(candidate, ComputationState)
                and type(candidate) is not ComputationState
            ) or not isinstance(candidate, (Mapping, ComputationState)):
                reasons.append("compute_run_state_invalid")
                continue
            try:
                normalized = (
                    candidate
                    if type(candidate) is ComputationState
                    else ComputationState.from_dict(candidate)
                )
            except Exception:  # noqa: BLE001 - malformed state fails closed
                reasons.append("compute_run_state_invalid")
                continue
            state_values.append(normalized)
    if not state_seen:
        reasons.append("compute_run_state_missing")
    state = state_values[0] if state_values else None
    if state_values and any(item.to_dict() != state.to_dict() for item in state_values[1:]):
        reasons.append("compute_run_state_mismatch")
    if status != "completed":
        reasons.append("compute_run_status_not_completed")
    if state is not None and state.computability != "computed":
        reasons.append("compute_run_status_state_mismatch")

    descriptor_values: list[str] = []
    for current in (payload, result):
        if not isinstance(current, Mapping) or "descriptor_id" not in current:
            continue
        candidate = current["descriptor_id"]
        if candidate is None:
            continue
        if not isinstance(candidate, str) or not candidate.strip():
            reasons.append("compute_run_descriptor_invalid")
            continue
        descriptor_values.append(candidate.strip())
    descriptor_id = descriptor_values[0] if descriptor_values else None
    if descriptor_values and any(item != descriptor_id for item in descriptor_values[1:]):
        reasons.append("compute_run_descriptor_mismatch")
    projections: dict[str, dict[str, Any]] = {
        "provenance": {},
        "uncertainty": {},
    }
    for name in projections:
        values: list[Mapping[str, Any]] = []
        for current in (payload, result):
            if not isinstance(current, Mapping) or name not in current:
                continue
            candidate = current[name]
            if candidate is None:
                continue
            if not isinstance(candidate, Mapping):
                reasons.append(f"compute_run_{name}_invalid")
                continue
            values.append(candidate)
        if values:
            projections[name] = dict(values[0])
            if any(dict(item) != dict(values[0]) for item in values[1:]):
                reasons.append(f"compute_run_{name}_mismatch")

    # ``ComputeResult.metric_manifest`` repeats the shared aliases on each
    # metric row.  Treat rows as additional projections: one contradictory row
    # must not be allowed to shadow the enclosing run state or provenance.  A
    # manifest is a typed public contract, so every row must carry an explicit
    # status; otherwise a downstream consumer could silently default a forged
    # value to ``computed``.
    manifest_values: list[Any] = []
    for container in (result, payload):
        if isinstance(container, Mapping) and "metric_manifest" in container:
            manifest_values.append(container["metric_manifest"])
    manifests: list[list[Any] | tuple[Any, ...]] = []
    for manifest in manifest_values:
        if not isinstance(manifest, (list, tuple)):
            reasons.append("compute_run_metric_manifest_invalid")
            continue
        manifests.append(manifest)
    if len(manifests) > 1:
        try:
            # JSON serializers may choose list or tuple independently while
            # preserving the same rows.  Normalize only the outer sequence
            # for the alias comparison; row-level validation below remains
            # authoritative for every entry.
            if list(manifests[0]) != list(manifests[1]):
                reasons.append("compute_run_metric_manifest_mismatch")
        except Exception:  # noqa: BLE001 - malformed read-only payloads fail closed
            reasons.append("compute_run_metric_manifest_mismatch")

    # ``metric_manifest`` is a projection of ``result.metrics`` rather than a
    # second source of scientific values.  Whenever the metrics mapping is
    # supplied, computed rows must resolve to the same field and (for scalar
    # rows) carry the same value.  A lightweight projection may still omit the
    # metrics mapping entirely; that compatibility shape is validated only by
    # the row-level rules above.
    # ``metrics`` is normally nested under ``result``.  Some lightweight
    # callers flatten the result fields directly onto the ComputeRun envelope,
    # however, and a top-level ``metric_manifest`` may accompany that shape.
    # Treat both locations as aliases: validate either source and reject a
    # disagreement instead of silently validating only the nested copy.
    metric_values: list[Mapping[str, Any]] = []
    for container, reason_code in (
        (result, "compute_run_result_metrics_invalid"),
        (payload, "compute_run_metrics_invalid"),
    ):
        if not isinstance(container, Mapping) or "metrics" not in container:
            continue
        candidate_metrics = container["metrics"]
        if not isinstance(candidate_metrics, Mapping):
            reasons.append(reason_code)
            continue
        metric_values.append(candidate_metrics)
    result_metrics: Mapping[str, Any] | None = metric_values[0] if metric_values else None
    if len(metric_values) > 1 and not _metric_values_equal(
        dict(metric_values[0]), dict(metric_values[1])
    ):
        reasons.append("compute_run_metrics_mismatch")

    for manifest in manifests:
        seen_paths: set[str] = set()
        for item in manifest:
            if not isinstance(item, Mapping):
                reasons.append("compute_run_metric_manifest_invalid")
                continue

            path_value = item.get("path", _MISSING)
            normalized_path: str | None = None
            if not isinstance(path_value, str) or not path_value.strip():
                reasons.append("compute_run_metric_manifest_path_invalid")
            else:
                normalized_path = path_value.strip()
                if any(not part or part != part.strip() for part in normalized_path.split(".")):
                    reasons.append("compute_run_metric_manifest_path_invalid")
                if normalized_path in seen_paths:
                    reasons.append("compute_run_metric_manifest_duplicate_path")
                seen_paths.add(normalized_path)

            status_value = item.get("status", _MISSING)
            row_status: str | None = None
            if status_value is _MISSING:
                reasons.append("compute_run_metric_manifest_status_missing")
            elif not isinstance(status_value, str) or not status_value.strip():
                reasons.append("compute_run_metric_manifest_status_invalid")
            else:
                row_status = status_value.strip().casefold()
                if row_status not in _METRIC_MANIFEST_STATUSES:
                    reasons.append("compute_run_metric_manifest_status_invalid")
            if "value" in item and row_status != "computed":
                reasons.append("compute_run_metric_manifest_value_status_mismatch")

            if (
                result_metrics is not None
                and row_status == "computed"
                and normalized_path is not None
            ):
                metric_present, metric_value = _metric_value_at_path(
                    result_metrics,
                    normalized_path,
                )
                if not metric_present:
                    reasons.append("compute_run_metric_manifest_metrics_missing")
                elif "value" in item:
                    if not _metric_values_equal(item["value"], metric_value):
                        reasons.append("compute_run_metric_manifest_value_mismatch")
                elif item.get("kind") == "scalar":
                    # A computed scalar without a declared value cannot be
                    # consumed as a complete manifest when its source metrics
                    # are present.
                    reasons.append("compute_run_metric_manifest_value_missing")

            row_states: list[ComputationState] = []
            for alias in _STATE_ALIASES:
                if alias not in item:
                    continue
                candidate = item[alias]
                if candidate is None or (
                    isinstance(candidate, ComputationState)
                    and type(candidate) is not ComputationState
                ) or not isinstance(candidate, (Mapping, ComputationState)):
                    reasons.append("compute_run_state_invalid")
                    continue
                try:
                    normalized = (
                        candidate
                        if type(candidate) is ComputationState
                        else ComputationState.from_dict(candidate)
                    )
                except Exception:  # noqa: BLE001 - malformed state fails closed
                    reasons.append("compute_run_state_invalid")
                    continue
                row_states.append(normalized)
                if state is None:
                    # Metric rows repeat, but never establish, the run's
                    # authoritative state.
                    reasons.append("compute_run_state_missing")
                elif normalized.to_dict() != state.to_dict():
                    reasons.append("compute_run_state_mismatch")
            if row_states and any(
                candidate.to_dict() != row_states[0].to_dict()
                for candidate in row_states[1:]
            ):
                reasons.append("compute_run_state_mismatch")
            if row_status in _METRIC_STATUS_COMPUTABILITY and row_states:
                expected = _METRIC_STATUS_COMPUTABILITY[row_status]
                if any(candidate.computability != expected for candidate in row_states):
                    reasons.append("compute_run_metric_manifest_status_state_mismatch")

            item_descriptor = item.get("descriptor_id")
            if item_descriptor is not None:
                if not isinstance(item_descriptor, str) or not item_descriptor.strip():
                    reasons.append("compute_run_descriptor_invalid")
                elif descriptor_id is None:
                    descriptor_id = item_descriptor.strip()
                elif item_descriptor.strip() != descriptor_id:
                    reasons.append("compute_run_descriptor_mismatch")
            for name in projections:
                if name not in item or item[name] is None:
                    continue
                candidate = item[name]
                if not isinstance(candidate, Mapping):
                    reasons.append(f"compute_run_{name}_invalid")
                    continue
                normalized = dict(candidate)
                if name == "uncertainty" and projections[name]:
                    # Run/result uncertainty is often keyed by metric
                    # path, while a manifest row carries only that path's
                    # leaf.  Compare the corresponding leaf when present.
                    metric_path = normalized_path or ""
                    scoped = projections[name].get(metric_path)
                    if scoped is None and metric_path:
                        current: Any = projections[name]
                        for part in metric_path.split("."):
                            if not isinstance(current, Mapping) or part not in current:
                                current = None
                                break
                            current = current[part]
                        scoped = current
                    if scoped is not None:
                        if not isinstance(scoped, Mapping) or dict(scoped) != normalized:
                            reasons.append(f"compute_run_{name}_mismatch")
                        continue
                if not projections[name]:
                    projections[name] = normalized
                elif normalized != projections[name]:
                    reasons.append(f"compute_run_{name}_mismatch")

    deduped_reasons = tuple(dict.fromkeys(reasons))
    return ComputeRunProjection(
        present=True,
        valid=not deduped_reasons,
        status=status,
        state=state,
        result=result,
        descriptor_id=descriptor_id,
        provenance=projections["provenance"],
        uncertainty=projections["uncertainty"],
        payload=payload,
        reason_codes=deduped_reasons,
    )


def merge_compute_run_projections(
    *projections: ComputeRunProjection,
) -> ComputeRunProjection:
    """Combine duplicate direct/summary projections without choosing silently.

    Agent and project records may retain the same run in both a dedicated
    ``compute_run`` field and a nested ``result_summary``.  Their shared
    identity fields must agree before a consumer uses either representation.
    """

    # ``ComputeRunProjection`` is a public frozen DTO, so callers can still
    # instantiate one by hand (or provide a subclass).  Its convenience flags
    # are not an attestation: for every present projection, reparse the
    # serialized payload through the one strict parser and use that result.
    # This keeps merge from becoming a second trust boundary that can promote
    # a forged ``valid=True``/``computed`` object.  The absent sentinel is the
    # sole compatibility exception and remains usable for legacy summaries.
    normalized: list[ComputeRunProjection] = []
    preexisting_reasons: list[str] = []
    for item in projections:
        if type(item) is not ComputeRunProjection:
            normalized.append(
                _invalid(
                    present=True,
                    reason_codes=("compute_run_projection_type_invalid",),
                )
            )
            continue
        if type(item.present) is not bool or type(item.valid) is not bool:
            normalized.append(
                _invalid(
                    present=True,
                    reason_codes=("compute_run_projection_flags_invalid",),
                )
            )
            continue
        try:
            item_reasons = tuple(item.reason_codes)
        except Exception:  # noqa: BLE001 - malformed manually supplied DTOs fail closed
            normalized.append(
                _invalid(
                    present=True,
                    reason_codes=("compute_run_projection_flags_invalid",),
                )
            )
            continue
        if any(not isinstance(reason, str) for reason in item_reasons):
            normalized.append(
                _invalid(
                    present=True,
                    reason_codes=("compute_run_projection_flags_invalid",),
                )
            )
            continue
        preexisting_reasons.extend(item_reasons)
        if not item.present:
            # Do not let a manually altered absent flag hide an attached
            # payload (or other projection fields) from strict parsing.
            if any(
                value is not None
                for value in (
                    item.status,
                    item.state,
                    item.result,
                    item.descriptor_id,
                    item.payload,
                )
            ) or (
                not item.valid
                or not _metric_values_equal(item.provenance, {})
                or not _metric_values_equal(item.uncertainty, {})
                or item_reasons
            ):
                normalized.append(
                    _invalid(
                        present=True,
                        reason_codes=("compute_run_projection_absent_invalid",),
                    )
                )
            else:
                normalized.append(_absent())
            continue
        if not isinstance(item.payload, Mapping):
            if not item.valid and not item_reasons:
                preexisting_reasons.append("compute_run_projection_invalid")
            normalized.append(
                _invalid(
                    present=True,
                    reason_codes=("compute_run_projection_payload_missing",),
                )
            )
            continue
        try:
            reparsed = parse_compute_run_projection(item.payload)
        except Exception:  # noqa: BLE001 - merge must fail closed on malformed payloads
            normalized.append(
                _invalid(
                    present=True,
                    reason_codes=("compute_run_projection_payload_invalid",),
                )
            )
            continue
        if not _projection_fields_equal(item, reparsed):
            preexisting_reasons.append("compute_run_projection_fields_mismatch")
        normalized.append(reparsed)

    present = tuple(item for item in normalized if item.present)
    if not present:
        return _absent()
    reasons: list[str] = []
    reasons.extend(preexisting_reasons)
    for item in present:
        reasons.extend(item.reason_codes)
    first = present[0]
    descriptor_id = first.descriptor_id
    provenance = first.provenance
    uncertainty = first.uncertainty
    result = first.result
    payload = first.payload
    for item in present[1:]:
        if item.status != first.status:
            reasons.append("compute_run_status_mismatch")
        if (item.state is None) != (first.state is None):
            reasons.append("compute_run_state_mismatch")
        elif item.state is not None and first.state is not None:
            if item.state.to_dict() != first.state.to_dict():
                reasons.append("compute_run_state_mismatch")
        if descriptor_id is not None and item.descriptor_id is not None and item.descriptor_id != descriptor_id:
            reasons.append("compute_run_descriptor_mismatch")
        elif descriptor_id is None and item.descriptor_id is not None:
            descriptor_id = item.descriptor_id
        if provenance and item.provenance and item.provenance != provenance:
            reasons.append("compute_run_provenance_mismatch")
        elif not provenance and item.provenance:
            provenance = item.provenance
        if uncertainty and item.uncertainty and item.uncertainty != uncertainty:
            reasons.append("compute_run_uncertainty_mismatch")
        elif not uncertainty and item.uncertainty:
            uncertainty = item.uncertainty
        if result is None and item.result is not None:
            result = item.result
            payload = item.payload
    deduped = tuple(dict.fromkeys(reasons))
    return ComputeRunProjection(
        present=True,
        valid=not deduped,
        status=first.status,
        state=first.state,
        result=result,
        descriptor_id=descriptor_id,
        provenance=provenance,
        uncertainty=uncertainty,
        payload=payload,
        reason_codes=deduped,
    )


def _absent() -> ComputeRunProjection:
    return ComputeRunProjection(present=False, valid=True)


def _invalid(*, present: bool, reason_codes: tuple[str, ...]) -> ComputeRunProjection:
    return ComputeRunProjection(
        present=present,
        valid=False,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )


__all__ = [
    "ComputeRunProjection",
    "merge_compute_run_projections",
    "parse_compute_run_projection",
    "read_compute_run_projection",
]
