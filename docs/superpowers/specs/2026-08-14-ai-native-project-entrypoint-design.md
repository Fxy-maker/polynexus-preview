# AI-Native Project Entrypoint Design

## Decision

Expose `ProjectWorkflowService.analyze_project(question=..., data_scope=())`
as the AI/ARS facade. It discovers files below `raw` when no scope is given,
uses the existing deterministic planner and adapters, runs one or more
same-technique routes, and packages successful/review-bound runs.

The facade returns a JSON-safe `ProjectAnalysisSummary`, not provider internals.
The existing lower-level APIs remain available for debugging and explicit
replay.

## Status projection

- `computation`: `passed` when all selected runs execute, `failed` when a
  provider fails, `blocked` when no valid route can execute.
- `data_quality`: `passed` when no review/limitation signal exists,
  `warning` when evidence is usable but review-bound, `failed` when blocked.
- `publication`: `ready` only for completed evidence without limitations;
  otherwise `review_required`, or `blocked` when no package exists.

The projection is intentionally lossy for user ergonomics but the raw reason
codes, run statuses, and evidence limits remain in the response and package.

## Failure behavior

The facade processes each discovered technique independently. One blocked
technique does not erase usable evidence from another; the summary reports
partial results and package status. It never asks for a technical parameter
unless the existing route cannot proceed without one.
