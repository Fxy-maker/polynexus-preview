# Joint workflow task identity acceptance

## Result

The Joint Results Workbench task card now consumes the existing display-only
identity resolver when a Joint report is active. A single report row such as
`PA6-A` is shown as the task source instead of `No data loaded`.

## Boundary

The report payload, persisted project identity, source-run provenance,
diagnostics, metrics, conflict severity, and scientific interpretation are
unchanged. Empty and multi-sample behavior remains delegated to the existing
resolver.

## Evidence

- TDD RED: `1 failed`, with `No data loaded` as the observed source.
- Focused Workspace/Joint/History/Persistence matrix: `41 passed, 177
  deselected in 48.16s`, exit code `0`.
- Structured verifier: exit `0`; quality `287 passed`, preprocessing `106
  passed`, Ruff, compile, type baseline, memory/task, and whitespace checks
  passed. `git diff --check` passed.
- The explicit allowlist checkpoint is the only commit action for this slice.

## Remaining release boundary

This closes a display-state inconsistency only. Restarted-GUI visual review,
Joint conflict interpretation, and final scientific/release approval remain
separate gates.
