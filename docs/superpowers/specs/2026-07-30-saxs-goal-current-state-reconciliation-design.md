# SAXS goal current-state reconciliation design

## Decision

Use a dated addendum to the existing SAXS quality-program plan as the source
of truth for later evidence. Do not rewrite historical stage records or infer
completion from a task filename, a process exit without a pytest summary, or a
rendered Figure.

## Classification

- `automated-ready`: the linked task card has focused evidence, task-scoped
  checks, and an explicit checkpoint for its contract boundary.
- `contract-ready`: transport and fail-closed behavior are covered, but real
  detector or instrument meaning is not established.
- `open`: the evidence requires a fresh run, restarted-GUI review, real-data
  scientific interpretation, or human release authorization.

The classification is descriptive only. It does not alter quality levels,
physical thresholds, rescue decisions, AI mode, or publication roles.

## Safety boundary

The audit must preserve the distinction between software validation and
scientific acceptance. Existing `Quantitative`, `Trend`, `Diagnostic`, and
`Unusable` evidence remains authoritative; a route index cannot promote it.
