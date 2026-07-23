"""Pure lifecycle rules for publishing GUI analysis results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RunStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETE = "complete"


@dataclass(frozen=True)
class RunState:
    status: RunStatus = RunStatus.IDLE


def transition_run_state(state: RunState | None, event: object) -> RunState:
    """Return the next lifecycle state without reviving cancelled work."""
    current = state or RunState()
    event_name = str(event or "").strip().lower()
    status = current.status
    if event_name == "start":
        return RunState(RunStatus.RUNNING)
    if event_name == "cancel" and status is RunStatus.RUNNING:
        return RunState(RunStatus.CANCELLING)
    if event_name == "cancelled" and status in {
        RunStatus.RUNNING,
        RunStatus.CANCELLING,
        RunStatus.CANCELLED,
    }:
        return RunState(RunStatus.CANCELLED)
    if event_name == "fail" and status in {RunStatus.RUNNING, RunStatus.CANCELLING}:
        return RunState(
            RunStatus.CANCELLED if status is RunStatus.CANCELLING else RunStatus.FAILED
        )
    if event_name == "complete" and status in {RunStatus.RUNNING, RunStatus.CANCELLING}:
        return RunState(
            RunStatus.CANCELLED if status is RunStatus.CANCELLING else RunStatus.COMPLETE
        )
    return current


def cancellation_requested(state: RunState | None) -> bool:
    return bool(state and state.status in {RunStatus.CANCELLING, RunStatus.CANCELLED})


def should_publish_result(state: RunState | None) -> bool:
    return bool(state and state.status is RunStatus.COMPLETE)


__all__ = [
    "RunState",
    "RunStatus",
    "cancellation_requested",
    "should_publish_result",
    "transition_run_state",
]
