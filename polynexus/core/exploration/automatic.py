"""Bounded automatic exploration orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Mapping, Sequence

from polynexus.core.ai_platform.contracts import canonical_json_hash

from .contracts import ExplorationRequest, ExplorationRun
from .runner import ExplorationRunner


@dataclass(frozen=True)
class ExplorationBudget:
    max_attempts: int = 32
    max_wall_time_s: float = 300.0
    max_consecutive_failures: int | None = None
    stop_on_first_completed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.max_attempts, int) or isinstance(self.max_attempts, bool) or self.max_attempts <= 0:
            raise ValueError("max_attempts must be a positive integer")
        if not isinstance(self.max_wall_time_s, (int, float)) or self.max_wall_time_s <= 0:
            raise ValueError("max_wall_time_s must be positive")
        if self.max_consecutive_failures is not None and (
            not isinstance(self.max_consecutive_failures, int)
            or isinstance(self.max_consecutive_failures, bool)
            or self.max_consecutive_failures <= 0
        ):
            raise ValueError("max_consecutive_failures must be a positive integer or null")

    @property
    def budget_hash(self) -> str:
        return canonical_json_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_attempts": self.max_attempts,
            "max_wall_time_s": float(self.max_wall_time_s),
            "max_consecutive_failures": self.max_consecutive_failures,
            "stop_on_first_completed": bool(self.stop_on_first_completed),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExplorationBudget":
        if not isinstance(value, Mapping):
            raise TypeError("exploration budget must be a mapping")
        return cls(
            max_attempts=value.get("max_attempts", 32),
            max_wall_time_s=value.get("max_wall_time_s", 300.0),
            max_consecutive_failures=value.get("max_consecutive_failures"),
            stop_on_first_completed=value.get("stop_on_first_completed", False),
        )


@dataclass(frozen=True)
class AutomaticExplorationResult:
    attempts: tuple[ExplorationRun, ...]
    stop_reason: str
    seed: int
    budget_hash: str
    exploration_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if not self.attempts:
            raise ValueError("automatic exploration must retain at least one attempt")
        if not all(type(attempt) is ExplorationRun for attempt in self.attempts):
            raise TypeError("automatic exploration attempts must be exact ExplorationRun values")
        if not str(self.stop_reason).strip():
            raise ValueError("stop_reason must be nonempty")
        payload = self._payload()
        expected = canonical_json_hash(payload)
        if self.exploration_hash and self.exploration_hash != expected:
            raise ValueError("automatic exploration hash does not match its content")
        object.__setattr__(self, "exploration_hash", expected)

    def _payload(self) -> dict[str, Any]:
        return {
            "attempts": [run.to_dict() for run in self.attempts],
            "stop_reason": self.stop_reason,
            "seed": self.seed,
            "budget_hash": self.budget_hash,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "exploration_hash": self.exploration_hash}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AutomaticExplorationResult":
        if not isinstance(value, Mapping):
            raise TypeError("automatic exploration result must be a mapping")
        attempts = value.get("attempts", ())
        if not isinstance(attempts, (list, tuple)):
            raise TypeError("automatic exploration attempts must be a sequence")
        return cls(
            attempts=tuple(ExplorationRun.from_dict(item) for item in attempts),
            stop_reason=value["stop_reason"],
            seed=value["seed"],
            budget_hash=value["budget_hash"],
            exploration_hash=value.get("exploration_hash", ""),
        )


class AutomaticExplorationRunner:
    """Execute a finite candidate sequence and retain every attempt."""

    def __init__(self, runner: ExplorationRunner) -> None:
        if type(runner) is not ExplorationRunner:
            raise TypeError("AutomaticExplorationRunner requires an ExplorationRunner")
        self.runner = runner

    def run(
        self,
        base_request: ExplorationRequest,
        candidates: Sequence[Mapping[str, Any]],
        *,
        seed: int,
        budget: ExplorationBudget,
    ) -> AutomaticExplorationResult:
        if type(base_request) is not ExplorationRequest:
            raise TypeError("base_request must be an ExplorationRequest")
        if base_request.canonical_admission is None:
            raise ValueError("automatic exploration requires canonical admission")
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if type(budget) is not ExplorationBudget:
            raise TypeError("budget must be an ExplorationBudget")
        attempts: list[ExplorationRun] = []
        seen_candidates: set[str] = set()
        attempt_index = 0
        consecutive_failures = 0
        started = time.monotonic()
        stop_reason = "candidate_sequence_exhausted"
        for candidate in candidates:
            if attempt_index >= budget.max_attempts:
                stop_reason = "budget_max_attempts"
                break
            if time.monotonic() - started >= budget.max_wall_time_s:
                stop_reason = "budget_wall_time"
                break
            if not isinstance(candidate, Mapping):
                raise TypeError("automatic exploration candidates must be mappings")
            candidate_key = canonical_json_hash({"parameters": candidate})
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)
            attempt_index += 1
            request = ExplorationRequest.create(
                source_artifact_id=base_request.source_artifact_id,
                source_content_hash=base_request.source_content_hash,
                technique=base_request.technique,
                executor_id=base_request.executor_id,
                executor_version=base_request.executor_version,
                executor_implementation_hash=base_request.executor_implementation_hash,
                executor_descriptor_hash=base_request.executor_descriptor_hash,
                method_intent=base_request.method_intent,
                parameters=candidate,
                parent_run_id=base_request.parent_run_id,
                canonical_admission=base_request.canonical_admission,
                seed=seed,
                attempt_id=f"attempt-{attempt_index:08d}",
            )
            run = self.runner.run(request)
            attempts.append(run)
            if run.status == "failed":
                consecutive_failures += 1
                if budget.max_consecutive_failures and consecutive_failures >= budget.max_consecutive_failures:
                    stop_reason = "stop_consecutive_failures"
                    break
            else:
                consecutive_failures = 0
            if run.status == "completed" and budget.stop_on_first_completed:
                stop_reason = "stop_first_completed"
                break
        if not attempts:
            raise ValueError("automatic exploration produced no attempts")
        return AutomaticExplorationResult(tuple(attempts), stop_reason, seed, budget.budget_hash)


__all__ = ["AutomaticExplorationResult", "AutomaticExplorationRunner", "ExplorationBudget"]
