"""Deterministic, evidence-first stability studies for preprocessing candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any, Callable, Mapping, Sequence

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


@dataclass(frozen=True)
class ParameterDomain:
    name: str
    minimum: float | None = None
    maximum: float | None = None
    values: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ValueError("parameter domain name is required")
        if self.values:
            if self.minimum is not None or self.maximum is not None:
                raise ValueError(f"{self.name}: categorical domain cannot have numeric bounds")
            return
        if not (_finite(self.minimum) and _finite(self.maximum)):
            raise ValueError(f"{self.name}: bounds must be finite")
        if float(self.minimum) > float(self.maximum):
            raise ValueError(f"{self.name}: minimum exceeds maximum")

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

    def __post_init__(self) -> None:
        if not self.baseline_config:
            raise ValueError("baseline_config is required")
        if not self.domains:
            raise ValueError("at least one parameter domain is required")
        names = [domain.name for domain in self.domains]
        if len(names) != len(set(names)):
            raise ValueError("parameter domain names must be unique")
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


@dataclass(frozen=True)
class StabilityReport:
    schema_version: str
    decision: str
    complete: bool
    baseline_config: dict[str, Any]
    selected_config: dict[str, Any]
    trials: tuple[StabilityTrial, ...]
    plateau: PlateauSummary
    bootstrap: dict[str, BootstrapInterval]
    continuity: ContinuityEvidence
    physics_gate_passed: bool
    quality_gate_passed: bool
    reason_codes: tuple[str, ...] = ()
    mode: str | None = None

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
            "bootstrap": {name: item.to_dict() for name, item in self.bootstrap.items()},
            "continuity": self.continuity.to_dict(),
            "physics_gate_passed": self.physics_gate_passed,
            "quality_gate_passed": self.quality_gate_passed,
            "reason_codes": list(self.reason_codes),
            "mode": self.mode,
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
        span = max(domain.span, 1e-12)
        if domain.values:
            distances.append(0.0 if first.get(domain.name) == second.get(domain.name) else 1.0)
        else:
            distances.append(abs(float(first[domain.name]) - float(second[domain.name])) / span)
    return float(np.sqrt(np.mean(np.square(distances)))) if distances else float("inf")


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
        finite = array[np.isfinite(array)]
        if finite.size:
            frames[str(name)] = tuple(float(value) for value in finite)
    reasons = tuple(str(item) for item in payload.get("reason_codes", ()) if item is not None)
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


def _continuity_for_trials(
    trials: Sequence[StabilityTrial], request: StabilityStudyRequest
) -> ContinuityEvidence:
    # Continuity is a frame-wise property.  Do not concatenate independent
    # parameter trials: the boundary between two trial results is not a
    # physical time/temperature step and would create a false discontinuity.
    frame_count = 0
    max_steps: dict[str, float] = {}
    reasons: list[str] = []
    observed = False
    for trial in trials:
        for name, sequence in trial.frame_values.items():
            observed = True
            frame_count = max(frame_count, len(sequence))
            array = np.asarray(sequence, dtype=float)
            if array.size < 2:
                max_steps.setdefault(name, 0.0)
                continue
            scale = max(abs(float(np.nanmedian(array))), 1e-12)
            step = float(np.nanmax(np.abs(np.diff(array))) / scale)
            max_steps[name] = max(max_steps.get(name, 0.0), step)
            if step > request.continuity_relative_tolerance:
                reasons.append(f"continuity_break:{name}")
    if not observed:
        return ContinuityEvidence(False, {}, frame_count, ("cross_frame_evidence_missing",))
    return ContinuityEvidence(not reasons, max_steps, frame_count, tuple(dict.fromkeys(reasons)))


def _trial_continuity_passed(trial: StabilityTrial, request: StabilityStudyRequest) -> bool:
    """Return whether one candidate's own frame sequence is continuous."""
    if not trial.frame_values:
        return False
    for sequence in trial.frame_values.values():
        array = np.asarray(sequence, dtype=float)
        if array.size < 2:
            continue
        scale = max(abs(float(np.nanmedian(array))), 1e-12)
        if float(np.nanmax(np.abs(np.diff(array))) / scale) > request.continuity_relative_tolerance:
            return False
    return True


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
        and trial.score >= request.acceptance_score
    ]
    if not eligible:
        return PlateauSummary(False)
    best = max(eligible, key=lambda trial: float(trial.score))
    component = {best.index}
    changed = True
    while changed:
        changed = False
        for trial in eligible:
            if trial.index in component:
                continue
            if any(
                _normalised_distance(trial.config, other.config, request) <= request.neighbor_radius
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
    }
    scores = np.asarray([float(trial.score) for trial in members], dtype=float)
    connected = len(members) >= request.min_plateau_points
    return PlateauSummary(
        connected=connected,
        trial_indices=tuple(sorted(component)),
        parameter_bounds=bounds,
        score_min=float(np.min(scores)),
        score_max=float(np.max(scores)),
        score_median=float(np.median(scores)),
        coverage_fraction=float(len(members) / max(len(eligible), 1)),
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
            trials.append(cached_trial)
            continue
        try:
            raw = evaluator(dict(config))
        except Exception as exc:
            raw = {"reason_codes": [f"evaluation_error:{type(exc).__name__}"]}
        trial = _normalise_trial(len(trials), config, raw, cached=False)
        cache[key] = trial
        trials.append(trial)

    best = max(
        trials,
        key=lambda trial: trial.score if trial.score is not None and trial.physical_passed and trial.quality_passed else -float("inf"),
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
        trial = _normalise_trial(len(trials), config, raw, cached=False)
        cache[key] = trial
        trials.append(trial)

    continuity = _continuity_for_trials(trials, request)
    trials = [
        StabilityTrial(
            **{
                **asdict(trial),
                "continuity_passed": _trial_continuity_passed(trial, request),
                "reason_codes": tuple(trial.reason_codes)
                + (() if _trial_continuity_passed(trial, request) else ("cross_frame_continuity_failed",)),
            }
        )
        for trial in trials
    ]
    plateau = _plateau(trials, request)
    plateau_trials = [trial for trial in trials if trial.index in plateau.trial_indices]
    bootstrap = _bootstrap(plateau_trials, request, int(request.seed) + 1)
    physics_passed = bool(plateau_trials) and all(trial.physical_passed for trial in plateau_trials)
    quality_passed = bool(plateau_trials) and all(trial.quality_passed for trial in plateau_trials)
    reasons: list[str] = []
    if not physics_passed:
        reasons.append("physical_gate_failed")
    if not quality_passed:
        reasons.append("quality_gate_failed")
    if not continuity.passed:
        reasons.append("cross_frame_continuity_failed")
    score_interval = bootstrap.get("score")
    stable = plateau.connected and plateau.coverage_fraction >= request.min_plateau_fraction
    if not stable:
        reasons.append("stable_plateau_insufficient")
    if stable and physics_passed and quality_passed and continuity.passed:
        if request.allow_auto_accept and score_interval is not None and score_interval.lower >= request.auto_accept_score:
            decision = "auto_accept"
        else:
            decision = "request_confirmation"
    else:
        decision = "keep_original"
    selected = max(plateau_trials or trials, key=lambda trial: trial.score if trial.score is not None else -float("inf"))
    return StabilityReport(
        schema_version="saxs-stability-v1",
        decision=decision,
        complete=True,
        baseline_config=dict(request.baseline_config),
        selected_config=dict(selected.config),
        trials=tuple(trials),
        plateau=plateau,
        bootstrap=bootstrap,
        continuity=continuity,
        physics_gate_passed=physics_passed,
        quality_gate_passed=quality_passed,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )
