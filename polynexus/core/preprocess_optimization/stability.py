"""Deterministic, evidence-first stability studies for preprocessing candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Mapping, Sequence

import numpy as np

from .candidates import stable_config_hash


def _finite(value: Any) -> bool:
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError, OverflowError):
        return False


def _json_safe(value: Any) -> Any:
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _normalise_reason_codes(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    items = (value,) if isinstance(value, str) else value
    if not isinstance(items, Sequence):
        items = (items,)
    reasons = [
        reason
        for item in items
        if item is not None and (reason := str(item).strip())
    ]
    return tuple(dict.fromkeys(reasons))


def _periodic_mean_180(values: np.ndarray) -> float:
    doubled = np.deg2rad(2.0 * np.asarray(values, dtype=float))
    sine = float(np.mean(np.sin(doubled)))
    cosine = float(np.mean(np.cos(doubled)))
    if abs(sine) < 1e-12 and abs(cosine) < 1e-12:
        reference = float(values[0])
        unwrapped = reference + (values - reference + 90.0) % 180.0 - 90.0
        return float(np.mean(unwrapped) % 180.0)
    return float((0.5 * np.rad2deg(np.arctan2(sine, cosine))) % 180.0)


def _unwrap_180(values: np.ndarray) -> np.ndarray:
    reference = _periodic_mean_180(values)
    return reference + (values - reference + 90.0) % 180.0 - 90.0


@dataclass(frozen=True)
class ParameterDomain:
    name: str
    minimum: float | None = None
    maximum: float | None = None
    values: tuple[Any, ...] = ()
    required_metrics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ValueError("parameter domain name is required")
        if any(not str(metric).strip() for metric in self.required_metrics):
            raise ValueError(f"{self.name}: required metric names cannot be empty")
        if self.values:
            if self.minimum is not None or self.maximum is not None:
                raise ValueError(f"{self.name}: categorical domain cannot have numeric bounds")
            return
        if not (_finite(self.minimum) and _finite(self.maximum)):
            raise ValueError(f"{self.name}: bounds must be finite")
        if float(self.minimum) >= float(self.maximum):
            raise ValueError(f"{self.name}: minimum must be less than maximum")

    @property
    def span(self) -> float:
        return float(self.maximum) - float(self.minimum) if not self.values else 1.0

    def clamp(self, value: float) -> float:
        if self.values:
            return self.values[int(round(float(value))) % len(self.values)]  # type: ignore[return-value]
        return float(np.clip(float(value), self.minimum, self.maximum))


@dataclass(frozen=True)
class StabilityStudyRequest:
    baseline_config: dict[str, Any]
    domains: tuple[ParameterDomain, ...]
    seed: int = 0
    global_trials: int = 24
    active_trials: int = 12
    confirmation_trials: int = 9
    min_plateau_points: int = 3
    min_plateau_fraction: float = 0.5
    neighbor_radius: float = 0.75
    continuity_relative_tolerance: float = 0.05
    acceptance_score: float = 0.82
    auto_accept_score: float = 0.90
    bootstrap_replicates: int = 256
    decision_mode: str = "strict"
    allow_auto_accept: bool = True
    continuity_required: bool = True

    def __post_init__(self) -> None:
        if not self.baseline_config:
            raise ValueError("baseline_config is required")
        if not self.domains:
            raise ValueError("at least one parameter domain is required")
        names = [domain.name for domain in self.domains]
        if len(names) != len(set(names)):
            raise ValueError("parameter domain names must be unique")
        missing_baseline = [
            name for name in names if name not in self.baseline_config
        ]
        if missing_baseline:
            raise ValueError(
                "baseline_config missing active domain keys: "
                + ", ".join(missing_baseline)
            )
        if self.global_trials < 1 or self.active_trials < 0 or self.confirmation_trials < 0:
            raise ValueError("trial counts are invalid")
        if self.min_plateau_points < 1 or self.bootstrap_replicates < 16:
            raise ValueError("stability evidence counts are invalid")
        if not (0.0 < self.min_plateau_fraction <= 1.0):
            raise ValueError("min_plateau_fraction must be in (0, 1]")
        if self.decision_mode not in {"strict", "quick"}:
            raise ValueError("decision_mode must be strict or quick")

    @property
    def max_trials(self) -> int:
        return 1 + self.global_trials + self.active_trials + self.confirmation_trials


@dataclass(frozen=True)
class BootstrapInterval:
    lower: float
    median: float
    upper: float
    replicates: int

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class ContinuityEvidence:
    passed: bool
    metric_max_relative_step: dict[str, float] = field(default_factory=dict)
    frame_count: int = 0
    reason_codes: tuple[str, ...] = ()
    status: str | None = None
    metric_median_increment: dict[str, float] = field(default_factory=dict)
    metric_mad_increment: dict[str, float] = field(default_factory=dict)
    metric_max_robust_deviation: dict[str, float] = field(default_factory=dict)
    metric_finite_frame_count: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        status = self.status or ("passed" if self.passed else "failed")
        if status not in {"passed", "failed", "insufficient", "not_applicable"}:
            raise ValueError(f"invalid continuity status: {status}")
        if self.passed != (status == "passed"):
            raise ValueError("continuity passed/status values are inconsistent")
        object.__setattr__(self, "status", status)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return _json_safe(payload)


@dataclass(frozen=True)
class PlateauSummary:
    connected: bool
    trial_indices: tuple[int, ...] = ()
    parameter_bounds: dict[str, tuple[float, float]] = field(default_factory=dict)
    score_min: float | None = None
    score_max: float | None = None
    score_median: float | None = None
    coverage_fraction: float = 0.0
    active_dimensions: tuple[str, ...] = ()
    spread_dimensions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trial_indices"] = list(self.trial_indices)
        return _json_safe(payload)


@dataclass(frozen=True)
class StabilityTrial:
    index: int
    config: dict[str, Any]
    score: float | None
    physical_passed: bool
    quality_passed: bool
    continuity_passed: bool
    metrics: dict[str, float] = field(default_factory=dict)
    frame_values: dict[str, tuple[float, ...]] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return _json_safe(payload)


@dataclass(frozen=True, init=False)
class StabilityReport:
    interval_semantics: ClassVar[str] = "parameter_perturbation"

    schema_version: str
    decision: str
    complete: bool
    baseline_config: dict[str, Any]
    selected_config: dict[str, Any]
    trials: tuple[StabilityTrial, ...]
    plateau: PlateauSummary
    perturbation_intervals: dict[str, BootstrapInterval]
    continuity: ContinuityEvidence
    physics_gate_passed: bool
    quality_gate_passed: bool
    reason_codes: tuple[str, ...] = ()
    mode: str | None = None
    active_dimensions: tuple[str, ...] = ()
    excluded_dimensions: dict[str, str] = field(default_factory=dict)

    def __init__(
        self,
        schema_version: str,
        decision: str,
        complete: bool,
        baseline_config: dict[str, Any],
        selected_config: dict[str, Any],
        trials: tuple[StabilityTrial, ...],
        plateau: PlateauSummary,
        bootstrap: dict[str, BootstrapInterval] | None = None,
        continuity: ContinuityEvidence | None = None,
        physics_gate_passed: bool | None = None,
        quality_gate_passed: bool | None = None,
        reason_codes: tuple[str, ...] = (),
        mode: str | None = None,
        active_dimensions: tuple[str, ...] = (),
        excluded_dimensions: dict[str, str] | None = None,
        *,
        perturbation_intervals: dict[str, BootstrapInterval] | None = None,
    ) -> None:
        if continuity is None:
            raise TypeError("continuity is required")
        if physics_gate_passed is None:
            raise TypeError("physics_gate_passed is required")
        if quality_gate_passed is None:
            raise TypeError("quality_gate_passed is required")
        if (
            perturbation_intervals is not None
            and bootstrap is not None
            and perturbation_intervals != bootstrap
        ):
            raise ValueError(
                "perturbation_intervals and bootstrap alias are inconsistent"
            )
        intervals = (
            perturbation_intervals
            if perturbation_intervals is not None
            else bootstrap
            if bootstrap is not None
            else {}
        )
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "decision", decision)
        object.__setattr__(self, "complete", complete)
        object.__setattr__(self, "baseline_config", baseline_config)
        object.__setattr__(self, "selected_config", selected_config)
        object.__setattr__(self, "trials", trials)
        object.__setattr__(self, "plateau", plateau)
        object.__setattr__(self, "perturbation_intervals", dict(intervals))
        object.__setattr__(self, "continuity", continuity)
        object.__setattr__(self, "physics_gate_passed", physics_gate_passed)
        object.__setattr__(self, "quality_gate_passed", quality_gate_passed)
        object.__setattr__(self, "reason_codes", reason_codes)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "active_dimensions", active_dimensions)
        object.__setattr__(
            self,
            "excluded_dimensions",
            excluded_dimensions or {},
        )

    @property
    def bootstrap(self) -> Mapping[str, BootstrapInterval]:
        """Read-only compatibility alias for persisted v1 consumers."""

        return MappingProxyType(self.perturbation_intervals)

    @property
    def trial_count(self) -> int:
        return len(self.trials)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision": self.decision,
            "complete": self.complete,
            "baseline_config": _json_safe(self.baseline_config),
            "selected_config": _json_safe(self.selected_config),
            "trials": [trial.to_dict() for trial in self.trials],
            "plateau": self.plateau.to_dict(),
            "perturbation_intervals": {
                name: item.to_dict()
                for name, item in self.perturbation_intervals.items()
            },
            "interval_semantics": self.interval_semantics,
            # Read-only compatibility alias for persisted v1 consumers.
            "bootstrap": {name: item.to_dict() for name, item in self.bootstrap.items()},
            "continuity": self.continuity.to_dict(),
            "physics_gate_passed": self.physics_gate_passed,
            "quality_gate_passed": self.quality_gate_passed,
            "reason_codes": list(self.reason_codes),
            "mode": self.mode,
            "active_dimensions": list(self.active_dimensions),
            "excluded_dimensions": _json_safe(self.excluded_dimensions),
        }


def _latin_hypercube(request: StabilityStudyRequest, count: int, rng: np.random.Generator) -> list[dict[str, Any]]:
    dimensions = len(request.domains)
    if count <= 0:
        return []
    unit = np.empty((count, dimensions), dtype=float)
    for column in range(dimensions):
        values = (np.arange(count, dtype=float) + rng.random(count)) / count
        rng.shuffle(values)
        unit[:, column] = values
    configs: list[dict[str, Any]] = []
    for row in unit:
        config = dict(request.baseline_config)
        for value, domain in zip(row, request.domains):
            if domain.values:
                config[domain.name] = domain.values[min(int(value * len(domain.values)), len(domain.values) - 1)]
            else:
                config[domain.name] = domain.clamp(float(domain.minimum) + value * domain.span)
        configs.append(config)
    return configs


def _normalised_distance(first: Mapping[str, Any], second: Mapping[str, Any], request: StabilityStudyRequest) -> float:
    distances = []
    for domain in request.domains:
        if domain.values:
            if first.get(domain.name) != second.get(domain.name):
                return float("inf")
            continue
        span = max(domain.span, 1e-12)
        distances.append(abs(float(first[domain.name]) - float(second[domain.name])) / span)
    return float(np.sqrt(np.mean(np.square(distances)))) if distances else 0.0


def _local_configs(
    center: Mapping[str, Any],
    request: StabilityStudyRequest,
    count: int,
    *,
    scale: float,
) -> list[dict[str, Any]]:
    if count <= 0:
        return []
    offsets = (-scale, 0.0, scale)
    configs: list[dict[str, Any]] = []
    for index in range(count):
        config = dict(request.baseline_config)
        for dimension, domain in enumerate(request.domains):
            offset = offsets[(index + dimension) % len(offsets)]
            if domain.values:
                current = domain.values.index(center[domain.name]) if center[domain.name] in domain.values else 0
                config[domain.name] = domain.values[(current + index + dimension) % len(domain.values)]
            else:
                config[domain.name] = domain.clamp(float(center[domain.name]) + offset * domain.span)
        configs.append(config)
    return configs


def _normalise_trial(index: int, config: dict[str, Any], raw: Any, *, cached: bool) -> StabilityTrial:
    payload = raw if isinstance(raw, Mapping) else {}
    score = payload.get("score")
    score_value = float(score) if _finite(score) else None
    metrics: dict[str, float] = {}
    for name, value in (payload.get("metrics", {}) or {}).items():
        if _finite(value):
            metrics[str(name)] = float(value)
    frames: dict[str, tuple[float, ...]] = {}
    for name, values in (payload.get("frame_values", {}) or {}).items():
        try:
            array = np.asarray(values, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            continue
        if array.size and bool(np.any(np.isfinite(array))):
            # Preserve frame slots, including non-finite values.  Compressing
            # them would fabricate adjacency across missing frames.
            frames[str(name)] = tuple(float(value) for value in array)
    for name in (
        "f_herman",
        "f_herman_raw",
        "orientation_axis_deg",
        "orientation_strength",
    ):
        if name in metrics or name not in frames:
            continue
        finite_values = np.asarray(frames[name], dtype=float)
        finite_values = finite_values[np.isfinite(finite_values)]
        if not finite_values.size:
            continue
        metrics[name] = (
            _periodic_mean_180(finite_values)
            if name == "orientation_axis_deg"
            else float(np.mean(finite_values))
        )
    reasons = _normalise_reason_codes(payload.get("reason_codes"))
    return StabilityTrial(
        index=index,
        config=dict(config),
        score=score_value,
        physical_passed=bool(payload.get("physical_passed", False)),
        quality_passed=bool(payload.get("quality_passed", False)),
        continuity_passed=True,
        metrics=metrics,
        frame_values=frames,
        reason_codes=reasons,
        cached=cached,
    )


def _active_dimension_evidence_reasons(
    trial: StabilityTrial,
    request: StabilityStudyRequest,
) -> tuple[str, ...]:
    observed_metrics = set(trial.metrics) | set(trial.frame_values)
    return tuple(
        f"active_dimension_evidence_missing:{domain.name}"
        for domain in request.domains
        if domain.required_metrics
        and not observed_metrics.intersection(domain.required_metrics)
    )


def _trial_has_active_dimension_evidence(trial: StabilityTrial) -> bool:
    return not any(
        reason.startswith("active_dimension_evidence_missing:")
        for reason in trial.reason_codes
    )


def _annotate_active_dimension_evidence(
    trial: StabilityTrial,
    request: StabilityStudyRequest,
) -> StabilityTrial:
    reasons = _active_dimension_evidence_reasons(trial, request)
    if not reasons:
        return trial
    return StabilityTrial(
        **{
            **asdict(trial),
            "reason_codes": tuple(dict.fromkeys((*trial.reason_codes, *reasons))),
        }
    )


def _has_isolated_increment_outlier(
    increments: np.ndarray,
    *,
    global_center: float,
    global_limit: float,
    relative_tolerance: float,
) -> bool:
    """Return true only for a globally unusual, two-sided local trend break."""

    if increments.size < 3:
        return False
    global_deviations = np.abs(increments - global_center)
    for index in np.flatnonzero(global_deviations > global_limit):
        if index <= 0 or index >= increments.size - 1:
            if index <= 0:
                neighbours = increments[1 : min(increments.size, 4)]
            else:
                neighbours = increments[max(0, increments.size - 4) : -1]
            local_center = float(np.median(neighbours))
            local_mad = float(np.median(np.abs(neighbours - local_center)))
            local_typical = max(float(np.median(np.abs(neighbours))), 1e-12)
            local_scale = max(
                1.4826 * local_mad,
                relative_tolerance * local_typical,
            )
            if abs(float(increments[index]) - global_center) > 6.0 * local_scale:
                return True
            continue
        neighbours = np.asarray(
            (increments[index - 1], increments[index + 1]),
            dtype=float,
        )
        local_center = float(np.median(neighbours))
        local_mad = float(np.median(np.abs(neighbours - local_center)))
        local_typical = max(float(np.median(np.abs(neighbours))), 1e-12)
        local_scale = max(
            1.4826 * local_mad,
            relative_tolerance * local_typical,
        )
        if abs(float(increments[index]) - local_center) > 6.0 * local_scale:
            return True
    return False


def _continuity_for_trials(
    trials: Sequence[StabilityTrial], request: StabilityStudyRequest
) -> ContinuityEvidence:
    # Continuity is a frame-wise property.  Do not concatenate independent
    # parameter trials: the boundary between two trial results is not a
    # physical time/temperature step and would create a false discontinuity.
    if not request.continuity_required:
        return ContinuityEvidence(False, status="not_applicable")

    frame_count = 0
    max_steps: dict[str, float] = {}
    median_step_samples: dict[str, list[float]] = {}
    mad_steps: dict[str, float] = {}
    robust_deviations: dict[str, float] = {}
    finite_counts: dict[str, int] = {}
    metric_trial_presence: dict[str, int] = {}
    reasons: list[str] = []
    statuses: list[str] = []
    for trial in trials:
        for name, sequence in trial.frame_values.items():
            frame_count = max(frame_count, len(sequence))
            array = np.asarray(sequence, dtype=float)
            finite = np.isfinite(array)
            finite_count = int(np.count_nonzero(finite))
            metric_trial_presence[name] = metric_trial_presence.get(name, 0) + 1
            finite_counts[name] = min(
                finite_counts.get(name, finite_count), finite_count
            )
            if finite_count < 4:
                statuses.append("insufficient")
                reasons.append(f"continuity_insufficient:{name}")
                continue
            if not bool(np.all(finite)):
                statuses.append("insufficient")
                reasons.append(f"continuity_nonfinite:{name}")
                continue
            increments = np.diff(array)
            if name == "orientation_axis_deg":
                increments = (increments + 90.0) % 180.0 - 90.0
            median_increment = float(np.median(increments))
            deviations = np.abs(increments - median_increment)
            mad_increment = float(np.median(deviations))
            max_deviation = float(np.max(deviations))
            response_scale = max(float(np.median(np.abs(array))), 1e-12)
            median_absolute_increment = max(
                float(np.median(np.abs(increments))), 1e-12
            )
            # MAD is the primary local increment scale.  When it collapses to
            # zero, use a small fraction of the typical increment; the
            # response's absolute offset must never relax the jump gate.
            robust_scale = max(
                1.4826 * mad_increment,
                request.continuity_relative_tolerance
                * median_absolute_increment,
            )
            robust_limit = 6.0 * robust_scale
            max_relative_step = float(np.max(np.abs(increments)) / response_scale)
            max_steps[name] = max(max_steps.get(name, 0.0), max_relative_step)
            median_step_samples.setdefault(name, []).append(median_increment)
            mad_steps[name] = max(mad_steps.get(name, 0.0), mad_increment)
            robust_deviations[name] = max(
                robust_deviations.get(name, 0.0), max_deviation
            )
            if _has_isolated_increment_outlier(
                increments,
                global_center=median_increment,
                global_limit=robust_limit,
                relative_tolerance=request.continuity_relative_tolerance,
            ):
                statuses.append("failed")
                reasons.append(f"continuity_jump:{name}")
            else:
                statuses.append("passed")
    for name, present_count in metric_trial_presence.items():
        if present_count < len(trials):
            finite_counts[name] = 0
    if not statuses:
        return ContinuityEvidence(
            False,
            frame_count=frame_count,
            reason_codes=("cross_frame_evidence_missing",),
            status="insufficient",
        )
    status = (
        "failed"
        if "failed" in statuses
        else "insufficient"
        if "insufficient" in statuses
        else "passed"
    )
    median_steps = {
        name: float(np.median(values))
        for name, values in median_step_samples.items()
    }
    return ContinuityEvidence(
        status == "passed",
        max_steps,
        frame_count,
        tuple(dict.fromkeys(reasons)),
        status,
        median_steps,
        mad_steps,
        robust_deviations,
        finite_counts,
    )


def _bootstrap(
    trials: Sequence[StabilityTrial], request: StabilityStudyRequest, seed: int
) -> dict[str, BootstrapInterval]:
    samples: dict[str, list[float]] = {"score": [float(t.score) for t in trials if t.score is not None]}
    for trial in trials:
        for name, value in trial.metrics.items():
            samples.setdefault(name, []).append(float(value))
    rng = np.random.default_rng(seed)
    result: dict[str, BootstrapInterval] = {}
    for name, values in samples.items():
        if not values:
            continue
        array = np.asarray(values, dtype=float)
        if name == "orientation_axis_deg":
            array = _unwrap_180(array)
        if array.size == 1:
            boot = array
        else:
            indices = rng.integers(0, array.size, size=(request.bootstrap_replicates, array.size))
            boot = np.mean(array[indices], axis=1)
        result[name] = BootstrapInterval(
            lower=float(np.percentile(boot, 2.5)),
            median=float(np.percentile(boot, 50.0)),
            upper=float(np.percentile(boot, 97.5)),
            replicates=int(request.bootstrap_replicates),
        )
    return result


def _plateau(
    trials: Sequence[StabilityTrial], request: StabilityStudyRequest
) -> PlateauSummary:
    eligible = [
        trial
        for trial in trials
        if trial.score is not None and trial.physical_passed and trial.quality_passed and trial.continuity_passed
        and _trial_has_active_dimension_evidence(trial)
        and trial.score >= request.acceptance_score
    ]
    unique_eligible: list[StabilityTrial] = []
    seen_indices: set[int] = set()
    seen_configs: set[str] = set()
    for trial in eligible:
        config_key = stable_config_hash(trial.config)
        if trial.index in seen_indices or config_key in seen_configs:
            continue
        seen_indices.add(trial.index)
        seen_configs.add(config_key)
        unique_eligible.append(trial)
    eligible = unique_eligible
    active_dimensions = tuple(domain.name for domain in request.domains)
    if not eligible:
        return PlateauSummary(False, active_dimensions=active_dimensions)
    best = max(eligible, key=lambda trial: float(trial.score))
    component = {best.index}
    neighbor_radius = min(
        request.neighbor_radius,
        0.35 + 0.05 / math.sqrt(len(request.domains)),
    )
    changed = True
    while changed:
        changed = False
        for trial in eligible:
            if trial.index in component:
                continue
            if any(
                _normalised_distance(trial.config, other.config, request) <= neighbor_radius
                for other in eligible
                if other.index in component
            ):
                component.add(trial.index)
                changed = True
    members = [trial for trial in eligible if trial.index in component]
    bounds = {
        domain.name: (
            min(float(trial.config[domain.name]) for trial in members),
            max(float(trial.config[domain.name]) for trial in members),
        )
        for domain in request.domains
        if not domain.values
    }
    spread_dimensions = tuple(
        domain.name
        for domain in request.domains
        if not domain.values
        and (
            bounds[domain.name][1] - bounds[domain.name][0]
        ) / max(domain.span, 1e-12)
        > 1e-12
    )
    scores = np.asarray([float(trial.score) for trial in members], dtype=float)
    numeric_dimension_count = sum(not domain.values for domain in request.domains)
    dimension_spread_sufficient = (
        numeric_dimension_count < 2 or len(spread_dimensions) >= 2
    )
    connected = (
        len(members) >= request.min_plateau_points
        and dimension_spread_sufficient
    )
    return PlateauSummary(
        connected=connected,
        trial_indices=tuple(sorted(component)),
        parameter_bounds=bounds,
        score_min=float(np.min(scores)),
        score_max=float(np.max(scores)),
        score_median=float(np.median(scores)),
        coverage_fraction=float(len(members) / max(len(eligible), 1)),
        active_dimensions=active_dimensions,
        spread_dimensions=spread_dimensions,
    )


def run_stability_study(
    request: StabilityStudyRequest,
    evaluator: Callable[[dict[str, Any]], Mapping[str, Any]],
) -> StabilityReport:
    """Evaluate a bounded neighborhood and return evidence without mutation."""
    rng = np.random.default_rng(int(request.seed))
    proposed = [dict(request.baseline_config)]
    proposed.extend(_latin_hypercube(request, request.global_trials, rng))
    trials: list[StabilityTrial] = []
    cache: dict[str, StabilityTrial] = {}
    for config in proposed:
        key = stable_config_hash(config)
        cached_trial = cache.get(key)
        if cached_trial is not None:
            continue
        try:
            raw = evaluator(dict(config))
        except Exception as exc:
            raw = {"reason_codes": [f"evaluation_error:{type(exc).__name__}"]}
        trial = _annotate_active_dimension_evidence(
            _normalise_trial(len(trials), config, raw, cached=False),
            request,
        )
        cache[key] = trial
        trials.append(trial)

    best = max(
        trials,
        key=lambda trial: trial.score if trial.score is not None and trial.physical_passed and trial.quality_passed and _trial_has_active_dimension_evidence(trial) else -float("inf"),
    )
    local = _local_configs(best.config, request, request.active_trials, scale=0.20)
    local.extend(_local_configs(best.config, request, request.confirmation_trials, scale=0.08))
    for config in local:
        if len(trials) >= request.max_trials:
            break
        key = stable_config_hash(config)
        if key in cache:
            continue
        try:
            raw = evaluator(dict(config))
        except Exception as exc:
            raw = {"reason_codes": [f"evaluation_error:{type(exc).__name__}"]}
        trial = _annotate_active_dimension_evidence(
            _normalise_trial(len(trials), config, raw, cached=False),
            request,
        )
        cache[key] = trial
        trials.append(trial)

    annotated_trials: list[StabilityTrial] = []
    for trial in trials:
        trial_continuity = _continuity_for_trials((trial,), request)
        required_failure = request.continuity_required and not trial_continuity.passed
        annotated_trials.append(
            StabilityTrial(
                **{
                    **asdict(trial),
                    "continuity_passed": not required_failure,
                    "reason_codes": tuple(
                        dict.fromkeys(
                            tuple(trial.reason_codes)
                            + tuple(trial_continuity.reason_codes)
                            + (
                                ("cross_frame_continuity_failed",)
                                if required_failure
                                else ()
                            )
                        )
                    ),
                }
            )
        )
    trials = annotated_trials
    plateau = _plateau(trials, request)
    plateau_trials = [trial for trial in trials if trial.index in plateau.trial_indices]
    # A non-empty plateau owns the study-level continuity decision.  When no
    # plateau survives, retain all per-trial evidence as diagnostics instead
    # of degrading a typed jump/insufficiency into "evidence missing".
    continuity = _continuity_for_trials(
        plateau_trials if plateau_trials else trials,
        request,
    )
    bootstrap = _bootstrap(plateau_trials, request, int(request.seed) + 1)
    physics_passed = bool(plateau_trials) and all(trial.physical_passed for trial in plateau_trials)
    quality_passed = bool(plateau_trials) and all(trial.quality_passed for trial in plateau_trials)
    reasons: list[str] = []
    if not physics_passed:
        reasons.append("physical_gate_failed")
    if not quality_passed:
        reasons.append("quality_gate_failed")
    continuity_gate_passed = (
        not request.continuity_required or continuity.status == "passed"
    )
    if not continuity_gate_passed:
        reasons.append("cross_frame_continuity_failed")
    score_interval = bootstrap.get("score")
    stable = plateau.connected and plateau.coverage_fraction >= request.min_plateau_fraction
    if not stable:
        reasons.append("stable_plateau_insufficient")
    numeric_dimension_count = sum(not domain.values for domain in request.domains)
    if (
        len(plateau.trial_indices) >= request.min_plateau_points
        and numeric_dimension_count >= 2
        and len(plateau.spread_dimensions) < 2
    ):
        reasons.append("stable_plateau_dimension_spread_insufficient")
    if stable and physics_passed and quality_passed and continuity_gate_passed:
        if request.allow_auto_accept and score_interval is not None and score_interval.lower >= request.auto_accept_score:
            decision = "auto_accept"
        else:
            decision = "request_confirmation"
    else:
        decision = "keep_original"
    selectable = plateau_trials or [
        trial
        for trial in trials
        if trial.score is not None and _trial_has_active_dimension_evidence(trial)
    ]
    selected_config = {}
    if selectable:
        selected = max(
            selectable,
            key=lambda trial: trial.score
            if trial.score is not None
            else -float("inf"),
        )
        selected_config = dict(selected.config)
    return StabilityReport(
        schema_version="saxs-stability-v1",
        decision=decision,
        complete=True,
        baseline_config=dict(request.baseline_config),
        selected_config=selected_config,
        trials=tuple(trials),
        plateau=plateau,
        bootstrap=bootstrap,
        continuity=continuity,
        physics_gate_passed=physics_passed,
        quality_gate_passed=quality_passed,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )
